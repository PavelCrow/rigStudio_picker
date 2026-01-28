# Switch Ik Fk of the arms and legs with store position for Rig Studio characters
#
# select control of the arm or leg and run:
# import rs_switchIkFk
# reload(rs_switchIkFk)
# rs_switchIkFk.switchIkFk()
#
# Pavel Korolyov
# pavel.crow@gmail.com

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.mel as mel
import maya.api.OpenMaya as OpenMaya
from functools import partial
import math, sys

mirrorAttrLis = ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ"]

m_type = ""
m_name = ""
control = ""
footM_name = ""
ns = ""

##################################
# functions
##################################

def getModuleName(obj): #
	if obj == None or obj == "" or not cmds.objExists(obj):
		return None	
	j = obj.replace("skinJoint", "outJoint")
	# j = obj.replace("joint", "outJoint")

	path = cmds.ls(j, l=1) or []
	
	# moduleName = path[0].split("modules|")[-1].split("_mod|")[0].split("_mod")[0]
	moduleName = path[0].split("modules|")[-1].split("_mod|")[0].split("_mod")[0].split(":")[-1]
	# print(222, path, moduleName)
	return moduleName

def getInternalNameFromControl(controlName):
	if cmds.objExists(controlName+".internalName"):
		return cmds.getAttr(controlName+".internalName")
	else:
		return ""

def getControlNameFromInternal(module_name, internalControlName):
	# print ("---", module_name)
	ctrls = getSetObjects(module_name+'_moduleControlSet')
	# print ("---", module_name, internalControlName, ctrls)
	for c in ctrls:
		#print c
		#if c == 'l_footB_heelFk':
			#print c
		try:
			int_name = cmds.getAttr(c+".internalName")
			if int_name == internalControlName:
				return c
		except: pass
	#cmds.warning('Cannot find control with internal name '+internalControlName+' in moduleControlSet')
	return ""

def getSetObjects(set):
	objects = []
	# print ("!!!", set)
	if cmds.sets(set, q=1) == None:
		return []
	for o in cmds.sets(set, q=1):
		#print o
		if cmds.objectType(o) == 'objectSet':
			innerObjects = getSetObjects(o)
			objects += innerObjects
		else:
			objects.append(o)
	return objects

def resetAttrs(o):
	#attrs = mel.eval('listAttr -k %s' %o)
	#print o#, attrs
	if not cmds.objExists:
		return
	
	for a in cmds.listAttr(o, k=True):
		#print o,a
		try:
			cmds.setAttr(o+'.'+a, 0)
		except: pass

	for a in [".sx", ".sy", ".sz"]:
		try:
			cmds.setAttr(o+a, 1)
		except: pass

	try:
		for a in [".shearXY", ".shearXZ", ".shearYZ"]:
			try:
				cmds.setAttr(o+a, 0)
			except: pass		
	except: pass

def getNS(ctrl):
	if ':' in ctrl:
		ctrl_name = ctrl.split(':')[-1]
		ns_ = ctrl.split(ctrl_name)[0]
		return ns_
	else:
		return ""

def getInputNode(obj, attr):
	if cmds.connectionInfo( obj+"."+attr, isDestination=True):
		inputAttr = cmds.connectionInfo( obj+"."+attr, sourceFromDestination=True)	
		inputNode = inputAttr.split('.')[0]
		return inputNode
	return None

def getOutputNodes(obj, attr):
	"""Возвращает узел, подключенный К атрибуту obj.attr (destination)"""
	if cmds.connectionInfo(obj+"."+attr, isSource=True):
		outputAttrs = cmds.connectionInfo(obj+"."+attr, destinationFromSource=True)
		outputNodes = []
		for a in outputAttrs:
			outputNodes.append(a.split('.')[0])
		return outputNodes
	return None

def getParent(module_name):
	# get node connected to connector object by matrix
	conn = module_name+'_root_connector'
	
	try:
		decMat_node = getInputNode(conn, 'tx')
		multMat_node = getInputNode(decMat_node, 'inputMatrix')
		parent_ctrl = getInputNode(multMat_node, 'matrixIn[2]')
		return parent_ctrl

	except:
		return ""

def getConnectedFootModule(control):
	outputs = cmds.connectionInfo( control + ".ikFk", destinationFromSource=True)
	for attr in outputs:
		if attr.split('.')[-1] == 'ikFk':
			in_node = attr.split('.')[0]	
			child_m_name = getModuleName(in_node)
			ns = getNS(control)
			return ns + child_m_name
	
	return False


##################################
# Switch IKFK
##################################

def switchIkFk(simple=False):
	global m_name, m_type, control, ns, footM_name
	
	sels = cmds.ls(sl=True)
	
	# get ikFk controls
	controls = []
	for sel in sels:
		ns = getNS(sel)
		intName = getInternalNameFromControl(sel)
		m_name = ns + getModuleName(sel)
		# print (11111, sel, m_name)

		# get switch control
		mod = m_name + "_mod"
		if cmds.objExists(mod+".ikFk"):
			control = getInputNode(mod, "ikFk")
		else:
			control = getControlNameFromInternal(m_name, "control")
		
		if control == "":
			cmds.warning('Control with ikFk attribute is not found')
		else:
			if control not in controls:
				controls.append(control)

	# switch ikFk
	for c in controls:
		ikFk = cmds.getAttr(c + ".ikFk")	
		if ikFk < 0.5 :
			if simple:
				cmds.setAttr(c + ".ikFk", 1)	
			else:
				from_fk_to_ik(c)
		else :
			if simple:
				cmds.setAttr(c + ".ikFk", 0)	
			else:			
				from_ik_to_fk(c)

	if sels:
		cmds.select(sels)

