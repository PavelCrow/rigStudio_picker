import os, re, imp, types, weakref, json
from datetime import datetime, timedelta
from math import sin, cos, pi
from functools import partial

import maya.cmds as cmds
import pymel.core as pm
from maya import OpenMayaUI
from maya import OpenMaya
import maya.app.general.mayaMixin as mayaMixin 
import logging, traceback, sys

#import anim_picker
#import picker
#reload(picker)


if sys.version[0] == "2":
	import picker
	reload(picker)
	import rigStudio_picker.utils as utils
	reload(utils)
else:
	import importlib
	import rigStudio_picker.picker.picker as picker
	importlib.reload(picker)
	import rigStudio_picker.utils as utils
	importlib.reload(utils)
	import rigStudio_picker.animTools as animTools


try:
	from PySide2 import QtWidgets, QtGui, QtCore, QtUiTools
except:
	from Qt import QtWidgets, QtGui, QtCore, QtUiTools
try: from shiboken2 import wrapInstance
except: from shiboken import wrapInstance

root_path = os.path.dirname(os.path.abspath(__file__))
images_pth = os.path.join(root_path, "images")

full = os.path.isfile(root_path.replace('picker', "full")) or os.path.isfile(root_path+"/full")

rootDebug = ""
debug = False
#debug = True
snap_time = None
script_errors = False
# script_errors = True

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

with open(root_path+'/config.json', mode='r') as f:
	configData = json.load(f)

#configData['debug'] = True

def compileUI():
	try:
		from pyside2uic import compileUi
	except:
		from pysideuic import compileUi

	pyfile = open(root_path+'\\pickerWindow.py', 'w')
	compileUi(root_path+"\\pickerWindow.ui", pyfile, False, 4,False)
	pyfile.close()

	pyfile = open(root_path+'\\saveWindow.py', 'w')
	compileUi(root_path+"\\saveWindow.ui", pyfile, False, 4,False)
	pyfile.close()

#compileUI()

if sys.version[0] == "2":
	import pickerWindow, saveWindow
	reload(pickerWindow)
	reload(saveWindow)
else:
	import importlib
	import rigStudio_picker.picker.pickerWindow as pickerWindow
	import rigStudio_picker.picker.saveWindow as saveWindow
	importlib.reload(pickerWindow)
	importlib.reload(saveWindow)


def oneStepUndo(func):
	def wrapper(*args, **kwargs):
		cmds.undoInfo(openChunk=True)
		func(*args, **kwargs)
		cmds.undoInfo(closeChunk=True)
	return wrapper	

edit = True
rigFromJoints = False
save_geometry = False

def debug_function(func):
	def wrapper(*args, **kwargs):
		if debug:
			global rootDebug
			rootDebug = rootDebug + ' -> ' + func.__name__
			print (__file__.split("\\")[-1] , rootDebug)
			func(*args, **kwargs)
			print (__file__.split("\\")[-1] , rootDebug + " -| ")
			rootDebug = rootDebug.split(' -> ' + func.__name__)[0]
		else:
			func(*args, **kwargs)
	return wrapper	

def debugStart(func, noEnd=False):
	if not configData['debug']: return
	global rootDebug
	rootDebug = rootDebug + ' -> ' + func
	logger.debug(rootDebug + ' -> ')	

	if noEnd:
		rootDebug = rootDebug.split(' -> ' + func)[0]		

def debugEnd(func):
	if not configData['debug']: return
	global rootDebug
	logger.debug(rootDebug + " -| ")
	rootDebug = rootDebug.split(' -> ' + func)[0]


# =============================================================================
# Dependencies ---
# =============================================================================
def get_module_path():
	return os.path.dirname(os.path.abspath(__file__))

def get_maya_window():
	try:
		ptr = OpenMayaUI.MQtUtil.mainWindow()
		if sys.version[0] == "2":
			return wrap_instance(long(ptr), QtWidgets.QMainWindow)
		else:
			return wrap_instance(int(ptr), QtWidgets.QMainWindow)
	except Exception:
		#    fails at import on maya launch since ui isn't up yet
		return None

def get_images_folder_path():
	# Get the path to this file
	return os.path.join(get_module_path(), "images")

class GroupLabel(QtWidgets.QLabel):
	def __init__(self, label_widget, groupFrame, layout, win=None):
		super(GroupLabel, self).__init__()

		self.on = True
		self.setText(label_widget.text())
		self.setAlignment(QtCore.Qt.AlignHCenter)
		self.groupFrame = groupFrame
		self.win = win

		layout.insertWidget(0, self)
		label_widget.setVisible(False)

	def mousePressEvent(self, QMouseEvent):
		self.on = not self.on
		self.groupFrame.setVisible(self.on)

		if self.groupFrame.objectName() == "controls_groupFrame":
			if self.on:
				self.win.moduleOptions_dummy_label.setVisible(False)
			else:
				self.win.moduleOptions_dummy_label.setVisible(True)


class ContextMenuTabWidget(QtWidgets.QTabWidget):
	@debug_function	
	def __init__(self,
                 parent,
                 main_window=None,
                     *args, **kwargs):
		QtWidgets.QTabWidget.__init__(self, main_window, *args, **kwargs)
		self.main = parent
		self.main_window = main_window

		self.views = []
		self.cur_view = None

		self.currentChanged.connect(self.tab_switch)
		self.main_window.axises_checkBox.stateChanged.connect(self.toggleAxises)
		self.main_window.selection_border_checkBox.stateChanged.connect(self.selection_border)

	@debug_function	
	def tab_switch (self, i):
		# disconnect right buttons
		try: self.main_window.background_set_btn.clicked.disconnect()
		except: pass
		try: self.main_window.background_clear_btn.clicked.disconnect()
		except: pass
		try: self.main_window.back_offset_x_spinBox.valueChanged.disconnect()
		except: pass
		try: self.main_window.back_offset_y_spinBox.valueChanged.disconnect()
		except: pass
		try: self.main_window.back_flip_checkBox.clicked.disconnect()
		except: pass
		try: self.main_window.tab_visibility_checkBox.clicked.disconnect()
		except: pass
		try: 
			self.main_window.polygon_btn.clicked.disconnect()
			self.main_window.rect_btn.clicked.disconnect()
			self.main_window.text_btn.clicked.disconnect()
			self.main_window.circle_btn.clicked.disconnect()
			self.main_window.button_btn.clicked.disconnect()
			self.main_window.image_btn.clicked.disconnect()
			self.main_window.label_btn.clicked.disconnect()
		except: pass
		try: self.main_window.editShapes_btn.clicked.disconnect()
		except: pass
		try: self.main_window.opacity_slider.valueChanged.disconnect()
		except: pass

		if len(self.views) == 0:
			return

		self.cur_view = self.views[i]
		self.cur_view.data = self.main.cur_picker.data["tabs"][i]

		#self.main.views[self.main.cur_picker.name] = [self.cur_view]

		# connect right buttons 
		self.main_window.background_set_btn.clicked.connect( self.cur_view.set_background_event )
		self.main_window.background_clear_btn.clicked.connect( self.cur_view.reset_background_event )
		self.main_window.opacity_slider.valueChanged.connect( self.cur_view.set_background_opacity )
		self.main_window.back_flip_checkBox.clicked.connect( self.cur_view.flip_background )
		self.main_window.tab_visibility_checkBox.clicked.connect( self.cur_view.tab_visibility_update )
		self.main_window.polygon_btn.clicked.connect(self.cur_view.add_picker_item)
		self.main_window.rect_btn.clicked.connect(self.cur_view.add_rect_item)
		self.main_window.text_btn.clicked.connect(self.cur_view.add_text_item)
		self.main_window.circle_btn.clicked.connect(self.cur_view.add_circle_item)
		self.main_window.button_btn.clicked.connect(self.cur_view.add_button_item)
		self.main_window.image_btn.clicked.connect(self.cur_view.add_image_item)
		self.main_window.label_btn.clicked.connect(self.cur_view.add_label_item)
		#self.main_window.editShapes_btn.clicked.connect(self.cur_view.toggle_all_handles_event)
		self.main_window.back_offset_x_spinBox.valueChanged.connect(self.cur_view.background_offset_x_update)
		self.main_window.back_offset_y_spinBox.valueChanged.connect(self.cur_view.background_offset_y_update)

		# update opacity slider value
		self.main_window.opacity_slider.setValue(self.cur_view.background_opacity*100)
		self.main_window.back_offset_x_spinBox.setValue(self.cur_view.background_offset_x)
		self.main_window.back_offset_y_spinBox.setValue(self.cur_view.background_offset_y)
		self.main_window.back_flip_checkBox.setChecked(self.cur_view.background_flip)
		self.main_window.tab_visibility_checkBox.setChecked(self.cur_view.tab_visibility)

		self.main.view = self.cur_view

		if self.cur_view.selected_items:
			self.main.picker_item = self.cur_view.selected_items[-1]

		self.main.updateItemFrame()
		self.main.moveLock_update()

		# update view selected items
		#self.cur_view.selectItemsFromControls() # Disable for bug fix with hidden item

	@debug_function	
	def contextMenuEvent(self, event):
		### Right click menu options
		# Abort out of edit mode
		if not edit:
			return

		# Init context menu
		menu = QtWidgets.QMenu(self)

		# Build context menu
		rename_action = QtWidgets.QAction("Rename", None)
		rename_action.triggered.connect(self.rename_event)
		menu.addAction(rename_action)

		add_action = QtWidgets.QAction("Add Tab", None)
		add_action.triggered.connect(self.add_tab_event)
		menu.addAction(add_action)

		remove_action = QtWidgets.QAction("Remove Tab", None)
		remove_action.triggered.connect(self.remove_tab_event)
		menu.addAction(remove_action)

		# Open context menu under mouse
		menu.exec_(self.mapToGlobal(event.pos()))

	@debug_function	
	def fit_contents(self):
		return
		for i in range(self.count()):
			widget = self.widget(i)
			if not isinstance(widget, GraphicViewWidget):
				continue
			widget.fit_scene_content()

	@debug_function	
	def rename_event(self, event=None):
		# Get current tab index
		index = self.currentIndex()
		old_name = self.tabText(index)

		# Open input window
		name, ok = QtWidgets.QInputDialog.getText(self,
                                                  self.tr("Tab name"),
                                                  self.tr('New name'),
                                                          QtWidgets.QLineEdit.Normal,
                                                          self.tabText(index))
		if not (ok and name):
			return

		# Update influence name
		self.setTabText(index, name)
		self.cur_view.tab_name = name

		for i, t_data in enumerate(self.main.cur_picker.data["tabs"]):
			t_name = t_data["name"]
			if t_name == old_name:
				self.main.cur_picker.data["tabs"][i]["name"] = name

		self.main.save_picker()

	@debug_function	
	def add_tab_event(self):
		# Open input window
		name, ok = QtWidgets.QInputDialog.getText(self,
                                                  self.tr("Create new tab"),
                                                  self.tr("Tab name"),
                                                          QtWidgets.QLineEdit.Normal,
                                                          self.tr(""))
		if not (ok and name):
			return

		# create data
		data = self.main.cur_picker.data
		count = len(data["tabs"])

		tab_data = self.main.cur_picker.createTabData()
		tab_data["index"] = count
		tab_data["name"] = name
		data["tabs"].append(tab_data)		
		self.main.cur_picker.data = data

		# Add tab
		self.addTab(GraphicViewWidget(main=self.main, main_window=self.main_window, tab_name=name), name)

		# update views list
		#print 111, self.views, len(self.views)
		self.views = []
		for i in range(self.count()):
			view = self.widget(i)
			self.views.append(view)
		self.views[-1].index = len(self.views) - 1

		# Set new tab active
		self.setCurrentIndex(self.count() - 1)

		self.main.save_picker()

	@debug_function	
	def remove_tab_event(self):
		# Get current tab index
		index = self.currentIndex()
		name = self.tabText(index)

		# Open confirmation
		reply = QtWidgets.QMessageBox.question(self,
                                               "Delete",
                                               "Delete tab '{}'?".format(
                                                           self.tabText(index)),
                                                       QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                       QtWidgets.QMessageBox.No)
		if reply == QtWidgets.QMessageBox.No:
			return

		# Remove tab
		self.removeTab(index)
		del self.main.cur_picker.data["tabs"][index]

		# reset indexes
		self.views = []
		for i in range(self.count()):
			view = self.widget(i)
			self.views.append(view)
			view.index = i
			self.main.cur_picker.data["tabs"][i]["index"] = i

		self.main.save_picker()

	def getViewByName(self, name):
		for v in self.views:
			if v.tab_name == name:
				return v
		return None

	@debug_function	
	def toggleAxises(self, v=None):
		# refresh scene after changing
		self.cur_view.scene().update()

	@debug_function	
	def selection_border(self, v=None):
		# refresh scene after changing
		self.cur_view.scene().update()

	@debug_function	
	def autorunScript(self):
		return
		self.cur_view

	@debug_function	
	def get_namespace(self):
		return
		# Proper parent
		if self.main_window and isinstance(self.main_window, MainWindow):
			return self.main_window.get_current_namespace()

		return None

	@debug_function	
	def get_current_picker_items(self):
		return
		return self.currentWidget().get_picker_items()

	@debug_function	
	def get_all_picker_items(self):
		return
		items = []
		for i in range(self.count()):
			items.extend(self.widget(i).get_picker_items())
		return items

	@debug_function	
	def get_data(self):
		return
		# Will return all tabs data

		data = []
		for i in range(self.count()):
			name = str(self.tabText(i))
			tab_data = self.widget(i).get_data()
			data.append({"name": name, "data": tab_data})
		return data

	@debug_function	
	def set_data(self, data):
		return
		# Will, set/load tabs data

		#self.clear()
		#for tab in data:
			#view = GraphicViewWidget(namespace=self.get_namespace(), main=self.main,
								#main_window=self.main_window)
			#self.addTab(view, tab.get('name', 'default'))

			#tab_content = tab.get('data', None)
			#if tab_content:
				#view.set_data(tab_content)

		frame = QtWidgets.QFrame()
		layout = QtWidgets.QHBoxLayout( )
		frame.setLayout( layout )

		self.addTab(frame, 'frame')

		for tab in data:
			view = GraphicViewWidget(namespace=self.get_namespace(), main=self.main,
                                     main_window=self.main_window)
			layout.addWidget( view )			

			#tab_content = tab.get('data', None)
			#if tab_content:
				#view.set_data(tab_content)

	# @debug_function
	def keyPressEvent(self, event):
		if event.key() == QtCore.Qt.Key_Escape:
			#print ("ECS")
			return

		super(ContextMenuTabWidget, self).keyPressEvent(event)

		# Re-direct ESC key to closeEvent
		modifiers = event.modifiers()
		shift = modifiers == QtCore.Qt.ShiftModifier
		if edit:
			if event.key() == event.key() == QtCore.Qt.Key_W:
				self.main.item_move("up", shift)
			elif event.key() == event.key() == QtCore.Qt.Key_S:
				self.main.item_move("down", shift)
			elif event.key() == event.key() == QtCore.Qt.Key_A:
				self.main.item_move("left", shift)
			elif event.key() == event.key() == QtCore.Qt.Key_D:
				self.main.item_move("right", shift)

		if event.key() == QtCore.Qt.Key_Escape:
			# print "ECS", self, 1, self.main_window
			# self.parent().parent().parent().parent().parent().parent().parent().close()
			# self.main_window.close()
			pass


		#elif event.key() == QKeySequence.Copy:
			#self.actionCopy.trigger()
		pass

	def wheelEvent(self, event):
		pass


