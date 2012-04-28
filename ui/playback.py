from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtXml import *
from PySide.QtNetwork import *
from PySide.phonon import *
try:
	from PySide.QtMaemo5 import *
except ImportError:
	pass
import urllib, re, urllib2, sys

from rpc.client import *
from window import MySqueezeBoxWindow

class ProtocolHandler:
	def __init__(self, url):
		self.radio = False
		self.httpStream = False
		self.title = ""
		self._parseUrl(url)
	
	def _parseUrl(self, url):
		print url
		parts = re.match("^([a-z]+)://(.+?)(?:\.([a-z]{3}))?$", url)
		self.protocol = parts.group(1)
		self.trackid = parts.group(2)
		self.ext = parts.group(3)
		
		if self.protocol == "napster":
			self.bulkinfourl = "/api/napster/v1/playback/getBulkMetadata"
			if self.ext == "wma":
				self.infourl = "/api/napster/v1/playback/getMediaURL?trackId="+ urllib.quote(self.trackid)
			elif self.ext == "nsr":
				self.infourl = "/api/napster/v1/radio/getNextTrack?stationId="+urllib.quote(self.trackid)
				self.radio = True
		elif self.protocol == "lfm":
			self.infourl = "/api/lastfm/v1/playback/getNextTrack?station="+ urllib.quote(self.trackid)+ "&isScrobbling=1&discovery=0&account=pthimon"
			self.radio = True
			#{contentType} = 'audio/mpeg'
		elif self.protocol == "deezer":
			self.bulkinfourl = "/api/deezer/v1/playback/getBulkMetadata"
			if self.ext == "mp3":
				self.infourl = "/api/deezer/v1/playback/getMediaURL?trackId="+ urllib.quote(self.trackid)
			elif self.ext == "dzr":
				self.infourl = "/api/deezer/v1/radio/getNextTrack?stationId="+urllib.quote(self.trackid)
				self.radio = True
		elif self.protocol == "http":
			self.httpStream = True
			if self.ext == "pls":
				# parse playlist
				req = urllib2.Request(url)
				f = urllib2.urlopen(req)
				for line in f:
					files = re.match("^File1=(.+)$", line)
					if files:
						self.infourl = files.group(1)
					titles = re.match("^Title1=(.+)$", line)
					if titles:
						self.title = titles.group(1)
				self.radio = True
			elif self.ext == "asx":
				# parse asx
				req = urllib2.Request(url)
				f = urllib2.urlopen(req)
				xml = f.read()
				doc = QDomDocument()
				doc.setContent(xml)
				docElem = doc.documentElement();
				n = docElem.firstChild();
				while (not n.isNull()):
					e = n.toElement()
					if(not e.isNull()):
						if e.tagName() == "TITLE":
							self.title = e.text()
						if e.tagName() == "Entry":
							self.infourl = e.firstChild().toElement().attribute("href")
							break
					n = n.nextSibling();
				self.radio = True
			else:
				self.radio = True
				self.infourl = url
	
	def getKeys(self):
		if self.protocol == 'napster':
			return {'url':'url', 'title':'title', 'artist':'artist', 'album':'album', 'cover':'cover', 'duration':'duration'}
		elif self.protocol == 'lfm':
			return {'url':'location', 'title':'title', 'artist':'creator', 'album':'album', 'cover':'image'}
		elif self.protocol == 'deezer':
			return {'url':'url', 'title':'title', 'artist':'artist_name', 'album':'album_name', 'cover':'cover', 'duration':'duration'}
		
		return {'url':'url', 'title':'title', 'artist':'artist', 'album':'album', 'cover':'cover', 'duration':'duration'}


class PlaybackUI(QWidget):
	def __init__(self):
		QWidget.__init__(self)
		vbox = QVBoxLayout()
		hbox = QHBoxLayout()
		vbox.addLayout(hbox)
		
		self.image = QPushButton(self)
		self.image.setFlat(True)
		self.image.setMinimumSize(300,300)
		self.image.setIconSize(QSize(300,300))
		hbox.addWidget(self.image)
		
		self.stackedWidget = QStackedWidget(self)
		hbox.addWidget(self.stackedWidget, 1)
		
		self.view = QListView(self)
		self.stackedWidget.addWidget(self.view)
		
		details = QWidget()
		dVBox = QVBoxLayout()
		self.title = QLabel()
		self.artist = QLabel()
		self.album = QLabel()
		self.time = QLabel()
		self.duration = QLabel()
		dVBox.addWidget(self.title)
		dVBox.addWidget(self.artist)
		dVBox.addWidget(self.album)
		timeBox = QHBoxLayout()
		timeBox.addWidget(self.time)
		timeBox.addWidget(self.duration)
		timeBox.addStretch()
		dVBox.addLayout(timeBox)
		details.setLayout(dVBox)
		self.stackedWidget.addWidget(details)
		
		self.controls = QHBoxLayout()
		
		self.playButton = QPushButton(">", self)
		self.controls.addWidget(self.playButton)
		
		self.nextButton = QPushButton(">|", self)
		self.controls.addWidget(self.nextButton)
		
		self.music = Phonon.MediaObject()
		
		slider = Phonon.SeekSlider(self)
		slider.setMediaObject(self.music)
		self.controls.addWidget(slider)
		slider.show()
		
		volume = Phonon.VolumeSlider(self)
		self.controls.addWidget(volume)
		volume.show()
		
		if (QApplication.style().inherits("QMaemo5Style")):
			out = Phonon.AudioOutput(Phonon.MusicCategory)
			out.setVolume(0.5)
			volume.setAudioOutput(out)
			Phonon.createPath(self.music, out)
		
		vbox.addLayout(self.controls)
		
		self.setLayout(vbox)

