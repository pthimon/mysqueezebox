from PySide.QtCore import *
from PySide.QtGui import *
try:
	from PySide.QtMaemo5 import *
except ImportError:
	pass

from rpc.client import *
import os

class MaemoWindow(QMainWindow):
	def __init__(self, parent):
		QMainWindow.__init__(self, parent)
		
		if (QApplication.style().inherits("QMaemo5Style")):
			# This attribute makes the whole Stacked Window thing work
			self.setAttribute(Qt.WA_Maemo5StackedWindow)
	
	def setBusy(self, busy):
		if (QApplication.style().inherits("QMaemo5Style")):
			self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, busy)

class LoginManager(QObject):
	client = Client.getClient()
	loggedIn = Signal()
	
	def __init__(self, parent = None):
		QObject.__init__(self, parent)
	
	def login(self):
		if not hasattr(self, 'settings'):
			self.settings = SettingsDialog.getSettings(self)
			
			self.client.loggedIn.connect(self.onLoggedIn)
			self.client.loginFailed.connect(self.onLoginFailed)
			
			# always save settings when closing dialog - on first run we will then login and choose client
			self.settings.accepted.connect(self.settings.saveSettings)
			self.settings.rejected.connect(self.onLoginCancelled)
			
			if self.settings.firstRun == 1:
				# get the username and password
				self.settings.showSettings()
			else:
				self.client.login(self.settings.username, self.settings.password)
	
	def onLoginCancelled(self):
		if self.settings.firstRun:
			msg = "You must first enter login information"
			self.onLoginFailed(msg)
			
	def onLoginFailed(self, msg):
		if (QApplication.style().inherits("QMaemo5Style")):
			QMaemo5InformationBox.information(self.parent(), msg, 0)
		else:
			QMessageBox.critical(self.parent(), "Login error", msg)
	
	def onLoggedIn(self):
		if self.settings.firstRun == 1:
			self.settings.firstRun = 2
			self.settings.showSettings()
			return
		elif self.settings.firstRun == 2:
			self.settings.firstRun = 0
		self.loggedIn.emit()


class MySqueezeBoxWindow(MaemoWindow):
	client = Client.getClient()
	
	def __init__(self, widget = None, parent = None):
		MaemoWindow.__init__(self, parent)
		
		self.setWindowTitle("MySqueezeBox")
		
		self.settings = SettingsDialog.getSettings()
		
		menu = QMenuBar(self)
		self.showPlayback = menu.addAction("Playback")
		self.showPlayback.triggered.connect(self.onShowPlayback)
		settings = menu.addAction("Settings")
		settings.triggered.connect(self.settings.showSettings)
		self.setMenuBar(menu)
		
		if widget:
			widget.setParent(self)
			self.setCentralWidget(widget)
		elif (not QApplication.style().inherits("QMaemo5Style")):
			self.widgetStack = QStackedWidget(self)
			self.toolbar = self.addToolBar("Navigation")
	
	def loaded(self, model):
		browse = BrowseWidget(model)
		if (QApplication.style().inherits("QMaemo5Style")):
			# create a stacked window to contain the BrowseWidget
			win = MySqueezeBoxWindow(browse, self)
			browse.loaded.connect(win.loaded)
			browse.play.connect(win.onPlay)
			win.setWindowTitle("MySqueezeBox - "+model.title())
			win.show()
			self.setBusy(False)
		else:
			# desktop version
			browse.loaded.connect(self.loaded)
			browse.play.connect(self.onPlay)
			browse.setParent(self)
			self.widgetStack.addWidget(browse)
			self.widgetStack.setCurrentWidget(browse)
			# navigation using the toolbar actions
			item = self.toolbar.addAction(model.title())
			item.setData(self.widgetStack.currentIndex())
			item.triggered.connect(self.onNavigate)
			browse.navAction = item
	
	@Slot()
	def onPlay(self, tracks):
		self.getPlaybackWidget().loadTracks(self, tracks)
		self.setBusy(True)
	
	@Slot()
	def onShowPlayback(self):
		playback = self.getPlaybackWidget()
		playback.makeParent(self)
		playback.show()
	
	@Slot()
	def onNavigate(self):
		# navigation using the toolbar actions in the desktop version
		index = self.sender().data()
		self.widgetStack.setCurrentIndex(index)
		for i in range(self.widgetStack.count()-1,index,-1):
			widget = self.widgetStack.widget(i)
			self.toolbar.removeAction(widget.navAction)
			self.widgetStack.removeWidget(widget)
	
	def getPlaybackWidget(self):
		if not hasattr(MySqueezeBoxWindow, 'playback'):
			print "creating playback window"
			MySqueezeBoxWindow.playback = PlaybackWidget(self.playbackUI, self)
		return MySqueezeBoxWindow.playback 


from playback import PlaybackWidget
from browse import BrowseWidget
from settings import SettingsDialog
