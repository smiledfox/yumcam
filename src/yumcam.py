#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  21 11:35:08 2016

@author: eric
"""
import os
import re
import statvfs
import time, datetime
import shutil
import signal
import oss2
import gl

USB_MOUNT_DIR = "/media/"
USBTYPE_NONE = 0
USBTYPE_SDCARD = 1
USBTYPE_DSLR = 2
##
'''
os.statvfs(path)
  •	f_bsize − preferred file system block size.
  •	f_frsize − fundamental file system block size.
  •	f_blocks − total number of blocks in the filesystem.
  •	f_bfree − total number of free blocks.
  •	f_bavail − free blocks available to non-super user.
  •	f_files − total number of file nodes.
  •	f_ffree − total number of free file nodes.
  •	f_favail − free nodes available to non-super user.
  •	f_flag − system dependent.
  •	f_namemax − maximum file name length.
posix.statvfs_result(f_bsize=4096, f_frsize=4096, f_blocks=7638277L, f_bfree=5164231L, f_bavail=4841077L, f_files=1923040L, f_ffree=1734745L, f_favail=1734745L, f_flag=1024, f_namemax=255)
'''
# Get current free RAM disk size
def getDiskFreeSize(diskPath):
  size = 0
  try:
    vfs=os.statvfs(diskPath)
    size = vfs[statvfs.F_BAVAIL]*vfs[statvfs.F_BSIZE]/1024
    #print "free RAM: " + str(size) + "k"
  except:
    print "getFreeRAMDiskSize Failed"
  return size

# Get file size
'''
import os
import statvfs
os.statvfs(diskPath)[statvfs.F_BLOCKS] - os.statvfs(diskPath)[statvfs.F_BAVAIL]
'''

## USB devices detection
'''
sudo lsusb
#Default Devices:
Bus 001 Device 006: ID 12d1:14db Huawei Technologies Co., Ltd.
Bus 001 Device 100: ID 12d1:14dc Huawei Technologies Co., Ltd. (BAD SINGAL with UNI)
Bus 001 Device 033: ID 12d1:1f01 Huawei Technologies Co., Ltd. (GOOD SINGAL with UNI)
Bus 001 Device 003: ID 0424:ec00 Standard Microsystems Corp. SMSC9512/9514 Fast Ethernet Adapter
Bus 001 Device 002: ID 0424:9514 Standard Microsystems Corp.
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
#Offical support SD card:
Bus 001 Device 004: ID 0bda:0309 Realtek Semiconductor Corp. 
#DSLR:
Bus 001 Device 027: ID 04b0:0428 Nikon Corp.

sudo /bin/mkdir -p /media/sda1
sudo /bin/mount /dev/sda1 /media/sda1
'''
# 0: No devices detectd
# 1: Realtek sd card reader detected
# 2: DSLR detected
'''
  http://www.linux-usb.org/usb.ids
  04a9  Canon, Inc.
  04b0  Nikon Corp.
  054c  Sony Corp.
  05ca  Ricoh Co., Ltd
'''
USB_DEV_SYSTEM = ["12d1:14db", "12d1:14dc", "12d1:1f01", "0424:ec00", "0424:9514", "1d6b:0002"]
USB_DEV_SDCARD = ["0bda:0184", "0bda:0186", "0bda:0301", "0bda:0307", "0bda:0309", "0bda:0326"]
USB_DEV_DSLR_VENDOR_ID = ["04a9", "04b0", "054c", "05ca"]

def usbDevicesTypeDetected():
  devicesType = 0
  retString = os.popen("sudo lsusb").read()
  pattern = re.compile(r': ID (\w+:\w+).+')
  infoList = pattern.findall(retString)
  for info in infoList:
    vendorID = ''
    deviceID = ''
    pattern = re.compile(r'(\w+):(\w+).+')
    devicesInfo = pattern.findall(retString)
    if len(devicesInfo) > 0:
      vendorID = devicesInfo[0][0]
      deviceID  = devicesInfo[0][1]
    if info not in USB_DEV_SYSTEM:
      if info in USB_DEV_SDCARD:
        devicesType = 1
      elif vendorID in USB_DEV_DSLR_VENDOR_ID:
        devicesType = 2
      else:
        devicesType = 1 # = 2 in the futher
      break
  return devicesType

# /dev/sda1 /media/sda1
def attachDevice(device, folder):
  print 'sudo /bin/mkdir -p ' + folder
  os.popen('sudo /bin/mkdir -p ' + folder).read()
  print 'sudo /bin/mount '+ device + ' ' + folder
  os.popen('sudo /bin/mount '+ device + ' ' + folder).read()

def disAttachDevice(folder):
  print 'sudo /bin/umount -l ' + folder
  os.popen('sudo /bin/umount -l ' + folder).read()
  print 'sudo rm -rf '+ folder
  os.popen('sudo rm -rf '+ folder).read()

# Auto mount or umount usb devices depends on the connection
'''
sudo blkid
  /dev/mmcblk0p1: SEC_TYPE="msdos" LABEL="boot" UUID="22E0-C711" TYPE="vfat" PARTUUID="fce41fa8-01"
  /dev/mmcblk0p2: UUID="202638e1-4ce4-45df-9a00-ad725c2537bb" TYPE="ext4" PARTUUID="fce41fa8-02"
  /dev/sda1: LABEL="NIKON D7000" UUID="4A9E-5664" TYPE="exfat"
  /dev/mmcblk0: PTUUID="fce41fa8" PTTYPE="dos"
'''
def autoMountUsbStoageDevices():
  retString = os.popen("sudo blkid").read()
  pattern = re.compile(r'/dev/(sd\w+).+TYPE="(\w+)')
  infoList = pattern.findall(retString)
  #Get partitionList
  partitionList = []
  for info in infoList:
    partitionList.append(info[0])
  #Remove unused partition
  folderlist = os.listdir(USB_MOUNT_DIR)
  for folder in folderlist:
    folderPath = os.path.join(USB_MOUNT_DIR, folder)
    if os.path.isdir(folderPath):
      if folder not in partitionList:
        disAttachDevice(folderPath)
  #Add new partition
  for info in infoList:
    folderPath = os.path.join(USB_MOUNT_DIR, info[0])
    if not os.path.exists(folderPath):
      attachDevice(('/dev/'+info[0]), folderPath)

# Unmount all usb storage devices
def umountAllUsbStorageDevices():
  folderlist = os.listdir(USB_MOUNT_DIR)
  for folder in folderlist:
    filepath = os.path.join(USB_MOUNT_DIR, folder)
    if os.path.isdir(filepath):
      disAttachDevice(filepath)

############DSLR download#########
# Auto download camera photo
#gphoto2 --set-config=capturetarget=card
def cameraDownloadProcess():
  print "gphoto2 process start"
  try:
    retString = os.popen("gphoto2 --auto-detect").read()
    pattern = re.compile(r'usb:\d+')
    matchs = pattern.findall(retString)
    if len(matchs) != 0:
      os.system("cd " + gl.CACHE_PATH_PREFIX + " && gphoto2 --set-config=capturetarget=card --wait-event-and-download --keep")
  except:
    print "Error... DSLR disconnected"
    gl.RunLEDOff()
    time.sleep(5)

############sd-card download#########
# check previous download state
def isPreviousDownloaed(namesavePath, folder, size):
  sizeHit = 0
  if os.path.exists(namesavePath):
    fileText = gl.fileRead(namesavePath)
    pattern = re.compile(r'(\w+)')
    stringList = pattern.findall(fileText)
    nameString = folder+size
    if nameString in stringList:
      sizeHit = 1
  return sizeHit

def appendDownloadFLag(namesavePath, folder, size):
  gl.fileWriteAppend(namesavePath, folder+size)

# file copy
def sdCardDownloadProcess_fileCopy(sourcePath, folder):
  basename = os.path.basename(sourcePath)
  cachePath = os.path.join(gl.CACHE_PATH_PREFIX, basename)
  namesavePath = os.path.join(gl.NAMESAVE_PATH_PREFIX, basename)
  size = str(os.path.getsize(sourcePath))
  if not isPreviousDownloaed(namesavePath, folder, size):
    print " task %s download from sdcard %s" % ("main",sourcePath)
    # Wait unitl free RAM space avaliable
    while True:
      if getDiskFreeSize(gl.RAM_ROOT_PATH_PREFIX) > 50000:#50,000K
        break
      time.sleep(1)
    shutil.copy(sourcePath, cachePath)
    appendDownloadFLag(namesavePath, folder, size)

# Download all sd-card process
def sdCardDownloadProcess():
  downloadComplete = 1
  try:
    # usb connection check
    usbConnectType = 1
    #Get file list
    sdCardFolderlist = os.listdir(USB_MOUNT_DIR)
    for sdcard in sdCardFolderlist:
      if usbConnectType != 1:
        break
      usb_path = os.path.join(USB_MOUNT_DIR, sdcard)
      if not os.path.isdir(usb_path):
        continue
      #print usb_path
      dcimPath = os.path.join(usb_path, "DCIM")
      if not os.path.isdir(dcimPath):
        continue
      #print dcimPath
      dcimFolderList = os.listdir(dcimPath)
      for folder in dcimFolderList:
        if usbConnectType != 1:
          break
        try:
          imageFolderPath = os.path.join(dcimPath, folder)
          if not os.path.isdir(imageFolderPath):
            continue
          fileList = os.listdir(imageFolderPath)
          for filename in fileList:
            try:
              (shotname,extension) = os.path.splitext(filename)
              if extension == '.JPG' or extension == '.jpg':
                imagepath = os.path.join(imageFolderPath, filename)
                sdCardDownloadProcess_fileCopy(imagepath, folder)
            except:
              downloadComplete = 0
              print "Error sdCardDownloadProcess file " + filename + " exception"
              usbConnectType = usbDevicesTypeDetected()
              if usbConnectType != 1:
                break
        except:
          downloadComplete = 0
          print "Error sdCardDownloadProcess folder " + folder + " exception"
          if usbDevicesTypeDetected() != 1:
            break
  except:
    downloadComplete = 0
    print "Error sdCardDownloadProcess base exception"
  print "... Congratulations! sd-card download complete"
  return downloadComplete

#############################################
## Check NTP synchronized
## aliyunConnectionStaus
def aliyunConnectionStaus():
  connectionStatus = 0
  bucket = oss2.Bucket(oss2.Auth(os.getenv('OSS2_ACCESS_KEY_ID'), os.getenv('OSS2_ACCESS_KEY_SECRET')), 'http://oss-cn-qingdao.aliyuncs.com', 'runffphoto')
  try:
    if bucket.object_exists('upload/photos/uploadupdate/sw_version.txt') == True:
      connectionStatus = 1
  except:
    print "aliyunConnectionStaus Failed"
  return connectionStatus

## Wait until NTP sync
def waitUntilNTPSync():
  os.system("sudo service ntp restart")
  ## Wait until time sync correctly
  ntpSyncRetryCount = 0
  while True:
    time.sleep(1)
    gl.shortBlinkRunLED()
    if aliyunConnectionStaus() == 1:
      break
    ntpSyncRetryCount += 1
    if ntpSyncRetryCount > 1000:
      print "waitUntilTimeSync, restart board"
      os.system("sudo reboot")

## Delete overtime JPG
def overtimeFilesDeleted():
  nowDate = str(datetime.date.today())[0:10]
  nowDataLast = gl.fileRead(gl.NOW_DATE_FILE)
  if len(nowDataLast) == 0 or nowDate != nowDataLast:
    os.system("sudo rm -rf " + gl.NAMESAVE_PATH_PREFIX)
    os.mkdir(gl.NAMESAVE_PATH_PREFIX)
    os.system("sudo chown -R pi:pi " + gl.NAMESAVE_PATH_PREFIX)
    os.system("sudo rm -rf " + gl.UPLOAD_PATH_PREFIX)
    os.mkdir(gl.UPLOAD_PATH_PREFIX)
    os.system("sudo chown -R pi:pi " + gl.UPLOAD_PATH_PREFIX)
    gl.set_downloadCnt(0)
    gl.set_uploadCnt(0)
    print "... PASS delete overtime files ..."
  gl.fileWrite(gl.NOW_DATE_FILE, nowDate)
  if not os.path.exists(gl.IMAGES_DOWNLOAD_FILE):
    gl.set_downloadCnt(0)
  if not os.path.exists(gl.IMAGES_UPLOAD_FILE):
    gl.set_uploadCnt(0)

## Initiazion
def init_cold():
  ## Hw init
  print "... H/W init ..."
  gl.GPIO_init()
  ## SW init
  os.system("sudo rm -rf " + gl.RAM_ROOT_PATH_PREFIX+"*")
  if not os.path.exists(gl.CACHE_PATH_PREFIX):
    os.mkdir(gl.CACHE_PATH_PREFIX)
    os.system("sudo chown -R pi:pi " + gl.CACHE_PATH_PREFIX)
  if not os.path.exists(gl.COMPRESS_PATH_PREFIX):
    os.mkdir(gl.COMPRESS_PATH_PREFIX)
    os.system("sudo chown -R pi:pi " + gl.COMPRESS_PATH_PREFIX)
  if not os.path.exists(gl.UPLOAD_PATH_PREFIX):
    os.mkdir(gl.UPLOAD_PATH_PREFIX)
    os.system("sudo chown -R pi:pi " + gl.UPLOAD_PATH_PREFIX)
  if not os.path.exists(gl.NAMESAVE_PATH_PREFIX):
    os.mkdir(gl.NAMESAVE_PATH_PREFIX)
    os.system("sudo chown -R pi:pi " + gl.NAMESAVE_PATH_PREFIX)
  gl.set_connected(0)
  waitUntilNTPSync()
  print "... PASS NTP Synchronize..."
  overtimeFilesDeleted()

def subProcessStart():
  mainPath = gl.ROM_ROOT_PATH_PREFIX + 'yumcam.py'
  compressPath = gl.ROM_ROOT_PATH_PREFIX + 'yumcam_compress.py'
  aliyunPath = gl.ROM_ROOT_PATH_PREFIX + 'yumcam_aliyun_upload.py'
  reporterPath = gl.ROM_ROOT_PATH_PREFIX + 'yumcam_report.py'
  networkPath = gl.ROM_ROOT_PATH_PREFIX + 'yumcam_network.py'
  if os.path.exists(mainPath):
    os.system('python -m py_compile ' + mainPath)
    os.system('rm -f ' + mainPath)
  if os.path.exists(compressPath):
    os.system('python -m py_compile ' + compressPath)
    os.system('rm -f ' + compressPath)
  if os.path.exists(aliyunPath):
    os.system('python -m py_compile ' + aliyunPath)
    os.system('rm -f ' + aliyunPath)
  if os.path.exists(reporterPath):
    os.system('python -m py_compile ' + reporterPath)
    os.system('rm -f ' + reporterPath)
  if os.path.exists(networkPath):
    os.system('python -m py_compile ' + networkPath)
    os.system('rm -f ' + networkPath)
  os.system('python ' + compressPath + 'c &')
  os.system('python ' + aliyunPath + 'c &')
  os.system('python ' + reporterPath + 'c &')
  os.system('python ' + networkPath + 'c &')

## main function
def main_func():
  ######################## init cold ########################
  init_cold()
  # Move to the "sudo nano /etc/local" mount -t tmpfs -o size=600m,mode=0777 tmpfs /ramdisk
  ######################## Daemon thread ########################
  subProcessStart()
  downloadMaxRetryCnt = 2
  while True:
    try:
      type = usbDevicesTypeDetected()
      gl.set_connected(type)
      gl.configRunLED(type)
      print '... USB devices detected: ' + str(type)
      time.sleep(5) # Wait until devices ready, some devices such as NIKON D810, has very slow response
      # Main function, download the photo from deives (sd-card or DSLR)
      if type == USBTYPE_NONE:
        downloadMaxRetryCnt = 2
      elif type == USBTYPE_SDCARD:
        if downloadMaxRetryCnt > 0:
          gl.set_timestamps(str(int(time.time())))
          umountAllUsbStorageDevices()
          autoMountUsbStoageDevices()
          if sdCardDownloadProcess() == 0:
            downloadMaxRetryCnt = downloadMaxRetryCnt - 1
          else:
            downloadMaxRetryCnt = 0
      elif type == USBTYPE_DSLR:
        umountAllUsbStorageDevices()
        cameraDownloadProcess()
        downloadMaxRetryCnt = 2
        umountAllUsbStorageDevices()
    except:
      print "... Main function exception ..."
      time.sleep(1)

###
if __name__== '__main__':
    main_func()


