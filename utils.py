import maya.cmds as cmds


def incrementName(name):
	suffix = name.split('_')[-1]
	rootName = name[:-len(suffix)-1]
	if suffix.isdigit():
		name = rootName + '_' + str( int(suffix) + 1 )
	else:
		name += '_1'
	return name

def setUserAttr(obj, attrName, value, type="string", lock=True, keyable=False, cb=False, enumList=""):
	#print obj, attrName
	# create attribute if not exists
	if not cmds.attributeQuery(attrName, n=obj, exists=True ):

		if type == "string":
			cmds.addAttr(obj, longName=attrName, dt=type, keyable=keyable)

		elif type == "bool":
			cmds.addAttr(obj, longName=attrName, at=type, keyable=keyable)

		elif type == "int":
			cmds.addAttr(obj, longName=attrName, at='short', keyable=keyable)

		elif type == "float":
			cmds.addAttr(obj, longName=attrName, at='float', keyable=keyable)

		elif type == "data":
			pyToAttr(obj+'.'+attrName, value)

		elif type == "enum":
			cmds.addAttr(obj, longName=attrName, at='enum', en=enumList, keyable=keyable)

	# set attribute value
	cmds.setAttr(obj+"."+attrName, e=1, l=0)

	if type == "string":
		cmds.setAttr(obj+"."+attrName, value, type="string")
	elif type == "bool":
		cmds.setAttr(obj+"."+attrName, value)
	elif type == "int":
		cmds.setAttr(obj+"."+attrName, value)
	elif type == "float":
		cmds.setAttr(obj+"."+attrName, value)
	elif type == "enum":
		cmds.setAttr(obj+"."+attrName, value)
	elif type == "data":
		pyToAttr(obj+'.'+attrName, value)		

	cmds.setAttr(obj+"."+attrName, e=1, l=lock )
	if not keyable: cmds.setAttr(obj+"."+attrName, e=1, cb=cb )

def getOpposite(obj):
	side = obj.split('_')[0]
	if side == "r":
		return "l" + obj[1:]
	elif side == "l":
		return "r" + obj[1:]
	else:
		return None	
	
def addWorldSpaceAttr(control=None):
	if control:
		sel = [control]
	else:
		sel = cmds.ls(sl=True)
		if len(sel) == 0:
			cmds.warning("Select control")
			return

	for c in sel:
		opp_c = getOpposite(c)
		if opp_c:
			setUserAttr(opp_c, "worldSpace", 1, type="bool", lock=False, keyable=False, cb=False)
		setUserAttr(c, "worldSpace", 1, type="bool", lock=False, keyable=False, cb=False)
		
def addMirrorLoc(sel=None):
	if cmds.objExists("mirror_loc"):
		cmds.warning("Mirror loc already exists")
		return

	if not sel:
		sel = cmds.ls(sl=True)
		if len(sel) != 2:
			cmds.warning("Select the root and the pelvis controls")
			return
	
	root, pelvis = sel
	
	l = cmds.spaceLocator(n="mirror_loc")[0]
	cmds.setAttr(l+".rotateOrder", 1)
	cmds.parent(l, root)
	cmds.setAttr(l+".t", 0,0,0)
	cmds.setAttr(l+".r", 0,0,0)
	cmds.setAttr(l+".s", 1,1,1)
	cmds.hide(l)
	cmds.pointConstraint(pelvis, l, mo=0, skip="y")
	cmds.orientConstraint(pelvis, l, mo=0, skip=["x", "z"])

def addMirrorAxisAttr(control=None, axis=None):
	if control:
		sel = [control]
	else:
		sel = cmds.ls(sl=True)
		if len(sel) == 0:
			cmds.warning("Select control")
			return
	
	for c in sel:
		opp_c = getOpposite(c)
		if opp_c:
			setUserAttr(opp_c, "mirrorAxis", 0, type="enum", enumList="none:x:y:z:", lock=False, keyable=False, cb=False)

		setUserAttr(c, "mirrorAxis", 0, type="enum", enumList="none:x:y:z:", lock=False, keyable=False, cb=False)
		if axis:
			cmds.setAttr(c+".mirrorAxis", axis)
			if opp_c:
				cmds.setAttr(opp_c+".mirrorAxis", axis)

def getModuleNameFromHierarhy(controlName):
	p = cmds.listRelatives(controlName, parent=1)[0]
	while p.split('_')[-1] != "mod":
		parents = cmds.listRelatives(p, parent=1) or []
		if len(parents) == 0:
			return None
		p = parents[0]

	return p[:-4]