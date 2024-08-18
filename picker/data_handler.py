import os, sys, json
from maya import cmds

if sys.version[0] == "2":
	import cPickle
else:
	import pickle as cPickle
	
root_path = os.path.dirname(os.path.abspath(__file__))

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
	loadedData = cPickle.loads(stringAttrData)
	loadedData = cPickle.loads(stringAttrData.encode())

	return loadedData

def setUserAttr(obj, attrName, value, type_="string", lock=True, keyable=False, cb=False, enumList=""):
	# create attribute if not exists
	if not cmds.attributeQuery(attrName, n=obj, exists=True ):
		if type(value) in [unicode, str]:
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

	if type(value) in [unicode, str]:
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
		self.name = name
		self.useNode = useNode
		self.data = {}

	def create(self, data=None):
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
	
			layer_data = self.createLayerData()
			tab_data = self.createTabData()
			self.data["layers"] = [layer_data]
			self.data["tabs"] = [tab_data]
			self.data["autorun_script"] = None
			self.data["moveLock"] = False
			self.data["autorun"] = True
			self.data["useNode"] = self.useNode
			self.data["tabBar_visibility"] = True
		
		self.save()

	def createLayerData(self):
		layer_data = {}
		layer_data["name"] = "default"
		layer_data["visibility"] = True
		layer_data["items"] = []
		
		return layer_data

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

	def rename(self, new_name):
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
		
	def load(self, name=None, path=None):
		self.data = {}
		
		if path:
			with open(path, mode='r') as f:
				self.data = json.load(f)	
				return
		if not name:
			name = self.name
			if not name:
				name = "picker"
		if self.useNode:
			self.data = attrToPy(name+"_pkrData.data")
		else:
			p = os.path.join(root_path.replace('picker', 'matchRig'), name+".json")
			if os.path.exists(root_path+'/pickers/%s.json' %name):
				with open(root_path+'/pickers/%s.json' %name, mode='r') as f:
					self.data = json.load(f)				
			elif os.path.exists(p):
				with open(p, mode='r') as f:
					self.data = json.load(f)
					
		#print 112233
		#for d in self.data:
			#print d, self.data[d]
		#for i in self.data['tabs'][0]['items']:
			#print i
		
		
		
	def load_controls_data(self, name=None, path=None):
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

	def save(self, file_path=None):
		if not file_path:
			file_path = root_path+'/pickers/%s.json' %self.name
		
		if self.name.split("_")[0] == 'mr':
			file_path = root_path.replace("picker", "matchRig")+'/pickers/%s.json' %self.name
		
		if self.useNode:
			if not cmds.objExists(self.name+"_pkrData"):
				node = cmds.createNode("network", n=self.name+"_pkrData")
				setUserAttr(node, "type", "rs_pickerNode")				
			pyToAttr(self.name+"_pkrData.data", self.data)

		else:
			json_string = json.dumps(self.data, indent=4)
			with open(file_path, 'w') as f:
				f.write(json_string)	

	def exportToFile(self, file_path):
		json_string = json.dumps(self.data, indent=4)
		with open(file_path, 'w') as f:
			f.write(json_string)					

	def setData(self, data_name, value):
		self.data[data_name] = value

	# =========================================================================

	'''
	# Maya attributes
	def _get_attr(self, attr):
		#Return node's attribute value

		self._assert_exists()
		if not cmds.attributeQuery(attr, n=self.name, ex=True):
			return
		return cmds.getAttr("{}.{}".format(self.name, attr)) or None

	def _add_str_attr(self, node, ln):
		#Add string attribute to data node

		self._assert_exists()

		cmds.addAttr(node, ln=ln, dt="string")
		cmds.setAttr("{}.{}".format(node, ln), k=False, l=False, type="string")

	def _set_str_attr(self, attr, value=None):
		#Set string attribute value

		# Sanity check
		self._assert_exists()
		self._assert_not_referenced()

		# Init value
		if not value:
			value = ''

		# Unlock attribute
		cmds.setAttr("{}.{}".format(self.name, attr), l=False, type="string")

		# Set value and re-lock attr
		cmds.setAttr("{}.{}".format(self.name, attr),
				     value,
				     l=True,
				     type="string")

	def get_namespace(self):
		#Return namespace for current node

		if not self.name.count(":"):
			return None
		return self.name.rsplit(":", 1)[0]

	# ==========================================================================
	# Set attributes
	def write_data(self, data=None, to_node=True, to_file=False, file_path=None):
		#Write data to data node and data file

		if not data:
			data = self.data

		# Write data to file
		if to_file:
			file_handlers.write_data_file(file_path=file_path,
						                  data=data)
			self._set_str_attr(self.__FILE_ATTR__, value=file_path)

		# Write data to node attribute
		if to_node:
			self._set_str_attr(self.__DATAS_ATTR__, value=data)

	def read_data_from_node(self):
		#Read data from data node or data file

		# Init data dict
		data = {}

		return data

	def read_data_from_file(self):
		#Read data from specified file

		file_path = root_path + "/" + self.name + ".json"
		if not os.path.exists(file_path):
			return None

		return

	def read_data(self, from_file=True):
		#Read picker data

		# Init data dict
		data = {}

		# Read data from file
		if from_file:
			data = self.read_data_from_file()

		# Read data from node
		if not data:
			data = self.read_data_from_node()

		self.data = data
		return data

'''