class GraphicViewWidget(QtWidgets.QGraphicsView):

	def __init__(self,
                 namespace=None, main=None,
                 main_window=None, tab_name=None):
		QtWidgets.QGraphicsView.__init__(self)

		self.setScene(OrderedGraphicsScene())

		self.namespace = namespace
		self.main = main
		self.main_window = main_window
		#try:
			#self.setParent(self.main_window)
		#except: 
			#print "cannot set parent"

		# Scale view in Y for positive Y values (maya-like)
		self.scale(1, 1)

		self.setResizeAnchor(self.AnchorViewCenter)

		# TODO
		# Set selection mode
		self.setRubberBandSelectionMode(QtCore.Qt.IntersectsItemBoundingRect)
		self.setDragMode(self.RubberBandDrag)
		self.scene_mouse_origin = QtCore.QPointF()
		self.doubleClick_select = False
		self.pan_active = False
		self.zoom_active = False
		self.drag_start = False
		self.drag_item = None
		self.ext_layers = self.main.get_external_layers()

		# Disable scroll bars
		self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		# Set background color
		brush = QtGui.QBrush(QtGui.QColor(70, 70, 70, 255))
		self.setBackgroundBrush(brush)

		# Disable blink on icon selecting in float mode of the main window
		self.setStyleSheet("border: 0px solid rgb(100, 0, 0)")

		self.tab_name = tab_name
		self.background_image = None
		self.background_opacity = 1
		self.background_image_path = None
		self.background_offset_x = 0
		self.background_offset_y = 0
		self.background_flip = False
		self.tab_visibility = True
		self.index = None
		self.items = []
		self.data = None
		self.selected_items = []
		self.item_menu = False
		self.moveLock = False
		self.autoKeyframe = False
		self.sizeValue = 1.000000
		self.centerValueX = 0.000000
		self.centerValueY = 0.000000
		self.zoom_pos = 0.000000
		self.init_zoom = 1.000000

		self.scene().set_size(2000, 2000)

	def get_center_pos(self):
		return self.mapToScene(QtCore.QPoint(self.width() / 2,
                                             self.height() / 2))

	def mousePressEvent(self, event):
		if event.button() == QtCore.Qt.LeftButton:
			scene_pos = self.mapToScene(event.pos())

			# Get current viewport transformation
			transform = self.viewportTransform()
			modifiers = event.modifiers()

			# if picker item below mouse
			if self.scene().itemAt(scene_pos, transform):
				#self.setDragMode(self.RubberBandDrag)
				item = self.scene().itemAt(scene_pos, transform)
				item = self.getPickerItemFromItem(item)

				if item:
					if not modifiers:
						self.drag_item = item

						# for mass moving
						for item_ in self.selected_items:	
							if item_ == item: continue
							item_.follow_offset = item.pos() - item_.pos()

						self.drag_start = True

						if self.drag_item.name.split("_")[-1] == 'slider':
							cmds.undoInfo(openChunk=True)
							self.autoKeyframe = cmds.autoKeyframe( q=1, state=True )
							if self.autoKeyframe:
								cmds.autoKeyframe( state=False )
						elif not edit:
							self.drag_item = None # Then area select from icon
		else:
			self.setDragMode(self.NoDrag)

		modifiers = event.modifiers()
		if modifiers == QtCore.Qt.AltModifier:		
			if event.button() == QtCore.Qt.MidButton:
				#self.setDragMode(self.NoDrag)
				self.pan_active = True
			if event.button() == QtCore.Qt.RightButton:	
				self.zoom_active = True
				self.zoom_pos = event.pos().x()
				self.init_zoom = self.matrix().m11()

		self.scene_mouse_origin = self.mapToScene(event.pos())

		QtWidgets.QGraphicsView.mousePressEvent(self, event)

	def getItemInPosition(self, scene_pos):
		transform = self.viewportTransform()
		sel_area = QtCore.QRectF(scene_pos.x(), scene_pos.y(), 2.0, 2.0)		
		items = self.scene().items(sel_area,
                                   QtCore.Qt.IntersectsItemShape,
                                   QtCore.Qt.AscendingOrder,
                                           deviceTransform=transform)		

		for item in items:
			item = self.getPickerItemFromItem(item)

			if item.layer in self.ext_layers or item.layer not in self.main.get_visible_internal_layers():
				continue

			return item

		return None

	def mouseMoveEvent(self, event):
		if self.pan_active:
			current_center = self.get_center_pos()
			scene_paning = self.mapToScene(event.pos())

			new_center = current_center - (scene_paning - self.scene_mouse_origin)
			self.centerOn(new_center)		

			return

		elif self.zoom_active:

			target_scale = self.init_zoom+(event.pos().x()-self.zoom_pos) * 0.01
			if target_scale < 0.5:
				target_scale = 0.5
			#elif target_scale > 5:
				#target_scale = 5
			scale_current = self.matrix().m11()
			factor = target_scale / scale_current
			#factor = 1.01
			#print (1111, factor)
			self.zoom(factor)

			return
			#print (2222, scale_current)

		if self.moveLock and edit:
			return				

		result = QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

		if event.modifiers():
			return

		if self.drag_item:
			if self.drag_item.slider:
				self.drag_item.update_slider()
			else:
				if self.drag_item not in self.selected_items and edit:
					self.selectItems([self.drag_item])
				for item in self.selected_items:

					if item.slider:
						continue
					if item != self.drag_item and not item.mirrored:
						item.update_followed_position(self.drag_item)
					#try: # if item is a point
					if item.mirror:
						item.mirror.update_mirrored_position()

		self.drag_start = False

		return result

	def getTopItem(self, items):
		top_item = None
		z_max = -1000
		for item in items:
			z = item.zValue()
			if z > z_max:
				z_max = z
				top_item = item
		return top_item

	def filterItems(self, items):
		filtered_items = []
		slider_items = []

		for item in items:
			item = self.getPickerItemFromItem(item)

			if not item:
				continue

			if item in filtered_items:
				continue

			if edit and item.layer not in self.main.get_visible_internal_layers():
				continue

			if item.slider:
				slider_items.append(item)

			if edit:
				if item.layer in self.ext_layers:
					#continue	# for selecting items from ext layers in edit mode
					pass

			else:
				if item.controls and not item.polygon.controlIsVisible() and not item.rmb_items:
					continue
				if item.polygon.opacity == 0:
					continue


			filtered_items.append(item)

			if len(slider_items) == 1:
				for i in filtered_items:
					if i.slider_item == slider_items[0]:
						filtered_items.remove(i)

		return filtered_items

	def selectItems(self, items, event=None, selectControls=True):
		debugStart(traceback.extract_stack()[-1][2])
		#print ("VIEW SelectItems Start", items, selectControls)

		sel = cmds.ls(sl=1)

		#if items and items == self.selected_items:
			#return

		if event:
			modifiers = event.modifiers()
		else:
			modifiers = None

		controls_for_remove = []

		if not modifiers:
			# clear selections
			for item in self.selected_items:
				item.set_selected_state(False)

			self.selected_items = []				

			# select items
			for item in items:
				item.set_selected_state(True)
				self.selected_items.append(item)	

		#elif modifiers == QtCore.Qt.ShiftModifier:
			#for item in items:
				#if item not in self.selected_items:	
					#item.set_selected_state(True)
					#self.selected_items.append(item)


		elif modifiers == QtCore.Qt.ControlModifier:
			if not items:
				return
			for item in items:
				if item in self.selected_items:		
					if not item.selectionOnClick:
						continue
					item.set_selected_state(False)
					self.selected_items.remove(item)
					for c in item.get_controls():
						if cmds.objExists(c):
							controls_for_remove.append(c)		
				else:	
					item.set_selected_state(True)
					self.selected_items.append(item)								

		#print ("Selected before", cmds.ls(sl=1))

		# Select controls if selecting only from picker
		#if event and event.button() == QtCore.Qt.RightButton:
			#return	

		self.main.skipSelectionUpdate = True
		if selectControls:
			
			if not edit or self.main.updateSelection:
				controls = []
				for item in self.selected_items:
					if not item.selectionOnClick:
						continue					
					for c in item.get_controls():
						if cmds.objExists(c):
							controls.append(c)
				if controls:
					if modifiers == QtCore.Qt.ControlModifier:
						self.main.win.autoLoadPicker_btn.setChecked(False)
						cmds.select(controls, add=1)
						self.main.win.autoLoadPicker_btn.setChecked(True)
					else:
						cmds.select(controls)
				#elif not sel:
					#cmds.select(clear=1)
				else:
					cmds.select(clear=1)

		if controls_for_remove:
			cmds.select(controls_for_remove, deselect=1)

		self.main.skipSelectionUpdate = False

		if edit:
			if self.selected_items:
				self.main.picker_item = self.selected_items[-1]
			else:
				self.main.picker_item = None
			self.main.updateItemFrame()	# Bug with hide items

		debugEnd(traceback.extract_stack()[-1][2])

		return self.selected_items

	@oneStepUndo
	def mouseReleaseEvent(self, event):
		debugStart(traceback.extract_stack()[-1][2])

		if self.doubleClick_select:
			debugEnd(traceback.extract_stack()[-1][2])
			return

		result = QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)

		transform = self.viewportTransform()
		scene_pos = self.mapToScene(event.pos())

		# Area selection
		sel_area = QtCore.QRectF(self.scene_mouse_origin, scene_pos)
		if event.button() == QtCore.Qt.LeftButton:
			if not sel_area.size().isNull() and not self.drag_item:
				#print ("area select")
				items = self.scene().items(sel_area, QtCore.Qt.IntersectsItemShape, QtCore.Qt.AscendingOrder, deviceTransform=transform)
				if not items: # second check, maybe size of the area 0 pixels in one of sides
					sel_area = QtCore.QRectF(scene_pos.x(), scene_pos.y(), 2.0, 2.0)	
					items = self.scene().items(sel_area, QtCore.Qt.IntersectsItemShape, QtCore.Qt.AscendingOrder, deviceTransform=transform)

				items = self.filterItems(items)

				# do not run command from button by area
				#last_sel_area = QtCore.QRectF(scene_pos.x(), scene_pos.y(), 5.0, 5.0)		
				#last_items = self.scene().items(last_sel_area,
											#QtCore.Qt.IntersectsItemShape,
															#QtCore.Qt.AscendingOrder,
															#deviceTransform=transform)				
				#last_items = self.filterItems(last_items)
				cmd_button = False 
				if len(items) == 1:# and last_items: 
					item = items[0]
					if not item.selectionOnClick and item.custom_action_script:
						#if not event.modifiers():
						cmd_button = item

				if not edit:
					items_for_select = []
					for item in items:
						if item.controls:
							items_for_select.append(item)
					items = items_for_select

				if not cmd_button: # for running script without deleselect
					self.selectItems(items, event)

				if cmd_button: 
					if not self.main.edit:
						cmd_button.run_script()


			else:
				#print ("click select")
				# Click selection
				sel_area = QtCore.QRectF(scene_pos.x(), scene_pos.y(), 2.0, 2.0)		
				items = self.scene().items(sel_area,
                                           QtCore.Qt.IntersectsItemShape,
                                           QtCore.Qt.AscendingOrder,
                                                       deviceTransform=transform)
				items = self.filterItems(items)
				item = self.getTopItem(items)

				# for slider end moving
				# if self.drag_item:
				# 	cmds.undoInfo(closeChunk=True)

				if item:

					if not edit and not item.controls:
						if self.main.match_rig:
							self.selected_items = [item]
					elif item in self.selected_items:
						# select item on single click only
						if event.modifiers() or self.drag_start:
							self.selectItems([item], event)
						elif self.drag_item:
							self.selectItems(self.selected_items, event)
							#self.main.picker_item = item
							#self.main.updateItemFrame()
					else:
						#if event.modifiers() != QtCore.Qt.ControlModifier:
						self.selectItems([item], event)

					if item.custom_action_script:
						# reset slider position if select with modifiers
						if event.modifiers() and item.slider:
							item.reset_slider()
						else:
							if not self.main.edit:
								item.run_script()			
				else:
					# for right mouse button click on clear area
					#if event.button() != QtCore.Qt.MidButton:
					self.selectItems([], event)

		if self.drag_item:
			if self.drag_item.name.split("_")[-1] == 'slider':
				cmds.undoInfo(closeChunk=True)
				if self.autoKeyframe:
					cmds.autoKeyframe( state=True )		
					self.drag_item.run_script()	# set keys

		self.item_menu = False
		self.drag_item = None
		self.drag_start = False
		self.setDragMode(self.RubberBandDrag)

		# Middle mouse view panning
		modifiers = event.modifiers()
		if modifiers == QtCore.Qt.AltModifier:
			if (self.pan_active and event.button() == QtCore.Qt.MidButton):
				current_center = self.get_center_pos()
				scene_drag_end = self.mapToScene(event.pos())

				new_center = current_center - (scene_drag_end -
                                               self.scene_mouse_origin)
				self.centerOn(new_center)
				self.pan_active = False

				self.centerValueX = self.get_center_pos().x()
				self.centerValueY = self.get_center_pos().y()
				cmds.optionVar( floatValue = ( "rsPicker_viewPosX_%s" %self.tab_name, self.centerValueX ) )
				cmds.optionVar( floatValue = ( "rsPicker_viewPosY_%s" %self.tab_name, self.centerValueY ) )
			if (self.zoom_active and event.button() == QtCore.Qt.RightButton):
				self.zoom_active = False
				self.sizeValue = self.matrix().m11()
				cmds.optionVar( floatValue = ( "rsPicker_viewSize_%s" %self.tab_name, self.sizeValue ) )	

		elif (event.button() == QtCore.Qt.RightButton):
			sel_area = QtCore.QRectF(scene_pos.x(), scene_pos.y(), 2.0, 2.0)	
			items = self.scene().items(sel_area, QtCore.Qt.IntersectsItemShape, QtCore.Qt.AscendingOrder, deviceTransform=transform)
			if not items: # second check, maybe size of the area 0 pixels in one of sides		
				self.main.selectItems([], event)
			##if not self.item_menu:
			#self.contextMenuEvent(event)
			#self.item_menu = True

		# fix lost viewport selection
		if not edit:
			name = pm.mel.eval("$tmp=$gMainWindow")
			cmds.showWindow(name)

		debugEnd(traceback.extract_stack()[-1][2])
		return result

	@oneStepUndo
	def mouseDoubleClickEvent(self, event):
		if edit:
			return

		modifiers = event.modifiers()
		transform = self.viewportTransform()
		scene_pos = self.mapToScene(event.pos())

		sel_area = QtCore.QRectF(scene_pos.x(), scene_pos.y(), 2.0, 2.0)		
		items = self.scene().items(sel_area,
                                   QtCore.Qt.IntersectsItemShape,
                                   QtCore.Qt.AscendingOrder,
                                           deviceTransform=transform)

		items = self.filterItems(items)

		if not items or not items[0].controls:
			return

		# Fix disable select set by second click and move
		self.doubleClick_select = True
		def stop():
			self.doubleClick_select = False
		QtCore.QTimer.singleShot(200, stop)		

		#self.selectItems(items, event)

		c_cur = None
		for c in items[0].get_controls():
			if cmds.objExists(c):
				c_cur = c
				break

		sets = cmds.listConnections(c_cur, type='objectSet') or []
		#print ("Cur_control", c_cur)


		sets_for_select = []
		for s in sets:
			if cmds.sets(s, q=1, text=1) == "gControlSet":
				if s not in sets_for_select:
					sets_for_select.append(s)		
		#print ("Select Set: ", sets_for_select)

		cur_is_sel = c_cur in cmds.ls(sl=1)


		#print ("Selected before select sets", cmds.ls(sl=1), cur_is_sel )	

		cmds.select(sets_for_select, tgl=1)
		if cur_is_sel:
			cmds.select(c_cur, add=1)
		else:
			cmds.select(c_cur, deselect=1)
		#print ("Selected after select sets", cmds.ls(sl=1))		


	def wheelEvent(self, event):

		# Run default event
		#QtWidgets.QGraphicsView.wheelEvent(self, event)

		#modifiers = event.modifiers()

		#if modifiers == QtCore.Qt.ControlModifier:
		scale_current = self.matrix().m11()
		# Define zoom up factor
		factor = 1.1
		#print event.delta()
		if event.delta() < 0:
			factor = 0.9

			## disable zoom below 1.0.  1.2 for bug fixing
			#if scale_current > 1.2:
				## Define zoom down factor
				#factor = 0.9
			#else:
				#factor = 1
				#self.setMatrix(QtGui.QMatrix(1,0,0,1,0,0))


		# Apply zoom
		#scene_pos = self.mapToScene(event.pos())

		self.zoom(factor )
		# self.get_center_pos())
		# self.mapToScene(event.pos()))
		pass

	def zoom(self, factor, center=QtCore.QPointF(0, 0)):
		center = self.get_center_pos()
		self.scale(factor, factor)
		#self.centerOn(center)

		#self.sizeValue = self.matrix().m11()
		#cmds.optionVar( floatValue = ( "rsPicker_viewSize_%s" %self.tab_name, self.sizeValue ) )

	def selectItemsFromControls(self):
		debugStart(traceback.extract_stack()[-1][2])
		#print "selectItemsFromControls"
		sel = cmds.ls(sl=1)

		items = []

		if sel: 
			for item in self.items:
				if not item.selectionOnClick:
					continue				
				if len(item.controls) > 0:
					for c in item.get_controls():
						if c in sel:
							items.append(item)


		# Select controls if selecting only from picker			
		self.selectItems(items, selectControls=False)

		debugEnd(traceback.extract_stack()[-1][2])

	def contextMenuEvent(self, event):
		# Right click menu options

		print ("MENU")
		if self.item_menu:
			return

		modifiers = event.modifiers()
		if modifiers == QtCore.Qt.AltModifier:
			return

		# Item area
		#item = self.getItemInPosition(event.pos())
		#item = self.itemAt(event.pos())
		#picker_item = self.getPickerItemFromItem(item)

		if event.pos() == QtCore.QPoint(0, 0):

			return

		#if picker_item and picker_item.layer in self.ext_layers:
			#picker_item = None

		# Init context menu
		menu = QtWidgets.QMenu(self)
		actions = []

		if edit and self.selected_items:
			#if self.selected_items:
				#if picker_item in self.selected_items:
					#pass
				#else:
					#for item in self.selected_items:
						#item.set_selected_state(False)		
					#self.selected_items = [picker_item]
					#picker_item.set_selected_state(True)
			#else:
				#self.selected_items = [picker_item]
				#picker_item.set_selected_state(True)



			# Build Edit move options
			if edit:
				#if picker_item.layer not in self.ext_layers and picker_item.layer in self.main.get_visible_internal_layers():
				dup_action = QtWidgets.QAction("Duplicate", None)
				dup_action.triggered.connect(self.duplicate_picker_item)
				menu.addAction(dup_action)
				mirror_action = QtWidgets.QAction("Create Mirror", None)
				mirror_action.triggered.connect(self.mirror_picker_item)
				menu.addAction(mirror_action)
				flip_action = QtWidgets.QAction("Flip", None)
				flip_action.triggered.connect(self.flip_picker_item)
				menu.addAction(flip_action)
				delete_action = QtWidgets.QAction("Delete", None)
				delete_action.triggered.connect(self.delete_picker_item)
				menu.addAction(delete_action)

				self.item_menu = True


		else:

			if edit:
				# Build Edit move options
				polygon_action = QtWidgets.QAction("Add Polygon", None)
				polygon_action.triggered.connect(partial(self.add_picker_item, event))
				menu.addAction(polygon_action)
				actions.append(polygon_action)				

				rect_action = QtWidgets.QAction("Add Rectangle", None)
				rect_action.triggered.connect(partial(self.add_rect_item, event))
				menu.addAction(rect_action)
				actions.append(rect_action)				

				circle_action = QtWidgets.QAction("Add Circle", None)
				circle_action.triggered.connect(partial(self.add_circle_item, event))
				menu.addAction(circle_action)
				actions.append(circle_action)				

				label_action = QtWidgets.QAction("Add Label", None)
				label_action.triggered.connect(partial(self.add_label_item, event))
				menu.addAction(label_action)
				actions.append(label_action)				

				text_action = QtWidgets.QAction("Add Text", None)
				text_action.triggered.connect(partial(self.add_text_item, event))
				menu.addAction(text_action)
				actions.append(text_action)				

				button_action = QtWidgets.QAction("Add Button", None)
				button_action.triggered.connect(partial(self.add_button_item, event))
				menu.addAction(button_action)
				actions.append(button_action)				

				slider_action = QtWidgets.QAction("Add Slider", None)
				slider_action.triggered.connect(partial(self.add_slider_item, event))
				menu.addAction(slider_action)
				actions.append(slider_action)				

				image_action = QtWidgets.QAction("Add Image..", None)
				image_action.triggered.connect(partial(self.add_image_item, event))
				menu.addAction(image_action)
				actions.append(image_action)				

				menu.addSeparator()

				background_action = QtWidgets.QAction("Set background image..", None)
				background_action.triggered.connect(self.set_background_event)
				menu.addAction(background_action)

				reset_background_action = QtWidgets.QAction("Reset background",
                                                            None)
				func = self.reset_background_event
				reset_background_action.triggered.connect(func)
				menu.addAction(reset_background_action)

				menu.addSeparator()

			else:
				item = self.itemAt(event.pos())
				picker_item = self.getPickerItemFromItem(item)

				if "RMBRun" in picker_item.custom_action_script:

					run_cmd = picker_item.custom_action_script.split("RMBRunStart\"")[1].split("\"RMBRunEnd")[0]
					exec(run_cmd)

				elif picker_item and picker_item.rmb_items:
					for a_name in picker_item.rmb_items:
						action = QtWidgets.QAction(a_name, None)
						action.triggered.connect(partial(self.run_rmb_command, picker_item, a_name))
						menu.addAction(action)
						actions.append(action)
						self.item_menu = True

				else:
					return

		# Open context menu under mouse
		menu.exec_(self.mapToGlobal(event.pos()))
		pass

	def add_picker_item(self, event=None, setData=True):
		item = PickerItem(main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self)

		item.setParent(self)

		self.add_item(item, event, setData)

		return item

	def add_rect_item(self, event=None, setData=True):
		item = PickerItem(main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self)
		item.setParent(self)
		item.polygon.shape_type = "rect"
		item.polygon.radius = 0

		self.add_item(item, event, setData)

		return item

	def add_item(self, item, event, setData, slider=None):
		self.scene().addItem(item)
		self.items.append(item)

		# set name
		i=1
		name = "item_"+str(i)

		names = []
		for it in self.items:
			if it.name:
				#print it.name
				names.append(it.name)
		#print len(names)

		while(name in names):
			i += 1
			name = "item_"+str(i)	
		item.name = name

		#print name
		try:
			item.layer = self.main.win.layers_tableWidget.currentItem().text()
		except:
			item.layer = "default"

		# Move item
		if event:
			item.setPos(self.mapToScene(event.pos()))
		else:
			item.setPos(0, 0)

		if setData:
			data = item.get_data()
			self.data["items"].append(data)

	def add_text_item(self, event=None, setData=True):
		item = PickerItem(main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self)
		item.setParent(self)
		item.polygon.shape_type = "text"
		item.polygon.radius = 0
		item.polygon.opacity = 0
		item.polygon.width = 60
		item.polygon.height = 40
		item.add_text_widget()

		self.add_item(item, event, setData)

		return item

	def add_button_item(self, event=None, setData=True):
		item = PickerItem(main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self)
		item.setParent(self)
		item.polygon.shape_type = "button"
		item.polygon.opacity = 0
		item.polygon.width = 60
		item.polygon.height = 40
		item.add_button_widget()

		self.add_item(item, event, setData)

		return item

	def add_circle_item(self, event=None, setData=True):
		item = PickerItem(main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self)
		item.setParent(self)
		item.polygon.shape_type = "circle"

		self.add_item(item, event, setData)

		return item

	def add_image_item(self, event=None, setData=True):
		file_path = QtWidgets.QFileDialog.getOpenFileName(self,"Open Image File",images_pth)[0]
		if not file_path:
			return
		item = PickerItem(main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self)
		item.setParent(self)
		item.polygon.image = QtGui.QImage(file_path)#.mirrored(False, True)
		item.polygon.image_path = file_path
		item.polygon.generate_grey_image()
		item.polygon.render_image = item.polygon.image		
		item.set_handles(item.get_default_handles())

		self.add_item(item, event, setData)

		return item

	def add_slider_item(self, event=None, setData=True):
		item = PickerItem(main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self)
		item.setParent(self)
		item.polygon.shape_type = "slider_back"
		item.polygon.radius = 0

		self.add_item(item, event, setData)

		item.polygon.width = 100
		item.polygon.height = 100		

		item.add_slider_widget()

		return item

	def add_label_item(self, event=None, setData=True):
		item = PickerItem(main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self)
		item.set_text("Label")
		item.polygon.opacity = 0
		item.setParent(self)

		self.add_item(item, event, setData)

		return item

	def delete_picker_item(self):
		views = self.main.views[self.main.cur_picker.name]

		for item in self.selected_items:
			if item.slider_item:
				self.items.remove(item.slider_item)
			if item.mirror:
				self.items.remove(item.mirror)
				if item.mirror.slider_item:
					self.items.remove(item.mirror.slider_item)				

			if item in self.items: # if item already removed as mirrored or slider for example
				self.items.remove(item)
				item.remove()


		for view in views:
			view.selected_items = []
		self.main.picker_item = None
		self.main.updateItemFrame()

	def duplicate_picker_item(self):
		new_items = []
		for item in self.selected_items:
			new_item = item.duplicate()
			new_items.append(new_item)

		self.selectItems(new_items)
		self.main.picker_item = self.selected_items[-1]
		self.main.updateItemFrame()

	def mirror_picker_item(self):
		for item in self.selected_items:
			item.create_mirror()

	def flip_picker_item(self):
		for item in self.selected_items:
			item.flip()

	def toggle_all_handles_event(self, event=None):
		new_status = None
		for item in self.scene().items():
			# Skip non picker items
			if not isinstance(item, PickerItem):
				continue

			# Get first status
			if new_status is None:
				new_status = not item.get_edit_status()

			# Set item status
			item.set_edit_status(new_status)

	def toggle_mode_event(self, event=None):
		if not self.main_window:
			return

		# Check for possible data change/loss
		if edit:
			if not self.main.check_for_data_change():
				return

		# Toggle mode
		self.main.edit = not self.main.edit

		# Reset size to default
		#self.main_window.reset_default_size()
		#self.main_window.refresh()
		pass

	def set_background(self, path=None):
		if not path:
			return
		path = str(path)

		#if not os.path.isfile(path):
		rel_path = path.split('picker')[-1]
		path = root_path + rel_path		

		self.background_image_path = path

		# Check that path exists
		if not (path and os.path.exists(path)):
			print ("# background image not found: '{}'".format(path))
			return		

		# Load image and mirror it vertically
		self.background_image = QtGui.QImage(path)#.mirrored(False, True)

		# Set scene size to background picture
		width = self.background_image.width()
		height = self.background_image.height()
		self.scene().set_size(width, height)
		self.data["background"] = self.background_image_path		

	def set_background_event(self, event=None):
		# Open file dialog
		img_dir = os.path.join(root_path, "images")
		file_path = QtWidgets.QFileDialog.getOpenFileName(self,
                                                          "Pick a background",
                                                          img_dir)

		# Filter return result (based on qt version)
		if isinstance(file_path, tuple):
			file_path = file_path[0]

		# Abort on cancel
		if not file_path:
			return

		# Set background
		self.set_background(file_path)

	def set_background_opacity(self, v):
		try:
			self.background_opacity = v * 0.01
			self.main_window.opacity_lineEdit.setText(str(self.main_window.opacity_slider.value()))
			self.main.cur_picker.data["tabs"][self.index]["background_opacity"] = self.background_opacity
			self.scene().update()
		except: pass

	def reset_background_event(self, event=None):
		self.background_image = None
		self.background_image_path = None
		self.background_opacity = 1.0
		self.background_flip = False
		self.tab_visibility = True
		self.scene().set_size(200, 200)
		self.main_window.opacity_slider.setValue(100)

		self.data["background"] = None	
		self.data["background_opacity"] = 1.0	
		self.data["background_offset_x"] = 0
		self.data["background_offset_y"] = 0
		self.data["background_flip"] = False
		self.data["tab_visibility"] = True
		self.main_window.back_offset_x_spinBox.setValue(0)
		self.main_window.back_offset_y_spinBox.setValue(0)		

	def run_rmb_command(self, item, name, var=None):
		tab_widget = self.main.tab_widgets[self.main.cur_picker.name]
		for i, item_name in enumerate(item.rmb_items):
			#print (3333, i, item_name, name, var)
			if item_name == name:
				#print (555, var)
				cmd = item.rmb_scripts[i]
				globalsParameter = {'tab_widget': tab_widget, 'item': item, 'self': item, 'var': var }
				exec (cmd)#, globalsParameter)					

	def background_offset_x_update(self, v=None):
		try:
			self.background_offset_x = self.main_window.back_offset_x_spinBox.value()
			self.main.cur_picker.data["tabs"][self.index]["background_offset_x"] = self.background_offset_x
			self.scene().update()
		except: pass

	def background_offset_y_update(self):
		try:
			self.background_offset_y = self.main_window.back_offset_y_spinBox.value()
			self.main.cur_picker.data["tabs"][self.index]["background_offset_y"] = self.background_offset_y
			self.scene().update()
		except: pass

	def clear(self):
		old_scene = self.scene()
		self.setScene(OrderedGraphicsScene())
		old_scene.deleteLater()

	def get_picker_items(self):
		items = []
		for item in self.scene().items():
			# Skip non picker graphic items
			if not isinstance(item, PickerItem):
				continue

			# Add picker item to filtered list
			items.append(item)

		# Reverse list order (to return back to front)
		items.reverse()

		return items

	def get_data(self):
		# Return view data

		data = {}

		# Add background to data
		if self.background_image_path:
			if not os.path.isfile(self.background_image_path):
				rel_path = self.background_image_path.split('picker')[-1]
				self.background_image_path = root_path + rel_path					
			#print 1111, self.background_image_path	
			data["background"] = self.background_image_path

		# Add items to data
		items = []
		for item in self.get_picker_items():
			items.append(item.get_data())
		if items:
			data["items"] = items

		return data

	def set_data(self, data):
		# Set/load view data

		self.clear()

		# Set backgraound picture
		background = data.get("background", None)
		if background:
			self.set_background(background)

		# Add items to view
		for item_data in data.get("items", []):
			item = self.add_picker_item()
			item.set_data(item_data)

	def drawBackground(self, painter, rect):
		# Default method override to draw view custom background image

		# Run default method
		result = QtWidgets.QGraphicsView.drawBackground(self, painter, rect)

		# Stop here if view has no background
		if not self.background_image:
			return result

		# Draw background image
		if self.background_flip:
			transform = QtGui.QTransform()
			transform.scale(-1, 1)
			img = self.background_image.transformed(transform)			
		else:
			img = self.background_image#.convertToFormat(QtGui.QImage.Format_RGB32)
		painter.setOpacity(self.background_opacity)
		painter.drawImage(self.sceneRect(),
                          #painter.drawImage(QtCore.QRectF(-100.000000, -100.000000, 200.000000, 200.000000),
                          img,
                                  QtCore.QRectF(self.background_image.rect().x() + self.background_offset_x, 
                                                self.background_image.rect().y() + self.background_offset_y, 
                                                        self.background_image.rect().width(), 
                                                                        self.background_image.rect().height()))
		#print self.background_image.bitPlaneCount()
		return result

	def drawForeground(self, painter, rect):
		# Default method override to draw origin axis in edit mode

		# Run default method
		result = QtWidgets.QGraphicsView.drawForeground(self, painter, rect)

		# Paint axis in edit mode
		if edit:
			self.draw_overlay_axis(painter, rect)

		return result

	def draw_overlay_axis(self, painter, rect):
		# Draw x and y origin axis

		if not self.main_window.axises_checkBox.isChecked():
			return

		# Set Pen
		pen = QtGui.QPen(QtGui.QColor(160, 160, 160, 120),
                         1,
                         QtCore.Qt.DashLine)
		painter.setPen(pen)

		# Get event rect in scene coordinates
		# Draw x line
		if rect.y() < 0 and (rect.height() - rect.y()) > 0:
			x_line = QtCore.QLine(rect.x(),
                                  0,
                                  rect.width() + rect.x(),
                                              0)
			painter.drawLine(x_line)

		# Draw y line
		if rect.x() < 0 and (rect.width() - rect.x()) > 0:
			y_line = QtCore.QLineF(0, rect.y(),
                                   0, rect.height() + rect.y())
			painter.drawLine(y_line)


		# bg border 
		if self.background_image:
			width = self.background_image.width()/2
			height = self.background_image.height()/2

			pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 120), 1)
			painter.setPen(pen)		
			top_line = QtCore.QLineF(-width, -height, width, -height)
			painter.drawLine(top_line)
			bot_line = QtCore.QLineF(-width, height, width, height)
			painter.drawLine(bot_line)
			left_line = QtCore.QLineF(-width, height, -width, -height)
			painter.drawLine(left_line)
			right_line = QtCore.QLineF(width, height, width, -height)
			painter.drawLine(right_line)

	def get_item_by_name(self, name):
		for item in self.items:
			if item.name == name:
				return item
		return None

	def get_named_controls(self):
		controls = {}
		for item in self.items:
			if item.controls:
				controls[item.name] = item.controls
		return controls

	def get_all_named_controls(self):
		tab_widget = self.main.tab_widgets[self.main.cur_picker.name]
		controls = {}
		for view in tab_widget.views:
			for item in view.items:
				if item.controls:
					controls[item.name] = item.controls
		return controls

	def flip_background(self):
		self.background_flip = self.main_window.back_flip_checkBox.isChecked()
		self.main.cur_picker.data["tabs"][self.index]["background_flip"] = self.background_flip
		self.scene().update()

	def tab_visibility_update(self):
		self.tab_visibility = self.main_window.tab_visibility_checkBox.isChecked()
		self.main.cur_picker.data["tabs"][self.index]["tab_visibility"] = self.tab_visibility
		self.scene().update()

	def getPickerItemFromItem(self, item):
		if type(item) is GraphicText:
			return item.parent

		elif type(item) is Polygon:
			return item.parent()

		elif type(item) is PointHandle:
			return item.parent()

		elif type(item) is QtWidgets.QGraphicsProxyWidget:
			return item.parentObject()

		if not item:
			return None

		if item.polygon.opacity == 0:
			return None

		return item


class OrderedGraphicsScene(QtWidgets.QGraphicsScene):

	def __init__(self, parent=None):
		QtWidgets.QGraphicsScene.__init__(self, parent=parent)

		#heith = 400
		#width = 400
		#self.set_size(width, heith)
		self._z_index = 0

	def set_size(self, width, heith):
		# Will set scene size with proper center position

		self.setSceneRect(-width / 2, -heith / 2, width, heith)

	def get_bounding_rect(self, margin=0):
		# Return scene content bounding box with specified margin
		# Warning: In edit mode, will return default scene rectangle

		# Return default size in edit mode
		if edit:
			return self.sceneRect()

		# Get item boundingBox
		scene_rect = self.itemsBoundingRect()

		# Stop here if no margin
		if not margin:
			return scene_rect

		# Add margin
		scene_rect.setX(scene_rect.x() - margin)
		scene_rect.setY(scene_rect.y() - margin)
		scene_rect.setWidth(scene_rect.width() + margin)
		scene_rect.setHeight(scene_rect.height() + margin)

		return scene_rect

	def clear(self):
		# Reset default z index on clear

		QtWidgets.QGraphicsScene.clear(self)
		self._z_index = 0

	def set_picker_items(self, items):
		self.clear()
		for item in items:
			QtWidgets.QGraphicsScene.addItem(self, item)
			self.set_z_value(item)
		self.add_axis_lines()

	def get_picker_items(self):
		picker_items = []
		# Filter picker items (from handles etc)
		for item in self.items():
			if not isinstance(item, PickerItem):
				continue
			picker_items.append(item)
		return picker_items

	def set_z_value(self, item):
		item.setZValue(self._z_index)
		self._z_index += 1

	def addItem(self, item):
		QtWidgets.QGraphicsScene.addItem(self, item)
		self.set_z_value(item)