def get_lengths(control):

	quad = cmds.objExists(control+".length3")
	lengths = []

	def get_element_scale(part):
		out_nodes = getOutputNodes(control, f"length{part}")
		for node in out_nodes:
			if cmds.objectType(node) == "multDoubleLinear":
				scale = cmds.getAttr(node + ".input1")
				return scale

	init_scale1 = get_element_scale(part=1)
	
	def get_local_length(j):
		vector = cmds.getAttr(j+".t")[0]
		x,y,z = vector
		length = math.sqrt(x**2 + y**2 + z**2)
		return length

	if cmds.objExists(m_name + "_b_finalJoint"):
		local_length_1 = get_local_length(m_name + "_b_finalJoint")
		length_1 = local_length_1 / init_scale1
		if length_1 < 0: length_1 *= -1
		
		init_scale2 = get_element_scale(part=2)
		if quad:
			local_length_2 = get_local_length(m_name + "_c_finalJoint")
		else:
			local_length_2 = get_local_length(m_name + "_end_finalJoint")
		length_2 = local_length_2 / init_scale2
		if length_2 < 0: length_2 *= -1

		lengths = [length_1, length_2]

		if quad:
			local_length_3 = get_element_scale(part=3)
			cur_scale3 = get_local_length(m_name + "_end_finalJoint")
			length_3 = cur_scale3 / local_length_3	
			if length_3 < 0: length_3 *= -1
			lengths.append(length_3)
	else:
		############### УСТАРЕВШИЙ КОД, для поддержки старых ригов ###############
		import pymel.core.datatypes as dt
		import pymel.core as pm
		p0 = pm.xform(m_name+'_root_outJoint', ws=1, q=1, t=1)        
		p1 = pm.xform(m_name+'_knee_outJoint', ws=1, q=1, t=1)
		v0 = dt.Vector(p0)
		v1 = dt.Vector(p1)
		v = v1 - v0
		l = v.length()
		scl = cmds.getAttr(m_name+"_root_connector_decomposeMatrix.outputScaleX")
		scl_converted = l/scl
		length_1 = scl_converted/init_scale1
		
		if not quad:
			p0 = pm.xform(m_name+'_b_finalJoint', ws=1, q=1, t=1)        
			p1 = pm.xform(m_name+'_end_outJoint', ws=1, q=1, t=1)
			v0 = dt.Vector(p0)
			v1 = dt.Vector(p1)
			v = v1 - v0
			l = v.length()
			scl_converted = l/scl
			init_scale2 = cmds.getAttr(m_name + "_initScaleEnd_mult.input1")
			length_3 = scl_converted/init_scale2
			print (444, length_1, length_3)
			
		else:
			p0 = pm.xform(m_name+'_knee_outJoint', ws=1, q=1, t=1)        
			p1 = pm.xform(m_name+'_ankle_outJoint', ws=1, q=1, t=1)
			v0 = dt.Vector(p0)
			v1 = dt.Vector(p1)
			v = v1 - v0
			l = v.length()
			scl_converted = l/scl
			init_scale2 = cmds.getAttr(m_name + "_initScale2_mult.input1")
			length_3 = scl_converted/init_scale2

			p0 = pm.xform(m_name+'_ankle_outJoint', ws=1, q=1, t=1)        
			p1 = pm.xform(m_name+'_end_outJoint', ws=1, q=1, t=1)
			v0 = dt.Vector(p0)
			v1 = dt.Vector(p1)
			v = v1 - v0
			l = v.length()
			scl_converted = l/scl
			init_scale2 = cmds.getAttr(m_name + "_initScaleEnd_mult.input1")
			length_2 = scl_converted/init_scale2
			print (44444, length_1, length_3, length_2 )
		##########################################################################
	
	return lengths

def from_fk_to_ik(control):
	print ("--- switch fk to ik ---")

	def snapIkElbow(sourceA, sourceB, sourceC, target):
		#print sourceA, sourceB, sourceC, target
		# Get pointPositions
		aPos = cmds.xform(sourceA, t=1, q=1, worldSpace=1)
		bPos = cmds.xform(sourceB, t=1, q=1, worldSpace=1)
		cPos = cmds.xform(sourceC, t=1, q=1, worldSpace=1)

		# Get point Vectors
		a = OpenMaya.MVector(aPos)
		b = OpenMaya.MVector(bPos)
		c = OpenMaya.MVector(cPos)

		# Get vectors
		ab = OpenMaya.MVector(b-a)
		ac = OpenMaya.MVector(c-a)

		# Get length of lower vector
		acLen = OpenMaya.MVector(ac).length()

		# Get projection upper vector on lower vector
		pr = ab*ac / acLen

		# Normalize result
		acNorm = OpenMaya.MVector(ac).normal()

		# Get new vector from start to middle point
		ce = acNorm * pr

		# Get position middle point
		e = ce + a

		# Get vector from middle to elbow point and normalize it
		eb = b - e
		ebNorm = OpenMaya.MVector(eb).normal()

		# Make vector as needed length and from b point and final Point elbow control
		if cmds.objExists(m_name+'_mod.aim_offset'):
			scale = cmds.getAttr(m_name+'_mainPoser_decomposeMatrix.outputScaleX')
			offset = cmds.getAttr(m_name+'_mod.aim_offset') * scale 
		else:
			offset = 0.5
		
		elbowV = ebNorm * offset + b
		#print ebNorm, offset , b
		# Move control
		cmds.xform(target, t=elbowV, worldSpace=1)

	ns = getNS(control)
	foot_m = getConnectedFootModule(control)
	
	m_name = ns + getModuleName(control)
	quad = cmds.objExists(control+".length3")

	if quad:
		length_1, length_2, length_3 = get_lengths(control)
	else:
		length_1, length_2 = get_lengths(control)

	if cmds.objExists(m_name + "_a_finalJoint"):
		joint_1 = m_name + '_a_finalJoint'
		if quad:
			joint_2 = m_name + '_b_finalJoint'
			joint_3 = m_name + '_c_finalJoint'	
		else:
			joint_2 = m_name + '_b_finalJoint'
		joint_last = m_name + '_end_finalJoint'
	else:
		joint_1 = m_name + '_root_outJoint'
		if quad:
			joint_2 = m_name + '_knee_outJoint'
			joint_3 = m_name + '_ankle_outJoint'	
		else:
			joint_2 = m_name + '_knee_outJoint'
		joint_last = m_name + '_end_outJoint'		

	root_ctrl = getControlNameFromInternal(m_name, "ik_root")
	end_ctrl = getControlNameFromInternal(m_name, "ik_end")
	aim_ctrl = getControlNameFromInternal(m_name, "ik_aim")
	ankle_ctrl = getControlNameFromInternal(m_name, "ik_ankle")

	# snappping
	snap( root_ctrl )
	if foot_m:
		heel_ctrl = getControlNameFromInternal(foot_m, "ik_heel") or None
		foot_ctrl = getControlNameFromInternal(foot_m, "ik_foot")
		toe_ctrl = getControlNameFromInternal(foot_m, "ik_toe")
		
		try:
			if heel_ctrl:
				for a in [".rx", ".ry", ".rz"]:
					cmds.setAttr(heel_ctrl+a, 0)
		except: pass

		# Bear fix
		try:
			cmds.setAttr(foot_ctrl+".hill", 0) 
			toeTip_ctrl = getControlNameFromInternal(foot_m, "toeTip")
			for a in [".rx", ".ry", ".rz"]:
				cmds.setAttr(toeTip_ctrl+a, 0)
		except: pass	
		
		snap( foot_ctrl )
		snap( toe_ctrl )	
	else:
		snap( end_ctrl )
	if quad:
		snapIkElbow(joint_1, joint_2, joint_3, aim_ctrl)
		snap( ankle_ctrl )
	else:
		snapIkElbow(joint_1, joint_2, joint_last, aim_ctrl)

	cmds.setAttr(control + ".ikFk", 1)
	
	cmds.setAttr(control + ".length1", length_1)
	if quad: 
		cmds.setAttr(control + ".length2", length_2)
		cmds.setAttr(control + ".length3", length_3)
	else:
		cmds.setAttr(control + ".length2", length_2)

	

