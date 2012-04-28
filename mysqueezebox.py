from PySide.QtCore import *
from PySide.QtGui import *
import sys

from ui.window import MySqueezeBoxWindow, LoginManager
from ui.browse import BrowseModel
from ui.playback import PlaybackUI
from rpc.client import LoadImageThread

class MySqueezeBox(MySqueezeBoxWindow):
	def __init__(self):
		MySqueezeBoxWindow.__init__(self, None)
		
		self.setBusy(True)
		
		self.showPlayback.setEnabled(False)
		
		self.loadingText = QLabel("Logging in...", self)
		self.loadingText.setAlignment(Qt.AlignCenter)
		self.setCentralWidget(self.loadingText)
		self.resize(500,500)
	
	def login(self):
		manager = LoginManager(self)
		manager.loggedIn.connect(self.onLogin)
		manager.login()
	
	def onLogin(self):
		# create the playback UI now, to avoid the instantiation delay when queuing tracks
		MySqueezeBoxWindow.playbackUI = PlaybackUI()
		
		# enable the show playback window action
		self.showPlayback.setEnabled(True)
		
		self.loadingText.setText("Loading mysqueezebox.com services...")
		
		self.client.getInThread(self, self.onServices, "http://www.mysqueezebox.com/api/v1/players")
		
		#self.client.getInThread(self, self.onTest, "/api/napster/v1/radio/getNextTrack?stationId=10008111")
		#self.client.getInThread(self, self.onTest, "/api/napster/v1/playback/getMediaURL?trackId=29860359")
	
	def onTest(self, data):
		print data
	
	def onServices(self, data):
		# parse settings
		players = []
		for item in data['inactive_players']:
			players.append(item)
		for item in data['players']:
			players.append(item)
		for i,item in enumerate(players):
			if item['mac'] == self.client.mac:
				apps = []
				for service in item['apps']:
					#lookup name
					app = item['apps'][service]
					for string in data['strings']:
						if string['token'] == item['apps'][service]['title']:
							app['title'] = string['strings']['EN']
					apps.append(app)
				self.player = item
				self.player['apps'] = apps
		
		cw = QWidget(self)
		if (QApplication.style().inherits("QMaemo5Style")):
			self.setCentralWidget(cw)
		else:
			self.widgetStack.addWidget(cw)
			self.setCentralWidget(self.widgetStack)
			item = self.toolbar.addAction("Home")
			item.setData(self.widgetStack.currentIndex())
			item.triggered.connect(self.onNavigate)
			cw.navAction = item
		
		self.grid = QGridLayout()
		cw.setLayout(self.grid)
		
		self.buttons = []
		self.iconUrls = []
		row = 0
		col = 0
		blankIcon = QPixmap(100,100)
		blankIcon.fill(Qt.transparent)
		icon = QIcon(blankIcon)
		numIcons = len(self.player['apps'])
		for app in self.player['apps']:
			print app
			button = QToolButton(cw)
			button.setText(app['title'])
			button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
			button.setIcon(blankIcon)
			button.setIconSize(QSize(100,100))
			button.url = app['url']
			self.grid.addWidget(button, row, col)
		
			button.clicked.connect(self.buttonPushed)
			self.buttons.append(button)
			self.iconUrls.append(app['icon'])
			col = col+1
			if numIcons < 5 or numIcons == 7 or numIcons == 8 or numIcons == 11 or numIcons == 12:
				cols = 4
			elif numIcons < 10:
				cols = 3
			else:
				cols = 5
			if col == cols:
				col = 0
				row = row+1
		
		thread = QThread(self)
		thread.client = LoadImageThread(self.iconUrls, True)
		thread.client.moveToThread(thread)
		
		thread.started.connect(thread.client.load)
		thread.finished.connect(thread.client.deleteLater)
		thread.client.finished.connect(self.showImage)
		
		thread.start()
		
		self.setBusy(False)
	
	def showImage(self, imgData, i):
		imgPixmap = QPixmap()
		imgPixmap.loadFromData(imgData)
		if not imgPixmap.isNull():
			icon = QIcon(imgPixmap.scaledToHeight(100,Qt.SmoothTransformation))
			self.buttons[i].setIcon(icon)
	
	def buttonPushed(self):
		self.setBusy(True)
		self.model = BrowseModel(self)
		self.model.finished.connect(self.onLoaded)
		button = self.sender()
		if button.text() == "BBC":
			self.model.setData("BBC", [{'URL':"http://bbc.co.uk/radio/listen/live/r1.asx",'text':"BBC Radio 1", 'type':"audio"},{'URL':"http://bbc.co.uk/radio/listen/live/r2.asx",'text':"BBC Radio 2", 'type':"audio"},{'URL':"http://bbc.co.uk/radio/listen/live/r3.asx",'text':"BBC Radio 3", 'type':"audio"},{'URL':"http://bbc.co.uk/radio/listen/live/r4.asx",'text':"BBC Radio 4", 'type':"audio"},{'URL':"http://bbc.co.uk/radio/listen/live/r4lw.asx",'text':"BBC Radio 4 LW", 'type':"audio"},{'URL':"http://www.bbc.co.uk/fivelive/live/live_int.asx",'text':"BBC 5 | news & sports", 'type':"audio"},{'URL':"http://www.bbc.co.uk/6music/ram/6music.asx",'text':"BBC 6 | adult alternative", 'type':"audio"},{'URL':"http://www.bbc.co.uk/bbc7/realplayer/bbc7.asx",'text':"BBC 7 | comedy & drama", 'type':"audio"},{'URL':"http://www.bbc.co.uk/worldservice/meta/tx/nb/live/www11.asx",'text':"BBC World Service | int'l news", 'type':"audio"}])
		else:
			self.model.loadData(self.sender().url)
	
	def onLoaded(self):
		self.loaded(self.model)

if __name__ == '__main__':
	app = QApplication(sys.argv)
	app.setApplicationName("MySqueezeBox")
	
	w = MySqueezeBox()
	w.login()
	w.show()
	
	# Main event loop of Qt. This won't return until the program exits.
	app.exec_()
	sys.exit() 