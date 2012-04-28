from PySide.QtCore import *
from PySide.QtGui import *
import urllib
import re

from rpc.client import *
from window import MySqueezeBoxWindow

class BrowseModel(QAbstractListModel):
	finished = Signal()
	
	def __init__(self, parent):
		QAbstractListModel.__init__(self, parent)
		self._parent = parent
		self.blank = QPixmap(60,60)
		self.blank.fill(Qt.transparent)
		self.client = Client.getClient()
	
	def setData(self, title, data):
		self._title = title
		self._items = data
		self.finished.emit()
		self.loadImages()
	
	def loadData(self, url):
		self.client.getInThread(self._parent, self.loaded, url)
	
	@Slot(dict)
	def loaded(self, info):
		#print "finished load"
		print info
		
		self._title = info['head']['title']
		self._items = info['body']['outline']
		
		self.finished.emit()
		
		self.loadImages()
	
	def rowCount(self, parent = QModelIndex()):  
		return len(self._items)
	
	def data(self, index, role = Qt.DisplayRole):
		if role == Qt.DisplayRole:
			return self._items[index.row()]['text'] 
		elif role == Qt.DecorationRole:
			img = self._items[index.row()].get('icon', None)
			if img:
				return img
		return
	
	def url(self, index):
		return self._items[index.row()]['URL']
	
	def isPlayable(self, index):
		return self._items[index.row()].get('playall', None)
	
	def getType(self, index):
		return self._items[index.row()].get('type', None)
	
	def isSearch(self, i = 0):
		itemType = self._items[i].get('type', None)
		if itemType == "search":
			return True
		return False
	
	def hasChildren(self, index):
		return self._items[index.row()].get('outline', None)
	
	def title(self):
		return self._title
	
	def playUrls(self):
		tracks = []
		for item in self._items:
			tracks.append(item['play'])
		return tracks
	
	def names(self):
		names = []
		for item in self._items:
			if item.get('play', None):
				names.append(item['text'])
		return names
	
	def allNames(self):
		names = []
		for item in self._items:
			names.append(item['text'])
		return names
	
	def showImage(self, imgData, i):
		imgPixmap = QPixmap()
		imgPixmap.loadFromData(imgData)
		if not imgPixmap.isNull():
			pixmap = imgPixmap.scaledToHeight(60)
			QPixmapCache.insert(self._items[i]['image'], pixmap)
			self._items[i]['icon'] = pixmap
			self.dataChanged.emit(self.index(i), self.index(i))
	
	def loadImages(self):
		urls = []
		for i,item in enumerate(self._items):
			itemUrl = item.get('image', None)
			if itemUrl:
				pm = QPixmap()
				ret = QPixmapCache.find(itemUrl, pm)
				if not pm.isNull():
					item['icon'] = pm
					self.dataChanged.emit(self.index(i), self.index(i))
					itemUrl = None
			urls.append(itemUrl)
			if itemUrl:
				item['icon'] = self.blank # placeholder
		
		thread = QThread(self)
		thread.client = LoadImageThread(urls)
		thread.client.moveToThread(thread)
		
		thread.started.connect(thread.client.load)
		thread.finished.connect(thread.client.deleteLater)
		thread.client.finished.connect(self.showImage)
		
		thread.start() 


class BrowseWidget(QWidget):
	loaded = Signal(BrowseModel)
	play = Signal(list)
	
	def __init__(self, model = None):
		QWidget.__init__(self)
		
		self.setAttribute(Qt.WA_DeleteOnClose);

		self.vbox = QVBoxLayout()
		
		if model.isSearch():
			self.model = model
			hbox = QHBoxLayout()
			self.vbox.addLayout(hbox)
			
			self.searchText = QLineEdit(self)
			self.searchType = QComboBox(self)
			searchOptions = model.allNames()
			self.searchType.addItems(searchOptions)
			searchButton = QPushButton("Search", self)
			searchButton.clicked.connect(self.onSearchClicked)
			
			hbox.addWidget(self.searchText)
			hbox.addWidget(self.searchType)
			hbox.addWidget(searchButton)
			if len(searchOptions) <= 1:
				self.searchType.setVisible(False)
		else:
			self.view = QListView()
			self.view.setModel(model)
			
			self.view.clicked.connect(self.onItemClicked)
			
			self.vbox.addWidget(self.view)
		
		self.setLayout(self.vbox)
	
	def onItemClicked(self, index):
		model = self.view.model()
		if model.isPlayable(index):
			self.play.emit(model.playUrls())
		elif model.getType(index) == "audio":
			self.play.emit([model.url(index)])
		elif model.isSearch(index.row()):
			# show search screen if search link pressed
			self.newmodel = BrowseModel(self)
			self.newmodel.finished.connect(self.onLoaded)
			self.newmodel.setData(model._items[index.row()]['text'], [model._items[index.row()]])
		elif model.hasChildren(index):
			# show next browse level with data from model
			self.newmodel = BrowseModel(self)
			self.newmodel.setData(model._items[index.row()]['text'], model._items[index.row()]['outline'])
			self.onLoaded()
		else:
			#show next browse level loaded from url
			if (QApplication.style().inherits("QMaemo5Style")):
				self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
			self.newmodel = BrowseModel(self)
			self.newmodel.finished.connect(self.onLoaded)
			self.newmodel.loadData(model.url(index))
	
	def onSearchClicked(self):
		if (QApplication.style().inherits("QMaemo5Style")):
			self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
		index = self.model.index(self.searchType.currentIndex())
		url = self.model.url(index)
		queryUrl = url.replace("{QUERY}", urllib.quote(self.searchText.text()))
		self.newmodel = BrowseModel(self)
		self.newmodel.finished.connect(self.onLoaded)
		self.newmodel.loadData(queryUrl)
	
	def onLoaded(self):
		self.loaded.emit(self.newmodel)