def from_ik_to_fk(control):
	print ("--- switch ik to fk ---22")
	
	# get variables
	ns = getNS(control)
	m_name = ns + getModuleName(control)
	foot_m = getConnectedFootModule(control)
	quad = cmds.objExists(control+".length3")

	if cmds.objExists(m_name + "_b_finalJoint"):
		if quad:
			length_1, length_2, length_3 = get_lengths(control)
		else:
			length_1, length_2 = get_lengths(control)
	else:
		############### УСТАРЕВШИЙ КОД, для поддержки старых ригов ###############
		import pymel.core.datatypes as dt
		import pymel.core as pm

		def get_element_scale(part):
			out_nodes = getOutputNodes(control, f"length{part}")
			for node in out_nodes:
				if cmds.objectType(node) == "multDoubleLinear":
					scale = cmds.getAttr(node + ".input1")
					return scale
		

		init_scale1 = get_element_scale(part=1)
				
		p0 = pm.xform(m_name+'_root_outJoint', ws=1, q=1, t=1)        
		p1 = pm.xform(m_name+'_knee_outJoint', ws=1, q=1, t=1)
		v0 = dt.Vector(p0)
		v1 = dt.Vector(p1)
		v = v1 - v0
		l = v.length()
		scl = cmds.getAttr(m_name+"_root_connector_decomposeMatrix.outputScaleX")
		scl_converted = l/scl
		length_1 = scl_converted/init_scale1
		
		if not quad:
			p0 = pm.xform(m_name+'_b_finalJoint', ws=1, q=1, t=1)        
			p1 = pm.xform(m_name+'_end_outJoint', ws=1, q=1, t=1)
			v0 = dt.Vector(p0)
			v1 = dt.Vector(p1)
			v = v1 - v0
			l = v.length()
			scl_converted = l/scl
			init_scale2 = cmds.getAttr(m_name + "_initScaleEnd_mult.input1")
			length_3 = scl_converted/init_scale2
			print (444, length_1, length_3)
			
		else:
			p0 = pm.xform(m_name+'_knee_outJoint', ws=1, q=1, t=1)        
			p1 = pm.xform(m_name+'_ankle_outJoint', ws=1, q=1, t=1)
			v0 = dt.Vector(p0)
			v1 = dt.Vector(p1)
			v = v1 - v0
			l = v.length()
			scl_converted = l/scl
			init_scale2 = cmds.getAttr(m_name + "_initScale2_mult.input1")
			length_3 = scl_converted/init_scale2

			p0 = pm.xform(m_name+'_ankle_outJoint', ws=1, q=1, t=1)        
			p1 = pm.xform(m_name+'_end_outJoint', ws=1, q=1, t=1)
			v0 = dt.Vector(p0)
			v1 = dt.Vector(p1)
			v = v1 - v0
			l = v.length()
			scl_converted = l/scl
			init_scale2 = cmds.getAttr(m_name + "_initScaleEnd_mult.input1")
			length_2 = scl_converted/init_scale2
			print (44444, length_1, length_3, length_2 )
		##########################################################################

	# snapping fk controls
	snap( getControlNameFromInternal(m_name, "fk_a") )
	snap( getControlNameFromInternal(m_name, "fk_b") )		
	
	if quad: 
		snap( getControlNameFromInternal(m_name, "fk_c") )
	if foot_m: 
		snap(getControlNameFromInternal(foot_m, "fk_heel") )
		snap(getControlNameFromInternal(foot_m, "fk_toe") )
	else:
		snap( getControlNameFromInternal(m_name, "fk_end") )
	
	cmds.setAttr(control + ".length1", length_1)
	if quad: 
		cmds.setAttr(control + ".length2", length_2)
		cmds.setAttr(control + ".length3", length_3)
	else:
		cmds.setAttr(control + ".length2", length_2)

	cmds.setAttr(control + ".ikFk", 0)

def snap(target, rev=True):
	# get helper
	ns = getNS(target)
	m_name = ns + getModuleName(target)
	
	source = m_name + "_" + getInternalNameFromControl(target) + "_ikFkSwitchHelper"

	if not cmds.objExists(source) or not cmds.objExists(target):
		print ("snap Miss source", source, " target", target)
		return

	print ("snap from", source, 'to', target )

	targetParent = cmds.listRelatives( target, parent=True )

	# get rotate order of the target
	rotOrderTarget = cmds.getAttr('%s.rotateOrder'%target)

	# get matrix of the source
	matrixList = cmds.getAttr('%s.worldMatrix'%source)
	mMatrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(matrixList, mMatrix)

	# get target parent inverse matrix
	parent_floatList = cmds.xform(targetParent,q=True,matrix=1, worldSpace=1)
	parent_matrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(parent_floatList,parent_matrix )
	invMatrixParent = parent_matrix.inverse()

	#targetWorldParent = cmds.objExists(target+".parent")
	#if not targetWorldParent and source.split('_')[0] == 'r':
		#scl = -1 
	#else:
		#scl = 1 
	#vector_floatList = [scl, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
	#vector_matrix = om.MMatrix()
	#om.MScriptUtil.createMatrixFromList(vector_floatList,vector_matrix )	

	# solve final matrix
	final_matrix = mMatrix * invMatrixParent

	# get rotation
	mTransformMtx = om.MTransformationMatrix(final_matrix)
	rotOrderTarget = cmds.getAttr('%s.rotateOrder'%target)
	eulerRot = mTransformMtx.eulerRotation()
	eulerRot.reorderIt(rotOrderTarget)
	angles = [math.degrees(angle) for angle in (eulerRot.x, eulerRot.y, eulerRot.z)]

	# rotate
	cmds.rotate(angles[0], angles[1], angles[2], target, os=True)

	# Move
	tr = cmds.xform( source, q=True, t=True, ws=True)
	cmds.move( tr[0], tr[1], tr[2], target, rotatePivotRelative=True)			

	#l = cmds.spaceLocator()[0]
	#cmds.move( tr[0], tr[1], tr[2], l, rotatePivotRelative=True)	
	#cmds.rotate(angles[0], angles[1], angles[2], l, os=True)
	pass


