	#-coding: UTF-8 -*-
"""
Easy Navigation - NVDA addon
This file is covered by the GNU General Public License.
See the file COPYING.txt for more details.
Copyright (C) 2020 Javi Dominguez <fjavids@gmail.com>

Substitute single key commands for a set of four keys to scroll through headings, links, etc. so that you can do everything with one hand more comfortably and efficiently.
Specially designed for facilitates navigation through the elements of a document for people with mobility difficulties.
"""

from gui import NVDASettingsDialog
from gui import guiHelper 
from gui.nvdaControls import CustomCheckListBox
from gui.settingsDialogs import SettingsPanel
from keyboardHandler import KeyboardInputGesture
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
	"""Here the navigation ring is defined:
	@ self.ring: (list of namedtuples): Each namedtuple contains this information about an option:
		- status (enabled/disabled)
		- name
		- previous and next (name of the scripts that execute the movements.
	@ self.defaultActive (boolean): Indicates if easy navigation mode will be activated by default when the addon is loaded.
	@ self.navKeys (namedtuple): Contains the movement keys that are used when the ring is active."""

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
		"""It receives as parameter an index (int) and returns the element of the ring (RingItem) corresponding to it."""
		return self.ring[index]

	def getNames(self):
		"""Returns a list with the names of all the ring options."""
		return [_(item.name) for item in self.ring]

	def getEnabledItems(self):
		"""Returns a list with the indexes of the enabled options."""
		enabled = []
		for item in self.ring[1:]:
			if item.status: enabled.append(self.ring[1:].index(item))
		return enabled

	def setEnabledItems(self, checkedItems=[]):
		"""Receive a list of indexes (int) and check enabled the corresponding options."""
		newRing = [RingItem(True, _("Lines"), "script_moveByLine_back", "script_moveByLine_forward")]
		for item in self.ring[1:]:
			status = True if self.ring[1:].index(item) in checkedItems else False
			newRing.append(RingItem(status, item.name, item.previous, item.next))
		self.ring = newRing

	def save(self):
		"""Save the current configuration in a file with pickle.
		The format is a tuple with the following items:
		(self.ring, self.defaultActive, self.navKeys)"""
		try:
			with open(os.path.join(globalVars.appArgs.configPath, "easyNavigation.pickle"), "wb") as f:
				pickle.dump((self.ring, self.defaultActive, self.navKeys), f, 0)
		except IOError:
			pass

	def load(self):
		"""Load preferences from a file with pickle.
		Returns True if load is succesfull, else returns False."""
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
		self.oldGestureBindings = {}

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
		for k in easyNavigationRing.navKeys:
			# Save binds (to restore them later) and remove then before binding the new ones to avoid keyboard conflicts.
			script = KeyboardInputGesture.fromName(k.split(":")[1]).script
			if script and self != script.__self__:
				self.oldGestureBindings[k] = script
				script.__self__.removeGestureBinding(k)
		self.bindGesture(easyNavigationRing.navKeys.nextOption, "easyNavigationRingNextOption")
		self.bindGesture(easyNavigationRing.navKeys.previousOption, "easyNavigationRingPreviousOption")
		self.bindGesture(easyNavigationRing.navKeys.nextItem, "easyNavigationNextItem")
		self.bindGesture(easyNavigationRing.navKeys.previousItem, "easyNavigationPreviousItem")

	def disableEasyNavigation(self, toggleFlag=True):
		try:
			for key in easyNavigationRing.navKeys:
				self.removeGestureBinding(key)
				# Restore old bindings
				try:
					script = self.oldGestureBindings[key]
				except KeyError:
					pass
				else:
					if hasattr(script.__self__, script.__name__):
						script.__self__.bindGesture(key, script.__name__[7:])
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

	#TRANSLATORS: Title of the preferences pane
	title = _("Easy Navigation")

	def makeSettings(self, settingsSizer):
		global easyNavigationRing 
		helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		self.turnOnByDefaultCheckBox=helper.addItem(wx.CheckBox(self, label=_(
		#TRANSLATORS: Label of the checkbox that indicates whether to activate the easy navigation by default when loading the addon.
		"Default active")))
		self.turnOnByDefaultCheckBox.SetValue(easyNavigationRing.defaultActive)

		self.navKeysModes = {
		# Dictionary containing the sets of keys that can be selected by the user for navigation.
		# Dictionary key will be the name shown in each option of the combo box in the preferences panel.
		_("Right hand vertical arrows"): NavKeys("kb:rightArrow", "kb:leftArrow", "kb:downArrow", "kb:upArrow"),
		_("Right hand horizontal arrows"): NavKeys("kb:downArrow", "kb:upArrow", "kb:rightArrow", "kb:leftArrow"),
		_("Right hand vertical numpad"): NavKeys("kb:numpad6", "kb:numpad4", "kb:numpad2", "kb:numpad8"),
		_("Right hand horizontal numpad"): NavKeys("kb:numpad2", "kb:numpad8", "kb:numpad6", "kb:numpad4"),
		_("Left hand vertical AD-WS"): NavKeys("kb:D", "kb:A", "kb:S", "kb:W"),
		_("Left hand horizontal WS-AD"): NavKeys("kb:S", "kb:W", "kb:D", "kb:A"),
		_("Left hand vertical SF-ED"): NavKeys("kb:F", "kb:S", "kb:D", "kb:E"),
		_("Left hand horizontal ED-SF"): NavKeys("kb:D", "kb:E", "kb:F", "kb:S")
		}
		self.navKeysSelection = helper.addLabeledControl(
		#TRANSLATORS: Label of the combo box where the user chooses the set of navigation keys they want to use.
		_("Set of navigation keys"), wx.Choice, choices=list(self.navKeysModes.keys()))
		try:
			self.navKeysSelection.SetSelection(list(self.navKeysModes.values()).index(easyNavigationRing.navKeys))
		except ValueError:
			self.navKeysSelection.SetSelection(0)

		self.ringCheckListBox = helper.addLabeledControl(
		#TRANSLATORS: Label of the selectable list where users choose the navigation items they want to use.
		_("Navigation items:"), CustomCheckListBox, choices=easyNavigationRing.getNames()[1:])
		self.ringCheckListBox.SetCheckedItems(easyNavigationRing.getEnabledItems())
		self.ringCheckListBox.SetSelection(0)

	def onSave(self):
		global easyNavigationRing 
		easyNavigationRing.setEnabledItems(self.ringCheckListBox.GetCheckedItems())
		easyNavigationRing.defaultActive = self.turnOnByDefaultCheckBox.GetValue()
		easyNavigationRing.navKeys = self.navKeysModes[list(self.navKeysModes.keys())[self.navKeysSelection.GetSelection()]]
		easyNavigationRing.save()