class GraphicText(QtWidgets.QGraphicsSimpleTextItem):
	__DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 255)

	def __init__(self, parent=None, scene=None):
		QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

		# Counter view scale
		self.scale_transform = QtGui.QTransform().scale(1, 1)
		self.setTransform(self.scale_transform)

		# Init default size
		self.set_size()
		self.set_color(GraphicText.__DEFAULT_COLOR__)

		self.parent = parent
		self.opacity = 255
		self.visible = True

	def set_text(self, text):
		self.setText(text)
		self.center_on_parent()

	def get_text(self):
		return str(self.text())

	def set_size(self, value=10.0):
		font = self.font()
		#font.setPointSizeF(value)
		font.setPixelSize(value*1.4)
		font.setBold(True)
		self.setFont(font)
		self.center_on_parent()

	def get_size(self):
		return self.font().pointSizeF()

	def get_color(self):
		return self.brush().color()

	def set_color(self, color=None):
		if not color:
			return
		brush = self.brush()
		brush.setColor(color)
		self.setBrush(brush)

	def set_opacity(self, value):
		self.opacity = value
		color = self.brush().color()
		new_color = QtGui.QColor(color.red(), color.green(), color.blue(), value)

		brush = self.brush()
		brush.setColor(new_color)
		self.setBrush(brush)

	def center_on_parent(self):
		center_pos = self.boundingRect().center()
		#self.setPos(-center_pos * self.scale_transform)
		self.setPos(-center_pos)

	def paint(self, painter, options, widget=None):
		if not edit and self.parent.controls:
			if not self.parent.polygon.controlIsVisible():
				return
		if self.parent.visible: # or (edit and self.parent.main.showHidden):
			super(GraphicText, self).paint(painter, options, widget)


class DefaultPolygon(QtWidgets.QGraphicsObject):
	__DEFAULT_COLOR__ = QtGui.QColor(0, 0, 0, 255)

	def __init__(self, parent=None):
		QtWidgets.QGraphicsObject.__init__(self, parent=parent)

		if parent:
			self.setParent(parent)

		# Hover feedback
		self.setAcceptHoverEvents(True)
		self._hovered = False

		# Init default
		self.color = DefaultPolygon.__DEFAULT_COLOR__

	def hoverEnterEvent(self, event=None):
		if type(self) == PickerItem: return
		#print "HOVER IN", self.parent().name, self.parent().zValue()
		QtWidgets.QGraphicsObject.hoverEnterEvent(self, event)
		self._hovered = True
		self.update()

	def hoverLeaveEvent(self, event=None):
		if type(self) == PickerItem: return
		#print "HOVER OUT", self.parent().name
		QtWidgets.QGraphicsObject.hoverLeaveEvent(self, event)
		self._hovered = False
		self.update()

	def boundingRect(self):
		return self.shape().boundingRect()

	def get_color(self):
		return self.color

	def set_color(self, color=None):
		if not color:
			color = self.__DEFAULT_COLOR__
		elif isinstance(color, (list, tuple)):
			color = QtGui.QColor(*color)

		msg = "input color '{}' is invalid".format(color)
		assert isinstance(color, QtGui.QColor), msg

		self.color = color
		self.update()

		return color


class Polygon(DefaultPolygon):
	__DEFAULT_COLOR__ = QtGui.QColor(200, 200, 200, 180)

	def __init__(self, parent=None, points=[], color=None):
		DefaultPolygon.__init__(self, parent=parent)
		self.points = points
		self.set_color(Polygon.__DEFAULT_COLOR__)

		self._edit_status = False
		self.selected = False
		self.opacity = 255
		self.image_path = None
		self.image = None
		self.grey_image = None
		self.render_image = None
		self.shape_type = "polygon"
		self.path_type = "linear"
		self.height = 20
		self.width = 40
		self.radius = 10
		self.squash = 1.0
		self.rotate = 0
		self.flipped = False
		self.select_color = QtGui.QColor(1, 1, 0, 1)
		self.par = self.parent()
		self.mr = self.par.main.match_rig

	def set_edit_status(self, status=False):
		self._edit_status = status
		self.update()

	def shape(self):
		path = QtGui.QPainterPath()

		# Polygon case
		if self.shape_type == "polygon":
			# Define polygon points for closed loop
			shp_points = []
			for handle in self.points:
				shp_points.append(handle.pos())
			shp_points.append(self.points[0].pos())

			if self.path_type == "linear":
				polygon = QtGui.QPolygonF(shp_points)
				path.addPolygon(polygon)

			elif self.path_type == "quadratic":	
				path.moveTo(shp_points[0])

				for i, x in enumerate(shp_points):
					if i == 0:
						continue					
					if i == len(shp_points):
						continue
					if i % 2 == 0:
						path.quadTo(shp_points[i-1], shp_points[i])

			elif self.path_type == "cubic":
				path.moveTo(shp_points[0])

				for i, x in enumerate(shp_points):
					if i == 0:
						continue					
					if i == len(shp_points):
						continue
					if i % 3 == 0:
						path.cubicTo(shp_points[i-2], shp_points[i-1], shp_points[i])



		elif self.shape_type == "rect" or self.shape_type == "slider_back":
			if self.radius:
				path.addRoundRect(QtCore.QRectF(self.width * -0.5, self.height * -0.5, self.width, self.height), self.radius)
			else:
				path.addRect(QtCore.QRectF(self.width * -0.5, self.height * -0.5, self.width, self.height))

		elif self.shape_type == "text" or self.shape_type == "button":
			path.addRect(QtCore.QRectF(self.width * -0.5, self.height * -0.5, self.width, self.height))

		elif self.shape_type == "circle":
			path.addEllipse(self.radius * -1 * self.squash,
                            self.radius * -1,
                            self.radius * 2 * self.squash,
                                        self.radius * 2)

		return path

	def shapeIsVisible(self, name):
		# get dag path of the object
		try:
			slist = OpenMaya.MSelectionList()
			slist.add(name)
			dagpath = OpenMaya.MDagPath()

			# get shape
			slist.getDagPath(0, dagpath)
			dagpath.extendToShapeDirectlyBelow( 0 )

			# return visibility
			return dagpath.isVisible()
		except:
			return None

	def controlIsVisible(self):
		for c in self.par.get_controls():
			# for match rig skip
			if self.mr and cmds.objExists(c) and cmds.objectType(c) == 'joint':
				return True
			if self.shapeIsVisible(c):
				return True
		return False

	def paint(self, painter, options, widget=None):
		#if self.par.name == "face_head":
			#print (2222, self.parent().name , self.parent().visible)
		if not self.parent().visible and edit:
			self.parent().setZValue(-1) # hover fix
			return
		#print "PAINT 1", self.parent().name, self.parent().controls
		if not self.par.main:
			return
		if not edit and "reset" in self.par.name:
			self.par.setEnabled(self.par.main.mirSymResetButtons)
			#self.par.setVisible(self.par.main.mirSymResetButtons)
			self.par.text.setVisible(self.par.main.mirSymResetButtons)
			if not self.par.main.mirSymResetButtons:
				self.opacity = 0
				return
			else:
				self.opacity = 255
		if not edit and "slider" in self.par.name:
			self.par.setEnabled(self.par.main.useFingerSliders)
			#self.par.setVisible(self.par.main.useFingerSliders)
			#self.par.selectionOnClick = False
			if not self.par.main.useFingerSliders:
				return
		#print "PAINT 2", self.parent().name, self.parent().controls, self.controlIsVisible()
		#if 'l_lowerlid1' in self.parent().controls:
			#self.controlIsVisible()

		# disable selecting if controls is hidden
		if not self.par.main.match_rig:
			if not edit or (edit and not self.par.main.showHidden):
				if self.par.controls:
					if not self.controlIsVisible():
						self.parent().setZValue(-1)
						self.par.text.visible=False
						return

		#print "PAINT", self.parent().name#, self.selected
		painter.setRenderHint(QtGui.QPainter.Antialiasing)

		self.parent().setZValue(1) # hover fix
		self.par.text.visible = True

		# Get polygon path
		path = self.shape()

		# Background color
		if self.image_path:
			if self._hovered:
				painter.setOpacity(float(self.opacity)/255*0.8)
			else:
				painter.setOpacity(float(self.opacity)/255)

			# rotate
			transform = QtGui.QTransform()
			transform.rotate(self.rotate)
			if self.flipped: transform.scale(-1, 1)
			img = self.render_image.transformed(transform)
			painter.drawImage(QtCore.QPoint(0, 0), img)

		elif self.shape_type == "slider_back":
			pass

		else:
			#if self.selected and self.par.selectionOnClick and not edit:
			if self.selected and not edit and self.par.selectionOnClick:
				brush = QtGui.QBrush(QtGui.QColor(250, 250, 0, 250))
			else:
				color = QtGui.QColor(self.color.red(), self.color.green(), self.color.blue(), self.opacity)
				if self._hovered:
					color = color.lighter(130)
				brush = QtGui.QBrush(color)

			painter.fillPath(path, brush)			
			#if self.par.name == "face_head":
				#print (444)				

		# Border status feedback
		borders = self.par.parent().main_window.selection_border_checkBox.isChecked()
		if edit and borders:
			border_pen = QtGui.QPen(QtGui.QColor(250, 250, 0, 250))
			border_pen.setWidthF(2)
			if self.selected:
				painter.setPen(border_pen)
				painter.drawPath(path)
				self.par.view.update() # fix border trailing


		else:
			#print (self.par.name, self.selected)
			if self.selected:
				pass
			elif self.par.le:
				print (self.par.name)
				pass
			elif self.par.get_text() and self.par.get_text() != " ":
				pass
			elif self.image_path:
				pass
			#else:
				#border_pen = QtGui.QPen(QtGui.QColor(150, 150, 150, 250))
				#border_pen.setWidthF(1)
				#painter.setPen(border_pen)
				#painter.drawPath(path)			

			#if self.selected:
				#if self.par.le:
					#pass
				#elif self.par.get_text():
					#pass

		if self.shape_type == "slider_back":
			if edit or self.par.main.useFingerSliders:
				border_pen = QtGui.QPen(self.color)
				border_pen.setWidthF(1)
				painter.setPen(border_pen)
				painter.drawPath(path)
				# self.parent().setZValue(-1) 		if uncomment - fps falling

		#if self.par.name == "face_head":
			#print (333, self.shapeIsVisible(name))
					

	def set_selected_state(self, state):
		# Do nothing on same state
		if state == self.selected:
			return

		# Change state, and update
		self.selected = state
		self.update()

	def set_color(self, color):
		# Run default method
		color = DefaultPolygon.set_color(self, color)

		# Store new color as default
		Polygon.__DEFAULT_COLOR__ = color

	def generate_grey_image(self):
		if not self.image_path:
			return
		img = QtGui.QImage(self.image_path)
		for i in range(img.width()):
			for j in range(img.height()):
				color = QtGui.QColor(img.pixelColor(i,j))
				hue = color.hue()
				sat = 0 #color.saturation() * 0.1
				#hue *= 0.5
				color.setHsv(hue, sat , color.value()*0.7, color.alpha())
				#color.setGreen(60)
				#color.setRed(0)
				img.setPixelColor(i, j, color);		
		self.grey_image = img

	def generate_red_image(self):
		if not self.image_path:
			return
		img = QtGui.QImage(self.image_path)
		for i in range(img.width()):
			for j in range(img.height()):
				color = QtGui.QColor(img.pixelColor(i,j))
				color.setGreen(0)
				color.setBlue(0)
				img.setPixelColor(i, j, color);		
		self.render_image = img

	def set_grey_render_image(self, grey):
		if grey:
			self.render_image = self.grey_image
		else:
			self.render_image = self.image


class PointHandle(DefaultPolygon):
	__DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 200)

	def __init__(self, x=0, y=0, size=8, color=None, parent=None, index=0):

		DefaultPolygon.__init__(self, parent)

		# Make movable
		self.setFlag(self.ItemIsMovable)
		self.setFlag(self.ItemSendsScenePositionChanges)
		self.setFlag(self.ItemIgnoresTransformations)

		# Set values
		self.setPos(x, y)
		self.index = index
		self.size = size
		self.set_color()
		self.draw_index = False

		# Hide by default
		self.setVisible(False)

		# Add index element
		self.index = PointHandleIndex(parent=self, index=index)

	# =========================================================================
	# Default python methods
	# =========================================================================
	def _new_pos_handle_copy(self, pos):
		new_handle = PointHandle(x=pos.x(),
                                 y=pos.y(),
                                 size=self.size,
                                         color=self.color,
                                         parent=self.parentObject())
		return new_handle

	def _get_pos_for_input(self, other):
		if isinstance(other, PointHandle):
			return other.pos()
		return other

	def __add__(self, other):
		other = self._get_pos_for_input(other)
		new_pos = self.pos() + other
		return self._new_pos_handle_copy(new_pos)

	def __sub__(self, other):
		other = self._get_pos_for_input(other)
		new_pos = self.pos() - other
		return self._new_pos_handle_copy(new_pos)

	def __div__(self, other):
		other = self._get_pos_for_input(other)
		new_pos = self.pos() / other
		return self._new_pos_handle_copy(new_pos)

	def __mul__(self, other):
		other = self._get_pos_for_input(other)
		new_pos = self.pos() / other
		return self._new_pos_handle_copy(new_pos)

	# =========================================================================
	# QT OVERRIDES
	# =========================================================================
	def setX(self, value=0):
		DefaultPolygon.setX(self, value)

	def setY(self, value=0):
		DefaultPolygon.setY(self, value)

	# =========================================================================
	# Graphic item methods
	# =========================================================================
	def shape(self):
		path = QtGui.QPainterPath()
		# TODO some ints are being set to negative, make sure it survived the
		# pep8
		rectangle = QtCore.QRectF(QtCore.QPointF(-self.size / 2.0,
                                                 self.size / 2.0),
                                  QtCore.QPointF(self.size / 2.0,
                                                 -self.size / 2.0))
	# path.addRect(rectangle)
		path.addEllipse(rectangle)
		return path

	def paint(self, painter, options, widget=None):
		#if __USE_OPENGL__:
			#painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
		#else:
		painter.setRenderHint(QtGui.QPainter.Antialiasing)

		# Get polygon path
		path = self.shape()

		# Set node background color
		brush = QtGui.QBrush(self.color)
		if self._hovered:
			brush = QtGui.QBrush(self.color.lighter(500))

		# Paint background
		painter.fillPath(path, brush)

		#border_pen = QtGui.QPen(QtGui.QColor(200, 200, 200, 255))
		#painter.setPen(border_pen)

		# Paint Borders
		painter.drawPath(path)

		# if not edit_mode: return
		# Paint center cross
		#cross_size = self.size / 2 - 2
		#painter.setPen(QtGui.QColor(0, 0, 0, 180))
		#painter.drawLine(-cross_size, 0, cross_size, 0)
		#painter.drawLine(0, cross_size, 0, -cross_size)

		#self.parent().view.update()
		self.parent().view.scene().update()

	def mirror_x_position(self):
		self.setX(-1 * self.x())

	def scale_pos(self, x=1.0, y=1.0):
		factor = QtGui.QTransform().scale(x, y)
		self.setPos(self.pos() * factor)
		self.update()

	def enable_index_draw(self, status=False):
		self.index.setVisible(status)

	def set_index(self, index):
		self.index.setText(index)

	def get_index(self):
		return int(self.index.text())


class PointHandleIndex(QtWidgets.QGraphicsSimpleTextItem):
	__DEFAULT_COLOR__ = QtGui.QColor(130, 50, 50, 255)

	def __init__(self, parent=None, scene=None, index=0):
		QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

		# Init defaults
		self.set_size()
		self.set_color(PointHandleIndex.__DEFAULT_COLOR__)
		self.setPos(QtCore.QPointF(-9, -14))
		self.setFlag(self.ItemIgnoresTransformations)

		# Hide by default
		self.setVisible(False)

		self.setText(index)

	def set_size(self, value=8.0):
		font = self.font()
		font.setPointSizeF(value)
		self.setFont(font)

	def set_color(self, color=None):
		if not color:
			return
		brush = self.brush()
		brush.setColor(color)
		self.setBrush(brush)

	def setText(self, text):
		return QtWidgets.QGraphicsSimpleTextItem.setText(self, str(text))