##################################
# Snap elbow/knee
##################################

def snapElbowKnee():
	global char, sidePrefix, armControls, legControls

	sels = cmds.ls(sl=True)
	for sel in sels:
		try:
			selObject = sel
			if ':' in selObject:
				ctrlName = selObject.split(":")[-1]
				char = selObject.split(ctrlName)[0]
				objectWithoutNS = ctrlName
			else:
				objectWithoutNS = selObject

			if "_" not in objectWithoutNS:
				print ("Select one control of arm or leg")
				return

			sidePrefix = objectWithoutNS.split("_")[0]
			controlWithoutSidePrefix = objectWithoutNS.split("_")[1]

			# Get sources and tragets
			if controlWithoutSidePrefix in armControls:
				sourceA = char + sidePrefix + "_" + "arm_limbA_skinJoint"
				sourceB = char + sidePrefix + "_" + "arm_limbB_skinJoint"
				sourceC = char + sidePrefix + "_" + "hand"
				target = char + sidePrefix + "_" + "elbow"

			elif controlWithoutSidePrefix in legControls:
				sourceA = char + sidePrefix + "_" + "upLeg_ikFkSwitchHelper"
				sourceB = char + sidePrefix + "_" + "leg_ikFkSwitchHelperAim"
				sourceC = char + sidePrefix + "_" + "kneeEnd_ikFkSwitchHelper"
				target = char + sidePrefix + "_" + "knee"

			else:
				print ("Select control of arm or leg")
				return


			# Get pointPositions
			aPos = cmds.xform(sourceA, t=1, q=1, worldSpace=1)
			bPos = cmds.xform(sourceB, t=1, q=1, worldSpace=1)
			cPos = cmds.xform(sourceC, t=1, q=1, worldSpace=1)

			# Get point Vectors
			a = OpenMaya.MVector(aPos)
			b = OpenMaya.MVector(bPos)
			c = OpenMaya.MVector(cPos)

			# Get vectors
			ab = OpenMaya.MVector(b-a)
			ac = OpenMaya.MVector(c-a)

			# Get length of lower vector
			acLen = OpenMaya.MVector(ac).length()

			# Get projection upper vector on lower vector
			pr = ab*ac / acLen

			# Normalize result
			acNorm = OpenMaya.MVector(ac).normal()

			# Get new vector from start to middle point
			ce = acNorm * pr

			# Get position middle point
			e = ce + a

			# Get vector from middle to elbow point and normalize it
			eb = b - e
			ebNorm = OpenMaya.MVector(eb).normal()

			# Make vector as needed length and from b point and final Point elbow control
			elbowV = ebNorm * acLen * 0.5 + b

			# Move control
			cmds.xform(target, t=elbowV, worldSpace=1)
		except: pass


##################################
# Symmetry Mirror
##################################

