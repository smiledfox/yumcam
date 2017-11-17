#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  21 11:35:08 2016

@author: eric
Comments:
  1: Move the candidate file into compress queue
  2: Compress the images in multi processes.
  3: Save the output file in upload folder
"""

import os
import re
import multiprocessing
from multiprocessing import Process, Queue, Lock
import string
import time
import shutil
import Image
import pyexiv2
import hashlib
import md5
import RPi.GPIO
import gl

## PROCESS
IMAGES_COMPRESS_PROCESS = 4

####################################
# Get thermal exeed the safe threshold
# pi@raspberrypi:~ $ cat /sys/class/thermal/thermal_zone0/temp
# 50464
def getThremalOverHeat(thermalCurrentThreshold):
  temperature = 0
  retString = os.popen("cat /sys/class/thermal/thermal_zone0/temp").read()
  if retString.isdigit() == True:
    temperature = int(retString)
  return (temperature > thermalCurrentThreshold)

####################################
class imagesCompressActionProcess(multiprocessing.Process):
  def __init__(self, compressQueue, compressLock, process_num):
    multiprocessing.Process.__init__(self)
    self.process_num = str(process_num)
    self.compressQueue = compressQueue
    self.compressLock = compressLock
    print " task #" + self.process_num + " start"

  def caculateFileMD5(self, path):
    m = hashlib.md5()
    a_file = open(path, 'rb')
    m.update(a_file.read())
    a_file.close()
    md5value = m.hexdigest()
    return md5value

  def compressImage(self, sourcePath, destPath):
    newH = 0
    newW = 0
    image = Image.open(sourcePath)
    w, h = image.size
    if w < h:
      newW = 1080
      newH = newW*h/w
    else:
      newH = 1080
      newW = newH*w/h
    # http://effbot.org/imagingbook/image.htm NEAREST, BILINEAR, BICUBIC, ANTIALIAS
    image = image.resize((newW, newH), Image.NEAREST)
    os.remove(sourcePath)
    if os.path.exists(destPath):
      os.remove(destPath)
    image.save(destPath, 'JPEG')
    return (newH, newW)

  def compressAction(self, filename):
    sourcePath = os.path.join(gl.CACHE_PATH_PREFIX, filename)
    labelPath = os.path.join(gl.COMPRESS_PATH_PREFIX, filename)
    try:
      #print " task c#%s converting %s" % (self.process_num, filename)
      # cacalute source image size, md5, metadata
      filesize = os.path.getsize(sourcePath)
      #print " task c#%s size done %s" % (self.process_num, filename)
      md5string = self.caculateFileMD5(sourcePath)
      #print " task c#%s md5 done %s" % (self.process_num, filename)
      source_metadata = pyexiv2.ImageMetadata(sourcePath)
      source_metadata.read()
      uploadPath = os.path.join(gl.UPLOAD_PATH_PREFIX, gl.get_timestamps() + '_' + os.path.splitext(filename)[0] + '_' + str(filesize) + '_' + md5string + os.path.splitext(filename)[1])
      uploadPath = uploadPath.lower()
      #print " task c#%s metadata done %s" % (self.process_num, filename)
      # compress source file
      (newW, newH) = self.compressImage(sourcePath, uploadPath)
      # copy EXIF data
      dest_metadata = pyexiv2.ImageMetadata(uploadPath)
      dest_metadata.read()
      source_metadata.copy(dest_metadata)
      # set EXIF image size info to resized size
      dest_metadata["Exif.Photo.PixelXDimension"] = newW
      dest_metadata["Exif.Photo.PixelYDimension"] = newH
      dest_metadata.write()
      gl.blinkRunLED()
      print " task c#%s compress done %s" % (self.process_num, os.path.basename(uploadPath))
    except:
      print "Error ... compressAction " + filename + " exception on task #" + self.process_num
      time.sleep(1)
    # Empty the temp file
    if os.path.exists(sourcePath):
      os.remove(sourcePath)
    if os.path.exists(labelPath):
      os.remove(labelPath)

  def run(self):
    while True:
      try:
        self.compressLock.acquire()
        if not self.compressQueue.empty():
          filename = self.compressQueue.get()
          self.compressLock.release()
          if filename == "exit":
            print " task #%s exit" % (self.process_num)
            break
          else:
            #print " task #%s processing %s" % (self.process_num, filename)
            self.compressAction(filename)
        else:
          self.compressLock.release()
          time.sleep(5)
      except:
        print "Error ... imagesCompressActionProcess run exception on task #" + self.process_num
        time.sleep(1)

####################################
# Check file compress timeout
def checkCompressTimeout(labelPath, threshold):
  timeout = True
  retString = gl.fileRead(labelPath)
  if retString.isdigit() == True:
    inQueueTimeStamps = int(retString)
    elapsedSeconds = int(time.time()) - inQueueTimeStamps
    #print str(elapsedSeconds) + " " + str(threshold)
    if elapsedSeconds < threshold:
      timeout = False
  return timeout

#
def main_func():
  # HW Init
  RPi.GPIO.setwarnings(False)
  RPi.GPIO.setmode(RPi.GPIO.BCM)
  RPi.GPIO.setup(gl.GPIO_CAMERA_USB, RPi.GPIO.OUT)
  RPi.GPIO.setup(gl.GPIO_LED_ONOFF, RPi.GPIO.OUT)
  # Data Init
  compressQueue = Queue(10000)
  compressLock = Lock()
  imagesDownloadCnt = gl.get_downloadCnt()
  lastImagesDownloadCnt = imagesDownloadCnt
  gl.set_timestamps(str(int(time.time())))
  os.system("rm -rf " + gl.COMPRESS_PATH_PREFIX + "*")
  # initiaze the multi compress process
  cpList = []
  for i in range(0, IMAGES_COMPRESS_PROCESS):
    compressProcess = imagesCompressActionProcess(compressQueue, compressLock, i)
    compressProcess.daemon = True
    compressProcess.start()
    cpList.append(compressProcess)
  # Loop
  while True:
    try:
      # Wait until heat c<80
      if getThremalOverHeat(80000) == True:
        print "Warning ... thremal over heat"
        time.sleep(5)
        continue
      compressFilelist = os.listdir(gl.CACHE_PATH_PREFIX)
      if len(compressFilelist) == 0:
        time.sleep(10)
        continue
      os.system('sync') # Force write file from cache to file system
      time.sleep(3)
      # Push the compress candidate images in queue
      for filename in compressFilelist:
        sourcePath = os.path.join(gl.CACHE_PATH_PREFIX, filename)
        if not os.path.exists(sourcePath):
          continue
        labelPath = os.path.join(gl.COMPRESS_PATH_PREFIX, filename)
        (shotname,extension) = os.path.splitext(filename)
        if extension == '.JPG' or extension == '.jpg':
          if not os.path.exists(labelPath):
            #print " task c# inqueue " + filename
            compressLock.acquire()
            compressQueue.put(filename)
            compressLock.release()
            # Add file label
            gl.fileWrite(labelPath, str(int(time.time())))
            imagesDownloadCnt += 1
          elif checkCompressTimeout(labelPath, 240):
            print "file timeout " + filename
            if os.path.exists(sourcePath):
              os.remove(sourcePath)
            os.remove(labelPath)
        else:
          os.remove(sourcePath)
      # update the timestamps every 10000 files downloaded
      if lastImagesDownloadCnt != imagesDownloadCnt:
        gl.set_downloadCnt(imagesDownloadCnt)
        if imagesDownloadCnt/9000 != lastImagesDownloadCnt/9000:
          gl.set_timestamps(str(int(time.time())))
        lastImagesDownloadCnt = imagesDownloadCnt
    except:
      print "Error ... images copy exception"
      time.sleep(5)

if __name__== '__main__':
    main_func()
