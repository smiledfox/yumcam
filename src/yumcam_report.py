#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  21 11:35:08 2016

@author: eric
"""
import os
import re
import threading
import time, datetime
import oss2
import hashlib
import md5
import random
import io
import RPi.GPIO
import urllib2
import collections
try:
  import simplejson
except:
  print 'install simplejson failed '
import urllib2
import gl

'''
downloadcount : The succesful download count, means the image has already processed.
uploadingcount : The images already in the queue, but not process yet.
'''

####################################
def main_func():
  startUpTime = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime()) 
  ## Get Mac address
  macAddress = gl.get_mac_address()
  version_num = gl.get_software_version()
  ## Upload files to aliyun
  bucket = oss2.Bucket(oss2.Auth(os.getenv('OSS2_ACCESS_KEY_ID'), os.getenv('OSS2_ACCESS_KEY_SECRET')), 'http://oss-cn-qingdao.aliyuncs.com', 'runffphoto')
  uploadAliyunInterval = 0
  while True:
    try:
      # Generate path
      connect_status_str = str(gl.get_connected())
      download_cnt_str = str(gl.get_downloadCnt())
      upload_cnt_str = str(gl.get_uploadCnt())
      remain_cnt_str = str(gl.get_remainCnt())
      uploadAliyunInterval += 1
      ########################### Report to aliyun ###########################
      if uploadAliyunInterval > 4:
        uploadAliyunInterval = 0
        # Update status to aliyun
        remoteFilepath = gl.ALIYUN_UPDATE_ROOT + macAddress + '_' + version_num + '_' + connect_status_str + '_' + download_cnt_str + '_' + upload_cnt_str + '_' + remain_cnt_str
        # Get content
        device_information = version_num + ' ' + connect_status_str + ' ' + download_cnt_str + ' ' + upload_cnt_str + ' ' + remain_cnt_str + '\n'
        # Dump usb 4G dock SIM card information
        try:
          opener = urllib2.build_opener(urllib2.HTTPRedirectHandler(), urllib2.HTTPCookieProcessor())
          opener.open("http://192.168.8.1/html/home.html", timeout=2).read()
          opener.close()
          device_information = opener.open("http://192.168.8.1/api/device/information", timeout=2).read()
          opener.close()
        except:
          opener.close()
          print "Get http://192.168.8.1/html/home.html get failed"
        try:
          response = bucket.put_object(remoteFilepath, device_information)
          list = bucket.list_objects(prefix=gl.ALIYUN_UPDATE_ROOT+macAddress, delimiter='', marker='', max_keys=10)
          for objectInfo in list.object_list:
            if objectInfo.key != remoteFilepath:
              bucket.delete_object(objectInfo.key)
        except:
          print " yumcam_report.py bucket failed"
      ########################### Report to system ###########################
      sign = ''
      key = '28a5240fefba7fbc3edbc81b25d7ec5c'
      dict = {'pid' : '8006010'}
      dict['timestamp'] = str(int(time.time()))
      dict['noncestr'] = str(int(random.uniform(1000000000000, 9000000000000)))
      dict['version'] = version_num
      dict['starttime'] = startUpTime
      dict['downloadcount'] = download_cnt_str
      dict['uploadingcount'] = remain_cnt_str
      dict['mac'] = macAddress
      dict['camerastatus'] = connect_status_str
      #
      urlString = ''
      try:
        dictSort = collections.OrderedDict(sorted(dict.items(), key=lambda t: t[0]))
        for k, v in dictSort.items():
          urlString = urlString + k + '=' + v + '&'
        keyString = urlString + 'key=' + key
        m = hashlib.md5()
        m.update(keyString)
        sign = m.hexdigest()
      except:
        print 'collections md5 failed'
      #
      data_content = ''
      if len(urlString) != 0:
        urlLink = 'http://api.ss.chinarun.com/html/api/photodevicepush.ashx?' + urlString +  'sign=' + sign
        try:
          data_content = urllib2.urlopen(urlLink, timeout=10).read()
        except:
          print "api.ss.chinarun.com photodevicepush failed"
    except:
      print "report main failed"
    #
    time.sleep(10)

###
if __name__== '__main__':
    main_func()