class PlaybackWidget(MySqueezeBoxWindow):
	def __init__(self, ui, parent = None):
		MySqueezeBoxWindow.__init__(self, None, parent)
		
		# disable the show playback window action
		self.showPlayback.setEnabled(False)
		
		ui.setParent(self)
		self.ui = ui
		
		self.ui.view.clicked.connect(self.onClicked)

		#self.ui.music.setPrefinishMark(2000)
		#self.ui.music.prefinishMarkReached.connect(self.enqueueNextTrack)
		self.ui.music.aboutToFinish.connect(self.enqueueNextTrack)
		self.ui.music.finished.connect(self.finished)
		self.ui.music.stateChanged.connect(self.stateChanged)
		self.ui.music.tick.connect(self.onTick)
		
		self.ui.playButton.clicked.connect(self.buttonPushed)
		self.ui.nextButton.clicked.connect(self.nextTrack)
		
		self.ui.image.clicked.connect(self.onImageClicked)
		
		self.setCentralWidget(self.ui)
		
		self.index = 0
		self.loadedImageUrl = None
	
	def loadTracks(self, parent, tracks):
		self.makeParent(parent)
		self.model = PlaybackModel(self)
		self.model.finished.connect(self.playTracks)
		self.model.loadData(tracks)
	
	def makeParent(self, parent):
		if (QApplication.style().inherits("QMaemo5Style")):
			# reparent to browse widget so pressing back goes back to browse
			self.setParent(parent, Qt.Window)
	
	def playTracks(self):
		print "play"
		self.ui.view.setModel(self.model)
		self.show()
		self.parent().setBusy(False)
		self.play(0)
	
	def buttonPushed(self):
		if self.ui.music.state() == Phonon.PlayingState:
			self.ui.playButton.setText(">")
			self.ui.music.pause()
		elif self.ui.music.state() == Phonon.StoppedState or self.ui.music.state() == Phonon.ErrorState:
			self.ui.playButton.setText("||")
			num = self.index
			if (num >= 0 and num < self.model.rowCount()):
				self.play(num)
			else:
				self.play(0)
		else:
			self.ui.playButton.setText("||")
			self.ui.music.play()
	
	def hideEvent(self, event):
		if (QApplication.style().inherits("QMaemo5Style")):
			# Reparent back to top level so not to get deleted when parent browse widget is deleted
			self.setParent(None, Qt.Window)
	
	def play(self, i, enqueue = False):
		if (i >= 0 and i < self.model.rowCount()):
			self.index = i
			self.ui.view.setCurrentIndex(self.model.index(i))
			url = self.model.url(i)
			if url:
				print "playing "+url.toString()
				if enqueue:
					self.ui.music.enqueue(url)
				else:
					self.ui.music.setCurrentSource(url)
					self.setBusy(True)
				self.ui.music.play()
				if (i == self.model.rowCount()-1) and not self.model.isRadio(i):
					self.ui.nextButton.setEnabled(False)
				else:
					self.ui.nextButton.setEnabled(True)
				self.ui.playButton.setText("||")
				self.loadCoverImage()
				self.ui.title.setText(self.model._items[i].get('title',None))
				self.ui.artist.setText(self.model._items[i].get('album',None))
				self.ui.album.setText(self.model._items[i].get('artist',None))
				duration = self.model._items[i].get('duration',None)
				if duration:
					self.ui.duration.setText(" / %d:%d"%((int(duration)/60),(int(duration)%60)))
		elif not enqueue:
			self.finished()
	
	def finished(self):
		self.ui.view.setCurrentIndex(QModelIndex())
		self.index = None
		self.stop()
	
	def stop(self):
		self.ui.music.stop()
		self.ui.playButton.setText(">")
	
	def onClicked(self, index):
		self.play(index.row())
	
	def nextTrack(self):
		if self.model.isRadio(self.index):
			self.nextRadioTrack()
		else:
			self.play(self.index + 1)
	
	def enqueueNextTrack(self):
		if self.model.isRadio(self.index):
			self.nextRadioTrack(True)
		else:
			self.play(self.index + 1, True)
	
	def nextRadioTrack(self, enqueue = False):
		self.model.nextRadioTrack(self.index)
		self.play(self.index, enqueue)
	
	def stateChanged(self, newState, oldState):
		if newState == Phonon.ErrorState:
			QMaemo5InformationBox.information(self, "Error loading stream")
			print "Error %d"%self.ui.music.errorType()
			if not self.model.isRadio(self.index):
				self.nextTrack()
		if newState != Phonon.LoadingState or newState != Phonon.BufferingState:
			self.setBusy(False)
	
	def showImage(self, imgData, i):
		imgPixmap = QPixmap()
		imgPixmap.loadFromData(imgData)
		#self.ui.image.setPixmap(imgPixmap.scaledToHeight(300))
		self.ui.image.setIcon(QIcon(imgPixmap.scaledToHeight(300)))
	
	def loadCoverImage(self):
		imageUrl = self.model.imageUrl(self.index)
		if imageUrl and self.loadedImageUrl != imageUrl:
			thread = QThread(self)
			thread.client = LoadImageThread(self.model.imageUrl(self.index))
			thread.client.moveToThread(thread)
			
			thread.started.connect(thread.client.load)
			thread.finished.connect(thread.client.deleteLater)
			thread.client.finished.connect(self.showImage)
			
			self.loadedImageUrl = imageUrl
			
			thread.start()
	
	def onImageClicked(self):
		self.ui.stackedWidget.setCurrentIndex((self.ui.stackedWidget.currentIndex() + 1)%2)
	
	def onTick(self, pos):
		pos = pos / 1000
		self.ui.time.setText("%d:%02d"%((pos/60),(pos%60)))