class PickerItem(DefaultPolygon):
	def __init__(self,
                 parent=None,
                 point_count=4,
                     namespace=None,
                     main=None,
                         main_window=None,
                                     view=None, movableAlways=False):
		DefaultPolygon.__init__(self, parent=parent)
		self.point_count = point_count

		#self.setPos(0, 0)

		# Default vars
		self.namespace = namespace
		self.main = main
		self.main_window = main_window
		self._edit_status = False
		self.edit_window = None
		self.view = view
		self.name = None
		self.layer = None

		# Add polygon
		self.polygon = Polygon(parent=self)

		# Add handles
		self.handles = []
		self.set_handles(self.get_default_handles())

		# Controls vars
		self.controls = []
		self.custom_menus = []

		# Custom action
		self.custom_action = False
		self.custom_action_script = None
		self.init_script = None
		self.le = None
		self.button = None
		self.slider = None
		self.slider_item = None
		self.slider_objects = {1:None, 2:None, 3:None, 4:None, 5:None}
		self.slider_attributes = {1:None, 2:None, 3:None, 4:None, 5:None}
		self.selectionOnClick = True
		self.visible = True
		self.menu_var = None

		# Make item movable
		if edit or movableAlways:
			self.setFlag(self.ItemIsMovable)
			self.setFlag(self.ItemSendsScenePositionChanges)		

		self.rmb_items = []
		self.rmb_scripts = []

		self.mirror = None
		self.source_mirror = None
		self.mirrored = False
		self.textWidget_value = ""
		self.follow_offset = QtCore.QPointF(0,0)

		# Add text
		self.text = GraphicText(parent=self)	

	def add_text_widget(self):
		prx = QtWidgets.QGraphicsProxyWidget(self)
		self.le = QtWidgets.QLineEdit()
		self.update_lineEdit()
		prx.setWidget(self.le)
		self.le.textChanged.connect(self.edit_lineEdit)

	def add_slider_widget(self):
		item = PickerItem(parent=self, main=self.main, main_window=self.main_window,
                          namespace=self.namespace, view=self.view, movableAlways=True)
		item.setParent(self)
		item.polygon.shape_type = "circle"
		item.slider = True
		item.layer = self.layer
		item.name = self.name+"_slider"
		self.slider_item = item
		#item.selectionOnClick = True
		self.view.items.append(item)
		item.selectionOnClick = False

		if not item.custom_action_script:
			text = "attrX = 'pCube1.tx'\n"
			text += "attrY = 'pCube1.ty'\n"
			text += "multX = 1.0\n"
			text += "multY = 1.0\n"
			text += "\n"			
			text += "w = self.parent().polygon.width/2\n"
			text += "h = self.parent().polygon.height/2\n"
			text += "\n"
			text += "cmds.setAttr(attrX, self.pos().x()/w*multX)\n"
			text += "cmds.setAttr(attrY, -self.pos().y()/h*multY)\n"
			item.custom_action_script = text

	def add_button_widget(self):
		prx = QtWidgets.QGraphicsProxyWidget(self)
		self.button = QtWidgets.QPushButton()
		self.selectionOnClick = False
		self.custom_action_script = ""
		self.update_lineEdit()
		prx.setWidget(self.button)
		self.button.clicked.connect(self.button_run)

	def button_run(self):
		if not self.selectionOnClick:
			# Run custom script action
			if self.custom_action_script:
				tab_widget = self.main.tab_widgets[self.main.cur_picker.name]
				localsParameter = {'tab_widget': tab_widget, 'item': self}
				cmd = self.custom_action_script
				exec (cmd)#, localsParameter)	
		# Run default selection action
		else:
			self.select_associated_controls()

	def run_init_script(self):
		tab_widget = self.main.tab_widgets[self.main.cur_picker.name]
		localsParameter = {'tab_widget': tab_widget, 'item': self}
		cmd = self.init_script
		if cmd:
			exec (cmd, localsParameter)		

	def edit_lineEdit(self):
		self.textWidget_value = self.le.text()
		#self.view.main_window.save_picker()
		pass

	def update_lineEdit(self):
		if self.le:
			self.le.setGeometry((self.polygon.width-20)*-0.5,(self.polygon.height-20)*-0.5, self.polygon.width-20, self.polygon.height-20)
		elif self.button:
			self.button.setGeometry((self.polygon.width-20)*-0.5,(self.polygon.height-20)*-0.5, self.polygon.width-20, self.polygon.height-20)

	def shape(self):

		path = QtGui.QPainterPath()

		if self.polygon:
			path.addPath(self.polygon.shape())

		# Stop here in default mode
		if not self._edit_status:
			return path

		# Add handles to shape
		for handle in self.handles:
			path.addPath(handle.mapToParent(handle.shape()))

		return path

	def paint(self, painter, *args, **kwargs):
		#super(PickerItem, self).paint(*args, **kwargs)
		return
		# for debug only
		# Set render quality
		painter.setRenderHint(QtGui.QPainter.Antialiasing)

		# Get polygon path
		path = self.shape()

		# Set node background color
		brush = QtGui.QBrush(QtGui.QColor(0,0,200,10))

		# Paint background
		painter.fillPath(path, brush)

		border_pen = QtGui.QPen(QtGui.QColor(0,200,0,255))
		painter.setPen(border_pen)

		# Paint Borders
		painter.drawPath(path)

	def get_default_handles(self, rotated=False):
		unit_scale = 20
		handles = []

		if self.polygon.image:
			handle1 = PointHandle(x=0, y=0, parent=self, index=1)
			handle2 = PointHandle(x=0, y=self.polygon.image.height(), parent=self, index=2)
			handle3 = PointHandle(x=self.polygon.image.width(), y=self.polygon.image.height(), parent=self, index=3)
			handle4 = PointHandle(x=self.polygon.image.width(), y=0, parent=self, index=4)
			handles.append(handle1)
			handles.append(handle2)
			handles.append(handle3)
			handles.append(handle4)
			return handles

		# Define angle step
		angle_step = pi * 2 / self.point_count

		r = 0
		if rotated:
			r = 0.785398

		# Generate point coordinates
		for i in range(0, self.point_count):
			x = sin(i * angle_step + pi / self.point_count + r) * unit_scale
			y = cos(i * angle_step + pi / self.point_count + r) * unit_scale
			handle = PointHandle(x=x, y=y, parent=self, index=i + 1)
			handles.append(handle)

		# Circle case
		if len(handles) == 2:
			handles.reverse()
			handles[0] = handles[0] + (handles[1] - handles[0]) / 2

		return handles

	def edit_point_count(self, value=4):
		# Update point count
		self.point_count = value

		# Reset points
		points = self.get_default_handles()
		self.set_handles(points)

	def get_handles(self):
		return self.handles

	def set_handles(self, handles=list()):
		# Remove existing handles
		for handle in self.handles:
			handle.setParent(None)
			handle.deleteLater()

		# Parse input type
		new_handles = []
		# start index at 1 since table Widget raw are indexed at 1
		index = 1
		for handle in handles:
			if isinstance(handle, (list, tuple)):
				handle = PointHandle(x=handle[0],
                                     y=handle[1],
                                     parent=self,
                                                     index=index)
			elif hasattr(handle, 'x') and hasattr(handle, 'y'):
				handle = PointHandle(x=handle.x(),
                                     y=handle.y(),
                                     parent=self,
                                                     index=index)
			new_handles.append(handle)
			index += 1

		# Update handles list
		self.handles = new_handles
		self.polygon.points = new_handles

		# Set current visibility status
		for handle in self.handles:
			handle.setVisible(self.get_edit_status())

		# Set new point count
		self.point_count = len(self.handles)

	def set_shape(self, shape):
		edit_status = self._edit_status
		self.set_edit_status(False)

		self.handles = []

		if shape == "square":
			self.main.win.linear_rbtn.setChecked(True)
			self.main.path_type_toggle()
			self.point_count = 4
			self.set_handles(self.get_default_handles())
		elif shape == "octagon":
			self.main.win.linear_rbtn.setChecked(True)
			self.main.path_type_toggle()
			self.point_count = 8
			self.set_handles(self.get_default_handles())
		elif shape == "rhomb":
			self.main.win.linear_rbtn.setChecked(True)
			self.main.path_type_toggle()
			self.point_count = 4
			self.set_handles(self.get_default_handles(rotated=True))
		elif shape == "custom":
			# Open input window
			count, ok = QtWidgets.QInputDialog.getInt(self.main.win,"Set Sides Count",'Count',QtWidgets.QLineEdit.Normal,2)
			if not (ok and count>1):
				return	

			if self.polygon.path_type == "linear":
				self.point_count = count
			elif self.polygon.path_type == "quadratic":
				self.point_count = count * 2
			elif self.polygon.path_type == "cubic":
				self.point_count = count * 3

			self.set_handles(self.get_default_handles(rotated=True))

		if self.mirror:
			self.mirror.set_shape(shape)

		self.set_edit_status(edit_status)

	def set_scale_shape(self, more):
		edit_status = self._edit_status
		self.set_edit_status(False)

		positions = []
		for h in self.handles:
			positions.append(h.pos())

		if more: m = 1.1
		else: m = 0.9

		self.handles = []
		for i, p in enumerate(positions):
			handle = PointHandle(x=p.x()*m, y=p.y()*m, parent=self, index=i + 1)
			self.handles.append(handle)

		self.set_handles(self.handles)

		if self.mirror:
			self.mirror.set_scale_shape(more)		

		self.set_edit_status(edit_status)

	def set_rotate_shape(self, left):
		edit_status = self._edit_status
		self.set_edit_status(False)

		positions = []
		for h in self.handles:
			positions.append(h.pos())

		if left: m = 1
		else: m = -1

		self.handles = []
		for i, p in enumerate(positions):
			handle = PointHandle(x=p.y()*m, y=p.x()*m, parent=self, index=i + 1)
			self.handles.append(handle)

		self.set_handles(self.handles)

		if self.mirror:
			self.mirror.set_scale_shape(left)		

		self.set_edit_status(edit_status)


	# =========================================================================
	# Mouse events ---

	def mouseReleaseEvent(self, event):
		#for it in self.view.items:
			#print ("release", it.get_data())
		DefaultPolygon.mouseReleaseEvent(self, event)

		if self.mirrored:
			self.update_mirrored_position()

	@oneStepUndo
	def run_script(self):
		if not self.selectionOnClick:
			# Run custom script action
			if self.custom_action_script:
				#print self.custom_action_script
				#print "--------------------", self.main.tab_widgets
				#tab_widget = self.main.tab_widgets[self.main.cur_picker.name]
				#localsParameter = {'tab_widget': tab_widget, 'item': self}
				localsParameter = {'item': self}
				cmd = self.custom_action_script
				if script_errors:
					exec (cmd)
				else:
					try:
						exec (cmd)#, localsParameter)	
					except: 
						cmds.warning("Error in the script of the item: "+self.name)
				#self.mouse_press_custom_action(event)


	def update_mirrored_position(self):
		m_item = self.source_mirror

		if m_item:
			if self.polygon.image:
				self.setX(-1 * ( m_item.pos().x() + self.polygon.image.width() ))
			else:
				self.setX(-1 * ( m_item.pos().x() ))
			self.setY(m_item.pos().y())		

	def update_followed_position(self, target_item):
		#print target_item.name, target_item.pos()
		self.setX( target_item.pos().x() - self.follow_offset.x())
		self.setY( target_item.pos().y() - self.follow_offset.y())

	def get_source_mirror(self):
		if self.mirrored:
			for source_item in self.view.items:
				if source_item.name == self.name.split("_MIRROR")[0]:
					return source_item
		return None

	def mouse_press_select_event(self, event=None):
		return
		# Get keyboard modifier
		if event:
			modifiers = event.modifiers()
		modifier = None

		# Shift cases (toggle)
		if modifiers == QtCore.Qt.ShiftModifier:
			modifier = "shift"

		# Controls case
		if modifiers == QtCore.Qt.ControlModifier:
			modifier = "control"

		# Alt case (remove)
		if modifiers == QtCore.Qt.AltModifier:
			modifier = "alt"

		# Call action
		self.select_associated_controls(modifier=modifier)

	def mouse_press_custom_action(self, event):
		# Run custom action script with picker item environnement
		python_handlers.safe_code_exec(self.get_custom_action_script(),
                                       env=self.get_exec_env())

	def mouseDoubleClickEvent(self, event):
		if not edit:
			return

		self.edit_options()

	def contextMenuEvent(self, event):
		return
		# Context menu for edition mode
		if edit:
			self.edit_context_menu(event)

		# Context menu for default mode
		else:
			self.default_context_menu(event)

		# Force call release method
		#self.mouseReleaseEvent(event)

	def edit_context_menu(self, event):
		return
		# Init context menu
		menu = QtWidgets.QMenu(self.parent())

		# Build edit context menu
		options_action = QtWidgets.QAction("Options", None)
		options_action.triggered.connect(self.edit_options)
		menu.addAction(options_action)

		handles_action = QtWidgets.QAction("Toggle handles", None)
		handles_action.triggered.connect(self.toggle_edit_status)
		menu.addAction(handles_action)

		menu.addSeparator()

		# Shape options menu
		shape_menu = QtWidgets.QMenu(menu)
		shape_menu.setTitle("Shape")

		move_action = QtWidgets.QAction("Move to center", None)
		move_action.triggered.connect(self.move_to_center)
		shape_menu.addAction(move_action)

		shp_mirror_action = QtWidgets.QAction("Mirror shape", None)
		shp_mirror_action.triggered.connect(self.mirror_shape)
		shape_menu.addAction(shp_mirror_action)

		color_mirror_action = QtWidgets.QAction("Mirror color", None)
		color_mirror_action.triggered.connect(self.mirror_color)
		shape_menu.addAction(color_mirror_action)

		menu.addMenu(shape_menu)

		move_back_action = QtWidgets.QAction("Move to back", None)
		move_back_action.triggered.connect(self.move_to_back)
		menu.addAction(move_back_action)

		move_front_action = QtWidgets.QAction("Move to front", None)
		move_front_action.triggered.connect(self.move_to_front)
		menu.addAction(move_front_action)

		menu.addSeparator()

		# Copy handling
		copy_action = QtWidgets.QAction("Copy", None)
		copy_action.triggered.connect(self.copy_event)
		menu.addAction(copy_action)

		paste_action = QtWidgets.QAction("Paste", None)
		if DataCopyDialog.__DATA__:
			paste_action.triggered.connect(self.past_event)
		else:
			paste_action.setEnabled(False)
		menu.addAction(paste_action)

		paste_options_action = QtWidgets.QAction("Paste Options", None)
		if DataCopyDialog.__DATA__:
			paste_options_action.triggered.connect(self.past_option_event)
		else:
			paste_options_action.setEnabled(False)
		menu.addAction(paste_options_action)

		menu.addSeparator()

		# Duplicate options
		duplicate_action = QtWidgets.QAction("Duplicate", None)
		duplicate_action.triggered.connect(self.duplicate)
		menu.addAction(duplicate_action)

		mirror_dup_action = QtWidgets.QAction("Duplicate/mirror", None)
		#mirror_dup_action.triggered.connect(self.duplicate_and_mirror)
		menu.addAction(mirror_dup_action)

		menu.addSeparator()

		# Delete
		remove_action = QtWidgets.QAction("Remove", None)
		remove_action.triggered.connect(self.remove)
		menu.addAction(remove_action)

		menu.addSeparator()

		# Control association
		ctrls_menu = QtWidgets.QMenu(menu)
		ctrls_menu.setTitle("Ctrls Association")

		select_action = QtWidgets.QAction("Select", None)
		select_action.triggered.connect(self.select_associated_controls)
		ctrls_menu.addAction(select_action)

		#replace_action = QtWidgets.QAction("Replace with selection", None)
		#replace_action.triggered.connect(self.replace_controls_selection)
		#ctrls_menu.addAction(replace_action)

		menu.addMenu(ctrls_menu)

		# Open context menu under mouse
		# offset position to prevent accidental mouse release on menu
		offseted_pos = event.pos() + QtCore.QPointF(5, 0)
		scene_pos = self.mapToScene(offseted_pos)
		view_pos = self.parent().mapFromScene(scene_pos)
		screen_pos = self.parent().mapToGlobal(view_pos)
		menu.exec_(screen_pos)

	def default_context_menu(self, event):
		# Init context menu
		menu = QtWidgets.QMenu(self.parent())

		# Add reset action
		# reset_action = QtWidgets.QAction("Reset", None)
		# reset_action.triggered.connect(self.active_control.reset_to_bind_pose)
		# menu.addAction(reset_action)

		# Add custom actions
		actions = self._get_custom_action_menus()
		for action in actions:
			menu.addAction(action)

		# Abort on empty menu
		if menu.isEmpty():
			return

		# Open context menu under mouse
		# offset position to prevent accidental mouse release on menu
		offseted_pos = event.pos() + QtCore.QPointF(5, 0)
		scene_pos = self.mapToScene(offseted_pos)
		view_pos = self.parent().mapFromScene(scene_pos)
		screen_pos = self.parent().mapToGlobal(view_pos)
		menu.exec_(screen_pos)

	def get_exec_env(self):
		# Init env
		env = {}

		# Add controls vars
		env["__CONTROLS__"] = self.get_controls()
		ctrls = self.get_controls()
		env["__FLATCONTROLS__"] = maya_handlers.get_flattened_nodes(ctrls)
		env["__NAMESPACE__"] = self.get_namespace()

		return env

	def _get_custom_action_menus(self):
		# Init action list to fix loop problem where qmenu only
		# show last action when using the same variable name ...
		actions = []

		# Define custom exec cmd wrapper
		def wrapper(cmd):
			def custom_eval(*args, **kwargs):
				python_handlers.safe_code_exec(cmd,
                                               env=self.get_exec_env())
			return custom_eval

		# Get active controls custom menus
		custom_data = self.get_custom_menus()
		if not custom_data:
			return actions

		# Build menu
		for i in range(len(custom_data)):
			actions.append(QtWidgets.QAction(custom_data[i][0], None))
			actions[i].triggered.connect(wrapper(custom_data[i][1]))

		return actions

	# =========================================================================
	# Edit picker item options ---
	def edit_options(self):
		return
		# Delete old window
		if self.edit_window:
			try:
				self.edit_window.close()
				self.edit_window.deleteLater()
			except Exception:
				pass

		# Init new window
		self.edit_window = ItemOptionsWindow(parent=self.main_window,
                                             picker_item=self)

		# Show window
		self.edit_window.show()
		self.edit_window.raise_()

	def set_edit_status(self, status):
		self._edit_status = status

		for handle in self.handles:
			handle.setVisible(status)

		self.polygon.set_edit_status(status)

	def get_edit_status(self):
		return self._edit_status

	def toggle_edit_status(self):
		self.set_edit_status(not self._edit_status)

	# =========================================================================
	# Properties methods ---
	def get_color(self):
		return self.polygon.get_color()

	def set_color(self, color=None):
		self.polygon.set_color(color)

	def set_red_color(self):
		self.polygon.set_color(QtGui.QColor(255,0,0,255))

	def set_grey_color(self):
		self.polygon.set_color(QtGui.QColor(170,170,170,255))

	def set_orange_color(self):
		self.polygon.set_color(QtGui.QColor(210,170,45,255))

	# =========================================================================
	# Text handling ---
	def get_text(self):
		return self.text.get_text()

	def set_text(self, text):
		if self.button:
			self.button.setText(text)
		else:
			self.text.set_text(text)

	def get_text_color(self):
		return self.text.get_color()

	def set_text_color(self, color):
		self.text.set_color(color)

	def get_text_size(self):
		return self.text.get_size()

	def set_text_size(self, size):
		self.text.set_size(size)

	# =========================================================================
	# Scene Placement ---
	def move_to_front(self):
		# Get current scene
		scene = self.scene()

		# Move to temp scene
		tmp_scene = QtWidgets.QGraphicsScene()
		tmp_scene.addItem(self)

		# Add to current scene (will be put on top)
		scene.addItem(self)

		# Clean
		tmp_scene.deleteLater()

	def move_to_back(self):
		# Get picker Items
		picker_items = self.scene().get_picker_items()

		# Reverse list since items are returned front to back
		picker_items.reverse()

		# Move current item to front of list (back)
		picker_items.remove(self)
		picker_items.insert(0, self)

		# Move each item in proper oder to front of scene
		# That will add them in the proper order to the scene
		for item in picker_items:
			item.move_to_front()

	def move_to_center(self):
		self.setPos(0, 0)

	def remove(self):
		("remove")
		if self.mirrored:
			source_item = self.get_source_mirror()
			if source_item:
				source_item.mirror = None

		if self.mirror:
			self.mirror.remove()

		self.scene().removeItem(self)
		self.setParent(None)
		self.deleteLater()

	# =========================================================================
	# Ducplicate and mirror methods ---
	def mirror_position(self):
		self.setX(-1 * self.pos().x())

	def mirror_shape(self):
		for handle in self.handles:
			if self.polygon.image:
				handle.setX(-1 * ( handle.x() - self.polygon.image.width() ))
			else:
				handle.mirror_x_position()

	def mirror_color(self):
		old_color = self.get_color()
		new_color = QtGui.QColor(old_color.blue(),
                                 old_color.green(),
                                 old_color.red(),
                                         alpha=old_color.alpha())
		self.set_color(new_color)

	def duplicate(self, *args, **kwargs):
		# Create new picker item
		new_item = PickerItem(main=self.main)
		
		#if self.slider:
			#new_item.polygon.shape_type = "slider_back"
			#item.add_slider_widget()

		new_item.setParent(self.parent())
		self.scene().addItem(new_item)

		# Copy data over
		data = self.get_data()

		# set new name
		name = data["name"]
		new_name = utils.incrementName(name)

		all_names = []
		for i in self.view.items:
			all_names.append(i.name)
			
		while (new_name in all_names):
			new_name = utils.incrementName(new_name)

		# set data
		if self.main.layerIsExternal(data['layer']):
			new_name = name.split(data['layer']+"_")[1]
			while (new_name in all_names):
				new_name = utils.incrementName(new_name)
			data['layer'] = "default"

		data['name'] = new_name
		new_item.view = self.view
		new_item.set_data(data)



		self.view.data["items"].append(data)
		self.view.items.append(new_item)

		self.view.item_menu = False
		new_item.main_window = self.main_window

		return new_item

	def create_mirror(self):
		new_item = self.duplicate()
		new_item.name = self.name+"_MIRROR"
		new_item.mirror_shape()
		self.mirror = new_item
		new_item.mirrored = True
		new_item.source_mirror = self
		new_item.polygon.flipped = True
		new_item.update_mirrored_position()

		new_item.controls = self.getOppositeControls(self.controls, ifExist=False)

		return new_item

	def flip(self):
		new_item = self.duplicate()
		new_item.mirror_shape()
		self.mirror = new_item
		new_item.mirrored = True
		new_item.source_mirror = self
		new_item.polygon.flipped = True
		new_item.update_mirrored_position()
		new_item.mirrored = False
		new_item.source_mirror = None
		self.view.items.remove(self)
		self.view.selected_items.remove(self)
		self.mirror = False
		self.remove()	

	def copy_event(self):
		DataCopyDialog.get(self)

	def past_event(self):
		DataCopyDialog.set(self)

	def past_option_event(self):
		DataCopyDialog.options(self)

	# =========================================================================
	# Transforms ---
	def scale_shape(self, x=1.0, y=1.0, world=False):
		# Scale handles
		for handle in self.handles:
			handle.scale_pos(x, y)

		# Scale position
		if world:
			factor = QtGui.QTransform().scale(x, y)
			self.setPos(self.pos() * factor)

		self.update()

	# =========================================================================
	# Custom action handling ---
	def get_custom_action_mode(self):
		return self.custom_action

	def set_custom_action_mode(self, state):
		self.custom_action = state

	def set_custom_action_script(self, cmd):
		self.custom_action_script = cmd

	def get_custom_action_script(self):
		return self.custom_action_script


	# =========================================================================
	# Controls handling ---
	def get_namespace(self):
		return self.namespace

	def get_controls(self, with_namespace=True):
		# Returned controls without namespace (as data stored)
		if not with_namespace:
			return list(self.controls)

		# Get namespace
		namespace = self.get_namespace()

		# No namespace, return nodes
		if not namespace:
			return list(self.controls)

		# Prefix nodes with namespace
		nodes = []
		for node in self.controls:
			nodes.append("{}{}".format(namespace, node))

		return nodes

	def select_associated_controls(self, modifier=None):
		self.select_nodes(self.get_controls(),
                          modifier=modifier)

	def getOppositeControls(self, controls, ifExist=True):
		opp_controls = []
		for c in controls:
			c_name = c.split(":")[-1]
			if c_name.split("_")[0] == "l":
				opp_name = "r" + c[1:]
				if ifExist:
					if cmds.objExists(opp_name):
						opp_controls.append(opp_name)	
				else:
					opp_controls.append(opp_name)	
					
			elif "L" in c_name.split("_"):
				opp_name = c[:-1] + "R"
				if ifExist:
					if cmds.objExists(opp_name):
						opp_controls.append(opp_name)
				else:
					opp_controls.append(opp_name)					
						
		return opp_controls

	def set_selected_controls(self):
		sel = cmds.ls(sl=1)

		if self.main.match_rig:
			if len(sel) == 0:
				self.polygon.set_grey_render_image(True)
				self.set_grey_color()
			else:
				self.polygon.set_grey_render_image(False)
				self.set_orange_color()

		self.controls = []
		for c in sel:
			self.controls.append(c.split("|")[-1])

		mirror_item = self.mirror
		if mirror_item:
			mirror_item.controls = self.getOppositeControls(self.controls)

		self.view.scene().update()		

	def set_opposite_controls(self):
		#get side names
		tab_widget = self.main.tab_widgets[self.main.cur_picker.name]
		for view in tab_widget.views:
			l_side_item = view.get_item_by_name("l_side")
			if l_side_item:
				l_side = l_side_item.le.text()
				r_side_item = view.get_item_by_name("r_side")
				r_side = r_side_item.le.text()

		mirror_item = self.mirror

		# get mirror item by name
		if not mirror_item:
			if self.name:
				if self.name.split("_")[0] == "l":
					opp_name = "r" + self.name[1:]

					for view in tab_widget.views:
						opp_item = view.get_item_by_name(opp_name)
						#print opp_item
						if opp_item:
							mirror_item = opp_item
							break

		if mirror_item:
			opp_controls = []
			for c in self.controls:
				c_name = c.split(":")[0]
				if c_name.split("_")[0] == l_side:
					opp_name = r_side + c[len(l_side):]
				elif c_name.split("_")[-1] == l_side:
					opp_name = c[:-len(r_side)] + r_side
				elif l_side in c_name.split("_"):
					opp_name = c.replace("_%s_" %l_side, "_%s_" %r_side)
				elif l_side in c_name:
					opp_name = c.replace(l_side, r_side)
				else:
					continue
				opp_controls.append(opp_name)

			mirror_item.controls = opp_controls
			if mirror_item.controls:
				mirror_item.polygon.set_grey_render_image(False)
				mirror_item.set_orange_color()

		self.view.scene().update()		

	def select_nodes(self, nodes, namespace=None, modifier=None):
		# Select maya node handler with specific modifier behavior

		# disable selection if needed
		if not self.main.updateSelection and self.main.edit:
			return

		# disable selecting if controls is hidden
		if not self.main.edit or (self.main.edit and not self.main.showHidden):
			if self.controls:
				if not self.polygon.controlIsVisible():
				#if not pm.PyNode(self.get_controls()[0]).isVisible():
					return

		# Parse nodes
		filtered_nodes = []
		for node in nodes:
			# Add namespace to node name
			if namespace:
				node = "{}:{}".format(namespace, node)

			# skip invalid nodes
			if not cmds.objExists(node):
				#cmds.warning("node '{}' not found, skipping\n".format(node))
				continue

			# Set case
			if cmds.nodeType(node) == "objectSet":
				content = get_flattened_nodes([node])
				filtered_nodes.extend(content)
				continue

			filtered_nodes.append(node)

		# Stop here on empty list
		if not filtered_nodes:
			return

		# Remove duplicates
		filtered_nodes = list(set(filtered_nodes))

		# No modifier case selection
		#if not modifier:
			#return cmds.select(filtered_nodes)

		## Control case (toggle)
		#if modifier == "control":
			#return cmds.select(filtered_nodes, tgl=True)

		## Alt case (remove)
		#elif modifier == "alt":
			#return cmds.select(filtered_nodes, d=True)

		# Shift case (add) and none
		#else:
		return cmds.select(filtered_nodes)	

	def is_selected(self):
		# Will return True if a related control is currently selected
		# (Only works with polygon that have a single associated maya_node)

		# Get controls associated nodes
		controls = self.get_controls()

		# Abort if not single control polygon
		if not len(controls) == 1:
			return False

		# Check
		return __SELECTION__.is_selected(controls[0])

	def set_selected_state(self, state):
		self.polygon.set_selected_state(state)

	def run_selection_check(self):
		self.set_selected_state(self.is_selected())

	# =========================================================================
	# Custom menus handling ---
	def set_custom_menus(self, menus):
		self.custom_menus = list(menus)

	def get_custom_menus(self):
		return self.custom_menus

	# =========================================================================
	# Data handling ---
	def set_data(self, data):
		self.name = data["name"]

		# Set color
		if "color" in data:
			color = QtGui.QColor(*data["color"])
			self.set_color(color)

		if "opacity" in data:
			v = data["opacity"]
			self.polygon.opacity = v

		# Set position
		if "position" in data:
			position = data.get("position", [0, 0])
			self.setPos(*position)

		# Set handles
		if "handles" in data:
			self.set_handles(data["handles"])

		# Set action mode
		if data.get("action_mode", False):
			self.set_custom_action_mode(True)
			self.set_custom_action_script(data.get("action_script", None))

		# Set controls
		if "controls" in data:
			self.controls = data["controls"]

		# Set custom menus
		if "menus" in data:
			self.set_custom_menus(data["menus"])

		if "shape_type" in data:
			self.polygon.shape_type = data["shape_type"]

		if "path_type" in data:
			self.polygon.path_type = data["path_type"]

		# Set text
		if "text" in data:
			self.set_text(data["text"])
			self.set_text_size(data["text_size"])
			color = QtGui.QColor(*data["text_color"])
			self.set_text_color(color)
			self.text.opacity = data["text_opacity"]

		# Set image
		if "image_path" in data:
			p = data["image_path"]
			#print 333, p, os.path.isfile(p)
			if not os.path.isfile(p):
				rel_path = p.split('picker')[-1]
				p = root_path + rel_path

			self.polygon.image = QtGui.QImage(p)#.mirrored(False, True)
			self.polygon.image_path = p
			self.polygon.generate_grey_image()



			self.polygon.render_image = self.polygon.image	

		if "width" in data:
			self.polygon.width = data["width"]

		if "height" in data:
			self.polygon.height = data["height"]

		if "radius" in data:
			self.polygon.radius = data["radius"]

		if "squash" in data:
			self.polygon.squash = data["squash"]

		if "rotate" in data:
			self.polygon.rotate = data["rotate"]

		if self.polygon.shape_type == "text":
			self.add_text_widget()

		if self.polygon.shape_type == "button":
			self.add_button_widget()

		if self.polygon.shape_type == "slider_back":
			self.add_slider_widget()
			self.slider_item.set_data(data["slider_data"])

		self.custom_action_script = data["script"]
		self.rmb_items = data["rmb_items"]
		self.rmb_scripts = data["rmb_scripts"]
		self.init_script = data["init_script"]
		self.selectionOnClick = data["selectionOnClick"]
		if "visible" in data:
			self.visible = data["visible"]
		self.mirrored = data["mirrored"]
		self.polygon.flipped = data["flipped"]
		if self.le:
			self.le.setText(data["le_text"])
		if self.button:
			self.button.setText(data["button_text"])

		if "layer" in data:
			self.layer = data["layer"]

		if "slider" in data:
			self.slider = data["slider"]

			def warn():
				if not self.main.view:
					return
				if self.main.view.drag_item:
					return				
				#print ("WARN")
				self.reset_slider()

			if self.custom_action_script:
				try:
					c1 = self.custom_action_script.split('\n')[1].split("'")[1]
					c2 = self.custom_action_script.split('\n')[2].split("'")[1]

					ns = self.namespace
					if cmds.objExists(ns+c1):			
						sj = cmds.scriptJob( attributeChange=[ns+c1, warn])
						self.main.slider_scriptJobs.append(sj)
						#print ("Create scriptJob", ns+c1)
					if cmds.objExists(ns+c2):	
						sj = cmds.scriptJob( attributeChange=[ns+c2, warn])
						self.main.slider_scriptJobs.append(sj)
						#print ("Create scriptJob", ns+c2)
				except:
					pass

		if "slider_objects" in data:
			self.slider_objects = data["slider_objects"]

			#if self.slider_objects[1]:
				#slist = OpenMaya.MSelectionList()
				#o, a = self.slider_objects[1].split(".")
				#slist.add(o)

				#mObj = OpenMaya.MObject()
				#slist.getDependNode(0, mObj)
				#mDepN = OpenMaya.MFnDependencyNode(mObj)

				#tx = mDepN.findPlug(a)

				#self.slider_attributes[1] = tx
		pass

	def set_visible(self, vis):
		self.visible = vis
		self.text.visible = vis
		self.setFlag(self.ItemIsMovable, vis)
		self.setFlag(self.ItemSendsScenePositionChanges, vis)			

	def get_data(self):
		# Init data dict
		data = {}

		# Add polygon color
		data["color"] = self.get_color().getRgb()
		data["opacity"] = self.polygon.opacity

		# Add position
		data["position"] = [self.x(), self.y()]

		# Add handles datas
		handles_data = []
		for handle in self.handles:
			handles_data.append([handle.x(), handle.y()])
		data["handles"] = handles_data

		# Add mode data
		if self.get_custom_action_mode():
			data["action_mode"] = True
			data["action_script"] = self.get_custom_action_script()

		# Add controls data
		if self.get_controls():
			data["controls"] = self.get_controls(with_namespace=False)

		# Add custom menus data
		if self.get_custom_menus():
			data["menus"] = self.get_custom_menus()

		if self.get_text():
			data["text"] = self.get_text()
			data["text_size"] = self.get_text_size()
			data["text_color"] = self.get_text_color().getRgb()
			data["text_opacity"] = self.text.opacity

		if self.polygon.image_path:
			data["image_path"] = self.polygon.image_path

		data["shape_type"] = self.polygon.shape_type
		data["path_type"] = self.polygon.path_type
		data["width"] = self.polygon.width
		data["height"] = self.polygon.height
		data["radius"] = self.polygon.radius
		data["squash"] = self.polygon.squash
		data["script"] = self.custom_action_script
		data["rmb_items"] = self.rmb_items
		data["rmb_scripts"] = self.rmb_scripts
		data["init_script"] = self.init_script
		data["selectionOnClick"] = self.selectionOnClick
		data["visible"] = self.visible
		data["mirrored"] = self.mirrored
		data["rotate"] = self.polygon.rotate
		data["flipped"] = self.polygon.flipped
		data["name"] = self.name
		data["layer"] = self.layer
		data["slider"] = self.slider
		data["slider_objects"] = self.slider_objects
		if self.slider_item:
			d = self.slider_item.get_data()
			d["position"] = [0,0]
			data["slider_data"] = d
		if self.le:
			data["le_text"] = self.le.text()
		if self.button:
			data["button_text"] = self.button.text()
		return data

	def update_slider(self):
		x = self.pos().x()
		y = self.pos().y()
		h = self.parent().polygon.height
		w = self.parent().polygon.width
		r = self.polygon.radius 

		if x > w * 0.5-r:
			self.setPos(w * 0.5-r, y)
		elif x < -w * 0.5+r:
			self.setPos(-w * 0.5+r, y)
		if y > h * 0.5-r:
			self.setPos(self.pos().x(), h * 0.5-r)
		elif y < -h * 0.5+r:
			self.setPos(self.pos().x(), -h * 0.5+r)

		#self.slider_attributes[1].setFloat(x*0.1) #x*5-y*7-40

		self.run_script()		

	def reset_slider(self):
		try:		
			c1 = self.custom_action_script.split('\n')[1].split("'")[1]
			c2 = self.custom_action_script.split('\n')[2].split("'")[1]

			multX = float(self.custom_action_script.split('\n')[3].split(" ")[-1])
			multY = float(self.custom_action_script.split('\n')[4].split(" ")[-1])
			offsetX = float(self.custom_action_script.split('\n')[5].split(" ")[-1])
			offsetY = float(self.custom_action_script.split('\n')[6].split(" ")[-1])

			ns = self.namespace
			if cmds.objExists(ns+c1):
				#if "39" in item.slider_item.name:
				self.setX(float((cmds.getAttr(ns+c1) - offsetX)) * self.parent().polygon.width/2 /multX)
				self.setY(-float((cmds.getAttr(ns+c2) - offsetY)) * self.parent().polygon.height/2 /multY)
			else:
				cmds.warning("Control is not exists "+ns+c)
		except: pass


