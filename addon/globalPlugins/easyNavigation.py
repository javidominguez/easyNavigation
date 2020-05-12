# -*- coding: UTF-8 -*-

# Easy Navigation - NVDA addon
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.
#Copyright (C) 2020 Javi Dominguez <fjavids@gmail.com>

# Substitute single key commands for arrow keys to scroll through headings, links, etc. so that you can do everything with one hand more comfortably and efficiently.
# Specially designed for facilitates navigation through the elements of a document for people with mobility difficulties.

import globalPluginHandler
import addonHandler
import appModuleHandler
import scriptHandler
import collections
import api
import ui
import tones

addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	scriptCategory = _("Easy Navigation")
	
	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		self.bindGesture("kb:shift+backspace", "toggleEasyNavigation")
		self.flagEasyNavigation = False
		self.ringIndex = 0
		Item = collections.namedtuple("easyNavigationRingItem", ("status", "name", "previous", "next"))
		self.easyNavigationRing = (
		Item(True, _("Lines"), "script_moveByLine_back", "script_moveByLine_forward"),
		Item(True, _("Headings"), "script_previousHeading", "script_nextHeading"),
		Item(True, _("Links"), "script_previousLink", "script_nextLink"),
		Item(True, _("Unvisited links"), "script_previousUnvisitedLink", "script_nextUnvisitedLink"),
		Item(True, _("Visited links"), "script_previousVisitedLink", "script_nextVisitedLink"),
		Item(True, _("Form fields"), "script_previousFormField", "script_nextFormField"),
		Item(True, _("Buttons"), "script_previousButton", "script_nextButton"),
		Item(True, _("Edit fields"), "script_previousEdit", "script_nextEdit"),
		Item(True, _("Check boxes"), "script_previousCheckBox", "script_nextCheckBox"),
		Item(True, _("Combo boxes"), "script_previousComboBox", "script_nextComboBox"),
		Item(True, _("Radio buttons"), "script_previousRadioButton", "script_nextRadioButton"),
		Item(True, _("Images"), "script_previousGraphic", "script_nextGraphic"),
		Item(True, _("Frames"), "script_previousFrame", "script_nextFrame"),
		Item(True, _("Articles"), "script_previousArticle", "script_nextArticle"),
		Item(True, _("Landmarks"), "script_previousLandmark", "script_nextLandmark"),
		Item(True, _("Separators"), "script_previousSeparator", "script_nextSeparator"),
		Item(True, _("Quotes"), "script_previousBlockQuote", "script_nextBlockQuote"),
		Item(True, _("Objects"), "script_previousEmbeddedObject", "script_nextEmbeddedObject"),
		Item(True, _("Lists"), "script_previousList", "script_nextList"),
		Item(True, _("List items"), "script_previousListItem", "script_nextListItem"),
		Item(True, _("Tables"), "script_previousTable", "script_nextTable"),
		Item(True, _("text blocks"), "script_previousNotLinkBlock", "script_nextNotLinkBlock"),
		Item(True, _("Searches"), "script_findPrevious", "script_findNext"))

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
		self.bindGesture("kb:rightArrow", "easyNavigationRingNextOption")
		self.bindGesture("kb:leftArrow", "easyNavigationRingPreviousOption")
		self.bindGesture("kb:downArrow", "easyNavigationNextItem")
		self.bindGesture("kb:upArrow", "easyNavigationPreviousItem")

	def disableEasyNavigation(self, toggleFlag=True):
		try:
			self.removeGestureBinding("kb:upArrow")
			self.removeGestureBinding("kb:downArrow")
			self.removeGestureBinding("kb:rightArrow")
			self.removeGestureBinding("kb:leftArrow")
		except:
			pass
		else:
			if toggleFlag: self.flagEasyNavigation = False

	def script_easyNavigationRingNextOption(self, gesture):
		ringIndex = self.ringIndex +1 if self.ringIndex+1 < len(self.easyNavigationRing) else 0
		while self.easyNavigationRing[ringIndex].status == False and ringIndex != self.ringIndex:
			ringIndex = ringIndex +1 if ringIndex+1 < len(self.easyNavigationRing) else 0
		self.ringIndex = ringIndex
		ui.message(self.easyNavigationRing[self.ringIndex].name)

	def script_easyNavigationRingPreviousOption(self, gesture):
		ringIndex = self.ringIndex -1 if self.ringIndex > 0 else len(self.easyNavigationRing)-1
		while self.easyNavigationRing[ringIndex].status == False and ringIndex != self.ringIndex:
			ringIndex = ringIndex -1 if ringIndex > 0 else len(self.easyNavigationRing)-1
		self.ringIndex = ringIndex
		ui.message(self.easyNavigationRing[self.ringIndex].name)

	def script_easyNavigationNextItem(self, gesture):
		treeInterceptor = api.getNavigatorObject().treeInterceptor
		scriptHandler.executeScript(getattr(treeInterceptor, self.easyNavigationRing[self.ringIndex].next), None)
		
	def script_easyNavigationPreviousItem(self, gesture):
		treeInterceptor = api.getNavigatorObject().treeInterceptor
		scriptHandler.executeScript(getattr(treeInterceptor, self.easyNavigationRing[self.ringIndex].previous), None)

	__gestures = {
	"kb:shift+backspace": "toggleEasyNavigation",
	}
