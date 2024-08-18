import os, sys, json, logging, traceback
from maya import cmds

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

root_path = os.path.dirname(os.path.abspath(__file__))
rootDebug = ""

if sys.version[0] == "2":
	import cPickle
else:
	import pickle as cPickle

with open(root_path+'/config.json', mode='r') as f:
	configData = json.load(f)

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


def pyToAttr(objAttr, data):
	"""
	Write (pickle) Python data to the given Maya obj.attr.  This data can
	later be read back (unpickled) via attrToPy().

	Arguments:
	objAttr : string : a valid object.attribute name in the scene.  If the
		object exists, but the attribute doesn't, the attribute will be added.
		The if the attribute already exists, it must be of type 'string', so
		the Python data can be written to it.
	data : some Python data :  Data that will be pickled to the attribute
		in question.
	"""
	obj, attr = objAttr.split('.')
	# Add the attr if it doesn't exist:
	if not cmds.objExists(objAttr):
		cmds.addAttr(obj, longName=attr, dataType='string')
	# Make sure it is the correct type before modifing:
	if cmds.getAttr(objAttr, type=True) != 'string':
		raise Exception("Object '%s' already has an attribute called '%s', but it isn't type 'string'"%(obj,attr))

	# Pickle the data and return the coresponding string value:
	#stringData = cPickle.dumps(data)
	stringData = cPickle.dumps(data, 0).decode()
	# Make sure attr is unlocked before edit:
	cmds.setAttr(objAttr, edit=True, lock=False)
	# Set attr to string value:
	cmds.setAttr(objAttr, stringData, type='string')
	# And lock it for safety:
	cmds.setAttr(objAttr, edit=True, lock=True)

def attrToPy(objAttr):
		"""
		Take previously stored (pickled) data on a Maya attribute (put there via
		pyToAttr() ) and read it back (unpickle) to valid Python values.

		Arguments:
		objAttr : string : A valid object.attribute name in the scene.  And of course,
			it must have already had valid Python data pickled to it.

		Return : some Python data :  The reconstituted, unpickled Python data.
		"""
		# Get the string representation of the pickled data.  Maya attrs return
		# unicode vals, and cPickle wants string, so we convert:
		stringAttrData = str(cmds.getAttr(objAttr))
		# Un-pickle the string data:
		#loadedData = cPickle.loads(stringAttrData)
		loadedData = cPickle.loads(stringAttrData.encode())

		return loadedData

def setUserAttr(obj, attrName, value, type_="string", lock=True, keyable=False, cb=False, enumList=""):
	# create attribute if not exists
	if not cmds.attributeQuery(attrName, n=obj, exists=True ):
		if type(value) in [str]:
			cmds.addAttr(obj, longName=attrName, dt="string", keyable=keyable)
		elif type(value) == bool:
			cmds.addAttr(obj, longName=attrName, at="bool", keyable=keyable)
		elif type(value) is int:
			cmds.addAttr(obj, longName=attrName, at='short', keyable=keyable)
		elif type(value) is float:
			cmds.addAttr(obj, longName=attrName, at='float', keyable=keyable)
		elif type(value) in [list, set, tuple]:
			pyToAttr(obj+'.'+attrName, value)
		#elif type(value) is list:
			#cmds.addAttr(obj, longName=attrName, at='enum', en=enumList, keyable=keyable)

	# set attribute value
	cmds.setAttr(obj+"."+attrName, e=1, l=0)

	if type(value) in [str]:
		cmds.setAttr(obj+"."+attrName, value, type="string")
	elif type(value) == bool:
		cmds.setAttr(obj+"."+attrName, value)
	elif type(value) == int:
		cmds.setAttr(obj+"."+attrName, value)
	elif type(value) == float:
		cmds.setAttr(obj+"."+attrName, value)
	elif type(value) in [list, set, tuple]:
		pyToAttr(obj+'.'+attrName, value)
	#elif type(value) is list:
		#cmds.setAttr(obj+"."+attrName, value)

	cmds.setAttr(obj+"."+attrName, e=1, l=lock, cb=cb )