class CustomScriptEditDialog(QtWidgets.QDialog):
	def __init__(self, parent=None, cmd=None, item=None ):
		QtWidgets.QDialog.__init__(self, parent)

		self.cmd = cmd
		self.picker_item = item
		self.title = "Custom Script"

		self.apply = False
		self.setup()

	@staticmethod
	def get_default_script():
		text = "import maya.cmds as cmds\n"
		text += "import maya.mel as mel\n"
		text += "\n"
		return text

	def setup(self):
		self.setWindowTitle(self.title)

		# Add layout
		self.main_layout = QtWidgets.QVBoxLayout(self)

		# Add cmd txt field
		self.cmd_widget = QtWidgets.QTextEdit()
		self.cmd_widget.setFontPointSize(10)
		if self.cmd:
			self.cmd_widget.setText(self.cmd)
		else:
			default_script = self.get_default_script()
			self.cmd_widget.setText(default_script)
		self.main_layout.addWidget(self.cmd_widget)

		# Add buttons
		btn_layout = QtWidgets.QHBoxLayout()
		self.main_layout.addLayout(btn_layout)

		ok_btn = QtWidgets.QPushButton()
		ok_btn.setText("Ok")
		ok_btn.clicked.connect(self.accept_event)
		btn_layout.addWidget(ok_btn)

		cancel_btn = QtWidgets.QPushButton()
		cancel_btn.setText("Cancel")
		cancel_btn.clicked.connect(self.cancel_event)
		btn_layout.addWidget(cancel_btn)

		self.resize(500, 600)

	def accept_event(self):
		self.apply = True

		self.accept()
		self.close()

	def cancel_event(self):
		self.apply = False
		self.close()

	def get_values(self):
		cmd_str = str(self.cmd_widget.toPlainText())

		return cmd_str, self.apply

	@classmethod
	def get(cls, cmd=None, item=None):
		win = cls(cmd=cmd, item=item)
		win.exec_()
		win.raise_()
		return win.get_values()


class SaveDialog(QtWidgets.QDialog, saveWindow.Ui_Dialog):
	@debug_function
	def __init__(self, parent=get_maya_window()):
		super(SaveDialog, self).__init__(parent)
		self.setupUi(self)
		self.parent = parent

		self.ok_btn.clicked.connect(self.save)
		self.cancel_btn.clicked.connect(self.close)

		self.show()

	def save(self):
		asNode = self.asNode_btn.isChecked()
		self.parent.export(name=self.lineEdit.text(), asNode=asNode)
		self.close()


def getMayaWindow():
	ptr = OpenMayaUI.MQtUtil.mainWindow()
	if ptr is not None:
		if sys.version[0] == "2":
			return wrapInstance(long(ptr), QtWidgets.QWidget)	
		else:
			return wrapInstance(int(ptr), QtWidgets.QWidget)	


def dock_window(dialog_class, edit_mode, rigFromJoints_tool):
	global edit, rigFromJoints
	edit = edit_mode
	rigFromJoints = rigFromJoints_tool

	try:
		cmds.deleteUI(dialog_class.CONTROL_NAME)
		#logger.info('removed workspace {}'.format(dialog_class.CONTROL_NAME))
	except:
		pass

	# building the workspace control with maya.cmds
	main_control = cmds.workspaceControl(dialog_class.CONTROL_NAME)

	# now lets get a C++ pointer to it using OpenMaya
	control_widget = OpenMayaUI.MQtUtil.findControl(dialog_class.CONTROL_NAME)
	# conver the C++ pointer to Qt object we can use
	if sys.version[0] == "2":
		control_wrap = wrapInstance(long(control_widget), QtWidgets.QWidget)
	else:
		control_wrap = wrapInstance(int(control_widget), QtWidgets.QWidget)

	# control_wrap is the widget of the docking window and now we can start working with it:
	control_wrap.setAttribute(QtCore.Qt.WA_DeleteOnClose)
	win = dialog_class(control_wrap)

	# after maya is ready we should restore the window since it may not be visible
	cmds.evalDeferred(lambda *args: cmds.workspaceControl(main_control, e=True, rs=True))

	# will return the class of the dock content.
	return win.run()


class ObjectsList(object):

	def loadUiWidget(self, uifilename, parent=None):
		loader = QtUiTools.QUiLoader()
		uifile = QtCore.QFile(uifilename)

		uifile.open(QtCore.QFile.ReadOnly)
		ui = loader.load(uifile, parent)
		uifile.close()

		return ui	

	def __init__(self, main):
		debugStart(traceback.extract_stack()[-1][2])
		self.main = main
		self.win = self.loadUiWidget(root_path+'//objectsWindow.ui', parent=main.win)

		self.objects = []
		self.picker_item = None

		self.win.show()

		self.win.add_btn.clicked.connect(self.add)
		self.win.remove_btn.clicked.connect(self.remove)
		self.win.addByName_btn.clicked.connect(self.addByName)
		self.win.close_btn.clicked.connect(self.win.close)

		debugEnd(traceback.extract_stack()[-1][2])

	def add(self):
		objects = cmds.ls(sl=1)
		for o in objects:
			if o not in self.picker_item.controls:
				name = o.split("|")[-1]
				self.picker_item.controls.append(name)

				mirror_item = self.picker_item.mirror
				if mirror_item:
					if name.split("_")[0] == "l":
						opp_name = "r" + name[1:]			
						mirror_item.controls.append(opp_name)

		self.fillList()

	def getOppositeControls(self, controls):
		opp_controls = []
		for c in controls:
			c_name = c.split(":")[-1]
			opp_name = "r" + c[1:]
		return opp_controls		

	def addByName(self):		
		name, ok = QtWidgets.QInputDialog().getText(self.win, 'Add object', 'Enter object name:', QtWidgets.QLineEdit.Normal, '')

		# remove spaces
		if ok and name != "":
			if name in self.picker_item.controls:
				QtWidgets.QMessageBox.information(self.win, "Warning", "This object already in list.")
				return			

		else:
			return	

		self.picker_item.controls.append(name)

		mirror_item = self.picker_item.mirror
		if mirror_item:
			if name.split("_")[0] == "l":
				opp_name = "r" + name[1:]			
				mirror_item.controls.append(opp_name)

		self.fillList()

	def remove(self):
		selected_items = self.win.listWidget.selectedItems()

		for item in selected_items:
			self.picker_item.controls.remove(item.text())

		self.fillList()

	def fillList(self):
		self.win.listWidget.clear()
		self.objects = self.picker_item.controls

		for name in self.objects:
			item = QtWidgets.QListWidgetItem(name)
			self.win.listWidget.addItem(item)

	def saveClose(self):
		print (self.picker_item.controls)


