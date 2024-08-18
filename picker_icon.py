# Picker icon
from maya import OpenMayaUI, OpenMaya
import maya.mel as mel
import maya.cmds as cmds
from PySide2 import QtWidgets, QtGui, QtCore
import shiboken2, os, imp, sys, importlib
from functools import partial

root_path = os.path.dirname(os.path.abspath(__file__))
mod_name = root_path.split('\\')[-1]

import importlib, json
picker_mod = importlib.import_module(mod_name+'.picker')

def convertPathToPySideObject(name):
	ptr = OpenMayaUI.MQtUtil.findControl(name)
	if ptr is None:         
		ptr = OpenMayaUI.MQtUtil.findLayout(name)    
	if ptr is None:         
		ptr = OpenMayaUI.MQtUtil.findMenuItem(name)
	if ptr is not None:     
		try:
			return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)
		except:
			return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)

def togglePkr(v):
	with open(root_path+'/picker/config.json', mode='r') as f:
		configData = json.load(f)
	reloadPickers = configData["autoLoadPickersOnStart"]

	#v = b.isChecked()
	if not v:
		
		#try:
		if reloadPickers:
			try:
				cmds.deleteUI('Rig Studio Picker')
				OpenMaya.MMessage.removeCallback(picker_mod.main.picker_win.selectionEvent)
			except:
				print ("Cannot delete UI")
		else:
			#OpenMaya.MMessage.removeCallback(picker_mod.main.picker_win.selectionEvent)
			try:
				picker_mod.main.picker_win.parent().parent().parent().parent().parent().hide()
			except:
				print ("UI deleted")
		#except: pass
	else:
		if reloadPickers:
			if sys.version[0] == "2":
				reload(picker_mod)
			else:
				importlib.reload(picker_mod)
			win = picker_mod.main.run(edit=False)
		else:
			try:
				picker_mod.main.picker_win.parent().parent().parent().parent().parent().show()
				#picker_mod.main.picker_win.selectionEvent = OpenMaya.MEventMessage.addEventCallback("SelectionChanged", picker_mod.main.picker_win.selectionUpdate)		
			except:
				if sys.version[0] == "2":
					reload(picker_mod)
				else:
					importlib.reload(picker_mod)
				win = picker_mod.main.run(edit=False)				
			

#statusLineName = mel.eval("$tmp=$gStatusLine")
#statusLineObj = convertPathToPySideObject(statusLineName)
#label = QtWidgets.QLabel(statusLineObj)
#label.setText("  ")
#b = QtWidgets.QToolButton(statusLineObj)
#statusLineObj.layout().addWidget(label)
#b.setText("")
#b.setIcon(QtGui.QIcon(root_path+'/ui/icons/selector.png'))
#b.setIconSize(QtCore.QSize(20, 20))	
#b.setMaximumHeight(23)
#b.setAutoRaise(1)
#b.setCheckable(1)
#b.clicked.connect(partial(togglePkr, b))
#statusLineObj.layout().addWidget(b)


w = convertPathToPySideObject('characterControlsButton')
try: w.clicked.disconnect() 
except Exception: pass
w.clicked.connect(partial(togglePkr))