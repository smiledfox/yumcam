#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  21 11:35:08 2016

@author: eric
"""
import os
import re
import time
import string
import urllib2

############################
ROOT_PATH_PREFIX    = '/home/pi/work/yumcam/'
UPGRADE_PATH_PREFIX = ROOT_PATH_PREFIX + 'upgrade/'
APP_PATH            = ROOT_PATH_PREFIX + 'yumcam.pyc'

############################Main Function############################
# start up script
if os.path.exists('/boot/startupbackdoor.sh'):
  os.system('sudo /boot/startupbackdoor.sh')
  os.system('sudo rm /boot/startupbackdoor.sh')
######################## init cold ########################
## Wait until ethernet connection up
newversion_num = ''
versionURL = "http://client.chinarun.com/html/api/living.ashx?method=getversion"
time.sleep(5)
try:
  maxWaitInterval = 120
  startUpTime = time.time()
  while True:
    maxWaitInterval -= 1
    image_content = ''
    try:
      image_content = urllib2.urlopen(versionURL, timeout=10).read()
    except:
      print "get newversion_num failed"
    if len(image_content) >= 4:
      newversion_num = image_content
      print "...Network Test PASS..."
      break
    time.sleep(1)
    # Check timeout
    if (time.time() - startUpTime) > 120.0 or maxWaitInterval == 0:
      print "...Network Test FAILED..."
      break
except:
  print "...Network Test FAILED..."
## Upgrade to the last version if avaliable
# get the upgrade file from remote
if not os.path.exists(UPGRADE_PATH_PREFIX):
  os.system("mkdir -vp " + UPGRADE_PATH_PREFIX)
os.system("rm -rf " + UPGRADE_PATH_PREFIX + '*')
#
fileURL = "http://client.chinarun.com/html/api/living.ashx?method=getupdatefile"
oldversion_num = ''
try:
  if os.path.exists(ROOT_PATH_PREFIX + 'sw_version'):
    f = open(ROOT_PATH_PREFIX+"sw_version", "r")
    line = f.readline()
    if line:
      oldversion_num = line
    f.close()
  print 'old ' + oldversion_num
except:
  print "readline failed"
if newversion_num != '' and newversion_num != oldversion_num:
  # do upgrade
  print ".............Upgrade Start............."
  try:
    os.system('cd ' + UPGRADE_PATH_PREFIX + ' && wget -O upgrade.tar.gz ' + fileURL)
    os.system('sync')
    tarResponse = os.system("tar xvf " + UPGRADE_PATH_PREFIX + "upgrade.tar.gz -C " + UPGRADE_PATH_PREFIX)
    if tarResponse == 0:
      if os.path.exists(UPGRADE_PATH_PREFIX + 'upgrade.sh'):
        os.system('cd ' + UPGRADE_PATH_PREFIX + ' && sudo ./upgrade.sh')
    os.system('sync')
    print ".............Upgrade Done............."
  except:
    print "Download upgrade zip failed"
# Start up
os.system('python ' + APP_PATH + '&')