class MyDockingUI(QtWidgets.QWidget):

	instances = list()
	CONTROL_NAME = 'RS Picker'
	LABEL_NAME = 'RS Picker'

	def getMayaWindow():
		ptr = OpenMayaUI.MQtUtil.mainWindow()
		if ptr is not None:
			if sys.version[0] == "2":
				return wrapInstance(long(ptr), QtWidgets.QWidget)
			else:
				return wrapInstance(int(ptr), QtWidgets.QWidget)

	def loadUiWidget(self, uifilename, parent=getMayaWindow()):
		loader = QtUiTools.QUiLoader()
		uifile = QtCore.QFile(uifilename)

		uifile.open(QtCore.QFile.ReadOnly)
		ui = loader.load(uifile, parent)
		uifile.close()

		return ui	

	def get_version(self):
		with open(root_path.replace('\\picker', "/versions.txt")) as f:
			lines = f.readlines()

		versions = []
		for l in lines:
			if '---' in l:
				versions.append(l)

		lastVestion = versions[-1].split('---')[1]		

		return lastVestion

	def __init__(self, parent=None):
		debugStart(traceback.extract_stack()[-1][2])
		super(MyDockingUI, self).__init__(parent)

		MyDockingUI.delete_instances()
		self.__class__.instances.append(weakref.proxy(self))

		self.window_name = self.LABEL_NAME
		self.ui = parent
		self.main_layout = parent.layout()

		self.__init_2(_edit=edit)

		debugEnd(traceback.extract_stack()[-1][2])	

	@staticmethod
	def delete_instances():
		debugStart(traceback.extract_stack()[-1][2])
		for ins in MyDockingUI.instances:
			#logger.info('Delete {}'.format(ins))
			try:
				ins.setParent(None)
				ins.deleteLater()
			except:
				# ignore the fact that the actual parent has already been deleted by Maya...
				pass

			MyDockingUI.instances.remove(ins)
			del ins

		debugEnd(traceback.extract_stack()[-1][2])	

	def run(self):
		debugStart(traceback.extract_stack()[-1][2])
		self.window_name = self.LABEL_NAME + " " + self.get_version()

		debugEnd(traceback.extract_stack()[-1][2])	
		return self		

	def __init_2(self, _edit=False, picker_name=None, match_rig=False, match_scene=False):
		debugStart(traceback.extract_stack()[-1][2])

		self.uiFilePath = root_path+'//pickerWindow.ui'
		app = QtWidgets.QApplication.instance()
		self.win = self.loadUiWidget(self.uiFilePath)		
		app.exec_()
		self.main_layout.addWidget(self.win)  

		#global edit
		#edit = _edit
		self.edit = edit
		self.rigFromJoints = rigFromJoints
		self.picker_name = None
		self.pickers = {}
		self.tab_widgets = {}
		self.cur_picker = None
		self.match_rig = match_rig
		self.match_scene = match_scene
		self.slider_scriptJobs = []
		self.picker_nodes = []

		if self.rigFromJoints:
			self.picker_name = 'mr'
			self.match_rig = True

		# Window size
		#self.default_width = 800
		#self.default_height = 837

		# Default vars
		self.status = False
		self.script_jobs = []

		# New
		self.event_disabled = False
		self.picker_item = None
		self.view = None
		self.items_update = True
		self.autorun = True
		self.moveLock = False
		self.updateSelection = False
		self.showHidden = True
		self.tabBar_visibility = True
		self.skipSelectionUpdate = False
		if cmds.optionVar( exists='pk_selector_mode' ): 
			self.panels_mode = cmds.optionVar( q='pk_selector_mode' )
		else: self.panels_mode = 1
		if cmds.optionVar( exists='rsPicker_fingerSliders' ): 
			self.useFingerSliders = cmds.optionVar( q='rsPicker_fingerSliders' )
		else: self.useFingerSliders = False
		if cmds.optionVar( exists='rsPicker_mirSymResetButtons' ): 
			self.mirSymResetButtons = cmds.optionVar( q='rsPicker_mirSymResetButtons' )
		else: self.mirSymResetButtons = True
		self.views = {}

		self.initUi()

		self.win.autoLoadPicker_btn.setIcon(QtGui.QIcon(root_path.replace('\\picker', '\\ui')+'/icons/arrowsCircle.png'))
		self.win.autoLoadPicker_btn.setIconSize(QtCore.QSize(20, 20))	

		self.win.zoomReset_btn.setIcon(QtGui.QIcon(root_path.replace('\\picker', '\\ui')+'/icons/zoomReset.png'))
		self.win.zoomReset_btn.setIconSize(QtCore.QSize(16, 16))	

		self.win.panels_btn.setIcon(QtGui.QIcon(root_path.replace('\\picker', '\\ui')+'/icons/gear.png'))
		self.win.panels_btn.setIconSize(QtCore.QSize(16, 16))	

		#self.win.setStyleSheet("QPushButton::checked{ background-color:darkGray; border: none; }")
		self.win.setStyleSheet("QPushButton::checked{ background-color:rgb(150, 150, 150); border: none; }")

		# Menu
		if not edit:
			menubar = QtWidgets.QMenuBar()
			#file_menu = menubar.addMenu("&Options")
			file_menu = QtWidgets.QMenu(self)
			self.win.panels_btn.setMenu(file_menu)
			self.win.panels_btn.setEnabled(False)
			#self.win.horizontalLayout_5.setMenuBar(menubar)


			# Fingers Sliders
			self.fingersSliders_menuBtn = QtWidgets.QAction(QtGui.QIcon("bug.png"), "Fingers Sliders", self)
			self.fingersSliders_menuBtn.triggered.connect(self.fingersSliders_action)
			self.fingersSliders_menuBtn.setCheckable(True)
			file_menu.addAction(self.fingersSliders_menuBtn)

			# Sym Mir Reset Buttons
			msr_action = QtWidgets.QAction(QtGui.QIcon("bug.png"), "Mir Sym Reset Buttons", self)
			#msr_action.setStatusTip("This is your button2")
			msr_action.triggered.connect(self.useMirSymResetButtons_action)
			msr_action.setCheckable(True)	
			msr_action.setChecked(self.mirSymResetButtons)
			file_menu.addAction(msr_action)

			# panels button
			button_action = QtWidgets.QAction(QtGui.QIcon("bug.png"), "Collapsed", self)
			button_action.setStatusTip("This is your button")
			button_action.triggered.connect(partial(self.switch_panels, 1))
			button_action.setCheckable(True)

			button_action2 = QtWidgets.QAction(QtGui.QIcon("bug.png"), "Horizontal", self)
			button_action2.setStatusTip("This is your button2")
			button_action2.triggered.connect(partial(self.switch_panels, 2))
			button_action2.setCheckable(True)

			button_action3 = QtWidgets.QAction(QtGui.QIcon("bug.png"), "Vertical", self)
			button_action3.setStatusTip("This is your button2")
			button_action3.triggered.connect(partial(self.switch_panels, 3))
			button_action3.setCheckable(True)

			file_submenu = file_menu.addMenu("Panels Placement")

			alignmentGroup = QtWidgets.QActionGroup(self)
			alignmentGroup.addAction(button_action)
			alignmentGroup.addAction(button_action2)
			alignmentGroup.addAction(button_action3)

			file_submenu.addAction(button_action)
			file_submenu.addAction(button_action2)
			file_submenu.addAction(button_action3)




		self.update_selector()

		self.connectSignals()
		#self.view.scene().set_size(200, 200)
		#self.win.tab_widget.tab_switch(0)

		#self.win.about_btn.setVisible(False)
		self.win.tab_visibility_checkBox.setVisible(False)
		self.win.tabBar_visibility_checkBox.setVisible(False)
		self.win.frame_2.setVisible(False)
		self.win.progressBar.setVisible(False)
		#self.win.pushButton_2.setVisible(False)
		#self.win.pushButton_3.setVisible(False)
		#self.win.pushButton_4.setVisible(False)

		self.selectionEvent = OpenMaya.MEventMessage.addEventCallback("SelectionChanged", self.selectionUpdateEvent)		
		self.newSceneEvent = OpenMaya.MEventMessage.addEventCallback("NewSceneOpened", self.reloadPickers)
		self.sceneOpenedEvent = OpenMaya.MEventMessage.addEventCallback("SceneOpened", self.reloadPickers)
		self.referenceLoadEvent = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterLoadReference, self.reloadPickers, 1)
		self.referenceUnloadEvent = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterUnloadReference, self.reloadPickers, 2)
		self.referenceCreateEvent = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterCreateReference, self.reloadPickers, 3)
		self.referenceRemoveEvent = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterRemoveReference, self.reloadPickers, 4)
		self.sjTimeChange = cmds.scriptJob( event=["timeChanged", self.timeChange_event], protected=True)

		# get top widget of the picker window (do not works, crush the maya on click Reload Button)
		#self.win.parent().parent().parent().parent().parent().installEventFilter(self)
		#self.top_widget = self.win.parent().parent().parent().parent().parent()
		# install event filter to replace close event
		#self.top_widget.installEventFilter(self)

		#self.win.setStyleSheet("border: 1px solid rgb(100, 0, 0)")

		if not edit:
			self.fingersSliders_menuBtn.setChecked(self.useFingerSliders)
			self.fingersSliders_menuBtn.setEnabled(False)


			if self.panels_mode == 1:
				button_action.setChecked(True)
			elif self.panels_mode == 2:
				button_action2.setChecked(True)
			elif self.panels_mode == 3:
				button_action3.setChecked(True)

		self.win.panels_btn.setVisible(False)

		debugEnd(traceback.extract_stack()[-1][2])	

	def selectionUpdateEvent(self, v):
		debugStart(traceback.extract_stack()[-1][2])

		if self.skipSelectionUpdate:
			debugEnd(traceback.extract_stack()[-1][2])	
			return
		
		if edit and not self.updateSelection:
			debugEnd(traceback.extract_stack()[-1][2])	
			return		

		try: # fix for running after main window closing
			update = self.win.autoLoadPicker_btn.isChecked()
			#global snap_time
			#snap_time = datetime.now()
			#print ("selectionUpdateEvent")
			sel = cmds.ls(sl=1)

			if len(sel) > 0:
				#char_name = sel[-1].split(":")[0]
				ctrl = sel[-1].split(":")[-1]
				char_name = sel[-1].split(ctrl)[0]				

				pickers = self.get_picker_nodes()
				#print (1111, char_name, pickers)
				if char_name+"picker_pkrData" in pickers and self.cur_picker.name != char_name+"picker":

					if update:
						print ("LOAD picker", char_name+"picker")
						self.set_current_selector(char_name+"picker")

			self.selectItemsFromSelected()

		except: pass

			#time_1 = datetime.now()
			#try:

			#except: pass
			#time_2 = datetime.now()

			#diff = time_2 - time_1
			#print "TIME IS", time_1, diff.seconds, diff.microseconds
			#print "SNAP TIME End 2 IS", datetime.now()

		debugEnd(traceback.extract_stack()[-1][2])	

	def timeChange_event(self):
		#print ("Update RS")
		try:
			#print (111, self.cur_picker.name, self.views)
			for view in self.views[self.cur_picker.name]:
				view.update()
				#print ("Update ", view)
		except:
			pass

	def remove_events(self):
		try:
			print ("Start removing the events")
			OpenMaya.MMessage.removeCallback(self.selectionEvent)
			OpenMaya.MMessage.removeCallback(self.newSceneEvent)
			OpenMaya.MMessage.removeCallback(self.sceneOpenedEvent)
			#print (3333)
			OpenMaya.MSceneMessage.removeCallback(self.referenceLoadEvent)
			OpenMaya.MSceneMessage.removeCallback(self.referenceUnloadEvent)
			#print (4444)
			OpenMaya.MSceneMessage.removeCallback(self.referenceCreateEvent)
			OpenMaya.MSceneMessage.removeCallback(self.referenceRemoveEvent)
			#print (5555)
			cmds.scriptJob(kill=self.sjTimeChange, force=1)
			print ("Removed all events")
		except: pass

		if edit and self.win != None:
			self.win.close()
			self.win = None


	def eventFilter(self, obj, event):
		# disable close button (do not work fully, crush the maya on click the reload button)
		if event.type() == QtCore.QEvent.Close:
			#if self.win.autoLoadPickersOnStart_btn.isChecked():
				#super().eventFilter(obj, event)
			#else:
			print ("Hide Window")
			event.ignore()
			#top_widget = self.win.parent().parent().parent().parent().parent()
			self.win.parent().parent().parent().parent().parent().hide()
			top_widget.hide()
			return True


	def save_geometry(self):
		print ("Save GEometry")

		debugStart(traceback.extract_stack()[-1][2])

		configData["window_positon_x"] = self.parent().parent().parent().parent().parent().geometry().x()
		configData["window_positon_y"] = self.parent().parent().parent().parent().parent().geometry().y()
		configData["window_width"] = self.parent().parent().parent().parent().parent().geometry().width()
		configData["window_height"] = self.parent().parent().parent().parent().parent().geometry().height()

		configData["autoLoadPickersOnStart"] = self.win.autoLoadPickersOnStart_btn.isChecked()

		json_string = json.dumps(configData, indent=4)
		with open(root_path+'/config.json', 'w') as f:
			f.write(json_string)	

		debugEnd(traceback.extract_stack()[-1][2])	


	# Menu Funcions =========================================================================

	def fingersSliders_action(self, v):
		self.useFingerSliders = v
		cmds.optionVar( intValue = ( "rsPicker_fingerSliders", v ) )

		views = self.views[self.get_root_name()]
		for view in views:
			view.update()

	def useMirSymResetButtons_action(self, v):
		self.mirSymResetButtons = v
		cmds.optionVar( intValue = ( "rsPicker_mirSymResetButtons", v ) )

		views = self.views[self.get_root_name()]
		for view in views:
			view.update()

	# =========================================================================
	def connectSignals(self):
		debugStart(traceback.extract_stack()[-1][2])

		self.win.new_char_btn.clicked.connect(self.new_picker)
		self.win.load_btn.clicked.connect(self.load_template)
		self.win.save_char_btn.clicked.connect(self.save_picker)
		self.win.exportSelected_char_btn.clicked.connect(self.exportSelected)
		self.win.saveAs_char_btn.clicked.connect(self.export)
		self.win.delete_char_btn.clicked.connect(self.delete_picker)		
		self.win.merge_char_btn.clicked.connect(self.merge_picker)		
		self.win.import_items_btn.clicked.connect(self.import_items)		
		self.win.rename_btn.clicked.connect(self.rename_picker)		
		self.win.editShape_btn.clicked.connect(self.edit_shape_toggle)		
		self.win.setShapeSquare_btn.clicked.connect(partial(self.set_shape, "square"))
		self.win.setShapeOctagon_btn.clicked.connect(partial(self.set_shape, "octagon"))
		self.win.setShapeRhomb_btn.clicked.connect(partial(self.set_shape, "rhomb"))
		self.win.setSidesCount_btn.clicked.connect(partial(self.set_shape, "custom"))
		self.win.linear_rbtn.clicked.connect(self.path_type_toggle)	
		self.win.quadratic_rbtn.clicked.connect(self.path_type_toggle)	
		self.win.cubic_rbtn.clicked.connect(self.path_type_toggle)	
		self.win.setShapeMore_btn.clicked.connect(partial(self.scale_shape, True))
		self.win.setShapeLess_btn.clicked.connect(partial(self.scale_shape, False))
		self.win.setShapeRotateLeft_btn.clicked.connect(partial(self.rotate_shape, True))
		self.win.setShapeRotateRight_btn.clicked.connect(partial(self.rotate_shape, False))
		self.win.btn_opacity_slider.valueChanged.connect(self.opacity_slider_update)		
		self.win.label_opacity_slider.valueChanged.connect(self.label_opacity_update)		
		self.win.item_x_spinBox.valueChanged.connect(partial(self.item_position_update, axis="x"))		
		self.win.item_y_spinBox.valueChanged.connect(partial(self.item_position_update, axis="y"))		
		self.win.moveItemUp_btn.clicked.connect(partial(self.item_move, "up"))
		self.win.moveItemDown_btn.clicked.connect(partial(self.item_move, "down"))
		self.win.moveItemLeft_btn.clicked.connect(partial(self.item_move, "left"))
		self.win.moveItemRight_btn.clicked.connect(partial(self.item_move, "right"))
		self.win.label_lineEdit.textChanged.connect(self.label_text_update)		
		self.win.label_size_spinBox.valueChanged.connect(self.label_size_update)		
		self.win.width_spinBox.valueChanged.connect(self.rect_width_update)
		self.win.height_spinBox.valueChanged.connect(self.rect_height_update)
		self.win.radius_spinBox.valueChanged.connect(self.circle_radius_update)
		self.win.squash_spinBox.valueChanged.connect(self.circle_squash_update)
		self.win.rotate_spinBox.valueChanged.connect(self.image_rotate_update)
		self.win.useMatchRig_checkBox.clicked.connect(self.update_selector)
		self.win.reloadPicker_btn.clicked.connect(partial(self.reloadPickers, reload=True))
		self.win.addLayer_btn.clicked.connect(self.addLayer)
		self.win.removeLayer_btn.clicked.connect(self.removeLayer)
		self.win.addExtLayer_btn.clicked.connect(partial(self.addLayer, ext=True))
		#self.win.layers_tableWidget.currentItemChanged.connect(self.switchLayer)
		self.win.layers_tableWidget.cellClicked.connect(self.switchLayer)
		self.win.about_btn.clicked.connect(self.action_about)

		self.win.selection_btn.clicked.connect(self.select_script_toggle)	
		self.win.pythonScript_btn.clicked.connect(self.select_script_toggle)	
		self.win.editScript_btn.clicked.connect(self.edit_custom_action_script)	
		self.win.runScript_btn.clicked.connect(self.run_custom_action_script)	
		self.win.initScript_btn.clicked.connect(self.edit_init_script)	
		self.win.rmb_editScript_btn.clicked.connect(self.edit_menu_script)	
		self.win.rmb_add_btn.clicked.connect(self.rmb_add)	
		self.win.rmb_remove_btn.clicked.connect(self.rmb_remove)	
		self.win.rmb_up_btn.clicked.connect(partial(self.rmb_move, "up"))
		self.win.rmb_down_btn.clicked.connect(partial(self.rmb_move, "down"))
		self.win.selection_btn.clicked.connect(self.selectionOnClick_update)
		self.win.pythonScript_btn.clicked.connect(self.selectionOnClick_update)
		self.win.flip_checkBox.clicked.connect(self.image_flip_update)
		self.win.tab_visibility_checkBox.clicked.connect(self.image_flip_update)
		self.win.setImagePath_btn.clicked.connect(self.image_set_update)
		self.win.setSelection_btn.clicked.connect(self.set_selection)
		self.win.sliderSetObject1_pushButton.clicked.connect(partial(self.set_slider_object, 1))
		self.win.sliderSetObject2_pushButton.clicked.connect(partial(self.set_slider_object, 2))
		self.win.sliderSetObject3_pushButton.clicked.connect(partial(self.set_slider_object, 3))
		self.win.sliderSetObject4_pushButton.clicked.connect(partial(self.set_slider_object, 4))
		self.win.sliderSetObject5_pushButton.clicked.connect(partial(self.set_slider_object, 5))
		self.win.clearSliderObjects_btn.clicked.connect(self.clear_slider_objects)
		self.win.visibility_checkBox.clicked.connect(self.set_visibility_item)

		self.win.autorunScript_btn.clicked.connect(self.edit_autorun_script)
		self.win.moveLock_checkBox.clicked.connect(self.moveLock_update)
		self.win.updateSelection_checkBox.clicked.connect(self.updateSelection_update)
		self.win.showHidden_checkBox.clicked.connect(self.showHidden_update)
		self.win.tabBar_visibility_checkBox.clicked.connect(self.tabBar_visibility_set)
		self.win.autorun_checkBox.clicked.connect(self.use_autorun)
		self.win.autorunRun_btn.clicked.connect(self.run_autorun)
		self.win.obj_name_set_btn.clicked.connect(self.set_obj_name)
		self.win.obj_layer_set_btn.clicked.connect(self.set_obj_layer)
		self.win.objectsList_btn.clicked.connect(self.objects_list)
		self.win.autoLoadPickersOnStart_btn.clicked.connect(self.autoLoadPickersOnStart)
		self.win.zoomReset_btn.clicked.connect(self.zoomReset)

		#self.win.panels_btn.clicked.connect(self.cycle_panels)

		debugEnd(traceback.extract_stack()[-1][2])	

	def initUi(self):
		debugStart(traceback.extract_stack()[-1][2])

		if self.edit:
			self.win.color_button.setParent(None)
			self.win.color_button.destroy()
			self.win.color_button = QtWidgets.QPushButton()
			self.win.color_button.clicked.connect(self.change_color_event)
			self.win.gridLayout_4.addWidget(self.win.color_button, 0, 1)

			self.win.label_color_btn.setParent(None)
			self.win.label_color_btn.destroy()			
			self.win.label_color_btn = QtWidgets.QPushButton()
			self.win.label_color_btn.clicked.connect(self.label_change_color_event)
			self.win.gridLayout.addWidget(self.win.label_color_btn, 1, 1)

			self.win.left_frame.setEnabled(0)
			self.win.buttons_frame.setEnabled(0)
			self.win.background_frame.setEnabled(0)
			self.win.rename_btn.setEnabled(0)

			self.win.autoLoadPicker_btn.hide()
			self.win.autoLoadPickersOnStart_btn.hide()
			self.win.reloadPicker_btn.hide()
			self.win.panels_btn.hide()
			self.win.useMatchRig_checkBox.hide()

			self.win.setWindowTitle("RS Picker"+self.get_version())

		else:
			self.win.right_frame.hide()
			self.win.left_frame.hide()
			#self.win.useMatchRig_label.hide()
			self.win.useMatchRig_checkBox.hide()
			self.win.rename_btn.hide()
			#self.win.panels_btn.hide()
			self.win.autoLoadPickersOnStart_btn.hide()


		if self.picker_name:
			self.win.char_selector_frame.setVisible(0)

		self.win.char_selector_cb.currentIndexChanged.connect(self.setCurrentPicker)

		self.win.tab_widget_delete.setParent(None)
		self.win.tab_widget_delete.destroy()


		g = GroupLabel(self.win.buttons_label, self.win.buttons_frame, self.win.verticalLayout, self.win)		
		g.off = False
		g.mousePressEvent(1)			

		g = GroupLabel(self.win.background_label, self.win.background_frame, self.win.verticalLayout_2, self.win)	
		g.off = False
		g.mousePressEvent(1)			

		self.win.autoLoadPickersOnStart_btn.setChecked(configData["autoLoadPickersOnStart"])

		#toolBar = QtWidgets.QToolBar()
		#self.win.verticalLayout_76.addWidget(toolBar)

		#action1 = QtWidgets.QAction("Add", toolBar)

		#self.addLayer("Default")
		
		#self.win.stackedWidget.setFrameRect(PySide.QtCore.QRect (0, 0, 500, 500))

		debugEnd(traceback.extract_stack()[-1][2])	

	def addLayer(self, name=None, path=None, ext=False, vis=True):
		debugStart(traceback.extract_stack()[-1][2])

		count = self.win.layers_tableWidget.rowCount()

		if ext:
			path = QtWidgets.QFileDialog.getOpenFileName(self.win, "load picker", root_path+'/pickers', "*.json")[0]
			name = path.split("/")[-1].split('.json')[0]
			if path == "":
				return

			# add data
			layer_data = self.cur_picker.createLayerData(name)
			layer_data["index"] = count
			layer_data["path"] = path
			self.cur_picker.data["layers"].append(layer_data)			

			self.load_picker_orig(self.cur_picker)
			return

		else:	
			if not name:
				# Open input window
				name, ok = QtWidgets.QInputDialog.getText(self.win,
                                                          "New Layer",
                                                          'Layer name',
                                                                          QtWidgets.QLineEdit.Normal,
                                                                          'new')
				if not (ok and name):
					return		

				if 'layers' in self.cur_picker.data:
					layers = self.cur_picker.data["layers"]
					for l in layers:
						if name == l["name"]:
							cmds.warning("this layer is already exists")
							return			
				else:
					self.cur_picker.data["layers"] = []

				# add data
				layer_data = self.cur_picker.createLayerData(name)
				layer_data["index"] = count
				self.cur_picker.data["layers"].append(layer_data)

		# add row to table
		self.win.layers_tableWidget.insertRow(count)

		# add name
		item = QtWidgets.QTableWidgetItem(name)
		self.win.layers_tableWidget.setItem(count, 1, item)	

		if path:
			font = QtGui.QFont()
			font.setUnderline(1)
			item.setFont(font)

		# add visible button
		try: # fix for load picker from picker icon
			vis_btn = QtWidgets.QPushButton(self.win)
			self.win.layers_tableWidget.setCellWidget(count, 0, vis_btn)	
			if vis:
				vis_btn.setText('On')
			else:
				vis_btn.setText('Off')
				vis_btn.setStyleSheet("background-color: red")
			vis_btn.clicked.connect(partial(self.toggleLayer, vis_btn, item))

			self.win.layers_tableWidget.setCurrentCell(count,1)
			self.cur_layer_id = count
		except: pass

		debugEnd(traceback.extract_stack()[-1][2])	

	def removeLayer(self):
		debugStart(traceback.extract_stack()[-1][2])

		cur_layer = self.win.layers_tableWidget.selectedItems()

		if not cur_layer:
			return

		i = self.win.layers_tableWidget.indexFromItem(cur_layer[0]).row()
		name = cur_layer[0].text()

		if name == 'default':
			return

		if 'layers' in self.cur_picker.data:
			layers = self.cur_picker.data["layers"]
			for l in layers:
				if name == l["name"]:
					self.cur_picker.data["layers"].remove(l)
					views = self.views[self.cur_picker.name]
					for view in views:
						for item in view.items:
							if item.layer == name:
								item.layer = "default"
					break

			layers = self.cur_picker.data["layers"]

		# add row to table
		self.win.layers_tableWidget.removeRow(i)		

		debugEnd(traceback.extract_stack()[-1][2])	

	def switchLayer(self):
		debugStart(traceback.extract_stack()[-1][2])

		item = self.win.layers_tableWidget.currentItem()

		if not item:
			return

		# deselect external layer 
		#if item.text() in self.get_external_layers():
			#for i in range(self.win.layers_tableWidget.rowCount()):
				#if self.win.layers_tableWidget.item(i, 1).text() == self.cur_picker.data["current_layer"]:
					#self.win.layers_tableWidget.setCurrentCell(i,1)
			#return

		if item:
			self.cur_picker.data["current_layer"] = item.text()

		debugEnd(traceback.extract_stack()[-1][2])	

	def toggleLayer(self, btn, item):
		debugStart(traceback.extract_stack()[-1][2])

		vis = btn.text() == "On"

		if vis:
			btn.setText('Off')
			#btn.setIcon(QtGui.QIcon(rootPath+'/ui/icons/delete_icon.png'))
			btn.setStyleSheet("background-color: red")
			#item.setFlags( QtCore.Qt.NoItemFlags )
		else:
			btn.setText('On')
			#item.setFlags( QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable )		
			btn.setStyleSheet("background-color: None")

		# set layer state in picker data
		for l in self.cur_picker.data["layers"]:
			if l["name"] == item.text():
				l["visibility"] = not vis

		tab_widget = self.tab_widgets[self.cur_picker.name]

		for i, t_data in enumerate(self.cur_picker.data["tabs"]):
			t_name = t_data["name"]

			view = tab_widget.getViewByName(t_name)

			for _item in view.items:
				if _item.layer == item.text():
					_item.set_visible(not vis)
					if _item.text:
						_item.text.visible = not vis
					if _item.slider_item:
						_item.slider_item.visible = not vis

			view.scene().update()
			view.update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def new_picker(self):
		debugStart(traceback.extract_stack()[-1][2])

		# Open input window
		name, ok = QtWidgets.QInputDialog.getText(self.win,"New character",'Node name',QtWidgets.QLineEdit.Normal,'picker')
		if not (ok and name):
			return		

		if cmds.objExists(name+"_pkrData"):
			cmds.warning("this picker is already exists")
			return

		# Create new data node
		self.cur_picker = picker.Picker(str(name))
		self.cur_picker.create()
		#self.skipUpdate = True
		self.update_selector()
		#self.set_current_selector(name)
		#i = self.win.char_selector_cb.currentIndex()
		#self.setCurrentPicker(i)

		debugEnd(traceback.extract_stack()[-1][2])	

	def save_picker(self):
		debugStart(traceback.extract_stack()[-1][2])

		ext_layers = []
		if 'layers' in self.cur_picker.data:
			for i, l in enumerate(self.cur_picker.data["layers"]):
				if l["path"]:
					ext_layers.append(l["name"])


		for i, t_data in enumerate(self.cur_picker.data["tabs"]):
			t_name = t_data["name"]
			view = self.tab_widgets[self.cur_picker.name].getViewByName(t_name)
			t_data["items"] = []
			for item in view.items:
				#if not item:
					#continue
				if item.layer in ext_layers:
					continue
				if item.name:
					if item.name.split("_")[0] not in ext_layers:
						t_data["items"].append(item.get_data())

		self.cur_picker.save()

		debugEnd(traceback.extract_stack()[-1][2])	

	def export(self, name=None, asNode=True):
		debugStart(traceback.extract_stack()[-1][2])

		if not full:
			QtWidgets.QMessageBox.information(self.win, "Sorry", "This feature is available in full version only.")
			return			
		path = None
		if not name:
			p = os.path.abspath('P:/Animaccord/MayaGlobals/animation/2022/scripts/pashaScripts/pickers_data')
			#path = QtWidgets.QFileDialog.getSaveFileName(self.win, "Export", root_path+'/pickers', "*.json")[0]
			path = QtWidgets.QFileDialog.getSaveFileName(self.win, "Export", p, "*.json")[0]
			if name == "":
				return	
			asNode = False
			name = os.path.basename(path).split('.')[0]

		self.cur_picker.exportToFile(path)

		debugEnd(traceback.extract_stack()[-1][2])	

	def exportSelected(self):
		if len(self.view.selected_items) == 0:
			QtWidgets.QMessageBox.information(self.win, "Warning", "Select items.")
			return

		p = os.path.abspath('P:/Animaccord/MayaGlobals/animation/2022/scripts/pashaScripts/pickers_data')
		path = QtWidgets.QFileDialog.getSaveFileName(self.win, "Export", p, "*.json")[0]
		if path:
			# tab_name = self.view.tab_name
			items_data = []
			
			for item in self.view.selected_items:
				items_data.append(item.get_data())

			self.cur_picker.exportSelectedToFile(path, items_data)

	def import_items(self):
		filePath = os.path.join(root_path, "pickers")

		# open select window 
		path = QtWidgets.QFileDialog.getOpenFileName(self.win, "merge template", filePath, "*.json")[0]
		if path == "":
			return

		self.cur_picker.importItems(path, self.view.tab_name)

		self.load_picker_orig(self.cur_picker)

	def delete_picker(self):
		debugStart(traceback.extract_stack()[-1][2])

		name = self.win.char_selector_cb.currentText().split(" ")[0]
		if cmds.objExists(name+"_pkrData"):
			cmds.delete(name+"_pkrData")

		del self.pickers[name]

		self.update_selector()

		debugEnd(traceback.extract_stack()[-1][2])	

	#def cycle_panels(self):
		#self.panels_mode += 1
		#if self.panels_mode == 4:
			#self.panels_mode = 1

		#cmds.optionVar( intValue = ( "pk_selector_mode", self.panels_mode ) )
		#self.reloadPickers()

	def switch_panels(self, v):
		self.panels_mode = v
		cmds.optionVar( intValue = ( "pk_selector_mode", self.panels_mode ) )
		self.reloadPickers(reload=True)

	def update_selector(self):
		debugStart(traceback.extract_stack()[-1][2])
		
		global save_geometry
		# get picker nodes
		self.picker_nodes = self.get_picker_nodes()
		pickers_names = self.get_picker_names()

		# get picker files
		if self.edit and self.win.useMatchRig_checkBox.isChecked():
			pickers_path = os.path.join(root_path.replace('picker', 'matchRig'), "pickers")
			for f in os.listdir(pickers_path):
				name, ext = f.split(".")
				if ext == "json":	
					pickers_names.append(name+" (file)")

		# Clear
		self.pickers = {}		

		self.win.char_selector_cb.clear()
		widgets_for_remove = []
		for i in range( self.win.stackedWidget.count() ):
			widgets_for_remove.append(self.win.stackedWidget.widget(i))
		
		for tw in widgets_for_remove:
			self.win.stackedWidget.removeWidget(tw)
			tw.setParent(None)
			tw.destroy()
		
		self.tab_widgets = {}		
		self.panel_widgets = {}		
		self.win.layers_tableWidget.setRowCount(0)

		if len(pickers_names) > 1:
			step = 100.0 / len(pickers_names) or 0
			self.win.progressBar.setVisible(True)
			#window = cmds.window(t='Load pickers')
			window = cmds.window(maximizeButton=0, titleBar=0, minimizeButton=0, leftEdge=0)
			cmds.columnLayout()			
			#progressControl = cmds.progressBar(maxValue=len(pickers_names), minValue=0, width=300)
			cmds.showWindow( window )
			cmds.deleteUI(window)

		# fill
		for n in sorted(pickers_names):
			# create picker 
			self.win.char_selector_cb.addItem(n.split(":picker")[0])
			p = picker.Picker(n)
			self.pickers[n] = p
			p.load()

			# create tabwidget
			if edit or self.panels_mode == 1:
				self.tab_widgets[n] = ContextMenuTabWidget(self, main_window=self.win)
				self.win.stackedWidget.addWidget(self.tab_widgets[n])	
				self.load_picker_orig(p)
			elif self.panels_mode == 2:
				#cmds.channelBox( 'dave', p='Rig Studio Picker|horizontalLayout_5|top_layout')
				#self.panel_widgets[n] = QtWidgets.QFrame()
				self.panel_widgets[n] = QtWidgets.QSplitter()
				self.panel_widgets[n].splitterMoved.connect(partial(self.save_spitter_sizes, self.panel_widgets[n]))
				layout = QtWidgets.QHBoxLayout( )
				layout.setContentsMargins(0,0,0,0)
				self.panel_widgets[n].setLayout( layout )
				self.win.stackedWidget.addWidget(self.panel_widgets[n])		
				self.load_picker_panel(p)
			else:
				#self.panel_widgets[n] = QtWidgets.QFrame()
				self.panel_widgets[n] = QtWidgets.QSplitter()
				self.panel_widgets[n].setOrientation(QtCore.Qt.Vertical)
				self.panel_widgets[n].splitterMoved.connect(partial(self.save_spitter_sizes, self.panel_widgets[n]))
				layout = QtWidgets.QVBoxLayout( )
				layout.setContentsMargins(0,0,0,0)
				self.panel_widgets[n].setLayout( layout )
				self.win.stackedWidget.addWidget(self.panel_widgets[n])		
				self.load_picker_panel(p)

			if len(pickers_names) > 1:
				#cmds.progressBar(progressControl, edit=True, step=1)	
				self.win.progressBar.setValue(self.win.progressBar.value()+step)				


		#if len(pickers_names) > 1:
			#cmds.deleteUI(window)

		self.win.progressBar.setVisible(False)

		pickerExist = len(pickers_names) > 0
		self.win.save_char_btn.setEnabled(pickerExist)
		self.win.delete_char_btn.setEnabled(pickerExist)
		self.win.load_btn.setEnabled(pickerExist)
		self.win.saveAs_char_btn.setEnabled(pickerExist)
		self.win.rename_btn.setEnabled(pickerExist)

		if pickerExist:
			self.cur_picker = self.pickers[self.get_root_name()]

		# save window geometry except first launch
		#if not edit and save_geometry:
			#self.save_geometry()
		save_geometry = True

		# fix for working create item buttons after launch
		self.setCurrentPicker(0)
		sel = cmds.ls(sl=1)
		if sel:
			self.selectionUpdateEvent(0)

		debugEnd(traceback.extract_stack()[-1][2])	

	def get_picker_nodes(self):
		network_nodes = cmds.ls(type = 'network')
		pickers_nodes = []
		for p in network_nodes:
			if cmds.objExists(p+'.type'):
				if cmds.getAttr(p+'.type') == "rs_pickerNode":
					pickers_nodes.append(p)
		
		return pickers_nodes

	def get_picker_names(self):
		pickers_names = []
		pickers_nodes = self.get_picker_nodes()
		for p in pickers_nodes:
			if p.split("_")[-1] == 'pkrData':
				name = p.split("_pkrData")[0]
				if p.replace("_pkrData", "Over_pkrData") in pickers_nodes:
					continue
				pickers_names.append(name)
		return pickers_names

	def get_root_name(self):
		root_name = self.win.char_selector_cb.currentText()
		if cmds.objExists(root_name+"_pkrData"):
			return root_name
		elif cmds.objExists(root_name+":pickerOver_pkrData"):
			return root_name + ":pickerOver"	
		elif cmds.objExists(root_name+":picker_pkrData"):
			return root_name + ":picker"

		cmds.warning("Miss picker")
		return None

	def save_spitter_sizes(self, s, v, n):
		x,y = s.sizes()
		#print("SSS", x,y)
		cmds.optionVar( floatValue = ( "rsPicker_splitterSizeX", x ) )
		cmds.optionVar( floatValue = ( "rsPicker_splitterSizeY", y ) )

	def setCurrentPicker(self, i):
		debugStart(traceback.extract_stack()[-1][2])
		#print ("SET Current picker")
		if not self.pickers:
			return

		self.win.stackedWidget.setCurrentIndex(i)

		name = self.get_root_name()

		if name in self.pickers:
			self.cur_picker = self.pickers[name]

			# update add item buttons connections
			if self.panels_mode:
				#n = self.panel_widgets[self.cur_picker.name].currentIndex()
				pass
			else:
				n = self.tab_widgets[self.cur_picker.name].currentIndex()
				self.tab_widgets[self.cur_picker.name].tab_switch(n)

		# Update layers list after loading all pickers
		self.win.layers_tableWidget.setRowCount(0)
		if 'layers' in self.cur_picker.data:
			for i, l in enumerate(self.cur_picker.data["layers"]):
				self.addLayer(l["name"], path=l["path"], vis=l["visibility"])


		# set current layer
		if "current_layer" not in self.cur_picker.data:
			self.cur_picker.data["current_layer"] = ["default"]
		for i in range(self.win.layers_tableWidget.rowCount()):
			if self.win.layers_tableWidget.item(i,1).text() == self.cur_picker.data["current_layer"]:
				self.win.layers_tableWidget.setCurrentItem(self.win.layers_tableWidget.item(i,1))		
				break

		# external autorun
		for cmd in self.cur_picker.data["autorun_ext_scripts"]:
			if script_errors:
				exec (cmd)
			else:			
				try:
					exec (cmd)
				except:
					cmds.warning ("Autorun external script error "+ self.cur_picker.name)

		# local autorun	
		self.autorun = self.cur_picker.data["autorun"]
		self.win.autorun_checkBox.setChecked(self.cur_picker.data["autorun"])
		cmd = self.cur_picker.data["autorun_script"]
		if self.autorun:
			if script_errors:
				if cmd:
					exec (cmd)
			else:			
				try:
					if cmd:
						exec (cmd)		
				except:
					cmds.warning ("Autorun script error "+ self.cur_picker.name)			

		# views size and position
		views = self.views[self.get_root_name()]
		for view in views:
			s = cmds.optionVar( q='rsPicker_viewSize_%s' %view.tab_name)
			
			if s:
				m = QtGui.QMatrix(s, 0.000000, 0.000000, s, 0.000000, 0.000000)
				view.setMatrix(m)
			x = cmds.optionVar( q='rsPicker_viewPosX_%s' %view.tab_name)
			y = cmds.optionVar( q='rsPicker_viewPosY_%s' %view.tab_name)
			view.centerOn(x,y)			

			# restore splitter sizes
			try:
				splitter = view.parent().parent().parent()
				splitter_sizes = [cmds.optionVar( q='rsPicker_splitterSizeX'), cmds.optionVar( q='rsPicker_splitterSizeY')]
				splitter.setSizes(splitter_sizes)
			except:
				pass
		
		self.view = self.tab_widgets[self.cur_picker.name].cur_view

		self.switchLayer()

		self.selectItemsFromSelected()


		debugEnd(traceback.extract_stack()[-1][2])	




	def load_picker_orig(self, picker, path=None):
		debugStart(traceback.extract_stack()[-1][2])

		#print ("LOAD PICKER")
		if not picker:
			return

		name = picker.name
		self.cur_picker = picker
		tab_widget = self.tab_widgets[name]

		tabs_names = []
		for t_data in picker.data["tabs"]:
			tabs_names.append(t_data["name"])

		# name
		if ":" in name:
			root_name = name.split(":")[-1]
			ns = name.split(":"+root_name)[0] + ":"
		else:
			ns = ""

		if path:
			picker.load(path=path)

		tabs_data = picker.data["tabs"]

		tab_widget.clear()

		for i, t_data in enumerate(tabs_data):
			t_name = t_data["name"]
			tab_widget.addTab(GraphicViewWidget(namespace=ns, main=self, main_window=self.win, tab_name=t_name), t_name)

		tab_widget.setCurrentIndex(0)


		layer_names = []
		for l in picker.data["layers"]:
			layer_names.append(l["name"])

		picker.data["autorun_ext_scripts"] = []

		# layers
		if 'layers' in picker.data:
			for i, l in enumerate(picker.data["layers"]):
				p = l["path"]

				if p and not os.path.exists(p):
					p_name = p.split('/')[-1]
					p = root_path + '/pickers/' + p_name

				# add external picker data
				if p:
					if os.path.exists(p):
						with open(p, mode='r') as f:
							layer_data = json.load(f)
							print ("Load external picker", p)

						# add external autorun script
						picker.data["autorun_ext_scripts"].append(layer_data["autorun_script"])

						# for every tab in external picker
						for t_data in layer_data["tabs"]:

							# if tab name already exist in main picker
							if t_data["name"] in tabs_names:

								# get this tab
								for t_d in tabs_data:
									if t_d["name"] == t_data["name"]:						
										if t_data["background"] != None:
											t_d["background_opacity"] = t_data["background_opacity"]
											t_d["background_offset_x"] = t_data["background_offset_x"]
											t_d["background_offset_y"] = t_data["background_offset_y"]
											t_d["background_flip"] = t_data["background_flip"]
											t_d["background"] = t_data["background"]									

										# add every item with renaming
										for item_data in t_data["items"]:
											item_data["name"] = l["name"] + "_" + item_data["name"]
											item_data["layer"] = l["name"]
											t_d["items"].append(item_data)
											#print (444, item_data["name"])

							else:
								tab_widget.addTab(GraphicViewWidget(namespace=ns, main=self, main_window=self.win, tab_name=t_name), t_data["name"])

								# add every item with renaming
								for item_data in t_data["items"]:
									item_data["name"] = l["name"] + "_" + item_data["name"]
									item_data["layer"] = l["name"]

								tabs_data.append(t_data)


		# set views list, data and indexes
		tab_widget.views = []
		for i in range(tab_widget.count()):
			view = tab_widget.widget(i)
			tab_widget.views.append(view)
			view.index = i
			view.data = tabs_data[i]
			view.tab_name = tabs_data[i]["name"]

		self.views[name] = tab_widget.views

		# create progress window
		count = tabs_data
		# set tabs data
		for i, t_data in enumerate(tabs_data):
			t_name = t_data["name"]

		#if len(count) > 1:
			#window = cmds.window(t='Load template')
			#cmds.columnLayout()			
			#progressControl = cmds.progressBar(maxValue=len(count)-1, minValue=0, width=300)
			#cmds.showWindow( window )

		tabs_vis = []
		names = []
		# set tabs data
		for i, t_data in enumerate(tabs_data):
			t_name = t_data["name"]

			view = tab_widget.getViewByName(t_name)

			if t_data["background"] != None:
				view.index = i
				view.background_opacity = t_data["background_opacity"]
				view.background_offset_x = t_data["background_offset_x"]
				view.background_offset_y = t_data["background_offset_y"]
				view.background_flip = t_data["background_flip"]
				view.tab_visibility = t_data["tab_visibility"]
				view.set_background(t_data["background"])	
				if view.tab_visibility:
					tabs_vis.append(i)

			if t_data["items"]:
				for item_data in t_data["items"]:
					# add item if it is visible
					if not self.edit and not item_data["visible"]:
						pass
					else:
						if not item_data["name"]:
							continue						
						if "slider" in item_data["name"]:
							continue
						#if "common_item_1" == item_data["name"] :
							#print (444, item_data["name"])							
						if not self.edit:
							skip = False
							if item_data["layer"] in self.get_external_layers():
								orig_name = item_data["name"].split(item_data["layer"]+"_")[1]
								if "face_head" == item_data["name"] :
									print (444, orig_name)	
									#print (444, item_data["name"])									
								for _item_data in t_data["items"]:
									if _item_data["name"] == orig_name:
										skip = True
										break						
							if skip:
								continue
						item = view.add_picker_item(setData=False)

						item_data_name = item_data["name"]

						if item_data["layer"] not in layer_names:
							item_data["layer"] = "default"	

						if item_data_name and item_data_name not in names:
							names.append(item_data_name)

						else: # set name if item has not name or it has duplicate name
							i=1
							name = "item_"+str(i)
							while(name in names):
								i += 1
								name = "item_"+str(i)	
							names.append(name)
							item_data["name"] = name							

						item.set_data(item_data)

						# fix mirrored attribute
						item.mirrored = item.name.split("_")[-1] == "MIRROR"

						if item.layer in self.get_external_layers():
							item.setFlag(item.ItemIsMovable, False)
							item.setFlag(item.ItemSendsScenePositionChanges, False)	
							item.setFlag(item.ItemIsSelectable, True)	

						if item.slider_item:
							item.slider_item.name = item.name+"_slider"
							item.slider_item.reset_slider()

				# connect mirrored items
				for item in view.items:
					if item.mirrored:
						source_item = item.get_source_mirror()
						if source_item:
							source_item.mirror = item
							item.source_mirror = source_item

			#if len(count) > 1:
				#cmds.progressBar(progressControl, edit=True, step=1)

			view.moveLock = picker.data["moveLock"]

		#if len(count) > 1:
			#cmds.deleteUI(window)

		# set current layer
		if "current_layer" not in picker.data:
			picker.data["current_layer"] = ["default"]
		for i in range(self.win.layers_tableWidget.rowCount()):
			if self.win.layers_tableWidget.item(i,1).text() == picker.data["current_layer"]:
				self.win.layers_tableWidget.setCurrentItem(self.win.layers_tableWidget.item(i,1))		
				break


		self.win.moveLock_checkBox.setChecked(picker.data["moveLock"])
		if "updateSelection" in picker.data:
			self.updateSelection = picker.data["updateSelection"]
			self.win.updateSelection_checkBox.setChecked(picker.data["updateSelection"])

		# refresh right buttons
		tab_widget.tab_switch(0)

		self.tabBar_visibility = picker.data['tabBar_visibility']
		self.win.tabBar_visibility_checkBox.setChecked(self.tabBar_visibility)

		# hide tabbar for matchrig
		if not self.edit and not self.tabBar_visibility:
			tab_widget.tabBar().hide()
		elif not self.edit:
			tab_widget.setTabBarAutoHide(True)
		else:
			tab_widget.tabBar().show()


		#self.autorun = picker.data["autorun"]
		#self.win.autorun_checkBox.setChecked(picker.data["autorun"])
		#cmd = picker.data["autorun_script"]
		#if self.autorun:
			#try:
				#if cmd:
					#localsParameter = {'tab_widget': tab_widget}
					#exec (cmd)#, localsParameter)		
			#except:
				#cmds.warning ("Autorun script error "+ picker.name)

		# run inital script				
		for view in tab_widget.views:
			for item in view.items:
				if item.init_script:
					localsParameter = {'tab_widget': tab_widget, 'item': item}
					cmd = item.init_script
					exec (cmd, localsParameter)	

		self.win.buttons_frame.setEnabled(1)
		self.win.rename_btn.setEnabled(1)
		self.win.background_frame.setEnabled(1)

		debugEnd(traceback.extract_stack()[-1][2])	

	def load_picker_panel(self, picker, path=None):
		debugStart(traceback.extract_stack()[-1][2])

		#print ("LOAD PICKER")
		if not picker:
			return

		name = picker.name
		self.cur_picker = picker
		panel_widget = self.panel_widgets[name]

		tabs_data = picker.data["tabs"]


		tabs_names = []
		for t_data in picker.data["tabs"]:
			tabs_names.append(t_data["name"])

		# name
		if ":" in name:
			root_name = name.split(":")[-1]
			ns = name.split(":"+root_name)[0] + ":"
		else:
			ns = ""

		if path:
			picker.load(path=path)

		tabs_data = picker.data["tabs"]

		#tab_widget.clear()
		views = []
		for i, t_data in enumerate(tabs_data):
			t_name = t_data["name"]

			tab_widget = ContextMenuTabWidget(self, main_window=self.win)
			panel_widget.layout().addWidget(tab_widget)				
			tab_widget.addTab(GraphicViewWidget(namespace=ns, main=self, main_window=self.win, tab_name=t_name), t_name)

			# set views list, data and indexes
			view = tab_widget.widget(0)
			view.data = tabs_data[i]
			views.append(view)

			tab_widget.tabBar().hide()

		self.views[name] = views

		picker.data["autorun_ext_scripts"] = []

		# layers
		if 'layers' in picker.data:
			for i, l in enumerate(picker.data["layers"]):
				p = l["path"]

				if p and not os.path.exists(p):
					p_name = p.split('/')[-1]
					p = root_path + '/pickers/' + p_name

				# add external picker data
				if p:
					if os.path.exists(p):

						with open(p, mode='r') as f:
							layer_data = json.load(f)
							print ("Load external picker", p)

						# add external autorun script
						picker.data["autorun_ext_scripts"].append(layer_data["autorun_script"])

						# for every tab in external picker
						for t_data in layer_data["tabs"]:

							# if tab name already exist in main picker
							if t_data["name"] in tabs_names:

								# get this tab
								for t_d in tabs_data:
									if t_d["name"] == t_data["name"]:						
										if t_data["background"] != None:
											t_d["background_opacity"] = t_data["background_opacity"]
											t_d["background_offset_x"] = t_data["background_offset_x"]
											t_d["background_offset_y"] = t_data["background_offset_y"]
											t_d["background_flip"] = t_data["background_flip"]
											t_d["background"] = t_data["background"]									

										# add every item with renaming
										for item_data in t_data["items"]:
											item_data["name"] = l["name"] + "_" + item_data["name"]
											item_data["layer"] = l["name"]
											t_d["items"].append(item_data)

							else:
								# add every item with renaming
								for item_data in t_data["items"]:
									item_data["name"] = l["name"] + "_" + item_data["name"]
									item_data["layer"] = l["name"]
								tabs_data.append(t_data)

		# create progress window
		count = tabs_data
		# set tabs data
		for i, t_data in enumerate(tabs_data):
			t_name = t_data["name"]

		#if len(count) > 1:
			#window = cmds.window(t='Load template')
			#cmds.columnLayout()			
			#progressControl = cmds.progressBar(maxValue=len(count)-1, minValue=0, width=300)
			#cmds.showWindow( window )

		names = []
		# set tabs data
		for i, t_data in enumerate(tabs_data):
			t_name = t_data["name"]
			#view = tab_widget.getViewByName(t_name)
			view = views[i]

			if t_data["background"] != None:
				view.index = i
				view.background_opacity = t_data["background_opacity"]
				view.background_offset_x = t_data["background_offset_x"]
				view.background_offset_y = t_data["background_offset_y"]
				view.background_flip = t_data["background_flip"]
				view.tab_visibility = t_data["tab_visibility"]
				view.set_background(t_data["background"])	

			if t_data["items"]:
				for item_data in t_data["items"]:

					# add item if it is visible
					if not self.edit and not item_data["visible"]:
						pass
					else:
						if not item_data["name"]:
							continue						
						if "slider" in item_data["name"]:
							continue

						item = view.add_picker_item(setData=False)

						item_data_name = item_data["name"]

						if item_data_name and item_data_name not in names:
							names.append(item_data_name)

						else: # set name if item has not name or it has duplicate name
							i=1
							name = "item_"+str(i)
							while(name in names):
								i += 1
								name = "item_"+str(i)	
							names.append(name)
							item_data["name"] = name							

						item.set_data(item_data)

						# fix mirrored attribute
						item.mirrored = item.name.split("_")[-1] == "MIRROR"

						if item.layer in self.get_external_layers():
							item.setFlag(item.ItemIsMovable, False)
							item.setFlag(item.ItemSendsScenePositionChanges, False)	

						if item.slider_item:
							item.slider_item.name = item.name+"_slider"
							item.slider_item.reset_slider()

				# connect mirrored items
				for item in view.items:
					if item.mirrored:
						source_item = item.get_source_mirror()
						if source_item:
							source_item.mirror = item
							item.source_mirror = source_item
			#if len(count) > 1:
				#cmds.progressBar(progressControl, edit=True, step=1)

			view.moveLock = picker.data["moveLock"]

		#if len(count) > 1:
			#cmds.deleteUI(window)

		tab_widget.tabBar().hide()

		#self.autorun = picker.data["autorun"]
		#self.win.autorun_checkBox.setChecked(picker.data["autorun"])
		#cmd = picker.data["autorun_script"]
		#if self.autorun:
			#try:
				#if cmd:
					#localsParameter = {'tab_widget': tab_widget}
					#exec (cmd)#, localsParameter)		
			#except:
				#cmds.warning ("Autorun script error "+ picker.name)

		# run inital script				
		for view in views:
			for item in view.items:
				if item.init_script:
					localsParameter = {'tab_widget': tab_widget, 'item': item}
					cmd = item.init_script
					exec (cmd, localsParameter)	

		debugEnd(traceback.extract_stack()[-1][2])	

	def selectItemsFromSelected(self):
		debugStart(traceback.extract_stack()[-1][2])
		views = self.views[self.cur_picker.name]
		items = []
		sel = cmds.ls(sl=1)
		for view in views:
			for item in view.items:
				if not item.selectionOnClick:
					continue
				if len(item.controls) > 0:
					for c in item.get_controls():
						if c in sel:
							items.append(item)
		self.selectItems(items, event=None, selectControls=False)
		debugEnd(traceback.extract_stack()[-1][2])

	def selectItems(self, items, event=None, selectControls=True):
		debugStart(traceback.extract_stack()[-1][2])

		views = self.views[self.cur_picker.name]

		selected_items = []
		#controls = []
		for view in views:
			view_items = []
			for it in items:
				if it in view.items:
					view_items.append(it)
					#for c in it.get_controls():
						#if cmds.objExists(c):
							#controls.append(c)
			#if view_items:
			sel_view_items = view.selectItems(view_items, event=event, selectControls=selectControls)
			if sel_view_items:
				selected_items += sel_view_items

		if edit:
			if selected_items:
				self.picker_item = items[-1]
			else:
				self.picker_item = None
			self.updateItemFrame()	
		#else:
			#print (3333, controls)

			#if event:
				#modifiers = event.modifiers()
			#else:
				#modifiers = None

			#if modifiers == QtCore.Qt.ControlModifier:
				#self.win.autoLoadPicker_btn.setChecked(False)
				#cmds.select(controls, add=1)
				#print (444)
				#self.win.autoLoadPicker_btn.setChecked(True)
			#else:
				#cmds.select(controls)



			#cmds.select(controls)

		debugEnd(traceback.extract_stack()[-1][2])

	def merge_picker(self, path=None):
		debugStart(traceback.extract_stack()[-1][2])

		filePath = os.path.join(root_path, "pickers")

		if not full:
			QtWidgets.QMessageBox.information(self.win, "Sorry", "This feature is available in full version only.")
			return		

		# open select window 
		if not path:
			path = QtWidgets.QFileDialog.getOpenFileName(self.win, "merge template", filePath, "*.json")[0]
			if path == "":
				return
		merge_name = path.split("/")[-1].split(".")[0]

		self.cur_picker.merge(path=path)

		self.cur_picker.load(path=path)

		self.load_picker_orig(self.cur_picker)		

		#debugEnd(traceback.extract_stack()[-1][2])	


	def reloadPickers(self, v=False, reload=False):
		debugStart(traceback.extract_stack()[-1][2])
		print ("reloadPickers", v)

		if not reload:

			picker_nodes = self.get_picker_nodes()
			if picker_nodes != self.picker_nodes:
				self.update_selector()
			return

		import rigStudio_picker.picker
		rigStudio_picker.picker.main.run(edit=False)	

		return

		#self.remove_events()

		global save_geometry, picker_win

		if not edit and save_geometry:
			self.save_geometry()
		save_geometry = True

		x = configData["window_positon_x"]
		y = configData["window_positon_y"]
		w = configData["window_width"]
		h = configData["window_height"]

		#cmds.deleteUI('RS Picker')

		import rigStudio_picker.picker
		rigStudio_picker.picker.main.run(edit=False)		

		#print (picker_win)

		# restore geometry
		picker_win.parent().parent().parent().parent().parent().adjustSize()
		picker_win.parent().parent().parent().parent().parent().setGeometry(x,y,w,h)			
		return		



		x = self.parent().parent().parent().parent().parent().geometry().x()
		y = self.parent().parent().parent().parent().parent().geometry().y()
		w = self.parent().parent().parent().parent().parent().geometry().width()
		h = self.parent().parent().parent().parent().parent().geometry().height()		

		picker_win = dock_window(MyDockingUI, edit, rigFromJoints)

		# restore geometry
		picker_win.parent().parent().parent().parent().parent().adjustSize()
		picker_win.parent().parent().parent().parent().parent().setGeometry(x,y,w,h)	

		#configData["window_positon_x"] = x
		#configData["window_positon_y"] = y
		#configData["window_width"] = w
		#configData["window_height"] = h

		#json_string = json.dumps(configData, indent=4)
		#with open(root_path+'/config.json', 'w') as f:
			#f.write(json_string)	

		debugEnd(traceback.extract_stack()[-1][2])	



	def rename_picker(self):
		debugStart(traceback.extract_stack()[-1][2])

		name, ok = QtWidgets.QInputDialog.getText(self,
                                                  self.tr("Rename"),
                                                  self.tr('Node name'),
                                                          QtWidgets.QLineEdit.Normal,
                                                          self.cur_picker.name)
		if not (ok and name):
			return			

		self.cur_picker.rename(name)
		self.update_selector()
		self.set_current_selector(name)

		debugEnd(traceback.extract_stack()[-1][2])	

	def set_current_selector(self, name):
		debugStart(traceback.extract_stack()[-1][2])
		#print ("SET Current selector")
		#Will set character selector to specified data_node
		for i in range(self.win.char_selector_cb.count()):
			item_name = self.win.char_selector_cb.itemText(i)

			if item_name + ":picker" == name:
				self.win.char_selector_cb.setCurrentIndex(i)
				return

		debugEnd(traceback.extract_stack()[-1][2])	

	def updateItemFrame(self):
		debugStart(traceback.extract_stack()[-1][2])
		#print (2222, self.picker_item)
		if not self.picker_item:
			self.win.left_frame.setEnabled(False)
			self.win.label_lineEdit.setText("")
			self.win.obj_name_lineEdit.setText("")
			self.win.obj_layer_lineEdit.setText("")
			self.win.label_size_spinBox.setValue(0)
			palette = QtGui.QPalette()
			palette.setColor(QtGui.QPalette.Button, QtGui.QColor(100,100,100))
			self.win.color_button.setPalette(palette)
			self.win.label_color_btn.setPalette(palette)
			self.win.width_spinBox.setValue(0)
			self.win.height_spinBox.setValue(0)
			return

		else:
			self.items_update = False

			item = self.picker_item
			self.win.left_frame.setEnabled(True)

			isLabel = False
			isRect = False
			isButton = False

			if type(item) is PointHandle:
				return
			elif type(item) is QtWidgets.QGraphicsProxyWidget:
				item = item.parentItem()
			elif type(item) is GraphicText:
				item = item.parentItem()
			elif item.polygon.shape_type == "rect" or item.polygon.shape_type == "slider_back":	isRect = True
			elif item.polygon.shape_type == "button":	isButton = True
			elif item.get_text():	isLabel = True

			self.win.color_label.setVisible(False)
			self.win.color_button.setVisible(False)
			self.win.opacity_label.setVisible(False)
			self.win.btn_opacity_slider.setVisible(False)
			self.win.btn_opacity_lineEdit.setVisible(False)
			self.win.width_label.setVisible(False)
			self.win.width_spinBox.setVisible(False)
			self.win.height_label.setVisible(False)
			self.win.height_spinBox.setVisible(False)
			self.win.radius_label.setVisible(False)
			self.win.squash_label.setVisible(False)
			self.win.radius_spinBox.setVisible(False)
			self.win.squash_spinBox.setVisible(False)	
			self.win.editShape_frame.setVisible(False)
			self.win.rotate_label.setVisible(False)
			self.win.rotate_spinBox.setVisible(False)
			self.win.flip_label.setVisible(False)
			self.win.flip_checkBox.setVisible(False)
			self.win.path_label.setVisible(False)
			self.win.path_lineEdit.setVisible(False)
			self.win.setImagePath_btn.setVisible(False)			

			self.win.label_frame.setVisible(isLabel or isRect or isButton)
			self.win.clickCommand_frame.setVisible(not isLabel)
			self.win.shape_frame.setVisible(not isLabel)
			self.win.rmb_frame.setVisible(not isLabel)
			self.win.slider_frame.setVisible(item.slider!=None)

			self.win.visibility_checkBox.setChecked(item.visible)
			self.win.obj_name_lineEdit.setText(item.name)
			self.win.obj_layer_lineEdit.setText(item.layer)

			#self.win.slider_1_lineEdit.setText(self.picker_item.slider_objects[1])
			#self.win.slider_2_lineEdit.setText(self.picker_item.slider_objects[2])
			#self.win.slider_3_lineEdit.setText(self.picker_item.slider_objects[3])
			#self.win.slider_4_lineEdit.setText(self.picker_item.slider_objects[4])
			#self.win.slider_5_lineEdit.setText(self.picker_item.slider_objects[5])

			if isLabel:
				self.win.color_label.setVisible(True)
				self.win.color_button.setVisible(True)
				self.win.opacity_label.setVisible(True)
				self.win.btn_opacity_slider.setVisible(True)
				self.win.btn_opacity_lineEdit.setVisible(True)
				self.win.label_lineEdit.setText(item.get_text())
				self.win.label_size_spinBox.setValue(item.text.get_size())

			elif isRect:
				self.win.color_label.setVisible(True)
				self.win.color_button.setVisible(True)
				self.win.opacity_label.setVisible(True)				
				self.win.btn_opacity_slider.setVisible(True)				
				self.win.btn_opacity_lineEdit.setVisible(True)				
				self.win.width_label.setVisible(True)
				self.win.width_spinBox.setVisible(True)
				self.win.height_label.setVisible(True)
				self.win.height_spinBox.setVisible(True)
				self.win.width_spinBox.setValue(item.polygon.width)
				self.win.height_spinBox.setValue(item.polygon.height)
				self.win.radius_label.setVisible(True)
				self.win.radius_spinBox.setVisible(True)
				self.win.radius_spinBox.setValue(item.polygon.radius)
				self.win.label_lineEdit.setText(item.get_text())
				self.win.label_size_spinBox.setValue(item.text.get_size())				
				self.win.rotate_label.setVisible(True)
				self.win.rotate_spinBox.setVisible(True)
				self.win.rotate_spinBox.setValue(item.polygon.rotate)

			elif item.polygon.shape_type == "text":
				self.win.width_label.setVisible(True)
				self.win.width_spinBox.setVisible(True)
				self.win.width_spinBox.setValue(item.polygon.width)

			elif isButton:
				self.win.width_label.setVisible(True)
				self.win.width_spinBox.setVisible(True)
				self.win.height_label.setVisible(True)
				self.win.height_spinBox.setVisible(True)
				self.win.width_spinBox.setValue(item.polygon.width)
				self.win.height_spinBox.setValue(item.polygon.height)
				self.win.label_lineEdit.setText(item.button.text())


			elif item.polygon.shape_type == "circle":
				self.win.color_label.setVisible(True)
				self.win.color_button.setVisible(True)
				self.win.opacity_label.setVisible(True)				
				self.win.btn_opacity_slider.setVisible(True)				
				self.win.btn_opacity_lineEdit.setVisible(True)				
				self.win.radius_label.setVisible(True)
				self.win.squash_label.setVisible(True)
				self.win.radius_spinBox.setVisible(True)
				self.win.squash_spinBox.setVisible(True)
				self.win.radius_spinBox.setValue(item.polygon.radius)
				self.win.squash_spinBox.setValue(item.polygon.squash)

			else:
				self.win.color_label.setVisible(True)
				self.win.color_button.setVisible(True)
				self.win.opacity_label.setVisible(True)				
				self.win.btn_opacity_slider.setVisible(True)				
				self.win.btn_opacity_lineEdit.setVisible(True)				
				self.win.editShape_frame.setVisible(True)
				self.win.linear_rbtn.setChecked(item.polygon.path_type=="linear")
				self.win.cubic_rbtn.setChecked(item.polygon.path_type=="cubic")
				self.win.quadratic_rbtn.setChecked(item.polygon.path_type=="quadratic")

			# Image
			if item.polygon.image_path:
				self.win.rotate_label.setVisible(True)
				self.win.rotate_spinBox.setVisible(True)
				self.win.flip_label.setVisible(True)
				self.win.flip_checkBox.setVisible(True)
				self.win.path_lineEdit.setVisible(True)
				self.win.setImagePath_btn.setVisible(True)
				self.win.path_label.setVisible(True)
				self.win.flip_checkBox.setChecked(item.polygon.flipped)
				self.win.rotate_spinBox.setValue(item.polygon.rotate)
				self.win.path_lineEdit.setText(item.polygon.image_path)


			# Update button color

			if isLabel or item.polygon.shape_type == "text":
				palette = QtGui.QPalette()
				color = item.text.get_color()
				palette.setColor(QtGui.QPalette.Button, color)
				self.win.label_color_btn.setPalette(palette)
			else:
				color = item.get_color()
				palette = QtGui.QPalette()
				palette.setColor(QtGui.QPalette.Button, color)
				self.win.color_button.setPalette(palette)

			opacity = int(float(item.polygon.opacity)/255*100)  
			self.win.btn_opacity_lineEdit.setText(str(opacity))

			label_opacity = int(float(item.text.opacity)/255*100)  
			self.win.label_opacity_lineEdit.setText(str(label_opacity))

			self.win.btn_opacity_slider.setValue(item.polygon.opacity)
			self.win.label_opacity_slider.setValue(item.text.opacity)
			self.win.item_x_spinBox.setValue(item.x())
			self.win.item_y_spinBox.setValue(item.y())

			if item.selectionOnClick:
				self.win.selection_btn.setChecked(True)
			else:
				self.win.pythonScript_btn.setChecked(True)
			self.select_script_toggle()

			self.rmb_list_update()

			self.items_update = True

		debugEnd(traceback.extract_stack()[-1][2])	

	def opacity_slider_update(self, v):
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		for item in self.view.selected_items:
			color = item.get_color()
			item.polygon.opacity = v
			item.update()
			self.win.btn_opacity_lineEdit.setText(str( int(float(v)/255*100)) )

		debugEnd(traceback.extract_stack()[-1][2])	

	def item_position_update(self, v, axis):
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return
		for item in self.view.selected_items:
			pos = item.pos()
			if axis == "x":
				item.setPos(float(v), pos.y())
			else:
				item.setPos(pos.x(), float(v))

			if item.mirror:
				item.mirror.update_mirrored_position()

		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def item_move(self, direction, shift=None):
		debugStart(traceback.extract_stack()[-1][2])

		if shift: v = 10
		else: v = 1

		for item in self.view.selected_items:
			if not item.mirrored:
				pos = item.pos()
				if direction == "up":
					item.setPos(pos.x(), pos.y()-v)
				elif direction == "down":
					item.setPos(pos.x(), pos.y()+v)
				elif direction == "left":
					item.setPos(pos.x()-v, pos.y())
				elif direction == "right":
					item.setPos(pos.x()+v, pos.y())

			if item.mirror:
				item.mirror.update_mirrored_position()

		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	



	def label_text_update(self, text):
		debugStart(traceback.extract_stack()[-1][2])

		if not self.picker_item:
			return		
		if not self.items_update:
			return
		for item in self.view.selected_items:
			if not text:
				text = " "
			item.set_text(text)

		debugEnd(traceback.extract_stack()[-1][2])	

	def label_size_update(self, v):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.picker_item:
			return		
		if not self.items_update:
			return
		for item in self.view.selected_items:
			item.text.set_size(v)

		debugEnd(traceback.extract_stack()[-1][2])	

	def label_opacity_update(self, v):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		for item in self.view.selected_items:
			item.text.set_opacity(v)
			self.win.label_opacity_lineEdit.setText(str( int(float(v)/255*100)) )

		debugEnd(traceback.extract_stack()[-1][2])	

	def rect_width_update(self, v):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		views = self.views[self.cur_picker.name]
		for view in views:
			for item in view.selected_items:
				item.polygon.width = v
				item.update_lineEdit()
				item.update()
				view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def rect_height_update(self, v):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		views = self.views[self.cur_picker.name]
		for view in views:
			for item in view.selected_items:
				item.polygon.height = v
				item.update_lineEdit()
				item.update()
				view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def circle_radius_update(self, v):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		for item in self.view.selected_items:
			item.polygon.radius = v
			item.update()

			if item.mirror:
				item.mirror.polygon.radius = v
				item.mirror.update()

		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def circle_squash_update(self, v):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		for item in self.view.selected_items:
			item.polygon.squash = v
			item.update()
		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def image_rotate_update(self, v):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		for item in self.view.selected_items:
			item.polygon.rotate = v
			item.update()
		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def image_flip_update(self):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		v = self.win.flip_checkBox.isChecked()
		for item in self.view.selected_items:
			item.polygon.flipped = v
			item.update()
		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def set_visibility_item(self):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		v = self.win.visibility_checkBox.isChecked()
		for item in self.view.selected_items:
			item.set_visible(v)
			#item.text.visible = v
			#item.update()
		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def image_set_update(self):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		file_path = QtWidgets.QFileDialog.getOpenFileName(self.win,"Open Image File",images_pth)[0]
		if file_path:
			for item in self.view.selected_items:
				item.polygon.image = QtGui.QImage(file_path)#.mirrored(False, True)
				item.polygon.image_path = file_path
				item.polygon.generate_grey_image()
				item.polygon.render_image = item.polygon.image
				item.set_handles(item.get_default_handles())				
				item.update()
			self.view.scene().update()
			self.updateItemFrame()

		debugEnd(traceback.extract_stack()[-1][2])	

	def edit_shape_toggle(self):	
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return		
		for item in self.view.selected_items:
			item.toggle_edit_status()

		debugEnd(traceback.extract_stack()[-1][2])	

	def set_shape(self, shape):
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return
		for item in self.view.selected_items:
			item.set_shape(shape)
		self.view.scene().update()

	def scale_shape(self, more=1):
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return
		for item in self.view.selected_items:
			item.set_scale_shape(more)
		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def rotate_shape(self, left=1):
		debugStart(traceback.extract_stack()[-1][2])

		if not self.items_update:
			return
		for item in self.view.selected_items:
			item.set_rotate_shape(left)
		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def path_type_toggle(self):
		debugStart(traceback.extract_stack()[-1][2])

		if self.win.linear_rbtn.isChecked():
			self.picker_item.polygon.path_type = "linear"
		elif self.win.quadratic_rbtn.isChecked():
			self.picker_item.polygon.path_type = "quadratic"
		elif self.win.cubic_rbtn.isChecked():
			self.picker_item.polygon.path_type = "cubic"

		self.picker_item.view.update()

	def select_script_toggle(self):
		debugStart(traceback.extract_stack()[-1][2])

		if self.win.selection_btn.isChecked():
			self.win.setSelection_btn.setEnabled(True)
			self.win.editScript_btn.setEnabled(False)
		else:
			self.win.setSelection_btn.setEnabled(False)
			self.win.editScript_btn.setEnabled(True)

		debugEnd(traceback.extract_stack()[-1][2])	

	def edit_autorun_script(self):
		debugStart(traceback.extract_stack()[-1][2])

		# Open input window
		script = self.cur_picker.data["autorun_script"]

		cmd, ok = CustomScriptEditDialog.get(cmd=script,
                                             item=None)
		if not (ok and cmd):
			return

		self.cur_picker.data["autorun_script"] = cmd

		debugEnd(traceback.extract_stack()[-1][2])	

	def edit_custom_action_script(self):
		debugStart(traceback.extract_stack()[-1][2])

		# Open input window
		action_script = self.picker_item.custom_action_script

		cmd, ok = CustomScriptEditDialog.get(cmd=action_script,
                                             item=self.picker_item)
		if not (ok and cmd):
			return

		#self.picker_item.custom_action_script = cmd
		for item in self.view.selected_items:
			try:
				item.custom_action_script = cmd
			except: pass		

		debugEnd(traceback.extract_stack()[-1][2])	

	def run_custom_action_script(self):
		debugStart(traceback.extract_stack()[-1][2])

		if self.picker_item.custom_action_script:
			self.picker_item.run_script()

	def edit_init_script(self):
		debugStart(traceback.extract_stack()[-1][2])

		# Open input window
		script = self.picker_item.init_script
		cmd, ok = CustomScriptEditDialog.get(cmd=script, item=self.picker_item)

		if not ok:
			return

		#self.picker_item.init_script = cmd
		for item in self.view.selected_items:
			try:
				item.init_script = cmd
			except: pass	

		debugEnd(traceback.extract_stack()[-1][2])	

	def edit_menu_script(self):
		debugStart(traceback.extract_stack()[-1][2])

		curItem = self.win.rmb_listWidget.currentItem()
		if not curItem:
			return		

		curItem_name = curItem.text()

		def indexByName(name, item):
			for i, name in enumerate(item.rmb_items):
				if name == curItem_name:
					return i
			return None

		# Open input window
		ind = indexByName(curItem_name, self.picker_item)
		action_script = self.picker_item.rmb_scripts[ind]

		cmd, ok = CustomScriptEditDialog.get(cmd=action_script,
                                             item=self.picker_item)
		if not (ok and cmd):
			return

		#self.picker_item.rmb_scripts[ind] = cmd

		for item in self.view.selected_items:
			i = indexByName(curItem_name, item)
			try:
				item.rmb_scripts[i] = cmd
			except: pass

		debugEnd(traceback.extract_stack()[-1][2])	

	def rmb_list_update(self):
		debugStart(traceback.extract_stack()[-1][2])

		try:
			self.win.rmb_listWidget.clear()
			self.win.rmb_listWidget.addItems(self.picker_item.rmb_items)		
		except: pass

		debugEnd(traceback.extract_stack()[-1][2])	

	def rmb_add(self):
		debugStart(traceback.extract_stack()[-1][2])

		name, ok = QtWidgets.QInputDialog().getText(self.win, 'Add menu item', 'Enter action name:', QtWidgets.QLineEdit.Normal, 'action')

		# remove spaces
		if ok and name != "":
			if name in self.picker_item.rmb_items:
				QtWidgets.QMessageBox.information(self.win, "Warning", "Action with this name is exist.")
				return			
		else:
			return	


		default_script = CustomScriptEditDialog.get_default_script()

		for item in self.view.selected_items:
			if name not in item.rmb_items:
				item.rmb_items.append(name)
				item.rmb_scripts.append(default_script)

		self.rmb_list_update()

		item = self.win.rmb_listWidget.findItems(name, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)[0]
		self.win.rmb_listWidget.setCurrentItem(item)	

		debugEnd(traceback.extract_stack()[-1][2])	

	def rmb_remove(self):
		debugStart(traceback.extract_stack()[-1][2])

		item = self.win.rmb_listWidget.currentItem()
		if not item:
			return		

		curItem_name = item.text()

		def indexByName(name, item):
			for i, name in enumerate(item.rmb_items):
				if name == curItem_name:
					return i
			return None

		for item in self.view.selected_items:
			i = indexByName(curItem_name, item)
			try:
				del item.rmb_items[i]
				del item.rmb_scripts[i]
			except: pass

		self.rmb_list_update()

	def rmb_move(self, direction):
		debugStart(traceback.extract_stack()[-1][2])

		curItem = self.win.rmb_listWidget.currentItem()
		if not curItem:
			return		

		curItem_name = curItem.text()

		for i, name in enumerate(self.picker_item.rmb_items):
			if name == curItem_name:
				curIndex = i

		# stop on edges of list
		if direction == "up" and curIndex == 0:
			return
		if direction == "down" and curIndex == len(self.picker_item.rmb_items)-1:
			return

		if direction == "up":
			targetIndex = curIndex - 1
		elif direction == "down":
			targetIndex = curIndex + 1

		first_ele = self.picker_item.rmb_items.pop(targetIndex)
		self.picker_item.rmb_items.insert(curIndex, first_ele) 			
		first_ele = self.picker_item.rmb_scripts.pop(targetIndex)
		self.picker_item.rmb_scripts.insert(curIndex, first_ele) 			

		# change selection
		self.rmb_list_update()
		item = self.win.rmb_listWidget.findItems(curItem_name, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)[0]
		self.win.rmb_listWidget.setCurrentItem(item)			

		debugEnd(traceback.extract_stack()[-1][2])	

	def selectionOnClick_update(self):
		debugStart(traceback.extract_stack()[-1][2])

		self.picker_item.selectionOnClick = self.win.selection_btn.isChecked()

		debugEnd(traceback.extract_stack()[-1][2])	

	def set_selection(self):
		debugStart(traceback.extract_stack()[-1][2])

		self.picker_item.set_selected_controls()

		debugEnd(traceback.extract_stack()[-1][2])	

	def moveLock_update(self):
		debugStart(traceback.extract_stack()[-1][2])

		self.view.moveLock = self.win.moveLock_checkBox.isChecked()
		self.cur_picker.data["moveLock"] = self.view.moveLock

		debugEnd(traceback.extract_stack()[-1][2])	

	def updateSelection_update(self):
		debugStart(traceback.extract_stack()[-1][2])

		self.updateSelection = self.win.updateSelection_checkBox.isChecked()
		self.cur_picker.data["updateSelection"] = self.updateSelection

		debugEnd(traceback.extract_stack()[-1][2])	

	def showHidden_update(self):
		debugStart(traceback.extract_stack()[-1][2])

		self.showHidden = self.win.showHidden_checkBox.isChecked()
		self.view.scene().update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def tabBar_visibility_set(self):
		debugStart(traceback.extract_stack()[-1][2])

		self.tabBar_visibility = self.win.tabBar_visibility_checkBox.isChecked()
		self.cur_picker.data["tabBar_visibility"] = self.tabBar_visibility

		debugEnd(traceback.extract_stack()[-1][2])	

	def use_autorun(self):
		debugStart(traceback.extract_stack()[-1][2])

		self.autorun = self.win.autorun_checkBox.isChecked()
		self.cur_picker.data["autorun"] = self.autorun

		debugEnd(traceback.extract_stack()[-1][2])	

	def run_autorun(self):
		debugStart(traceback.extract_stack()[-1][2])

		cmd = self.cur_picker.data["autorun_script"]
		tab_widget = self.tab_widgets[self.cur_picker.name]
		if cmd:
			localsParameter = {'tab_widget': tab_widget}
			if script_errors:
				exec (cmd)
			else:
				try:
					exec (cmd)#, localsParameter)
				except:
					cmds.warning ("Run autorun script error ")

		debugEnd(traceback.extract_stack()[-1][2])	

	def set_obj_name(self):
		debugStart(traceback.extract_stack()[-1][2])

		name, ok = QtWidgets.QInputDialog().getText(self.win, 'Set item name', 'Enter name:', QtWidgets.QLineEdit.Normal, self.picker_item.name)

		# remove spaces
		if ok and name != "":
			pass
			#for item in self.view.items:
				#if name == item.name:
					#QtWidgets.QMessageBox.information(self, "Warning", "Object with this name is already exist")
					#return
		else:
			return			

		for item in self.view.selected_items:
			try:
				item.name = name
				item.mirror.name = name + "_MIRROR"
			except: pass	

		self.updateItemFrame()

		debugEnd(traceback.extract_stack()[-1][2])	

	def layerIsExternal(self, layer_name):
		for l in self.cur_picker.data["layers"]:
			if l["name"] == layer_name:
				if l["path"]:
					return True
				else:
					return False
		cmds.warning("Cannot find the layer")

	def set_obj_layer(self):
		debugStart(traceback.extract_stack()[-1][2])

		layers = []
		ext_layers = []
		for l in self.cur_picker.data["layers"]:
			layers.append(l["name"])
			if l["path"]:
				ext_layers.append(l["name"])

		#name, ok = QtWidgets.QInputDialog().getText(self.win, 'Set item layer', 'Enter name:', QtWidgets.QListWidget.Normal, self.picker_item.layer)
		name, ok = QtWidgets.QInputDialog.getItem(self, "select input dialog", "list of languages", layers, 0, False)		

		# remove spaces
		if ok:
			#for item in self.view.selected_items:
				#print (444, item)
				#print (444, self.itemFromExternalLayer(item))
				#if self.itemFromExternalLayer(item):
					#QtWidgets.QMessageBox.information(self, "Warning", "Items from external layers cannot be changed.")
					#return

			for item in self.view.selected_items:
				item.layer = name
				item.set_visible(l["visibility"])

			self.updateItemFrame()

		self.view.scene().update()
		#self.view.update()

		debugEnd(traceback.extract_stack()[-1][2])	

	def get_all_picker_items(self):
		debugStart(traceback.extract_stack()[-1][2])
		#Return all picker items for current picker

		#Returns all picker items for all tabs
		tab_widget = self.tab_widgets[self.cur_picker.name]
		items = []
		for i in range(tab_widget.count()):
			items.extend(tab_widget.widget(i).get_picker_items())

		debugEnd(traceback.extract_stack()[-1][2])	
		return items

	def get_data(self):
		debugStart(traceback.extract_stack()[-1][2])
		return
		#tabs data
		data = []
		for i in range(self.win.tab_widget.count()):
			name = str(self.win.tab_widget.tabText(i))
			tab_data = self.win.tab_widget.widget(i).get_data()
			data.append({"name": name, "data": tab_data})
		return data

	def set_data(self, data):
		debugStart(traceback.extract_stack()[-1][2])
		return
		#tabs data
		self.win.tab_widget.clear()
		for tab in data:
			self.win.tab_widget.addTab(self.view, tab.get('name', 'default'))

			tab_content = tab.get('data', None)
			if tab_content:
				view.set_data(tab_content)	

	def change_color_event(self):
		debugStart(traceback.extract_stack()[-1][2])

		#Will edit polygon color based on new values

		# Skip if event is disabled (updating ui value)
		if self.event_disabled or not self.picker_item:
			return

		# Open color picker dialog
		picker_color = self.picker_item.get_color()
		color = QtWidgets.QColorDialog.getColor(initial=picker_color,
                                                parent=self.win)

		# Abort on invalid color (cancel button)
		if not color.isValid():
			return

		# Update button color
		palette = QtGui.QPalette()
		palette.setColor(QtGui.QPalette.Button, color)
		self.win.color_button.setPalette(palette)

		# Edit new color alpha
		alpha = self.picker_item.get_color().alpha()
		color.setAlpha(alpha)
		#self.btn_opacity_slider.setValue(alpha)

		# Update color
		for item in self.view.selected_items:
			item.set_color(color)

			if item.mirror:			
				item.mirror.set_color(color)

		debugEnd(traceback.extract_stack()[-1][2])	

	def label_change_color_event(self):
		debugStart(traceback.extract_stack()[-1][2])

		#Will edit polygon color based on new values
		# Skip if event is disabled (updating ui value)
		if self.event_disabled or not self.picker_item:
			return

		# Open color picker dialog
		picker_color = self.picker_item.text.get_color()
		color = QtWidgets.QColorDialog.getColor(initial=picker_color,
                                                parent=self.win)
		# Abort on invalid color (cancel button)
		if not color.isValid():
			return

		# Update button color
		palette = QtGui.QPalette()
		palette.setColor(QtGui.QPalette.Button, color)
		self.win.label_color_btn.setPalette(palette)

		# Edit new color alpha
		alpha = self.picker_item.text.get_color().alpha()
		color.setAlpha(alpha)
		#self.btn_opacity_slider.setValue(alpha)

		# Update color
		self.picker_item.text.set_color(color)

		debugEnd(traceback.extract_stack()[-1][2])	

	def load_template(self, path=None):
		debugStart(traceback.extract_stack()[-1][2])

		filePath = os.path.join(root_path, "pickers")

		if not full:
			QtWidgets.QMessageBox.information(self.win, "Sorry", "This feature is available in full version only.")
			return		

		# open select window 
		if not path:
			path = QtWidgets.QFileDialog.getOpenFileName(self.win, "load template", filePath, "*.json")[0]
			if path == "":
				return
		name = path.split("/")[-1].split(".")[0]

		self.load_picker_orig(self.cur_picker, path)
		#self.save_picker()

		debugEnd(traceback.extract_stack()[-1][2])	

	def load_controls_template(self, path=None):
		debugStart(traceback.extract_stack()[-1][2])

		filePath = os.path.join(root_path, "pickers")

		# open select window 
		if not path:
			path = QtWidgets.QFileDialog.getOpenFileName(self.win, "load joints set", filePath, "*.json")[0]
			if path == "":
				return

		name = path.split("/")[-1].split(".")[0]
		self.cur_picker.load_controls_data(name=name, path=path)
		self.load_picker_orig(self.cur_picker)
		#self.save_picker()

		debugEnd(traceback.extract_stack()[-1][2])	

	def save_as_template(self):
		debugStart(traceback.extract_stack()[-1][2])

		filePath = os.path.join(root_path, "pickers")
		t_name = QtWidgets.QFileDialog.getSaveFileName(self.win, "Save template", filePath, "*.json")[0]

		if t_name == "":
			return		

		self.cur_picker.exportToFile(t_name)	

		debugEnd(traceback.extract_stack()[-1][2])	

	def get_external_layers(self):
		debugStart(traceback.extract_stack()[-1][2])

		if 'layers' not in self.cur_picker.data:
			return []
		ext_layers = []
		for l in self.cur_picker.data["layers"]:
			if l["path"]:
				ext_layers.append(l["name"])

		debugEnd(traceback.extract_stack()[-1][2])	
		return ext_layers

	def get_visible_internal_layers(self):
		debugStart(traceback.extract_stack()[-1][2])

		if 'layers' not in self.cur_picker.data:
			return []

		visible_layers = []
		for i in range(self.win.layers_tableWidget.rowCount()):
			b = self.win.layers_tableWidget.cellWidget(i, 0)	
			if b.text() == "On":
				visible_layers.append(self.win.layers_tableWidget.item(i, 1).text())

		debugEnd(traceback.extract_stack()[-1][2])	
		return visible_layers

	def objects_list(self):
		debugStart(traceback.extract_stack()[-1][2])

		global pkr_objectsWin
		try:
			pkr_objectsWin.close()
		except: pass


		pkr_objectsWin = ObjectsList(self)
		pkr_objectsWin.picker_item = self.picker_item
		pkr_objectsWin.fillList()
		pkr_objectsWin.win.setWindowTitle("Objects List (%s)" %self.picker_item.name)

	def autoLoadPickersOnStart(self):
		with open(root_path+'/config.json', mode='r') as f:
			configData = json.load(f)		

		configData["autoLoadPickersOnStart"] = self.win.autoLoadPickersOnStart_btn.isChecked()

		json_string = json.dumps(configData, indent=4)
		with open(root_path+'/config.json', 'w') as f:
			f.write(json_string)			

	def zoomReset(self):
		self.view.setMatrix(QtGui.QMatrix(1,0,0,1,0,0))
		cmds.optionVar( floatValue = ( "rsPicker_viewSize_%s" %self.view.tab_name, 1 ) )
		cmds.optionVar( floatValue = ( "rsPicker_viewPosX_%s" %self.view.tab_name, 0 ) )
		cmds.optionVar( floatValue = ( "rsPicker_viewPosY_%s" %self.view.tab_name, 0 ) )

	def action_about(self):
		debugStart(traceback.extract_stack()[-1][2])

		def aboutClose():
			self.aboutWin.close()

		#if os.path.exists(root_path+'//aboutWindow.ui'):
			#path = root_path+'//aboutWindow.ui'
		#else:
			#path = root_path.replace('\\picker', "\\ui")+'//aboutWindow.ui'
		path = root_path.replace('\\picker', "\\ui")+'//helpWindow.ui'

		self.aboutWin = self.loadUiWidget(path, parent=self.win)
		self.aboutWin.pushButton.clicked.connect(aboutClose)

		# get version
		with open(root_path.replace('\\picker', "/versions.txt")) as f:
			lines = f.readlines()

		versions = []
		for l in lines:
			if '---' in l:
				versions.append(l)

		lastVestion = versions[-1].split('---')[1]

		if not full:
			lastVestion += "(animation version)"

		# write version to ui
		self.aboutWin.label_5.setText(lastVestion)
		self.aboutWin.label_5.setText("")
		self.aboutWin.label.setVisible(False)

		# logo
		#if os.path.exists(root_path.replace('\\picker', "\\ui")+'/icons/rs_logo_about.png'):
			#imagemap = QtGui.QPixmap(root_path.replace('\\picker', "\\ui")+'/icons/rs_logo_about.png')
		#else:
			#imagemap = QtGui.QPixmap(root_path.replace('\\picker', "\\icons")+'/rs_logo_about.png')
		imagemap = QtGui.QPixmap(root_path.replace('\\picker', "\\ui")+'/help.png')
		self.aboutWin.logo_label.setPixmap(imagemap)	

		self.aboutWin.show()	

	def set_slider_object(self, i):
		sel = cmds.ls(sl=1)
		if len(sel) != 1:
			cmds.warning("Select one attribute of the object")
			return

		channelBox = pm.mel.eval('global string $gChannelBoxName; $temp=$gChannelBoxName;')
		attrs = cmds.channelBox(channelBox, q=True, sma=True)
		if not attrs:
			cmds.warning("Select one attribute of the object")
			return		

		self.picker_item.slider_objects[i] = sel[0] + "." + attrs[0]

		self.updateItemFrame()

	def clear_slider_objects(self):
		self.picker_item.slider_objects = {1:None, 2:None, 3:None, 4:None, 5:None}
		self.updateItemFrame()


