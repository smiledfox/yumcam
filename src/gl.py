#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  21 11:35:08 2016

@author: eric
"""
import os
import re
import shutil
import time
import RPi.GPIO

## Hardware configuration
GPIO_CAMERA_USB = 26
GPIO_LED_ONOFF = 19

## Software Configration
RAM_ROOT_PATH_PREFIX = '/ramdisk/'
ROM_ROOT_PATH_PREFIX = '/home/pi/work/yumcam/'

## Processing Folder
# file buffer download from sd-card or camera
CACHE_PATH_PREFIX = RAM_ROOT_PATH_PREFIX + 'cache/'
# file waiting for upload, store in ROM
UPLOAD_PATH_PREFIX = ROM_ROOT_PATH_PREFIX + 'upload/'
# file tag waiting for compress
COMPRESS_PATH_PREFIX = RAM_ROOT_PATH_PREFIX + 'compress/'
# file tag already downloaded
NAMESAVE_PATH_PREFIX = ROM_ROOT_PATH_PREFIX + 'namesave/'

## Variable on flash for cold reboot
SW_VERSION = ROM_ROOT_PATH_PREFIX + 'sw_version'
NOW_DATE_FILE = ROM_ROOT_PATH_PREFIX + 'nowDate'

## Aliyun
ALIYUN_REMOTE_ROOT = 'upload/photos/upload/'
ALIYUN_UPDATE_ROOT = 'upload/photos/uploadupdate/'

##### LED #######
def GPIO_init():
  RPi.GPIO.setwarnings(False)
  RPi.GPIO.setmode(RPi.GPIO.BCM)
  RPi.GPIO.setup(GPIO_CAMERA_USB, RPi.GPIO.OUT)
  RPi.GPIO.setup(GPIO_LED_ONOFF, RPi.GPIO.OUT)
  RPi.GPIO.output(GPIO_LED_ONOFF, RPi.GPIO.LOW)
  RPi.GPIO.output(GPIO_CAMERA_USB, RPi.GPIO.LOW)

def RunLEDOff():
  RPi.GPIO.output(GPIO_LED_ONOFF, RPi.GPIO.LOW)

def blinkRunLED():
  # LED Blink
  gpioValue = RPi.GPIO.input(GPIO_LED_ONOFF)
  RPi.GPIO.output(GPIO_LED_ONOFF, (not gpioValue))

def shortBlinkRunLED():
  # LED Blink
  gpioValue = RPi.GPIO.input(GPIO_LED_ONOFF)
  RPi.GPIO.output(GPIO_LED_ONOFF, (not gpioValue))
  time.sleep(0.2)
  RPi.GPIO.output(GPIO_LED_ONOFF, (gpioValue))

def configRunLED(status):
  if status == 0:
    RPi.GPIO.output(GPIO_LED_ONOFF, RPi.GPIO.LOW)
  else:
    RPi.GPIO.output(GPIO_LED_ONOFF, RPi.GPIO.HIGH)

## Get MAC address on ETH0
def get_mac_address(): 
  macAddress = ''
  ## Get devices eth0 mac address
  mac_pattern = re.compile(r'[\w|:]+')
  mac_matchs = mac_pattern.findall(os.popen("cat /sys/class/net/eth0/address").read())
  for mac_match in mac_matchs:
    macAddress = mac_match
    break
  macAddress = macAddress.replace(':','')
  return macAddress

def get_software_version():
  version_num = '0.0'
  try:
    if os.path.exists(SW_VERSION):
      f = open(SW_VERSION, "r")
      line = f.readline()
      if line:
        version_num = line
        pattern = re.compile(r'.+')
        matchs = pattern.findall(version_num)
        for match in matchs:
          version_num = match
          break
      f.close()
  except:
    print "version_num failed"
  return version_num

## File Read action
def fileRead(filePtr):
  all_the_text = ''
  if os.path.exists(filePtr):
    file_object = open(filePtr)
    try:
      all_the_text = file_object.read( )
      all_the_text = all_the_text.strip('\n')
    finally:
      file_object.close( )
  return all_the_text

## File Write action
def fileWrite(filePtr, text):
  if not os.path.exists(os.path.dirname(filePtr)):
    os.makedirs(folderPath)
  file_object = open(filePtr, 'w')
  try:
    file_object.write(text)
  finally:
    file_object.close( )

def fileWriteAppend(filePtr, text):
  if not os.path.exists(os.path.dirname(filePtr)):
    os.makedirs(folderPath)
  file_object = open(filePtr, 'a')
  try:
    file_object.write(text+'\n')
  finally:
    file_object.close( )

##### VARIABLE ####
IMAGES_DOWNLOAD_FILE = ROM_ROOT_PATH_PREFIX + 'imagesDownloadCnt'
IMAGES_UPLOAD_FILE = ROM_ROOT_PATH_PREFIX + 'imagesUploadCnt'
## Temp variable
CONNECTED_FILE = RAM_ROOT_PATH_PREFIX + 'connected'
TIMESTAMPS_FILE = RAM_ROOT_PATH_PREFIX + 'timestamps'
IMAGES_REMAIN_FILE = RAM_ROOT_PATH_PREFIX + 'remain'

def set_connected(connected):
  if connected == 0:
    if os.path.exists(CONNECTED_FILE):
      os.remove(CONNECTED_FILE)
  else:
    if not os.path.exists(CONNECTED_FILE):
      os.mknod(CONNECTED_FILE)

def set_downloadCnt(downloadCnt):
  fileWrite(IMAGES_DOWNLOAD_FILE, str(downloadCnt))

def set_uploadCnt(uploadCnt):
  fileWrite(IMAGES_UPLOAD_FILE, str(uploadCnt))

def set_timestamps(timestamps):
  fileWrite(TIMESTAMPS_FILE, timestamps)

def set_remainCnt(remainCnt):
  fileWrite(IMAGES_REMAIN_FILE, str(remainCnt))

def get_connected():
  if os.path.exists(CONNECTED_FILE):
    return 1
  else:
    return 0

def get_downloadCnt():
  if os.path.exists(IMAGES_DOWNLOAD_FILE):
    return int(fileRead(IMAGES_DOWNLOAD_FILE))
  else:
    return 0

def get_uploadCnt():
  if os.path.exists(IMAGES_UPLOAD_FILE):
    return int(fileRead(IMAGES_UPLOAD_FILE))
  else:
    return 0

def get_timestamps():
  return fileRead(TIMESTAMPS_FILE)

def get_remainCnt():
  if os.path.exists(IMAGES_REMAIN_FILE):
    return int(fileRead(IMAGES_REMAIN_FILE))
  else:
    return 0

###############CAMERA API######################
# Auto detect the camera is connect or not
'''
def detectCameraType():
  cameraType = ''
  retString = os.popen('gphoto2  --auto-detect').read()
  pattern = re.compile(r'.+\n')
  matchs = pattern.findall(retString)
  for match in matchs:
    if match.find("usb") != -1:
      cameraType = match
      break
  return cameraType

# Detect camera SN
def detectCameraSN():
  cameraSN = ''
  retString = os.popen('gphoto2 --summary').read()
  pattern = re.compile(r'Serial Number:.+')
  matchs = pattern.findall(retString)
  if len(matchs) != 0:
    cameraSN = matchs[0]
  return cameraSN
'''
