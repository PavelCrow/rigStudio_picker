import types
import maya.cmds as cmds
import maya.mel as mel

def getSetObjects(set):
	objects = []
	if not cmds.objExists(set):
		return []
	if type(cmds.sets(set, q=1)) is types.NoneType:
		return []
	for o in cmds.sets(set, q=1):
		if cmds.objectType(o) == 'objectSet':
			innerObjects = getSetObjects(o)
			objects += innerObjects
		else:
			objects.append(o)
	return objects

def getVisibleAttrs(ctrl):
	attrList = []
	attrListKeyable = cmds.listAttr( ctrl, keyable=True )
	if type(attrListKeyable) != list :
		attrListKeyable = []
	attrListNonkeyable = cmds.listAttr( ctrl, channelBox = True )
	if type(attrListNonkeyable) != list :
		attrListNonkeyable = []
	attrList = attrListKeyable + attrListNonkeyable
	
	out_list = []
	for a in attrList:
		if a not in ["translate", "rotate", "scale"]:
			out_list.append(a)
	
	return out_list

def savePos(): 
	allControls = cmds.ls(selection=True)
	
	if len(allControls) == 0:
		cmds.warning("Select controls")
		return

	for ctrl in allControls:
		for attr in getVisibleAttrs(ctrl):
			# if locked, continue
			#if cmds.getAttr(ctrl+"."+attr, lock=1):
				#continue
			
			value = cmds.getAttr(ctrl + "." + attr)
			
			# Set default value for custom aatr's
			#cmds.addAttr( ctrl, longName='default_'+attr, at='float', keyable=False)
			#cmds.setAttr( ctrl+".default_"+attr, value)
			if not cmds.attributeQuery('default_'+attr, node=ctrl, exists=True):
				cmds.addAttr( ctrl, longName='default_'+attr, dataType='string', keyable=False)
			cmds.setAttr( ctrl+".default_"+attr, str(value), type="string")			

def loadPos():
	# Get selected objects
	selectedObjs = cmds.ls(sl=True)
	if len(selectedObjs) == 0:
		cmds.warning("Select controls")
		return

	for ctrl in selectedObjs:
		attrs = getVisibleAttrs(ctrl)
		
		for attr in attrs:
			# if default attr is exists
			if cmds.attributeQuery('default_'+attr, node=ctrl, exists=True):
				# get saved value
				value = cmds.getAttr(ctrl + ".default_" + attr)
				
				# convert attr type
				if value == "True":
					value = True
				elif value == "False":
					value = False
				else:
					value = float(value)
				
				# If not locked, set value
				if not cmds.getAttr(ctrl+"."+attr, lock=1):
					cmds.setAttr( ctrl+'.'+attr, value )
			else:
				value = cmds.attributeQuery(attr, node=ctrl, listDefault=True)[0]
				if not cmds.getAttr(ctrl+"."+attr, lock=1):
					cmds.setAttr( ctrl+'.'+attr, value )

		
		
		

#######################################################
### Copy Paste Pos
#######################################################

attrData = {}

def copyPos():
	global attrData

	# Save controls attr's
	controls = cmds.ls(selection=True)

	if len(controls) > 0:
		cmds.select (clear=True)

		attrData = {}

		for ctrl in controls:
			ctrlName = ctrl.split(":")[-1]
			cmds.select (ctrl)
			attrList = []
			attrListKeyable = cmds.listAttr( keyable=True )
			if type(attrListKeyable) != list :
				attrListKeyable = []
			attrListNonkeyable = cmds.listAttr( channelBox = True )
			if type(attrListNonkeyable) != list :
				attrListNonkeyable = []
			attrList = attrListKeyable + attrListNonkeyable

			for attr in attrList:
				attrVar = cmds.getAttr(ctrl + "." + attr)
				attrData[(ctrlName + "." + attr)] = attrVar

		cmds.select (controls)


def pastePos():
	global attrData

	char = mel.eval( 'selectorCurrentCharacter' )

	selectedObjs = cmds.ls(sl=True)
	# Paste selected objects
	for obj in selectedObjs:
		for attr in attrData:
			if (obj == (char+attr).split(".")[0] ):
				try:
					cmds.setAttr( char + attr, attrData[attr] )
				except:
					pass