class Picker():

	def __init__(self, name=None, useNode=True):
		debugStart(traceback.extract_stack()[-1][2])
		
		self.name = name
		self.useNode = useNode
		self.data = {}
		
		debugEnd(traceback.extract_stack()[-1][2])	

	def create(self, data=None):
		debugStart(traceback.extract_stack()[-1][2])
		
		# Abort if node already exists
		#if cmds.objExists(self.name):
			#sys.stderr.write("node %s already exists." %self.name)
			#return self.name
		
		if data:
			self.data = data
		
		else:
			# Create data node (render sphere for outliner "icon")
			node = cmds.createNode("network", n=self.name+"_pkrData")
	
			# Tag data node
			setUserAttr(node, "type", "rs_pickerNode")
	
			self.data = self.createData()
		
		self.save()
		
		debugEnd(traceback.extract_stack()[-1][2])	

	def createData(self):
		data = {}
		
		layer_data = self.createLayerData("default")
		tab_data = self.createTabData()
		
		data["layers"] = [layer_data]
		data["current_layer"] = 0
		data["tabs"] = [tab_data]
		data["autorun_script"] = None
		data["moveLock"] = False
		data["autorun"] = True
		data["tabBar_visibility"] = True
		
		return data

	def createTabData(self):
		tab_data = {}
		tab_data["index"] = 0
		tab_data["name"] = "default"
		tab_data["background"] = None
		tab_data["background_offset_x"] = 0
		tab_data["background_offset_y"] = 0
		tab_data["background_opacity"] = 1
		tab_data["background_flip"] = False
		tab_data["tab_visibility"] = True
		tab_data["items"] = []		
		
		return tab_data
	
	def createLayerData(self, name):
		layer_data = {}
		layer_data["index"] = 0
		layer_data["name"] = name
		layer_data["visibility"] = True
		layer_data["path"] = None
		layer_data["locked"] = False		

		return layer_data
	
	def rename(self, new_name):
		debugStart(traceback.extract_stack()[-1][2])
		
		# save data
		data = self.data.copy()
		
		# delete old
		if self.useNode:
			cmds.delete(self.name+"_pkrData")
		else:
			os.remove(root_path+'/pickers/%s.json' %self.name)	
		
		# create new
		self.name = new_name
		self.create()
		
		# load data
		self.data = data
		
		# set data
		self.save()
		
		debugEnd(traceback.extract_stack()[-1][2])	
		
	def load(self, name=None, path=None):
		debugStart(traceback.extract_stack()[-1][2])
		
		self.data = {}
		
		if path:
			with open(path, mode='r') as f:
				self.data = json.load(f)	
				#for d in self.data:
					#print d, self.data[d]		
					
			debugEnd(traceback.extract_stack()[-1][2])	
			return
		
		if not name:
			name = self.name
			if not name:
				name = "picker"
		if self.useNode:
			# print (88, name+"_pkrData.data")
			self.data = attrToPy(name+"_pkrData.data")
		else:
			p = os.path.join(root_path.replace('picker', 'matchRig'), name+".json")
			if os.path.exists(root_path+'/pickers/%s.json' %name):
				with open(root_path+'/pickers/%s.json' %name, mode='r') as f:
					self.data = json.load(f)				
			elif os.path.exists(p):
				with open(p, mode='r') as f:
					self.data = json.load(f)
					

		#for i in self.data['tabs'][0]['items']:
			#print i
		debugEnd(traceback.extract_stack()[-1][2])	
				
	def merge(self, name=None, path=None):
		debugStart(traceback.extract_stack()[-1][2])
		
		#self.data = {}
		data = {}
		
		if path:
			with open(path, mode='r') as f:
				data = json.load(f)	
				for d in data:
					print (d, data[d])
		for i in data["tabs"][0]["items"]:
			self.data["tabs"][0]["items"].append(i)
			
		self.save()

	def load_controls_data(self, name=None, path=None):
		debugStart(traceback.extract_stack()[-1][2])
		
		if not name:
			name = self.name
		
		if path:
			with open(path, mode='r') as f:
				data = json.load(f)	
		else:
			with open(root_path+'/pickers/%s.json' %name, mode='r') as f:
				data = json.load(f)	
				
		# reset controls
		for i, t_data in enumerate(self.data["tabs"]):
			if t_data["items"]:
				for item_data in t_data["items"]:
					if "controls" in item_data:
						item_data['controls'] = []
					
		# set controls	
		for i, t_data in enumerate(data["tabs"]):
			#print t_data["name"], "-----------------------------------------"
			if t_data["items"]:
				for item_data in t_data["items"]:
					if "controls" in item_data:
						#print item_data["name"], item_data["controls"]	
						for d in self.data['tabs']:
							for item in d['items']:
								if item['name'] == item_data["name"]:
									item['controls'] = item_data["controls"]	
		
		self.save()
		#for d in self.data['tabs']:
			#for item in d['items']:
				#print item['name'], "controls" in item
				#if item['name'] == item_data["name"]:
					#item['controls'] = item_data["controls"]		
					
		debugEnd(traceback.extract_stack()[-1][2])	

	def save(self, file_path=None):
		debugStart(traceback.extract_stack()[-1][2])
		
		#if not file_path:
			#file_path = root_path+'/pickers/%s.json' %self.name
		
		#if self.name.split("_")[0] == 'mr':
			#file_path = root_path.replace("picker", "matchRig")+'/pickers/%s.json' %self.name
		
		#if self.useNode:
		if not cmds.objExists(self.name+"_pkrData"):
			node = cmds.createNode("network", n=self.name+"_pkrData")
			setUserAttr(node, "type", "rs_pickerNode")				
		pyToAttr(self.name+"_pkrData.data", self.data)
		#else:
			#json_string = json.dumps(self.data, indent=4)

			#with open(file_path, 'w') as f:
				#f.write(json_string)
				
		debugEnd(traceback.extract_stack()[-1][2])	

	def exportToFile(self, file_path):
		debugStart(traceback.extract_stack()[-1][2])
		
		if not file_path:
			return
		
		json_string = json.dumps(self.data, indent=4)
		with open(file_path, 'w') as f:
			f.write(json_string)			
			
		debugEnd(traceback.extract_stack()[-1][2])	

	def exportSelectedToFile(self, file_path, items_data):
		json_string = json.dumps(items_data, indent=4)
		with open(file_path, 'w') as f:
			f.write(json_string)

			print(file_path)

	def importItems(self, path, tab_name):
		with open(path, mode='r') as f:
			new_items_data = json.load(f)	
		
		for tabs_data in self.data["tabs"]:
			if tabs_data["name"] == tab_name:
				current_items_data = tabs_data["items"]
				current_items_data += new_items_data

	def setData(self, data_name, value):
		debugStart(traceback.extract_stack()[-1][2])
		
		self.data[data_name] = value

		debugEnd(traceback.extract_stack()[-1][2])	