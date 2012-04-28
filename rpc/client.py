# -*- coding: utf-8 -*-
import hashlib
import base64
import time
import urllib2
import urllib
import simplejson as json
import sys
from PySide.QtCore import *
from PySide.QtNetwork import *

import os

class LoadImageThread(QObject):
	finished = Signal(QByteArray, int)
	def __init__(self, urls, cache = False):
		QObject.__init__(self)
		if isinstance(urls, str):
			urls = [urls]
		self._urls = urls
		self._cache = cache
	
	def loadUrl(self, url, i):
		if (url[0:4] != "http"): 
			url = "http://www.mysqueezebox.com" + url
		# check if image exists in disk cache
		fileurl = url.replace('/','_')
		path = os.path.expanduser("~/.mysqueezebox/cache/"+fileurl)
		if os.path.exists(path):
			# load from disk
			c = open(path, 'rb')
			img = c.read()
			self.finished.emit(QByteArray(img), i)
		else:
			# load from web
			req = urllib2.Request(url)
			f = urllib2.urlopen(req)
			img = f.read()
			self.finished.emit(QByteArray(img), i)
			if self._cache:
				# save to disk
				c = open(path, 'w')
				c.write(img)
				c.close()
	
	def load(self):
		for i, url in enumerate(self._urls):
			if url:
				data = self.loadUrl(url, i)
		self.thread().quit()

class ClientThread(QObject):
	
	finished = Signal(dict)
	
	def __init__(self, url, sid = None, data = None):
		QObject.__init__(self)
		self._sid = sid
		self._url = url
		self._data = data
	
	def load(self):
		if (self._url[0:4] != "http"): 
			self._url = "http://www.mysqueezebox.com" + self._url
		
		req = urllib2.Request(self._url)
		
		if (self._sid):
			#req.add_header('X-Player-DeviceInfo', '4:130')
			req.add_header('X-Player-MAC', '00:04:20:12:67:a8')
			#req.add_header('X-Player-Model', 'squeezebox2')
			#req.add_header('X-Player-Name', 'U3F1ZWV6ZUJveA==')
			req.add_header('Cookie', "sdi_squeezenetwork_session="+urllib.quote(self._sid))
			req.add_header('Accept', 'text/x-json, text/xml')
			req.add_header("cache-control", "no-cache")
		
		f = urllib2.urlopen(req, self._data)
		data = f.read()
		
		info = json.loads(data)
		return info 
	
	@Slot()
	def get(self):
		#print "started thread"
		info = self.load()
		self.finished.emit(info)
		self.thread().quit()

class Client(QObject):
	loggedIn = Signal()
	loginFailed = Signal(str)
	
	def __init__(self):
		QObject.__init__(self)
		self.sid = None
		self.mac = None
		self.manager = QNetworkAccessManager(self);
		
	def sha1_base64(self, text):
		return base64.b64encode(hashlib.sha1(text).digest())[0:-1]
	
	def getLoginUrl(self, username, password):
		uname = urllib.quote(username)
		t = str(int(time.time()))
		password = urllib.quote(self.sha1_base64(password+t))
		url = "http://www.mysqueezebox.com/api/v1/login?v=sn7.4.1&u="+uname+"&t="+t+"&a="+password
		
		return url
	
	def onLogin(self, info):
		self.loginInfo = info
		#print info
		if (not info['sid']):
			self.loginFailed.emit(info['error'])
		else:
			self.sid = info['sid']
			print "logged in"
			self.loggedIn.emit()
	
	def login(self, username, password):
		self.getInThread(self, self.onLogin, self.getLoginUrl(username, password))
	
	def get(self, url, data = None):
		client = ClientThread(url, self.sid, data)
		info = client.load()
		return info
	
	def getInThread(self, parent, callback, url, data = None):
		thread = QThread(parent)
		thread.client = ClientThread(url, self.sid, data)
		thread.client.moveToThread(thread)
		
		thread.started.connect(thread.client.get)
		thread.client.finished.connect(callback)
		
		thread.start()
	
	@staticmethod
	def getClient():
		if not hasattr(Client, '_client'):
			Client._client = Client()
		return Client._client