class PlaybackModel(QAbstractListModel):
	finished = Signal()
	
	def __init__(self, parent):
		QAbstractListModel.__init__(self, parent)
		self._parent = parent
	
	def isRadio(self, i):
		return self.tracks[i].radio
	
	def loadNextRadioTrack(self, i):
		self._parent.client.getInThread(self._parent, self.saveNextRadioTrack, self.tracks[i].infourl)
	
	def saveNextRadioTrack(self, info):
		self.nextRadioTrackInfo = info
	
	def nextRadioTrack(self, i):
		self._items[i] = self.nextRadioTrackInfo
		self.dataChanged.emit(self.index(i), self.index(i))
		self.loadNextRadioTrack(0)
		
	@Slot(dict)
	def loaded(self, info):
		print info
		# save single track details
		self._items = []
		self.loadTrackInfo(0,info)
		self.finished.emit()
	
	def loadData(self, tracks):
		if len(tracks) > 1:
			self.tracks = []
			tracklist = []
			for track in tracks:
				handler = ProtocolHandler(track)
				tracklist.append(handler.trackid)
				self.tracks.append(handler)
			trackstr = urllib.urlencode([('trackIds',','.join(tracklist))])
			self._parent.client.getInThread(self._parent, self.bulkInfoLoaded, self.tracks[0].bulkinfourl, trackstr)
		else:
			self.tracks = [ProtocolHandler(tracks[0])]
			track = self.tracks[0]
			if track.httpStream:
				self._items = [{'url':track.infourl, 'title':track.title}]
				self.finished.emit()
			else:
				self._parent.client.getInThread(self._parent, self.loaded, track.infourl)
				if self.isRadio(0):
					self.loadNextRadioTrack(0)
	
	def loadTrackInfo(self, i, info):
		keys = self.tracks[i].getKeys()
		item = {}
		for key,infoKey in keys.items():
			item[key] = info.get(infoKey, None)
		self._items.append(item)
	
	@Slot(dict)
	def bulkInfoLoaded(self, info):
		print info
		# save multiple track details
		self._items = []
		for i,item in enumerate(info):
			self.loadTrackInfo(i,item)
		
		self.urlLoad = -1
		self.loadUrls()
	
	def loadUrls(self):
		self.urlLoad = self.urlLoad + 1
		if self.urlLoad < len(self._items):
			self._parent.client.getInThread(self._parent, self.urlLoaded, self.tracks[self.urlLoad].infourl)
	
	def urlLoaded(self, info):
		print info['url']
		self._items[self.urlLoad]['url'] = info['url']
		if self.urlLoad == 0:
			self.finished.emit()
		self.loadUrls()
	
	def rowCount(self, parent = QModelIndex()):  
		return len(self._items)
		
	def data(self, index, role = Qt.DisplayRole):  
		if role == Qt.DisplayRole:
			return self._items[index.row()]['title']
		else:  
			return
	
	def url(self, i):
		if i < 0 or i >= len(self._items):
			return
		link = self._items[i].get('url', None)
		if self.tracks[i].protocol == "lfm":
			print "Error: Phonon can't handle last.fm streams for some reason"
			#reply = self._parent.client.manager.get(QNetworkRequest(QUrl(link)));
			#reply.finished.connect(self.replyFinished)
			#reply.readyRead.connect(self.replyReady)
			#return reply
		if not link:
			print "Loading url synchronously"
			info = self._parent.client.get(self.tracks[i].infourl)
			keys = self.tracks[i].getKeys()
			link = info[keys['url']]
			
		return QUrl(link)
	
	def imageUrl(self, i):
		return self._items[i].get('cover',None)