'''
def getMatrix(node):
	# Gets the world matrix of an object based on name.
	#Selection list object and MObject for our matrix
	selection = OpenMaya.MSelectionList()
	matrixObject = OpenMaya.MObject()

	#Adding object
	selection.add(node)

	#New api is nice since it will just return an MObject instead of taking two arguments.
	MObjectA = selection.getDependNode(0)

	#Dependency node so we can get the worldMatrix attribute
	fnThisNode = OpenMaya.MFnDependencyNode(MObjectA)

	#Get it's world matrix plug
	worldMatrixAttr = fnThisNode.attribute( "worldMatrix" )

	#Getting mPlug by plugging in our MObject and attribute
	matrixPlug = OpenMaya.MPlug( MObjectA, worldMatrixAttr )
	matrixPlug = matrixPlug.elementByLogicalIndex( 0 )

	#Get matrix plug as MObject so we can get it's data.
	matrixObject = matrixPlug.asMObject(  )

	#Finally get the data
	worldMatrixData = OpenMaya.MFnMatrixData( matrixObject )
	worldMatrix = worldMatrixData.matrix( )

	return worldMatrix

def decompMatrix(node,matrix):
	# Decomposes a MMatrix in new api. Returns an list of translation,rotation,scale in world space.
	#Rotate order of object
	rotOrder = cmds.getAttr('%s.rotateOrder'%node)
	#print rotOrder

	#Puts matrix into transformation matrix
	mTransformMtx = OpenMaya.MTransformationMatrix(matrix)

	#Translation Values
	trans = mTransformMtx.translation(OpenMaya.MSpace.kWorld)

	#Euler rotation value in radians
	eulerRot = mTransformMtx.rotation()

	#Reorder rotation order based on ctrl.
	eulerRot.reorderIt(rotOrder)

	#Find degrees
	angles = [math.degrees(angle) for angle in (eulerRot.x, eulerRot.y, eulerRot.z)]

	#Find world scale of our object.
	scale = mTransformMtx.scale(OpenMaya.MSpace.kWorld)

	#Return Values
	return [trans.x,trans.y,trans.z],angles,scale

def symmetryByMatrix(source, target, ns):
	# set float lists
	source_floatList = cmds.xform(source, q=True, matrix=1, worldSpace=1)
	#print source_floatList

	mirror_floatList = cmds.xform(ns + "mirror_loc",q=True,matrix=1, worldSpace=1)
	vector_floatList = [-1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
	# vector2_floatList = [-1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, -1.0]

	# Make matrixes
	source_matrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(source_floatList,source_matrix)

	mirror_matrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(mirror_floatList,mirror_matrix)
	mirror_transformMatrix = om.MTransformationMatrix(mirror_matrix)
	mirror_inverse_matrix = mirror_transformMatrix.asMatrixInverse()

	vector_matrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(vector_floatList,vector_matrix )

	# vector2_matrix = om.MMatrix()
	# om.MScriptUtil.createMatrixFromList(vector2_floatList,vector2_matrix )

	# Solve
	final_matrix = source_matrix * mirror_inverse_matrix * vector_matrix * mirror_matrix #* vector2_matrix
	final_transformMatrix = om.MTransformationMatrix(final_matrix)

	# Apply
	t = final_transformMatrix.translation(om.MSpace.kWorld)
	cmds.move( t.x, t.y, t.z, target, absolute=True, worldSpace=True )


	cmds.rotate( 0, cmds.getAttr(ns + "transform.ry")*-2, 0, target, relative=True, worldSpace=True )
	cmds.rotate( 0, cmds.getAttr(ns + "mirror_loc.ry")*2, 0, target, relative=True, worldSpace=True )

	#Get Matrix
	# mat = getMatrix(source)
	# print mat

	# #Decompose matrix
	# matDecomp = decompMatrix(source,mat)

	#Print our values
	# sys.stdout.write('\n---------------------------%s---------------------------\n'%source)
	# sys.stdout.write('\nTranslation : %s' %matDecomp[0])
	# sys.stdout.write('\nRotation    : %s' %matDecomp[1])
	# sys.stdout.write('\nScale       : %s\n' %matDecomp[2])
	pass
	
	
def mirrorByMatrix(source, target, ns):
	# set float lists
	source_floatList = cmds.xform(source,q=True,matrix=1, worldSpace=1)
	target_floatList = cmds.xform(target,q=True,matrix=1, worldSpace=1)
	# print source_floatList

	sourceT = cmds.getAttr(source + ".t")
	targetT = cmds.getAttr(target + ".t")

	mirror_floatList = cmds.xform(ns + "mirror_loc",q=True,matrix=1, worldSpace=1)
	vector_floatList = [-1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]

	# Make matrixes
	source_matrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(source_floatList,source_matrix)

	mirror_matrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(mirror_floatList,mirror_matrix)
	mirror_transformMatrix = om.MTransformationMatrix(mirror_matrix)
	mirror_inverse_matrix = mirror_transformMatrix.asMatrixInverse()

	vector_matrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(vector_floatList,vector_matrix )

	# Solve
	final_matrix = source_matrix * mirror_inverse_matrix * vector_matrix * mirror_matrix
	final_transformMatrix = om.MTransformationMatrix(final_matrix)

	# Apply
	t = final_transformMatrix.translation(om.MSpace.kWorld)
	cmds.move( t.x, t.y, t.z, target, absolute=True, worldSpace=True )

	cmds.rotate( 0, cmds.getAttr(ns + "transform.ry")*-2, 0, target, relative=True, worldSpace=True )
	cmds.rotate( 0, cmds.getAttr(ns + "mirror_loc.ry")*2, 0, target, relative=True, worldSpace=True )





	# Make matrixes
	target_matrix = om.MMatrix()
	om.MScriptUtil.createMatrixFromList(target_floatList,target_matrix)

	# Solve
	final_matrix = target_matrix * mirror_inverse_matrix * vector_matrix * mirror_matrix
	final_transformMatrix = om.MTransformationMatrix(final_matrix)

	# Apply
	t = final_transformMatrix.translation(om.MSpace.kWorld)
	cmds.move( t.x, t.y, t.z, source, absolute=True, worldSpace=True )

	cmds.rotate( 0, cmds.getAttr(ns + "transform.ry")*-2, 0, source, relative=True, worldSpace=True )
	cmds.rotate( 0, cmds.getAttr(ns + "mirror_loc.ry")*2, 0, source, relative=True, worldSpace=True )
'''
def symmetryByConstraint(source, target, ns):
	sel = cmds.ls(sl=True)
	
	loc = cmds.spaceLocator()
	cmds.parent(loc, ns+"mirror_loc")
	con = cmds.parentConstraint(source, loc)
	cmds.delete(con)
	gr = cmds.group(loc)
	cmds.xform(os=1, piv=(0,0,0) )
	cmds.setAttr(gr+".scaleX", -1)
	
	loc2 = cmds.duplicate(loc)[0]
	cmds.parent(loc2, loc)
	
	cmds.setAttr(loc2+".rx", 180)
	
	parent = False
	point = False
	orient = False
	if not cmds.getAttr(target+'.tx', lock=True) and not cmds.getAttr(target+'.rx', lock=True):
		con = cmds.parentConstraint(loc2, target, mo=0)
		hasTKeys = cmds.keyframe(target+".t", q=1) or []
		hasRKeys = cmds.keyframe(target+".r", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(target+".t")
		if hasRKeys:
			cmds.setKeyframe(target+".r")			
	elif not cmds.getAttr(target+'.tx', lock=True):
		con = cmds.pointConstraint(loc2, target, mo=0)
		hasTKeys = cmds.keyframe(target+".t", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(target+".t")			
	elif not cmds.getAttr(target+'.rx', lock=True):
		con = cmds.orientConstraint(loc2, target, mo=0)
		hasRKeys = cmds.keyframe(target+".r", q=1) or []
		if hasRKeys:
			cmds.setKeyframe(target+".r")			
	
	cmds.delete(gr)
	cmds.select(sel)

def symmetryRoot(target):
	sel = cmds.ls(sl=True)

	ns = getNS(target)
	if not cmds.getAttr(target+'.tx', lock=True) and not cmds.getAttr(target+'.rx', lock=True):
		con = cmds.parentConstraint(ns+"mirror_loc", target, mo=0, skipTranslate="y")
		hasTKeys = cmds.keyframe(target+".t", q=1) or []
		hasRKeys = cmds.keyframe(target+".r", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(target+".t")
		if hasRKeys:
			cmds.setKeyframe(target+".r")			
	elif not cmds.getAttr(target+'.tx', lock=True):
		con = cmds.pointConstraint(ns+"mirror_loc", target, mo=0, skipTranslate="y")
		hasTKeys = cmds.keyframe(target+".t", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(target+".t")			
	elif not cmds.getAttr(target+'.rx', lock=True):
		con = cmds.orientConstraint(ns+"mirror_loc", target, mo=0)
		hasRKeys = cmds.keyframe(target+".r", q=1) or []
		if hasRKeys:
			cmds.setKeyframe(target+".r")			
	
	cmds.delete(con)
	cmds.select(sel)

def SymmetryWolrdConrols(targets):
	for target in targets:
		
		ns = getNS(target)
		if not cmds.getAttr(target+'.tx', lock=True) and not cmds.getAttr(target+'.rx', lock=True):
			con = cmds.parentConstraint(ns+"mirror_loc", target, mo=0, skipTranslate="y")
			hasTKeys = cmds.keyframe(target+".t", q=1) or []
			hasRKeys = cmds.keyframe(target+".r", q=1) or []
			if hasTKeys:
				cmds.setKeyframe(target+".t")
			if hasRKeys:
				cmds.setKeyframe(target+".r")				
		elif not cmds.getAttr(target+'.tx', lock=True):
			con = cmds.pointConstraint(ns+"mirror_loc", target, mo=0, skipTranslate="y")
			hasTKeys = cmds.keyframe(target+".t", q=1) or []
			if hasTKeys:
				cmds.setKeyframe(target+".t")				
		elif not cmds.getAttr(target+'.rx', lock=True):
			con = cmds.orientConstraint(ns+"mirror_loc", target, mo=0)
			hasRKeys = cmds.keyframe(target+".r", q=1) or []
			if hasRKeys:
				cmds.setKeyframe(target+".r")				
		
		cmds.delete(con)

def mirrorRoot(target):
	sel = cmds.ls(sl=True)
	
	ns = getNS(target)
	loc = cmds.spaceLocator()
	cmds.parent(loc, ns+"mirror_loc")
	con = cmds.parentConstraint(target, loc)
	cmds.delete(con)
	gr = cmds.group(loc)
	cmds.xform(os=1, piv=(0,0,0) )
	cmds.setAttr(gr+".scaleX", -1)
	
	loc2 = cmds.duplicate(loc)[0]
	cmds.parent(loc2, loc)
	cmds.setAttr(loc2+".rx", 180)

	if not cmds.getAttr(target+'.tx', lock=True) and not cmds.getAttr(target+'.rx', lock=True):
		con = cmds.parentConstraint(loc2, target, mo=0)
		hasTKeys = cmds.keyframe(target+".t", q=1) or []
		hasRKeys = cmds.keyframe(target+".r", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(target+".t")
		if hasRKeys:
			cmds.setKeyframe(target+".r")			
	elif not cmds.getAttr(target+'.tx', lock=True):
		con = cmds.pointConstraint(loc2, target, mo=0)
		hasTKeys = cmds.keyframe(target+".t", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(target+".t")	
	elif not cmds.getAttr(target+'.rx', lock=True):
		con = cmds.orientConstraint(loc2, target, mo=0)
		hasRKeys = cmds.keyframe(target+".r", q=1) or []
		if hasRKeys:
			cmds.setKeyframe(target+".r")			
	
	cmds.delete(gr)	
	cmds.select(sel)

def symmetry():
	controls = cmds.ls(selection=True)
	filtered_controls = []
	clear_names = []
	parents = {}
	worldCenter_controls = []
	
	for control in controls:
		#Get control name without ns
		ctrlName = control.split(":")[-1]
		
		side = ctrlName.split("_")[0]
		if side == "l" or side == "r":
			nameUnside = ctrlName[2:]
		else:
			nameUnside = ctrlName
		
		if nameUnside not in clear_names:
			clear_names.append(nameUnside)
			filtered_controls.append(control)
	
	# save data of the controls with parent attr and switch to world
	for control in filtered_controls:
		if cmds.attributeQuery( 'parent', node=control, exists=True ):
			if cmds.attributeQuery( 'parent', node=control, keyable=True ):
				parent = cmds.getAttr(control+".parent", asString=1)
				if parent == "world":
					continue
				
				ctrlName = control.split(":")[-1]
				ns = getNS(control)

				side = ctrlName.split("_")[0]
				if side != "l" and side != "r":
					continue

				nameUnside = ctrlName[2:]

				if side == "l":
					target = ns + "r_" + nameUnside
				elif side == "r":
					target = ns + "l_" + nameUnside				

				parents[control] = cmds.getAttr(control+".parent", asString=1)
				changeParent(control, "world")
				parents[target] = cmds.getAttr(target+".parent", asString=1)
				changeParent(target, "world")	
				
		if cmds.attributeQuery( 'worldSpace', node=control, exists=True ):
			if cmds.getAttr(control + ".worldSpace"):	
				#print control, getControlSide(control)
				if getControlSide(control) == "c":
					worldCenter_controls.append(control)				
	
	for control in filtered_controls:
		#Get control name without ns
		ctrlName = control.split(":")[-1]

		#Get namespases
		ns = getNS(control)

		#Get side
		side = ctrlName.split("_")[0]
		if side != "l" and side != "r":
			side = "c"
		
		#Get name without side prefix
		nameUnside = ctrlName[2:]
		if side == "c":
			nameUnside = ctrlName

		#Get target control
		if side == "c":
			target = ctrlName
		elif side == "l":
			target = "r_" + nameUnside
		elif side == "r":
			target = "l_" + nameUnside


		attrList = []
		attrListKeyable = cmds.listAttr(control, keyable=True )
		if type(attrListKeyable) != list :
			attrListKeyable = []
		attrListNonkeyable = cmds.listAttr(control, channelBox = True )
		if type(attrListNonkeyable) != list :
			attrListNonkeyable = []
		attrList = attrListKeyable + attrListNonkeyable

		#print control, attrList
		if side != "c":
			for attr in attrList:
				#print control, attr
				attrVar = cmds.getAttr(control + "." + attr)

				try:
					cmds.setAttr((ns + target + "." + attr), attrVar)
				except:
					print (target, "cannot modify")
					pass

			if cmds.attributeQuery( 'worldSpace', node=control, exists=True ):
				if cmds.getAttr(control + ".worldSpace"):
					symmetryByConstraint(control, ns + target, ns)

		else:
			# else if ctrl have mirrors attr's
			if cmds.attributeQuery( 'mirrorAxis', node=control, exists=True ):
				# mirror atribute and set
				if cmds.getAttr(control + ".mirrorAxis") == 1:
					conns_out = cmds.listConnections(control, plugs=1, connections=1, s=0, d=1) or []
					center_ctrl = False
					for c in conns_out:
						if "mirror_loc" in c:
							center_ctrl = True
							break
					if center_ctrl:
						try:
							cmds.setAttr(ns + target + ".rz", 0)
						except: pass						
					else:						
						try:
							cmds.setAttr(ns + target + ".tx", 0)
						except: pass
						try:
							cmds.setAttr(ns + target + ".ry", 0)
						except: pass
						try:					
							cmds.setAttr(ns + target + ".rz", 0)
						except: pass
				elif cmds.getAttr(control + ".mirrorAxis") == 2:
					try:
						cmds.setAttr(ns + target + ".ty", 0)
					except: pass
					try:
						cmds.setAttr(ns + target + ".rx", 0)
					except: pass
					try:					
						cmds.setAttr(ns + target + ".rz", 0)
					except: pass					
				elif cmds.getAttr(control + ".mirrorAxis") == 3:
					try:
						cmds.setAttr(ns + target + ".tz", 0)
					except: pass
					try:
						cmds.setAttr(ns + target + ".rx", 0)
					except: pass
					try:					
						cmds.setAttr(ns + target + ".ry", 0)
					except: pass			
					
			elif cmds.attributeQuery( 'worldSpace', node=control, exists=True ):
				if cmds.getAttr(control + ".worldSpace"):
					symmetryRoot(control)
					
	if worldCenter_controls:
		SymmetryWolrdConrols(worldCenter_controls)	

	# restore parent attr of the controls with parent attr
	for c in parents:
		p = parents[c]
		changeParent(c, p)

def mirrorByConstraint(source, target, ns):
	sel = cmds.ls(sl=True)
	
	loc1 = cmds.spaceLocator()
	cmds.parent(loc1, ns+"mirror_loc")
	con1 = cmds.parentConstraint(source, loc1)
	loc2 = cmds.spaceLocator()
	cmds.parent(loc2, ns+"mirror_loc")
	con2 = cmds.parentConstraint(target, loc2)
		
	cmds.delete(con1, con2)
	gr = cmds.group(loc1, loc2)
	cmds.xform(os=1, piv=(0,0,0) )
	cmds.setAttr(gr+".scaleX", -1)
	
	loc1_2 = cmds.duplicate(loc1)[0]
	cmds.parent(loc1_2, loc1)
	cmds.setAttr(loc1_2+".rx", 180)
	
	if not cmds.getAttr(target+'.tx', lock=True) and not cmds.getAttr(target+'.rx', lock=True):
		con = cmds.parentConstraint(loc1_2, target, mo=0)
		hasTKeys = cmds.keyframe(target+".t", q=1) or []
		hasRKeys = cmds.keyframe(target+".r", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(target+".t")
		if hasRKeys:
			cmds.setKeyframe(target+".r")	
	elif not cmds.getAttr(target+'.tx', lock=True):
		con = cmds.pointConstraint(loc1_2, target, mo=0)
		hasTKeys = cmds.keyframe(target+".t", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(target+".t")			
	elif not cmds.getAttr(target+'.rx', lock=True):
		con = cmds.orientConstraint(loc1_2, target, mo=0)
		hasRKeys = cmds.keyframe(target+".r", q=1) or []
		if hasRKeys:
			cmds.setKeyframe(target+".r")			
		
	loc2_2 = cmds.duplicate(loc2)[0]
	cmds.parent(loc2_2, loc2)
	cmds.setAttr(loc2_2+".rx", 180)

	if not cmds.getAttr(source+'.tx', lock=True) and not cmds.getAttr(source+'.rx', lock=True):
		con = cmds.parentConstraint(loc2_2, source, mo=0)
		hasTKeys = cmds.keyframe(source+".t", q=1) or []
		hasRKeys = cmds.keyframe(source+".r", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(source+".t")
		if hasRKeys:
			cmds.setKeyframe(source+".r")		
	elif not cmds.getAttr(source+'.tx', lock=True):
		con = cmds.pointConstraint(loc2_2, source, mo=0)
		hasTKeys = cmds.keyframe(source+".t", q=1) or []
		if hasTKeys:
			cmds.setKeyframe(source+".t")		
	elif not cmds.getAttr(source+'.rx', lock=True):
		con = cmds.orientConstraint(loc2_2, source, mo=0)
		hasRKeys = cmds.keyframe(source+".r", q=1) or []
		if hasRKeys:
			cmds.setKeyframe(source+".r")			
	
	cmds.delete(gr)
	cmds.select(sel)

def mirrorWolrdConrolsStart(targets):
	ns = getNS(targets[0])
	gr = cmds.group(empty=1, n="MIROR_GR")
	con = cmds.parentConstraint(ns+"mirror_loc", gr, mo=0)
	cmds.delete(con)
	cmds.xform(os=1, piv=(0,0,0) )
	
	for target in targets:
		loc = cmds.spaceLocator(n=target+"_MIRROR_LOC")
		cmds.parent(loc, ns+"mirror_loc")
		con = cmds.parentConstraint(target, loc)
		cmds.delete(con)
		cmds.parent(loc, "MIROR_GR")

def mirrorWolrdConrolsEnd(targets):
	cmds.setAttr("MIROR_GR.scaleX", -1)

	for target in targets:
		loc2 = cmds.duplicate(target+"_MIRROR_LOC")[0]
		cmds.parent(loc2, target+"_MIRROR_LOC")
		cmds.setAttr(loc2+".rx", 180)

		if not cmds.getAttr(target+'.tx', lock=True) and not cmds.getAttr(target+'.rx', lock=True):
			con = cmds.parentConstraint(loc2, target, mo=0)
			hasTKeys = cmds.keyframe(target+".t", q=1) or []
			hasRKeys = cmds.keyframe(target+".r", q=1) or []
			if hasTKeys:
				cmds.setKeyframe(target+".t")
			if hasRKeys:
				cmds.setKeyframe(target+".r")				
		elif not cmds.getAttr(target+'.tx', lock=True):
			con = cmds.pointConstraint(loc2, target, mo=0)
			hasTKeys = cmds.keyframe(target+".t", q=1) or []
			if hasTKeys:
				cmds.setKeyframe(target+".t")					
		elif not cmds.getAttr(target+'.rx', lock=True):
			con = cmds.orientConstraint(loc2, target, mo=0)
			hasRKeys = cmds.keyframe(target+".r", q=1) or []
			if hasRKeys:
				cmds.setKeyframe(target+".r")				

	cmds.delete("MIROR_GR")	

def getControlSide(control):
	ctrlName = control.split(":")[-1]
	side = ctrlName.split("_")[0]
	if side != "l" and side != "r":
		side = "c"
	return side

def mirror():
	controls = cmds.ls(selection=True)
	if len(controls) == 0:
		return
	
	filtered_controls = []
	clear_names = []
	parents = {}
	worldCenter_controls = []
	
	for control in controls:
		#Get control name without ns
		ctrlName = control.split(":")[-1]
		
		side = ctrlName.split("_")[0]
		if side == "l" or side == "r":
			nameUnside = ctrlName[2:]
		else:
			nameUnside = ctrlName
		
		if nameUnside not in clear_names:
			clear_names.append(nameUnside)
			filtered_controls.append(control)

	# save data of the controls with parent attr and switch to world
	for control in filtered_controls:
		
		if cmds.attributeQuery( 'parent', node=control, exists=True ):
			if cmds.attributeQuery( 'parent', node=control, keyable=True ):
				parent = cmds.getAttr(control+".parent", asString=1)
				if parent == "world":
					continue
				
				ctrlName = control.split(":")[-1]
				ns = getNS(control)

				side = ctrlName.split("_")[0]
				if side != "l" and side != "r":
					continue

				nameUnside = ctrlName[2:]

				if side == "l":
					target = ns + "r_" + nameUnside
				elif side == "r":
					target = ns + "l_" + nameUnside				

				parents[control] = cmds.getAttr(control+".parent", asString=1)
				changeParent(control, "world")
				parents[target] = cmds.getAttr(target+".parent", asString=1)
				changeParent(target, "world")

		if cmds.attributeQuery( 'worldSpace', node=control, exists=True ):
			if cmds.getAttr(control + ".worldSpace"):	
				#print control, getControlSide(control)
				if getControlSide(control) == "c":
					worldCenter_controls.append(control)
	
	if worldCenter_controls:
		mirrorWolrdConrolsStart(worldCenter_controls)
		
	for control in filtered_controls:
		#Get control name without ns
		ctrlName = control.split(":")[-1]

		#Get namespases
		ns = getNS(control)
		#print 1, ctrlName, ns

		#Get side
		side = ctrlName.split("_")[0]
		if side != "l" and side != "r":
			side = "c"

		#Get name without side prefix
		nameUnside = ctrlName[2:]
		if side == "c":
			nameUnside = ctrlName

		#Get target control
		if side == "c":
			target = ctrlName
		elif side == "l":
			target = "r_" + nameUnside
		elif side == "r":
			target = "l_" + nameUnside


		attrList = []
		attrListKeyable = cmds.listAttr(control, keyable=True )
		if type(attrListKeyable) != list :
			attrListKeyable = []
		attrListNonkeyable = cmds.listAttr(control, channelBox = True )
		if type(attrListNonkeyable) != list :
			attrListNonkeyable = []
		attrList = attrListKeyable + attrListNonkeyable

		if cmds.attributeQuery( 'mirrored', node=control, exists=True ):
			mirrored = cmds.getAttr(control + ".mirrored")
		else:
			mirrored = False

		if cmds.attributeQuery( 'matrixMirror', node=control, exists=True ):
			matrixMirror = cmds.getAttr(control + ".matrixMirror")
		else:
			matrixMirror = False

		if cmds.attributeQuery( 'constraintMirror', node=control, exists=True ):
			constraintMirror = cmds.getAttr(control + ".constraintMirror")
		else:
			constraintMirror = False

		if side != "c":
			use_constraint = False
			if cmds.attributeQuery( 'worldSpace', node=control, exists=True ):
				if cmds.getAttr(control + ".worldSpace"):
					use_constraint = True
					
			for attr in attrList:
				#print 44444, control + "." + attr
				attrVar = cmds.getAttr(control + "." + attr)

				if attr in mirrorAttrLis and use_constraint:
					continue
				
				try:
					old_value = cmds.getAttr(ns + target + "." + attr)
					cmds.setAttr((ns + target + "." + attr), attrVar)
					cmds.setAttr((control + "." + attr), old_value)
				except:
					print (target, "cannot modify", attr)
					pass

			if use_constraint:
				mirrorByConstraint(control, ns + target, ns)

		else:
			# else if ctrl have mirrors attr's
			if cmds.attributeQuery( 'mirrorAxis', node=control, exists=True ):
				# mirror atribute and set
				if cmds.getAttr(control + ".mirrorAxis") == 1:
					conns_out = cmds.listConnections(control, plugs=1, connections=1, s=0, d=1) or []
					center_ctrl = False
					for c in conns_out:
						if "mirror_loc" in c:
							center_ctrl = True
							break
					if center_ctrl:
						try:
							cmds.setAttr(ns + target + ".rz", cmds.getAttr(ns + target + ".rz")*-1 )
						except: pass					
					else:	
						try:
							cmds.setAttr(ns + target + ".tx", cmds.getAttr(ns + target + ".tx")*-1 )
						except: pass
						try:
							cmds.setAttr(ns + target + ".ry", cmds.getAttr(ns + target + ".ry")*-1 )
						except: pass
						try:
							cmds.setAttr(ns + target + ".rz", cmds.getAttr(ns + target + ".rz")*-1 )
						except: pass
				elif cmds.getAttr(control + ".mirrorAxis") == 2:
					try:
						cmds.setAttr(ns + target + ".ty", cmds.getAttr(ns + target + ".ty")*-1 )
					except: pass
					try:
						cmds.setAttr(ns + target + ".rx", cmds.getAttr(ns + target + ".rx")*-1 )
					except: pass
					try:
						cmds.setAttr(ns + target + ".rz", cmds.getAttr(ns + target + ".rz")*-1 )
					except: pass					
				elif cmds.getAttr(control + ".mirrorAxis") == 3:
					try:
						cmds.setAttr(ns + target + ".tz", cmds.getAttr(ns + target + ".tz")*-1 )
					except: pass
					try:
						cmds.setAttr(ns + target + ".rx", cmds.getAttr(ns + target + ".rx")*-1 )
					except: pass
					try:
						cmds.setAttr(ns + target + ".ry", cmds.getAttr(ns + target + ".ry")*-1 )
					except: pass					
					
			elif cmds.attributeQuery( 'worldSpace', node=control, exists=True ):
				if cmds.getAttr(control + ".worldSpace"):
					mirrorRoot(control)					
		
	if worldCenter_controls:
		mirrorWolrdConrolsEnd(worldCenter_controls)	
		
	# restore parent attr of the controls with parent attr
	for c in parents:
		p = parents[c]
		changeParent(c, p)
				
	cmds.select(controls)
					
def changeParent(o, parentName):
	if not cmds.attributeQuery( 'parent', node=o, exists=True ):
		return		

	# Get transform
	tr = cmds.xform( o, q=True, t=True, ws=True)
	rt = cmds.xform( o, q=True, ro=True, ws=True)

	# get size of parent attribute enum
	list = mel.eval('attributeQuery -node %s -listEnum "parent"' %o)
	parents = list[0].split(":")

	for i, p in enumerate(parents):
		if p == parentName:
			cmds.setAttr(o + ".parent", i)

	# Set Transform
	cmds.move( tr[0], tr[1], tr[2], o, rotatePivotRelative=True)
	cmds.rotate(rt[0], rt[1], rt[2], o, ws=True)
	
def hasWorldParent(control):
	list = mel.eval('attributeQuery -node %s -listEnum "parent"' %control)
	parents = list[0].split(":")
	
	return "world" in parents
	
	
