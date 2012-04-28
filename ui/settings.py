from PySide.QtCore import *
from PySide.QtGui import *

from rpc.client import *

import os

class SettingsDialog(QDialog):
	client = Client.getClient()
	
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		
		self.setWindowTitle("Settings")
		
		formBox = QFormLayout()
		
		self.usernameLabel = QLabel("Username:", self)
		self.usernameText = QLineEdit(self)
		self.passwordLabel = QLabel("Password:", self)
		self.passwordText = QLineEdit(self)
		self.passwordText.setEchoMode(QLineEdit.Password)
		self.playerLabel = QLabel("Player:", self)
		self.playerNames = QComboBox(self)
		
		formBox.addRow(self.usernameLabel, self.usernameText)
		formBox.addRow(self.passwordLabel, self.passwordText)
		formBox.addRow(self.playerLabel, self.playerNames)
		
		buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel);
		
		buttonBox.accepted.connect(self.accept);
		buttonBox.rejected.connect(self.reject);
		
		self.firstRun = 1
		path = os.path.expanduser("~/.mysqueezebox/config")
		if os.path.exists(path):
			# load self from file
			self.f = open(path, "r+")
			self.username = self.f.readline().strip()
			self.usernameText.setText(self.username)
			self.password = self.f.readline().strip()
			self.clientMac = self.f.readline().strip()
			self.client.mac = self.clientMac
			if self.username != "":
				# not the first run
				self.firstRun = 0
		else:
			directory = os.path.expanduser("~/.mysqueezebox")
			if not os.path.exists(directory):
				os.mkdir(directory, 0755)
			cachedirectory = os.path.expanduser("~/.mysqueezebox/cache")
			if not os.path.exists(cachedirectory):
				os.mkdir(cachedirectory, 0755)
			# no self found
			self.f = open(path, "w")
			self.username = None
			self.password = None
			self.clientMac = None
		
		if (QApplication.style().inherits("QMaemo5Style")):
			# put the save button on the right
			hbox = QHBoxLayout()
			hbox.addLayout(formBox, 1)
			vbox = QVBoxLayout()
			vbox.addStretch()
			vbox.addWidget(buttonBox)
			hbox.addLayout(vbox)
			self.setLayout(hbox)
		else:
			vbox = QVBoxLayout()
			vbox.addLayout(formBox)
			vbox.addWidget(buttonBox)
			self.setLayout(vbox)
	
	@staticmethod
	def getSettings(parent = None):
		if not hasattr(SettingsDialog, '_settings'):
			SettingsDialog._settings = SettingsDialog(parent)
		return SettingsDialog._settings
	
	def showSettings(self):
		if self.firstRun == 1:
			# hide the player selection combo box until after login
			self.playerNames.setVisible(False)
			self.playerLabel.setVisible(False)
			self.show()
		elif self.firstRun == 2:
			if (QApplication.style().inherits("QMaemo5Style")):
				self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
			# hide the username and password
			self.playerNames.setVisible(True)
			self.playerLabel.setVisible(True)
			self.playerNames.setEnabled(False)
			self.usernameLabel.setVisible(False)
			self.usernameText.setVisible(False)
			self.passwordLabel.setVisible(False)
			self.passwordText.setVisible(False)
			self.client.getInThread(self, self.onPlayers, "http://www.mysqueezebox.com/api/v1/players")
			self.exec_()
		else:
			if (QApplication.style().inherits("QMaemo5Style")):
				self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
			# make sure everything is visible
			self.playerNames.setVisible(True)
			self.playerLabel.setVisible(True)
			self.playerNames.setEnabled(False)
			self.usernameLabel.setVisible(True)
			self.usernameText.setVisible(True)
			self.passwordLabel.setVisible(True)
			self.passwordText.setVisible(True)
			self.client.getInThread(self, self.onPlayers, "http://www.mysqueezebox.com/api/v1/players")
			self.show()
		#self.client.getInThread(self, self.onPlayers, "/api/v1/prefs/can_sync")
		# "/api/v1/prefs/sync_down" {'uuid', 'id', 'deviceid', 'name', 'model', 'revision', 'since'}
	
	def onPlayers(self, data):
		if (QApplication.style().inherits("QMaemo5Style")):
			self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, False)
		playerNames = []
		players = []
		for item in data['inactive_players']:
			playerNames.append(item['name'])
			players.append(item)
		for item in data['players']:
			playerNames.append(item['name'])
			players.append(item)
		self.playerNames.clear()
		self.playerNames.addItems(playerNames)
		self.playerNames.setEnabled(True)
		self.players = players
		for i,item in enumerate(players):
			if item['mac'] == self.clientMac:
				self.playerNames.setCurrentIndex(i)
	
	def saveSettings(self):
		self.f.seek(0)
		self.f.truncate()
		
		logon = False
		username = self.usernameText.text()
		if self.username != username:
			self.username = username
			logon = True
		
		passwordHash = self.client.sha1_base64(self.passwordText.text())
		if passwordHash != self.password:
			self.password = passwordHash
			logon = True
		
		if self.firstRun != 1:
			client = self.players[self.playerNames.currentIndex()]['mac']
			if self.clientMac != client:
				self.clientMac = client
			
			self.client.mac = self.clientMac
			self.f.write(self.username +'\n'+ self.password +'\n'+ self.clientMac)
			self.f.flush()
			
		if self.firstRun == 2:
			# a bit of a hack
			self.client.loggedIn.emit()
			return
		
		if logon:
			# username and/or password have changed (or is first run) so login
			self.client.login(self.username, self.password)