def run_dockable_old(edit=False, picker_name=None, match_rig=False, match_scene=False):
	from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
	global picker_win

	if not 'picker_win' in globals():
		picker_win = None	

	class DockableWidget(MayaQWidgetDockableMixin, Main):
		def __init__(self, parent=None, edit=True, picker_name=None, match_rig=False, match_scene=False):
			super(DockableWidget, self).__init__(parent=parent, _edit=edit, picker_name=picker_name, match_rig=match_rig, match_scene=match_scene)
			self.setObjectName('picker_win')

			#self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum )
			#self.setMaximumSize(200, 200)
			self.resize(200, 200)	

		def keyPressEvent(self, event):
			pass

	try:
		picker_win.close()
		picker_win.deleteLater()
		if cmds.workspaceControl('picker_winWorkspaceControl', q=True, exists=True):
			cmds.workspaceControl('picker_winWorkspaceControl',e=True, close=True)
			cmds.deleteUI('picker_winWorkspaceControl',control=True)
	except: pass		

	#picker_win = MainWindow(_edit=edit)  
	#picker_win.show()

	picker_win = DockableWidget(edit=edit, picker_name=picker_name, match_rig=match_rig, match_scene=match_scene)  
	picker_win.show(dockable=True)

def run_old(edit=False):
	global picker_win

	if not 'picker_win' in globals():
		picker_win = None	

	try:
		picker_win.close()
		picker_win.deleteLater()
		if cmds.workspaceControl('picker_winWorkspaceControl', q=True, exists=True):
			cmds.workspaceControl('picker_winWorkspaceControl',e=True, close=True)
			cmds.deleteUI('picker_winWorkspaceControl',control=True)
	except: pass		

	picker_win = MainWindow(_edit=edit)  
	#picker_win = MyDockingUI(getMayaWindow())  

	# set on top
	#picker_win.setWindowFlags(picker_win.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

	picker_win.show()

def run(edit=False, rigFromJoints=None):
	global picker_win

	try:
		picker_win.remove_events()
	except: pass

	# if animation mode - dock windown, if edit mode - floating window
	if edit:
		try:
			cmds.deleteUI('RS Picker')
		except:
			pass
		picker_win = MyDockingUI(getMayaWindow())  
	else:
		picker_win = dock_window(MyDockingUI, edit, rigFromJoints)

	return
	# restore geometry
	x = configData["window_positon_x"]
	y = configData["window_positon_y"]
	w = configData["window_width"]
	h = configData["window_height"]

	wd = picker_win.parent().parent().parent().parent().parent()
	wd.adjustSize()
	wd.setGeometry(x,y,w,h)

