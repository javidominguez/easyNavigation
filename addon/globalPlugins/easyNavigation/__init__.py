#-coding: UTF-8 -*-

# Easy Navigation - NVDA addon
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2020 Javi Dominguez <fjavids@gmail.com>

# Substitute single key commands for arrow keys to scroll through headings, links, etc. so that you can do everything with one hand more comfortably and efficiently.
# Specially designed for facilitates navigation through the elements of a document for people with mobility difficulties.

from gui import NVDASettingsDialog
from gui import guiHelper 
from gui.nvdaControls import CustomCheckListBox
from gui.settingsDialogs import SettingsPanel
import addonHandler
import api
import appModuleHandler
import collections
import globalPluginHandler
import globalVars
import os
import pickle
import scriptHandler
import tones
import ui
import wx

RingItem = collections.namedtuple("RingItem", ("status", "name", "previous", "next"))
NavKeys = collections.namedtuple("NavKeys", ("nextOption", "previousOption", "nextItem", "previousItem"))

class EasyNavigationRing():

	def __init__(self):
		if self.load(): return 
		self.ring = [
		RingItem(True, _("Lines"), "script_moveByLine_back", "script_moveByLine_forward"),
		RingItem(True, _("Headings"), "script_previousHeading", "script_nextHeading"),
		RingItem(True, _("Links"), "script_previousLink", "script_nextLink"),
		RingItem(True, _("Unvisited links"), "script_previousUnvisitedLink", "script_nextUnvisitedLink"),
		RingItem(True, _("Visited links"), "script_previousVisitedLink", "script_nextVisitedLink"),
		RingItem(True, _("Form fields"), "script_previousFormField", "script_nextFormField"),
		RingItem(True, _("Buttons"), "script_previousButton", "script_nextButton"),
		RingItem(True, _("Edit fields"), "script_previousEdit", "script_nextEdit"),
		RingItem(True, _("Check boxes"), "script_previousCheckBox", "script_nextCheckBox"),
		RingItem(True, _("Combo boxes"), "script_previousComboBox", "script_nextComboBox"),
		RingItem(True, _("Radio buttons"), "script_previousRadioButton", "script_nextRadioButton"),
		RingItem(True, _("Images"), "script_previousGraphic", "script_nextGraphic"),
		RingItem(True, _("Lists"), "script_previousList", "script_nextList"),
		RingItem(True, _("List items"), "script_previousListItem", "script_nextListItem"),
		RingItem(True, _("Tables"), "script_previousTable", "script_nextTable"),
		RingItem(True, _("Frames"), "script_previousFrame", "script_nextFrame"),
		RingItem(True, _("Articles"), "script_previousArticle", "script_nextArticle"),
		RingItem(True, _("Landmarks"), "script_previousLandmark", "script_nextLandmark"),
		RingItem(True, _("Separators"), "script_previousSeparator", "script_nextSeparator"),
		RingItem(True, _("Quotes"), "script_previousBlockQuote", "script_nextBlockQuote"),
		RingItem(True, _("Objects"), "script_previousEmbeddedObject", "script_nextEmbeddedObject"),
		RingItem(True, _("text blocks"), "script_previousNotLinkBlock", "script_nextNotLinkBlock"),
		RingItem(True, _("Searches"), "script_findPrevious", "script_findNext")]
		self.itemsCount = len(self.ring)
		self.defaultActive = False
		self.navKeys = NavKeys("kb:rightArrow", "kb:leftArrow", "kb:downArrow", "kb:upArrow")

	def getItem(self, index=0):
		return self.ring[index]

	def getNames(self):
		return [_(item.name) for item in self.ring]

	def getEnabledItems(self):
		enabled = []
		for item in self.ring[1:]:
			if item.status: enabled.append(_(item.name))
		return enabled

	def setEnabledItems(self, names=[]):
		newRing = [RingItem(True, _("Lines"), "script_moveByLine_back", "script_moveByLine_forward")]
		for item in self.ring[1:]:
			status = True if _(item.name) in names else False
			newRing.append(RingItem(status, item.name, item.previous, item.next))
		self.ring = newRing

	def save(self):
		try:
			with open(os.path.join(globalVars.appArgs.configPath, "easyNavigation.pickle"), "wb") as f:
				pickle.dump((self.ring, self.defaultActive, self.navKeys), f, 0)
		except IOError:
			pass

	def load(self):
		try:
			with open(os.path.join(globalVars.appArgs.configPath, "easyNavigation.pickle"), "rb") as f:
				self.ring, self.defaultActive, self.navKeys = pickle.load(f)
		except (IOError, EOFError, NameError, ValueError, pickle.UnpicklingError):
			return False
		else:
			self.itemsCount = len(self.ring)
			return True

easyNavigationRing = EasyNavigationRing()

addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	scriptCategory = _("Easy Navigation")
	
	def __init__(self, *args, **kwargs):
		global easyNavigationRing 
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		self.bindGesture("kb:shift+backspace", "toggleEasyNavigation")
		NVDASettingsDialog.categoryClasses.append(EasyNavigationPanel)
		self.flagEasyNavigation = easyNavigationRing.defaultActive
		self.ringIndex = 0

	def terminate(self):
		NVDASettingsDialog.categoryClasses.remove(EasyNavigationPanel)

	def _get_flagExplorationMode(self):
		try:
			return True if api.getFocusObject().treeInterceptor.passThrough == False else False
		except AttributeError:
			return False

	def event_gainFocus(self, obj, nextHandler):
		if self.flagEasyNavigation:
			if self.flagExplorationMode:
				self.enableEasyNavigation()
			else:
				self.disableEasyNavigation(False)
		nextHandler()

	def script_toggleEasyNavigation(self, gesture):
		if self.flagExplorationMode:
			if self.flagEasyNavigation:
				tones.beep(300,100)
				self.disableEasyNavigation()
			else:
				tones.beep(1200,100)
				self.enableEasyNavigation()
	#TRANSLATORS: message shown in Input gestures dialog for this script
	script_toggleEasyNavigation.__doc__ = _("Toggles easy navigation mode.")

	def enableEasyNavigation(self):
		self.flagEasyNavigation = True
		self.bindGesture(easyNavigationRing.navKeys.nextOption, "easyNavigationRingNextOption")
		self.bindGesture(easyNavigationRing.navKeys.previousOption, "easyNavigationRingPreviousOption")
		self.bindGesture(easyNavigationRing.navKeys.nextItem, "easyNavigationNextItem")
		self.bindGesture(easyNavigationRing.navKeys.previousItem, "easyNavigationPreviousItem")

	def disableEasyNavigation(self, toggleFlag=True):
		try:
			for key in easyNavigationRing.navKeys:
				self.removeGestureBinding(key)
		except:
			pass
		else:
			if toggleFlag: self.flagEasyNavigation = False

	def script_easyNavigationRingNextOption(self, gesture):
		global easyNavigationRing 
		ringIndex = self.ringIndex +1 if self.ringIndex+1 < easyNavigationRing.itemsCount else 0
		while easyNavigationRing.getItem(ringIndex).status == False and ringIndex != self.ringIndex:
			ringIndex = ringIndex +1 if ringIndex+1 < easyNavigationRing.itemsCount else 0
		self.ringIndex = ringIndex
		ui.message(_(easyNavigationRing.getItem(self.ringIndex).name))

	def script_easyNavigationRingPreviousOption(self, gesture):
		global easyNavigationRing 
		ringIndex = self.ringIndex -1 if self.ringIndex > 0 else easyNavigationRing.itemsCount-1
		while easyNavigationRing.getItem(ringIndex).status == False and ringIndex != self.ringIndex:
			ringIndex = ringIndex -1 if ringIndex > 0 else easyNavigationRing.itemsCount-1
		self.ringIndex = ringIndex
		ui.message(_(easyNavigationRing.getItem(self.ringIndex).name))

	def script_easyNavigationNextItem(self, gesture):
		global easyNavigationRing 
		treeInterceptor = api.getFocusObject().treeInterceptor
		scriptHandler.executeScript(getattr(treeInterceptor, easyNavigationRing.getItem(self.ringIndex).next), gesture)

	def script_easyNavigationPreviousItem(self, gesture):
		global easyNavigationRing 
		treeInterceptor = api.getFocusObject().treeInterceptor
		scriptHandler.executeScript(getattr(treeInterceptor, easyNavigationRing.getItem(self.ringIndex).previous), gesture)

class EasyNavigationPanel(SettingsPanel):
	title = _("Easy Navigation")

	def makeSettings(self, settingsSizer):
		global easyNavigationRing 
		helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		self.turnOnByDefaultCheckBox=helper.addItem(wx.CheckBox(self, label=_("Default active")))
		self.turnOnByDefaultCheckBox.SetValue(easyNavigationRing.defaultActive)

		self.navKeysModes = {
		_("Right handed (vertical arrows)"): NavKeys("kb:rightArrow", "kb:leftArrow", "kb:downArrow", "kb:upArrow"),
		_("Right handed (horizontal arrows)"): NavKeys("kb:downArrow", "kb:upArrow", "kb:rightArrow", "kb:leftArrow"),
		_("Left hand (vertical AD-WS)"): NavKeys("kb:D", "kb:A", "kb:S", "kb:W"),
		_("Left hand (horizontal WS-AD)"): NavKeys("kb:S", "kb:W", "kb:D", "kb:A")
		}
		self.navKeysSelection = helper.addLabeledControl(_("Set of navigation keys"), wx.Choice, choices=list(self.navKeysModes.keys()))
		self.navKeysSelection.SetSelection(list(self.navKeysModes.values()).index(easyNavigationRing.navKeys))

		self.ringCheckListBox = helper.addLabeledControl(_("Select items:"), CustomCheckListBox, choices=easyNavigationRing.getNames()[1:])
		self.ringCheckListBox.SetCheckedStrings(easyNavigationRing.getEnabledItems())
		self.ringCheckListBox.SetSelection(0)

	def onSave(self):
		global easyNavigationRing 
		easyNavigationRing.setEnabledItems(self.ringCheckListBox.GetCheckedStrings())
		easyNavigationRing.defaultActive = self.turnOnByDefaultCheckBox.GetValue()
		easyNavigationRing.navKeys = self.navKeysModes[list(self.navKeysModes.keys())[self.navKeysSelection.GetSelection()]]
		easyNavigationRing.save()
