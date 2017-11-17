#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  21 11:35:08 2016

@author: eric
"""

import os
import re
import oss2
import time
import string
import threading
import Queue
import copy
import RPi.GPIO
import gl

#
## Aliyun Configration
ALIYUN_UPLOAD_PROCESS = 16

''' Aliyun process
  import oss2
  bucket = oss2.Bucket(oss2.Auth(os.getenv('OSS2_ACCESS_KEY_ID'), os.getenv('OSS2_ACCESS_KEY_SECRET')), 'http://oss-cn-qingdao.aliyuncs.com', 'runffphoto')
  resp = bucket.object_exists('upload/photos/upload/')
  bucket.list_objects('upload/photos/upload/')
'''

# global debug info
imagesUploadCnt = 0
cnt_mutex = threading.Lock()
aliyun_mutex = threading.Lock()
processingFileList = []

##
class aliyunUploadThread(threading.Thread): 
  def __init__(self, aliyunQueue, thread_num):
    threading.Thread.__init__(self)
    self.thread_num = str(thread_num)
    self.aliyunQueue = aliyunQueue
    self.macAddress = gl.get_mac_address() ## Get Mac address
    self.thread_stop = False
    print "aliyunUploadAction thread #" + self.thread_num + " start"

  def aliyunUploadAction(self, filename):
    global imagesUploadCnt, cnt_mutex, processingFileList
    try:
      bucket = oss2.Bucket(oss2.Auth(os.getenv('OSS2_ACCESS_KEY_ID'), os.getenv('OSS2_ACCESS_KEY_SECRET')), 'http://oss-cn-qingdao.aliyuncs.com', 'runffphoto')
      localFilepath = os.path.join(gl.UPLOAD_PATH_PREFIX, filename)
      if os.path.exists(localFilepath):
        remoteFilepath = os.path.join(gl.ALIYUN_REMOTE_ROOT, self.macAddress)
        remoteFilepath = os.path.join(remoteFilepath, filename)
        remoteFilepath = remoteFilepath.lower()
        response = bucket.put_object_from_file(remoteFilepath, localFilepath)
        print remoteFilepath
        if response.status == 200:
          print " thread a#%s %s aliyun uploaded %s" % (self.thread_num, str(response.status), filename)
          os.remove(localFilepath)
          if cnt_mutex.acquire():
            imagesUploadCnt += 1
            cnt_mutex.release()
        else:
          time.sleep(10)
      if cnt_mutex.acquire():
        processingFileList.remove(filename)
        cnt_mutex.release()
    except:
      time.sleep(1)
      print "aliyunUploadAction exception on thread #" + self.thread_num

  def run(self):
    global aliyun_mutex
    while True:
      try:
        aliyun_mutex.acquire()
        if not self.aliyunQueue.empty():
          filename = self.aliyunQueue.get()
          aliyun_mutex.release()
          #print " thread #%s processing %s" % (self.thread_num, filename)
          self.aliyunUploadAction(filename)
        else:
          aliyun_mutex.release()
          time.sleep(5)
      except:
        print "Error ... aliyunUploadThread run exception on thread #" + self.thread_num
        time.sleep(1)

##
def main_func():
  global imagesUploadCnt, cnt_mutex, aliyun_mutex, processingFileList
  RPi.GPIO.setwarnings(False)
  RPi.GPIO.setmode(RPi.GPIO.BCM)
  RPi.GPIO.setup(gl.GPIO_CAMERA_USB, RPi.GPIO.OUT)
  RPi.GPIO.setup(gl.GPIO_LED_ONOFF, RPi.GPIO.OUT)
  # Data
  aliyunQueue = Queue.Queue(100000)
  # initiaze the multi upload thread
  for i in range(0, ALIYUN_UPLOAD_PROCESS):
    aliyunUpload = aliyunUploadThread(aliyunQueue, i)
    aliyunUpload.setDaemon(True)
    aliyunUpload.start()
  # main loop
  imagesUploadCnt = gl.get_uploadCnt()
  lastImagesUploadCnt = imagesUploadCnt
  #
  while True:
    try:
      # Update counter
      if lastImagesUploadCnt != imagesUploadCnt:
        gl.set_uploadCnt(imagesUploadCnt)
        lastImagesUploadCnt = imagesUploadCnt
      gl.set_remainCnt(len(processingFileList))
      # Check the queue over max size
      if aliyunQueue.qsize() > ALIYUN_UPLOAD_PROCESS*20:
        time.sleep(10)
        continue
      # Save power when file list
      aliyunFilelist = os.listdir(gl.UPLOAD_PATH_PREFIX)
      if len(aliyunFilelist) == 0:
        processingFileList = []
        time.sleep(10)
        continue
      os.system('sync') # Force write file from cache to file system
      gl.shortBlinkRunLED()
      time.sleep(5)
      # Inqueue the new file
      for filename in aliyunFilelist:
        (shotname,extension) = os.path.splitext(filename)
        if extension != '.JPG' and extension != '.jpg':
          continue
        if filename in processingFileList:
          continue
        if aliyun_mutex.acquire():
          aliyunQueue.put(filename)
          aliyun_mutex.release()
        if cnt_mutex.acquire():
          processingFileList.append(filename)
          cnt_mutex.release()
    except:
      print "Error ... yumcam_aliyun_upload.py failed"

###
if __name__== '__main__':
    main_func()

