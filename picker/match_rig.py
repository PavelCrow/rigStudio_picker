import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import math, os, imp, json, sys

from functools import wraps

if sys.version[0] == "2":
	from .. import utils
	
	try: import rigStudio_picker.animTools.rs_switchIkFk
	except: import rigStudio2.animTools.rs_switchIkFk	
else:
	import importlib
	import rigStudio2.utils as utils
	
	#try: import rigStudio_picker.animTools.rs_switchIkFk
	#except: import rigStudio2.animTools.rs_switchIkFk	
'''
# -----------------------------------------------------------------------------
# Decorators 
# -----------------------------------------------------------------------------
def viewportOff( func ):
	"""
	Decorator - turn off Maya display while func is running.
	if func will fail, the error will be raised after.
	"""
	@wraps(func)
	def wrap( *args, **kwargs ):

		# Turn $gMainPane Off:
		mel.eval("paneLayout -e -manage false $gMainPane")

		# Decorator will try/except running the function. 
		# But it will always turn on the viewport at the end.
		# In case the function failed, it will prevent leaving maya viewport off.
		try:
			return func( *args, **kwargs )
		except Exception:
			raise # will raise original error
		finally:
			mel.eval("paneLayout -e -manage true $gMainPane")

	return wrap

ns = 'SKELETON'
path = ""

# add ns
def add_ns(root, name):
	cmds.namespace( add=name )
	cmds.namespace( set=name )
	for o in cmds.listRelatives(root, allDescendents=1):
		cmds.rename( o, ':%s:' %name + o )
	cmds.rename( root, ':%s:' %name + root )
	cmds.namespace( set = ":")

def get_spine_count(controls):
	count = 0
	for i in range(1, 10):
		if 'spine%s' %i in controls:
			count += 1
	return count	

def get_twists_count(controls, name):
	count = 0
	for i in range(1, 6):
		#print i, j, 'l_finger_%s_%s' %(i,j) in d
		if name+'_twist_%s' %i in controls:
			count += 1
	return count

def generate_rig(controls, tName):
	import rigStudio2
	reload(rigStudio2)
	rigStudio2.main.run(False)	

	if cmds.objExists('modules'):
		cmds.warning("Rig is already exists")
		return
	
	for o in ['pelvis', 'spine1', 'spine2', 'neck', 'head', 'root', 
	          'l_clavicle', 'l_arm', 'l_forearm', 'l_hand', 'l_leg', 'l_knee', 'l_foot', "l_toe", 
	          'r_clavicle', 'r_arm', 'r_forearm', 'r_hand', 'r_leg', 'r_knee', 'r_foot', "r_toe"
	          ]:
		if o not in controls:
			cmds.warning(o+" not assigned")
			return
		#if not cmds.objExists(o):
			#cmds.warning(o+" is not exist")
			#return
			
	useFace = False
	for o in ['noseTip', 'l_nostril', 'r_nostril', 'l_cheekup', 'r_cheekup', 'l_cheek', 'r_cheek', 
              't_lip', 'b_lip', 'l_t_lip', 'r_t_lip', 'l_b_lip', 'r_b_lip', 'l_lips_corner', "r_lips_corner", 
              'jaw', 'l_eye', 'r_eye', 'l_t_eyelid', 'r_t_eyelid', 'l_b_eyelid', 'r_b_eyelid',
              'l_brow_1', 'r_brow_1', 'l_brow_2', 'r_brow_2', 'l_brow_3', 'r_brow_3'
              ]:
		if o in controls:
			useFace = True
		
	root = controls["root"][0]
	
	if not cmds.objExists(ns+":"+root):
		add_ns(root, ns)
	
	# get scale
	root = ns+":"+controls["root"][0]
	
	y_max = 0
	for o in cmds.listRelatives(root, allDescendents=1):
		try:
			y = cmds.xform(o, q=1, t=1, ws=1)[1]
			if y > y_max: y_max = y
		except: print 'skip joint', o
	
	# read skeleton 
	
	def get_fingers_count():
		fingers_count = 0
		for i in range(1, 6):
			f = False
			for j in range(1, 5):
				#print i, j, 'l_finger_%s_%s' %(i,j) in d
				if 'l_finger_%s_%s' %(i,j) in controls:
					f = True
					fingers_count += 1
					break
		return fingers_count

	def get_fingers_lenght():
		fingers_lenght_max = 0
		for i in range(1, 6):
			fingers_lenght = 0
			for j in range(1, 5):
				if 'l_finger_%s_%s' %(i,j) in controls:
					fingers_lenght += 1
			if fingers_lenght > fingers_lenght_max:
				fingers_lenght_max = fingers_lenght
		return fingers_lenght_max  	

	fingers_count = get_fingers_count()
	fingers_lenght = get_fingers_lenght()	
	if fingers_count == 0: fingers_count = 1
	if fingers_lenght == 0: fingers_lenght = 1
	spine_count = get_spine_count(controls)
	arm_twists_count = get_twists_count(controls, 'l_arm')
	forearm_twists_count = get_twists_count(controls, 'l_forearm')
	leg_twists_count = get_twists_count(controls, 'l_leg')
	knee_twists_count = get_twists_count(controls, 'l_knee')

	fileName = __name__.split('.')[0]
	rootPath = os.path.abspath(imp.find_module(fileName)[1])
	
	with open(rootPath+'/templates/rigs/'+tName+'.tmpl', mode='r') as f:
		data = json.load(f)	
	
	# get data
	for d in data['modulesData']:
		if d["name"] == "l_hand":
			fingers_data = d['optionsData']
			fingers_data['chainsCount'] = fingers_count
			fingers_data['elementsCount'] = fingers_lenght
		#if d["name"] == "spine":
			#spine_data = d['optionsData']
			#spine_data['jointsCount'] = spine_count
	
	# set data
	for d in data['modulesData']:
		if d["name"] == "l_hand":
			d['optionsData'] = fingers_data
		if d["name"] == "spine":
			d['jointsCount'] = spine_count
		if d["name"] == "l_arm":
			for t in d['twistsData']:
				if t['name'] == 'MODNAME_root':
					t['jointsCount'] = arm_twists_count
				elif t['name'] == 'MODNAME_middle':
					t['jointsCount'] = forearm_twists_count
		if d["name"] == "l_leg":
			for t in d['twistsData']:
				if t['name'] == 'MODNAME_root':
					t['jointsCount'] = leg_twists_count
				elif t['name'] == 'MODNAME_middle':
					t['jointsCount'] = knee_twists_count
		
	#for d in data['modulesData']:
		#if d["name"] == "spine":
			#for  d_ in d:
				#print d_, d[d_]

	# generate rig
	rigStudio2.main.rs_win.create_rig()
	rigStudio2.main.rs_win.template_actions('rig_load', tName=tName, forceData=data)
	
	if useFace:
		rigStudio2.main.rs_win.addModule('gameFace', name="face", options={}, updateUI=False)
		cmds.setAttr('face_mainPoser.t', 0, 6.74, 0.3)
		cmds.setAttr('face_mainPoser.sx', 0.2)
		rigStudio2.main.rs_win.connectModule(target="head_root_poser", moduleName="face", updateUI=False)		
	
	cmds.setAttr('root_mainPoser.sx', y_max/8)	
	
	# unlock limb fk rotate
	cmds.setAttr(utils.getControlNameFromInternal("l_leg", "fk_b")+'.rotateX', k=1, l=0)
	cmds.setAttr(utils.getControlNameFromInternal("r_leg", "fk_b")+'.rotateX', k=1, l=0)
	cmds.setAttr(utils.getControlNameFromInternal("l_leg", "fk_b")+'.rotateZ', k=1, l=0)
	cmds.setAttr(utils.getControlNameFromInternal("r_leg", "fk_b")+'.rotateZ', k=1, l=0)
	cmds.setAttr(utils.getControlNameFromInternal("l_arm", "fk_b")+'.rotateX', k=1, l=0)
	cmds.setAttr(utils.getControlNameFromInternal("r_arm", "fk_b")+'.rotateX', k=1, l=0)
	cmds.setAttr(utils.getControlNameFromInternal("l_arm", "fk_b")+'.rotateZ', k=1, l=0)
	cmds.setAttr(utils.getControlNameFromInternal("r_arm", "fk_b")+'.rotateZ', k=1, l=0)
	
	match_rig(controls, useFace=useFace)
		
	for c in controls:
		cmds.select('root_ctrl')
		#print c, c.split("_")[0] == "add", c.split("_")[1].isdigit()
		if c.split("_")[0] == "add" and c.split("_")[1].isdigit():
			rigStudio2.main.rs_win.additionalControl_add(shape='box', name=controls[c][0]+"_ctrl")
			con = cmds.parentConstraint(ns+":"+controls[c][0], controls[c][0]+"_ctrl_addPoser", mo=0)
			cmds.delete(con)
			p = pm.listRelatives(ns+":"+controls[c][0], p=1)[0]
			name = controls[c][0]+"_ctrl"
			pm.disconnectAttr(name+'_group_decMat.outputTranslateX', name+"_group.translateX")
			pm.disconnectAttr(name+'_group_decMat.outputTranslateY', name+"_group.translateY")
			pm.disconnectAttr(name+'_group_decMat.outputTranslateZ', name+"_group.translateZ")
			pm.disconnectAttr(name+'_group_decMat.outputRotateX', name+"_group.rotateX")
			pm.disconnectAttr(name+'_group_decMat.outputRotateY', name+"_group.rotateY")
			pm.disconnectAttr(name+'_group_decMat.outputRotateZ', name+"_group.rotateZ")
			pm.disconnectAttr(name+'_group_decMat.outputScaleX', name+"_group.scaleX")
			pm.disconnectAttr(name+'_group_decMat.outputScaleY', name+"_group.scaleY")
			pm.disconnectAttr(name+'_group_decMat.outputScaleZ', name+"_group.scaleZ")
			pm.parentConstraint(p, controls[c][0]+"_ctrl_group", mo=1)
		elif c.split("_")[0] == "weapon" and c.split("_")[1].isdigit():
			rigStudio2.main.rs_win.additionalControl_add(shape='box', name=controls[c][0]+"_ctrl")
			con = cmds.parentConstraint(ns+":"+controls[c][0], controls[c][0]+"_ctrl_addPoser", mo=0)
			cmds.delete(con)
			p = pm.listRelatives(ns+":"+controls[c][0], p=1)[0]
			name = controls[c][0]+"_ctrl"
			pm.disconnectAttr(name+'_group_decMat.outputTranslateX', name+"_group.translateX")
			pm.disconnectAttr(name+'_group_decMat.outputTranslateY', name+"_group.translateY")
			pm.disconnectAttr(name+'_group_decMat.outputTranslateZ', name+"_group.translateZ")
			pm.disconnectAttr(name+'_group_decMat.outputRotateX', name+"_group.rotateX")
			pm.disconnectAttr(name+'_group_decMat.outputRotateY', name+"_group.rotateY")
			pm.disconnectAttr(name+'_group_decMat.outputRotateZ', name+"_group.rotateZ")
			pm.disconnectAttr(name+'_group_decMat.outputScaleX', name+"_group.scaleX")
			pm.disconnectAttr(name+'_group_decMat.outputScaleY', name+"_group.scaleY")
			pm.disconnectAttr(name+'_group_decMat.outputScaleZ', name+"_group.scaleZ")
			utils.create_space_group(ctrl=name, sources=[ns+":"+controls['l_hand'][0],
			                                             ns+":"+controls['r_hand'][0],
			                                             ns+":"+controls['root'][0]],
			                                    names=['l_hand', 'r_hand', 'world'])
			cmds.setAttr(name+'.parent', 2)

def match_rig(controls, useFace=False):

	def connectPoser(source, poser, parent=False, skip_axises=[]):
		if source not in controls:
			return
		if not cmds.objExists(poser):
			return
		joint = controls[source][0]
		
		if parent:
			con = cmds.parentConstraint(ns+":"+joint, poser, mo=0)
		else:
			con = cmds.pointConstraint(ns+":"+joint, poser, mo=0, skip=skip_axises)
		cmds.delete(con)

	def orientPoser(poser, aim, aimVector=(1,0,0), skip_axises=[]):
		if not cmds.objExists(poser):
			return
		aim_joint = controls[aim][0]
		
		con = cmds.aimConstraint(ns+":"+aim_joint, poser, aimVector=aimVector, upVector=(0,0,1), mo=0, worldUpType="vector", worldUpVector=[0,1,0], skip=skip_axises)
		cmds.delete(con)

	connectPoser('pelvis', 'spine_mainPoser')
	connectPoser('neck', 'spine_end_poser')
	connectPoser('neck', 'neck_mainPoser')
	connectPoser('head', 'head_mainPoser')
	connectPoser('l_clavicle', 'l_shoulder_mainPoser')
	connectPoser('l_arm', 'l_arm_mainPoser')
	connectPoser('l_forearm', 'l_arm_middle_poser')
	connectPoser('l_hand', 'l_hand_mainPoser')
	connectPoser('l_leg', 'l_leg_mainPoser')
	connectPoser('l_toe', 'l_foot_mainPoser')
	connectPoser('l_knee', 'l_leg_middle_poser')
	
	if useFace:
		con = pm.pointConstraint(ns+':'+controls['t_lip'][0], ns+':'+controls['b_lip'][0], 'face_mouth_poser', mo=0)
		pm.delete(con)
		con = pm.pointConstraint(ns+':'+controls['l_eye'][0], ns+':'+controls['r_eye'][0], 'face_eyes_mainPoser', mo=0)
		pm.delete(con)
		
		connectPoser('l_brow_2', 'face_brow_poser')
		connectPoser('l_brow_2', 'face_brow_2_poser')
		connectPoser('l_brow_1', 'face_brow_1_poser')
		connectPoser('l_brow_3', 'face_brow_3_poser')
		connectPoser('jaw', 'face_jaw_poser')
		connectPoser('t_lip', 'face_t_lip_poser')
		connectPoser('b_lip', 'face_b_lip_poser')
		connectPoser('l_t_lip', 'face_l_t_lip_poser')
		connectPoser('l_b_lip', 'face_l_b_lip_poser')
		connectPoser('l_lips_corner', 'face_lipCorner_poser')
		connectPoser('noseTip', 'face_nose_poser')
		connectPoser('l_nostril', 'face_nostril_poser')
		connectPoser('l_cheek', 'face_cheek_poser')
		connectPoser('l_cheekup', 'face_cheekUp_poser')
		connectPoser('l_eye', 'face_eyes_end_poser', skip_axises=['y', 'z'])
	
	# align fingers
	for i in range(1, 6):
		elem = 1
		for j in range(1, 5):
			if 'l_finger_%s_%s' %(i,j) in controls:
				connectPoser('l_finger_%s_%s' %(i,j), 'l_hand_chain_%s_element_%s_poser' %(i,elem))
				if 'l_finger_%s_%s' %(i,j+1) in controls:
					orientPoser('l_hand_chain_%s_element_%s_poser' %(i,elem), 'l_finger_%s_%s' %(i,j+1))
				elem += 1

	
	# align spine
	spine_count = get_spine_count(controls)
	
	for i in range(1, spine_count+1):
		closest = pm.createNode('closestPointOnSurface')
		point = pm.createNode('pointMatrixMult')
		j = ns + ":" + controls["spine"+str(i)][0]
		pm.connectAttr(j+'.worldMatrix[0]', point.inMatrix)
		pm.connectAttr('spine_bend_surfShape.worldSpace[0]', closest.inputSurface)
		point.output >> closest.inPosition
		pm.connectAttr(closest.parameterU, 'spine_local_%s_follicleShape.parameterU' %i)
		pm.disconnectAttr(closest.parameterU, 'spine_local_%s_follicleShape.parameterU' %i)
		pm.delete(closest)
		

	# foot correct	
	orientPoser('l_foot_mainPoser', 'l_foot', aimVector=(0,0,-1), skip_axises="x")
	pos = pm.xform('l_foot_mainPoser', q=1, t=1, ws=1)
	pm.xform('l_foot_mainPoser', t=(pos[0], 0, pos[2]), ws=1)
	#connectPoser('l_toe', 'l_foot_toe_poser', skip_axises="x")
	#cmds.setAttr('l_foot_toeTip_poser.ty', cmds.getAttr('l_foot_toe_poser.ty'))
	connectPoser('l_foot', 'l_foot_root_poser', skip_axises=['x'])
	
	# set vertical position
	data = []
	for out in pm.PyNode(ns+":"+controls["l_toe"][0]).worldMatrix[0].outputs():
		if out.type() == 'skinCluster':
			sc = out
			geo = sc.outputGeometry[0].outputs()[0]
			for v in geo.vtx:
				data.append(v)
	
	foot_poser = pm.PyNode(ns+":"+controls["l_foot"][0])
	y_limit = pm.xform(foot_poser, q=1, t=1, ws=1)[1]

	foots = []
	for v in data:    
		if v.getPosition()[1] < y_limit:
			foots.append(v)
			
	z_min = 9999
	z_max = -9999
	for v in foots:
		if v.getPosition()[2] > z_max:
			z_max = v.getPosition()[2]
		if v.getPosition()[2] < z_min:
			z_min = v.getPosition()[2]
	
	if foots:
		pos = pm.xform('l_foot_toeTip_poser', q=1, t=1, ws=1)
		pm.xform( 'l_foot_toeTip_poser', t=(pos[0], pos[1], z_max), ws=1)
		pos = pm.xform('l_foot_heelPoint_poser', q=1, t=1, ws=1)
		pm.xform( 'l_foot_heelPoint_poser', t=(pos[0], pos[1], z_min), ws=1)
	
	for m in cmds.listRelatives("modules"):
		try: cmds.hide(m.replace('_mod', '_posers'))
		except: pass

def alignSkeleton(controls, align=True):
	if cmds.objExists('modules'):
		cmds.warning("Rig is already exists")
		return
	
	for o in ['pelvis', 'spine1', 'spine2', 'neck', 'head', 'root', 
	          'l_clavicle', 'l_arm', 'l_forearm', 'l_hand', 'l_leg', 'l_knee', 'l_foot', "l_toe", 
	          'r_clavicle', 'r_arm', 'r_forearm', 'r_hand', 'r_leg', 'r_knee', 'r_foot', "r_toe"
	          ]:
		if o not in controls:
			cmds.warning(o+" not assigned")
			return
		#if not cmds.objExists(controls[o][0]):
			#cmds.warning(o+" is not exist")
			#return
		
	root = controls["root"][0]
	
	if not cmds.objExists("ORIGINAL:"+root):
		add_ns(root, ns)
		original_root = pm.duplicate(ns+':'+root, rr=1, un=1)[0]
	
		for j in pm.listRelatives(ns+':'+root, allDescendents=1):
			pm.cutKey(j)
	print 000
	def alignJoint(joint, aim_joint=None, up_joint=None, dir="world", offsetZ=0):
		# joint pos
		world_mat = pm.xform(joint, q=True, m=True, ws=True)
		x_axis = world_mat[0:3]
		y_axis = world_mat[4:7]
		z_axis = world_mat[8:11]
		v_x = pm.datatypes.Vector(x_axis)
		v_y = pm.datatypes.Vector(y_axis)
		v_z = pm.datatypes.Vector(z_axis)
		joint_pos = pm.xform(joint, q=True, t=True, ws=True)

		def getClosestAxis(point):
			pos = pm.xform(point, q=True, t=True, ws=True)
			v = pm.datatypes.Vector(pos[0]-joint_pos[0], pos[1]-joint_pos[1], pos[2]-joint_pos[2])
			v.normalize()

			angle_x = math.degrees(v_x.angle(v)) 
			angle_y = math.degrees(v_y.angle(v)) 
			angle_z = math.degrees(v_z.angle(v)) 
			_angle_x = math.degrees(v_x.angle(v*-1)) 
			_angle_y = math.degrees(v_y.angle(v*-1)) 
			_angle_z = math.degrees(v_z.angle(v*-1)) 
			closest = angle_x
			axis = "x"
			vec = [1,0,0]
			if angle_y < closest: 
				closest = angle_y
				axis = "y"
				vec = [0,1,0]
			if angle_z < closest: 
				closest = angle_z
				axis = "z"
				vec = [0,0,1]
			if _angle_x < closest: 
				closest = _angle_x
				axis = "-x"
				vec = [-1,0,0]
			if _angle_y < closest: 
				closest = _angle_y
				axis = "-y"
				vec = [0,-1,0]
			if _angle_z < closest: 
				closest = _angle_z
				axis = "-z"
				vec = [0,0,-1]
			return vec

		if dir == "world":
			pm.xform(joint, t=[0,joint_pos[1],0], ws=1)
			joint_pos = pm.xform(joint, q=True, t=True, ws=True)
			l_aim = pm.spaceLocator()
			l_aim.t.set(joint_pos[0]+10, joint_pos[1], joint_pos[2])
			l_up = pm.spaceLocator()
			l_up.t.set(joint_pos[0], joint_pos[1]+10, joint_pos[2])
			aim_vec = getClosestAxis(aim_joint)
			up_vec = getClosestAxis(up_joint)
			con = pm.aimConstraint(l_aim, joint, aimVector=aim_vec, upVector=up_vec, worldUpType="object", worldUpObject=l_up, mo=0)
			pm.delete(con, l_aim, l_up)

		elif dir == "up":
			l = pm.spaceLocator()
			l.t.set(joint_pos[0], joint_pos[1]+10, joint_pos[2])		
			if aim_joint:
				vec = getClosestAxis(aim_joint)
			else:
				vec = getClosestAxis(l)
			con = pm.aimConstraint(l, joint, aimVector=vec, upVector=[1,0,0], worldUpType="vector", worldUpVector=[0,1,0], mo=0)
			pm.delete(con, l)

		elif dir == "left":
			l_aim = pm.spaceLocator()
			l_aim.t.set(joint_pos[0]+10, joint_pos[1], joint_pos[2]+offsetZ)		
			l_up = pm.spaceLocator()
			l_up.t.set(joint_pos[0], joint_pos[1]+10, joint_pos[2])		
			up_vec = getClosestAxis(l_up)
			if aim_joint:
				aim_vec = getClosestAxis(aim_joint)
			else:
				aim_vec = getClosestAxis(l_aim)
			con = pm.aimConstraint(l_aim, joint, aimVector=aim_vec, upVector=up_vec, worldUpType="object", worldUpObject=l_up, mo=0)
			pm.delete(con, l_aim, l_up)

		elif dir == "right":
			l_aim = pm.spaceLocator()
			l_aim.t.set(joint_pos[0]-10, joint_pos[1], joint_pos[2]+offsetZ)		
			l_up = pm.spaceLocator()
			l_up.t.set(joint_pos[0], joint_pos[1]+10, joint_pos[2])		
			up_vec = getClosestAxis(l_up)
			if aim_joint:
				aim_vec = getClosestAxis(aim_joint)
			else:
				aim_vec = getClosestAxis(l_aim)
			con = pm.aimConstraint(l_aim, joint, aimVector=aim_vec, upVector=up_vec, worldUpType="object", worldUpObject=l_up, mo=0)
			pm.delete(con, l_aim, l_up)

		elif dir == "down":
			l_aim = pm.spaceLocator()
			l_aim.t.set(joint_pos[0], joint_pos[1]-10, joint_pos[2]+offsetZ)		
			l_up = pm.spaceLocator()
			l_up.t.set(joint_pos[0], joint_pos[1], joint_pos[2]+10)		
			up_vec = getClosestAxis(l_up)
			if aim_joint:
				aim_vec = getClosestAxis(aim_joint)
			else:
				aim_vec = getClosestAxis(l_aim)
			con = pm.aimConstraint(l_aim, joint, aimVector=aim_vec, upVector=up_vec, worldUpType="object", worldUpObject=l_up, mo=0)
			pm.delete(con, l_aim, l_up)

		elif dir == "front":
			l_aim = pm.spaceLocator()
			l_aim.t.set(joint_pos[0], joint_pos[1], joint_pos[2]+10)		
			l_up = pm.spaceLocator()
			l_up.t.set(joint_pos[0], joint_pos[1]+10, joint_pos[2])		
			up_vec = getClosestAxis(l_up)
			if aim_joint:
				con = pm.pointConstraint(aim_joint, l_aim, mo=0)
				pm.delete(con)
				aim_vec = getClosestAxis(aim_joint)
			else:
				aim_vec = getClosestAxis(l_aim)
			con = pm.aimConstraint(l_aim, joint, aimVector=aim_vec, upVector=up_vec, worldUpType="object", worldUpObject=l_up, mo=0)
			pm.delete(con, l_aim, l_up)


		
	print 111	
	alignJoint(ns+':'+controls["pelvis"][0], aim_joint=ns+':'+controls["l_leg"][0], up_joint=ns+':'+controls["spine1"][0])
	alignJoint(ns+':'+controls["spine1"][0], aim_joint=ns+':'+controls["spine2"][0], dir="up")
	alignJoint(ns+':'+controls["spine2"][0], aim_joint=ns+':'+controls["neck"][0], dir="up")
	alignJoint(ns+':'+controls["neck"][0], aim_joint=ns+':'+controls["head"][0], dir="up")
	alignJoint(ns+':'+controls["head"][0], dir="up")
	alignJoint(ns+':'+controls["l_clavicle"][0], aim_joint=ns+':'+controls["l_arm"][0], dir="left")
	alignJoint(ns+':'+controls["l_arm"][0], aim_joint=ns+':'+controls["l_forearm"][0], dir="left", offsetZ=-2)
	alignJoint(ns+':'+controls["l_forearm"][0], aim_joint=ns+':'+controls["l_hand"][0], dir="left", offsetZ=2)
	alignJoint(ns+':'+controls["l_hand"][0], dir="left")
	alignJoint(ns+':'+controls["l_leg"][0], aim_joint=ns+':'+controls["l_knee"][0], dir="down", offsetZ=2)
	alignJoint(ns+':'+controls["l_knee"][0], aim_joint=ns+':'+controls["l_foot"][0], dir="down", offsetZ=-2)
	#alignJoint(ns+':'+controls["l_foot"][0], aim_joint=ns+':'+controls["l_toe"][0], dir="front")
	#alignJoint(ns+':'+controls["l_foot"][0], dir="front")
	#alignJoint(ns+':'+controls["l_toe"][0], dir="front")
	
	alignJoint(ns+':'+controls["r_clavicle"][0], aim_joint=ns+':'+controls["r_arm"][0], dir="right")
	alignJoint(ns+':'+controls["r_arm"][0], aim_joint=ns+':'+controls["r_forearm"][0], dir="right", offsetZ=-2)
	alignJoint(ns+':'+controls["r_forearm"][0], aim_joint=ns+':'+controls["r_hand"][0], dir="right", offsetZ=2)
	alignJoint(ns+':'+controls["r_hand"][0], dir="right")
	alignJoint(ns+':'+controls["r_leg"][0], aim_joint=ns+':'+controls["r_knee"][0], dir="down", offsetZ=2)
	alignJoint(ns+':'+controls["r_knee"][0], aim_joint=ns+':'+controls["r_foot"][0], dir="down", offsetZ=-2)
	#alignJoint(ns+':'+controls["r_foot"][0], aim_joint=ns+':'+controls["r_toe"][0], dir="front")
	#alignJoint(ns+':'+controls["r_foot"][0], dir="front")
	#alignJoint(ns+':'+controls["r_toe"][0], dir="front")
	print 222
	# set vertical position
	sc = None
	y_min = cmds.xform(ns+':'+controls["l_toe"][0], q=1, t=1, ws=1)[1]
	for out in pm.PyNode(ns+':'+controls["l_toe"][0]).worldMatrix[0].outputs():
		if out.type() == 'skinCluster':
			sc = out
			geo = sc.outputGeometry[0].outputs()[0]
			y = geo.getBoundingBoxMin()[1]
			if y < y_min:
				y_min = y

	pelvis_pos = cmds.xform(ns+':'+controls["pelvis"][0], q=1, t=1, ws=1)
	cmds.xform(ns+':'+controls["pelvis"][0], t=[pelvis_pos[0], pelvis_pos[1]-y_min, pelvis_pos[2]], ws=1)	
	print 333
	for i in range(1, 6):
		for j in range(1, 5):
			if 'l_finger_%s_%s' %(i,j) in controls:
				c = pm.PyNode(ns+':'+controls['l_finger_%s_%s' %(i,j)][0])
				c.r.set(0,0,0)		
			if 'r_finger_%s_%s' %(i,j) in controls:
				c = pm.PyNode(ns+':'+controls['r_finger_%s_%s' %(i,j)][0])
				c.r.set(0,0,0)		
			
	
	print 444
	if not cmds.objExists("ORIGINAL:"+root):
		add_ns(original_root.name(), "ORIGINAL")

	if cmds.objExists("DRV:"+root):
		cmds.delete("DRV:"+root)
		cmds.namespace( removeNamespace="DRV", mergeNamespaceWithRoot=1 )	
	print 555
	drv_root = pm.duplicate(ns+':'+root)[0]
	add_ns(drv_root.name(), "DRV")		
	print 666
	pm.hide("ORIGINAL:"+root, "DRV:"+root)
	
def connectJoints(controls):
	for o in ['pelvis', 'spine1', 'spine2', 'neck', 'head', 'root', 
	          'l_clavicle', 'l_arm', 'l_forearm', 'l_hand', 'l_leg', 'l_knee', 'l_foot', "l_toe", 
	          'r_clavicle', 'r_arm', 'r_forearm', 'r_hand', 'r_leg', 'r_knee', 'r_foot', "r_toe"
	          ]:
		if o not in controls:
			cmds.warning(o+" not assigned")
			return
		#if not cmds.objExists(o):
			#cmds.warning(o+" is not exist")
			#return	
	#for i in range(1, 6):
		#elem = 1
		#for j in range(1, 5):
			#if 'l_finger_%s_%s' %(i,j) in controls:
			
	useFace = False
	for o in ['noseTip', 'l_nostril', 'r_nostril', 'l_cheekup', 'r_cheekup', 'l_cheek', 'r_cheek', 
              't_lip', 'b_lip', 'l_t_lip', 'r_t_lip', 'l_b_lip', 'r_b_lip', 'l_lips_corner', "r_lips_corner", 
              'jaw', 'l_eye', 'r_eye', 'l_t_eyelid', 'r_t_eyelid', 'l_b_eyelid', 'r_b_eyelid',
              'l_brow_1', 'r_brow_1', 'l_brow_2', 'r_brow_2', 'l_brow_3', 'r_brow_3'
              ]:
		if o in controls:
			useFace = True
			
	#return
	arm_twists_count = get_twists_count(controls, 'l_arm')
	forearm_twists_count = get_twists_count(controls, 'l_forearm')
	leg_twists_count = get_twists_count(controls, 'l_leg')
	knee_twists_count = get_twists_count(controls, 'l_knee')

	count = get_twists_count(controls, 'l_arm')
	for i in range(1, count+1):
		if 'l_arm_twist_%s' %i in controls:
			cmds.orientConstraint('l_arm_root_twist_%s_joint' %i, ns+":"+controls["l_arm_twist_%s" %i][0], mo=1)
			cmds.orientConstraint('r_arm_root_twist_%s_joint' %i, ns+":"+controls["r_arm_twist_%s" %i][0], mo=1)
	
	count = get_twists_count(controls, 'l_forearm')
	for i in range(1, count+1):
		if 'l_arm_twist_%s' %i in controls:
			cmds.orientConstraint('l_arm_middle_twist_%s_joint' %i, ns+":"+controls["l_forearm_twist_%s" %i][0], mo=1)
			cmds.orientConstraint('r_arm_middle_twist_%s_joint' %i, ns+":"+controls["r_forearm_twist_%s" %i][0], mo=1)
	
	count = get_twists_count(controls, 'l_leg')
	for i in range(1, count+1):
		if 'l_arm_twist_%s' %i in controls:
			cmds.orientConstraint('l_leg_root_twist_%s_joint' %i, ns+":"+controls["l_leg_twist_%s" %i][0], mo=1)
			cmds.orientConstraint('r_leg_root_twist_%s_joint' %i, ns+":"+controls["r_leg_twist_%s" %i][0], mo=1)
	
	count = get_twists_count(controls, 'l_knee')
	for i in range(1, count+1):
		if 'l_arm_twist_%s' %i in controls:
			cmds.orientConstraint('l_leg_middle_twist_%s_joint' %i, ns+":"+controls["l_knee_twist_%s" %i][0], mo=1)
			cmds.orientConstraint('r_leg_middle_twist_%s_joint' %i, ns+":"+controls["r_knee_twist_%s" %i][0], mo=1)
	

	# align fingers
	for i in range(1, 6):
		elem = 1
		for j in range(1, 5):
			if 'l_finger_%s_%s' %(i,j) in controls:
				cmds.parentConstraint('l_hand_chain_%s_element_%s_joint' %(i,elem), ns+":"+controls['l_finger_%s_%s' %(i,j)][0], mo=1)
				elem += 1	
	for i in range(1, 6):
		elem = 1
		for j in range(1, 5):
			if 'r_finger_%s_%s' %(i,j) in controls:
				cmds.parentConstraint('r_hand_chain_%s_element_%s_joint' %(i,elem), ns+":"+controls['r_finger_%s_%s' %(i,j)][0], mo=1)
				elem += 1	

	cmds.parentConstraint('spine_root_joint', ns+':'+controls["pelvis"][0], mo=1)
	cmds.parentConstraint('neck_root_joint', ns+':'+controls["neck"][0], mo=1)
	cmds.parentConstraint('head_root_joint', ns+':'+controls["head"][0], mo=1)
	
	cmds.parentConstraint('l_leg_root_joint', ns+':'+controls["l_leg"][0], mo=1)
	cmds.parentConstraint('l_leg_middle_joint', ns+':'+controls["l_knee"][0], mo=1)
	cmds.parentConstraint('l_foot_root_joint', ns+':'+controls["l_foot"][0], mo=1)
	cmds.parentConstraint('l_foot_toe_joint', ns+':'+controls["l_toe"][0], mo=1)

	cmds.parentConstraint('l_shoulder_root_joint', ns+':'+controls["l_clavicle"][0], mo=1)
	
	if arm_twists_count:
		cmds.parentConstraint('l_arm_root_twist_0_joint', ns+':'+controls["l_arm"][0], mo=1)
	else:
		cmds.parentConstraint('l_arm_root_joint', ns+':'+controls["l_arm"][0], mo=1)
		
	cmds.parentConstraint('l_arm_middle_joint', ns+':'+controls["l_forearm"][0], mo=1)
	cmds.parentConstraint('l_hand_root_joint', ns+':'+controls["l_hand"][0], mo=1)
	
	cmds.parentConstraint('r_leg_root_joint', ns+':'+controls["r_leg"][0], mo=1)
	cmds.parentConstraint('r_leg_middle_joint', ns+':'+controls["r_knee"][0], mo=1)
	cmds.parentConstraint('r_foot_root_joint', ns+':'+controls["r_foot"][0], mo=1)
	cmds.parentConstraint('r_foot_toe_joint', ns+':'+controls["r_toe"][0], mo=1)

	cmds.parentConstraint('r_shoulder_root_joint', ns+':'+controls["r_clavicle"][0], mo=1)
	cmds.parentConstraint('r_arm_root_joint', ns+':'+controls["r_arm"][0], mo=1)
	cmds.parentConstraint('r_arm_middle_joint', ns+':'+controls["r_forearm"][0], mo=1)
	cmds.parentConstraint('r_hand_root_joint', ns+':'+controls["r_hand"][0], mo=1)
	
	if useFace:
		cmds.parentConstraint('face_jaw_joint', ns+':'+controls["jaw"][0], mo=1)
		
		cmds.parentConstraint('face_l_cheek_joint', ns+':'+controls["l_cheek"][0], mo=1)
		cmds.parentConstraint('face_l_cheekUp_joint', ns+':'+controls["l_cheekup"][0], mo=1)
		cmds.parentConstraint('face_r_cheek_joint', ns+':'+controls["r_cheek"][0], mo=1)
		cmds.parentConstraint('face_r_cheekUp_joint', ns+':'+controls["r_cheekup"][0], mo=1)
		
		cmds.parentConstraint('face_noseTip_joint', ns+':'+controls["noseTip"][0], mo=1)
		cmds.parentConstraint('face_l_nostrill_joint', ns+':'+controls["l_nostril"][0], mo=1)
		cmds.parentConstraint('face_r_nostrill_joint', ns+':'+controls["r_nostril"][0], mo=1)
		
		cmds.parentConstraint('face_t_lip_joint', ns+':'+controls["t_lip"][0], mo=1)
		cmds.parentConstraint('face_b_lip_joint', ns+':'+controls["b_lip"][0], mo=1)
		cmds.parentConstraint('face_l_t_lip_joint', ns+':'+controls["l_t_lip"][0], mo=1)
		cmds.parentConstraint('face_r_t_lip_joint', ns+':'+controls["r_t_lip"][0], mo=1)
		cmds.parentConstraint('face_l_b_lip_joint', ns+':'+controls["l_b_lip"][0], mo=1)
		cmds.parentConstraint('face_r_b_lip_joint', ns+':'+controls["r_b_lip"][0], mo=1)
		cmds.parentConstraint('face_l_lipCorner_joint', ns+':'+controls["l_lips_corner"][0], mo=1)
		cmds.parentConstraint('face_r_lipCorner_joint', ns+':'+controls["r_lips_corner"][0], mo=1)
		
		cmds.parentConstraint('face_eyes_l_joint', ns+':'+controls["l_eye"][0], mo=1)
		cmds.parentConstraint('face_eyes_r_joint', ns+':'+controls["r_eye"][0], mo=1)
		cmds.parentConstraint('face_eyelids_l_t_eyeLid_joint', ns+':'+controls["l_t_eyelid"][0], mo=1)
		cmds.parentConstraint('face_eyelids_r_t_eyeLid_joint', ns+':'+controls["r_t_eyelid"][0], mo=1)
		cmds.parentConstraint('face_eyelids_l_b_eyeLid_joint', ns+':'+controls["l_b_eyelid"][0], mo=1)
		cmds.parentConstraint('face_eyelids_r_b_eyeLid_joint', ns+':'+controls["r_b_eyelid"][0], mo=1)
		
		cmds.parentConstraint('face_l_brow_1_joint', ns+':'+controls["l_brow_1"][0], mo=1)
		cmds.parentConstraint('face_l_brow_2_joint', ns+':'+controls["l_brow_2"][0], mo=1)
		cmds.parentConstraint('face_l_brow_3_joint', ns+':'+controls["l_brow_3"][0], mo=1)
		cmds.parentConstraint('face_r_brow_1_joint', ns+':'+controls["r_brow_1"][0], mo=1)
		cmds.parentConstraint('face_r_brow_2_joint', ns+':'+controls["r_brow_2"][0], mo=1)
		cmds.parentConstraint('face_r_brow_3_joint', ns+':'+controls["r_brow_3"][0], mo=1)
		
		
	
	#cmds.parentConstraint('l_arm_root_twist_1_joint', ns+':'+controls["l_arm_twist_1"][0], mo=1)
	
	max_count = get_spine_count(controls)
	count = 1
	for i in range(1, max_count+1):
		if 'spine%s' %i in controls:
			#if i == max_count:
				#cmds.parentConstraint('spine_local_end_joint', ns+":"+controls["spine%s" %i][0], mo=1)
			#else:
			cmds.parentConstraint('spine_local_%s_joint' %i, ns+":"+controls["spine%s" %i][0], mo=1)
			count += 1
			
	# add controls
	for c in controls:
		if c.split("_")[0] == "add" and c.split("_")[1].isdigit():
			cmds.parentConstraint(controls[c][0]+"_ctrl", ns+":"+controls[c][0], mo=1)
		if c.split("_")[0] == "weapon" and c.split("_")[1].isdigit():
			cmds.parentConstraint(controls[c][0]+"_ctrl", ns+":"+controls[c][0], mo=1)

	cmds.setAttr(utils.getControlNameFromInternal("l_arm", "control")+".ikFk", 0)
	cmds.setAttr(utils.getControlNameFromInternal("r_arm", "control")+".ikFk", 0)
	cmds.setAttr(utils.getControlNameFromInternal("l_leg", "control")+".ikFk", 0)
	cmds.setAttr(utils.getControlNameFromInternal("r_leg", "control")+".ikFk", 0)

#@viewportOff
def bake(controls):
	if not cmds.objExists('modules'):
		cmds.warning("Rig is not exists")
		return
	
	p = pm.PyNode(utils.getControlNameFromInternal("spine", "pelvis"))
	if p.tx.inputs():
		cmds.warning("Bake is already done")
		return
	
	#connectJoints(controls)
	
	# retore rig pose
	root = controls["root"][0]
	
	for j in pm.listRelatives("DRV:"+root, allDescendents=1):
		target_name = j.replace("DRV", "SKELETON")
		if pm.objExists(target_name):
			j_t = pm.PyNode(target_name)
			#print j, j_t
			pm.connectAttr(j.t, j_t.t)
			pm.connectAttr(j.r, j_t.r)
			pm.disconnectAttr(j.t, j_t.t)
			pm.disconnectAttr(j.r, j_t.r)
			#pm.connectAttr(j_t.t, j.t)
			#pm.connectAttr(j_t.r, j.r)
			#pm.disconnectAttr(j_t.t, j.t)
			#pm.disconnectAttr(j_t.r, j.r)
	
	# connect controls
	cmds.parentConstraint('DRV:'+controls["pelvis"][0], utils.getControlNameFromInternal("spine", "pelvis"), mo=1)
	cmds.parentConstraint('DRV:'+controls["neck"][0], utils.getControlNameFromInternal("neck", "root"), mo=1)
	cmds.parentConstraint('DRV:'+controls["head"][0], utils.getControlNameFromInternal("head", "root"), mo=1)
	
	cmds.parentConstraint('DRV:'+controls["l_leg"][0], utils.getControlNameFromInternal("l_leg", "fk_a"), mo=1)
	cmds.orientConstraint('DRV:'+controls["l_knee"][0], utils.getControlNameFromInternal("l_leg", "fk_b"), mo=1)
	cmds.orientConstraint('DRV:'+controls["l_foot"][0], utils.getControlNameFromInternal("l_foot", "fk_heel"), mo=1)
	cmds.orientConstraint('DRV:'+controls["l_toe"][0], utils.getControlNameFromInternal("l_foot", "fk_toe"), mo=1)
	cmds.parentConstraint('DRV:'+controls["l_foot"][0], utils.getControlNameFromInternal("l_foot", "ik_foot"), mo=1)
	
	cmds.parentConstraint('DRV:'+controls["l_clavicle"][0], utils.getControlNameFromInternal("l_shoulder", "root"), mo=1)
	cmds.parentConstraint('DRV:'+controls["l_arm"][0], utils.getControlNameFromInternal("l_arm", "fk_a"), mo=1)
	cmds.orientConstraint('DRV:'+controls["l_forearm"][0], utils.getControlNameFromInternal("l_arm", "fk_b"), mo=1)
	cmds.orientConstraint('DRV:'+controls["l_hand"][0], utils.getControlNameFromInternal("l_arm", "fk_end"), mo=1)
	cmds.parentConstraint('DRV:'+controls["l_hand"][0], utils.getControlNameFromInternal("l_arm", "ik_end"), mo=1)
	
	cmds.parentConstraint('DRV:'+controls["r_leg"][0], utils.getControlNameFromInternal("r_leg", "fk_a"), mo=1)
	cmds.orientConstraint('DRV:'+controls["r_knee"][0], utils.getControlNameFromInternal("r_leg", "fk_b"), mo=1)
	cmds.orientConstraint('DRV:'+controls["r_foot"][0], utils.getControlNameFromInternal("r_foot", "fk_heel"), mo=1)
	cmds.orientConstraint('DRV:'+controls["r_toe"][0], utils.getControlNameFromInternal("r_foot", "fk_toe"), mo=1)
	cmds.parentConstraint('DRV:'+controls["r_foot"][0], utils.getControlNameFromInternal("r_foot", "ik_foot"), mo=1)
	
	cmds.parentConstraint('DRV:'+controls["r_clavicle"][0], utils.getControlNameFromInternal("r_shoulder", "root"), mo=1)
	cmds.parentConstraint('DRV:'+controls["r_arm"][0], utils.getControlNameFromInternal("r_arm", "fk_a"), mo=1)
	cmds.orientConstraint('DRV:'+controls["r_forearm"][0], utils.getControlNameFromInternal("r_arm", "fk_b"), mo=1)
	cmds.orientConstraint('DRV:'+controls["r_hand"][0], utils.getControlNameFromInternal("r_arm", "fk_end"), mo=1)
	cmds.parentConstraint('DRV:'+controls["r_hand"][0], utils.getControlNameFromInternal("r_arm", "ik_end"), mo=1)
	
	# fingers
	for i in range(1, 6):
		elem = 1
		for j in range(1, 5):
			if 'l_finger_%s_%s' %(i,j) in controls:
				cmds.parentConstraint('DRV:'+controls['l_finger_%s_%s' %(i,j)][0], 'l_hand_finger_%s_%s_ctrl' %(i,elem), mo=1)
				elem += 1	
	for i in range(1, 6):
		elem = 1
		for j in range(1, 5):
			if 'r_finger_%s_%s' %(i,j) in controls:
				cmds.parentConstraint('DRV:'+controls['r_finger_%s_%s' %(i,j)][0], 'r_hand_finger_%s_%s_ctrl' %(i,elem), mo=1)
				elem += 1	
				
	# add controls
	for c in controls:
		if c.split("_")[0] == "add" and c.split("_")[1].isdigit():
			cmds.parentConstraint('DRV:'+controls[c][0], controls[c][0]+"_ctrl", mo=1)				


	def connectVectorSystem(j0, j1, j2, ctrl, sym=False):
		j0 = 'DRV:' + j0
		j1 = 'DRV:' + j1
		j2 = 'DRV:' + j2
		# make offset vector system
		loc1 = cmds.spaceLocator()[0]
		cmds.pointConstraint(j0, j2, loc1, mo=0)
		loc2 = cmds.spaceLocator()[0]
		cmds.parent(loc1, j1)
		cmds.parent(loc2, loc1)
		utils.resetAttrs(loc2)
		cmds.aimConstraint(j1, loc1, mo=0)
		cmds.pointConstraint(j1, loc2, mo=0)
		loc3 = cmds.spaceLocator()[0]
		cmds.parent(loc3, loc2)
		utils.resetAttrs(loc3)
		cmds.setAttr(loc3+".tx", 20)
	
		# connect vector control to system		
		print 555, ctrl
		con_ = cmds.pointConstraint(loc3, ctrl, mo=0)[0]
	
	connectVectorSystem(controls["l_leg"][0], controls["l_knee"][0], controls["l_foot"][0], utils.getControlNameFromInternal("l_leg", "ik_aim"))
	connectVectorSystem(controls["r_leg"][0], controls["r_knee"][0], controls["r_foot"][0], utils.getControlNameFromInternal("r_leg", "ik_aim"))
	connectVectorSystem(controls["l_arm"][0], controls["l_forearm"][0], controls["l_hand"][0], utils.getControlNameFromInternal("l_arm", "ik_aim"))
	connectVectorSystem(controls["r_arm"][0], controls["r_forearm"][0], controls["r_hand"][0], utils.getControlNameFromInternal("r_arm", "ik_aim"))

	
	# retore anim pose
	for j in pm.listRelatives("ORIGINAL:"+root, allDescendents=1):
		target_name = j.name().replace("ORIGINAL", "DRV")
		if pm.objExists(target_name):
			j_t = pm.PyNode(target_name)
			pm.connectAttr(j.t, j_t.t)
			pm.connectAttr(j.r, j_t.r)
			
	cmds.select('controlSet')
	mel.eval("string $minTime = `playbackOptions -q -minTime`;")
	mel.eval("string $maxTime = `playbackOptions -q -maxTime`;")
	mel.eval('string $range = $minTime + ":" + $maxTime;')
	mel.eval('bakeResults -simulation true -t $range  -sampleBy 1 -disableImplicitControl true -preserveOutsideKeys false -sparseAnimCurveBake false -removeBakedAttributeFromLayer false -bakeOnOverrideLayer false -minimizeRotation true -at "tx" -at "ty" -at "tz" -at "rx" -at "ry" -at "rz";')			


	pm.delete("ORIGINAL:"+root, "DRV:"+root)
	cmds.namespace( removeNamespace=ns, mergeNamespaceWithRoot=1 )	
	cmds.namespace( removeNamespace="ORIGINAL", mergeNamespaceWithRoot=1 )	
	cmds.namespace( removeNamespace="DRV", mergeNamespaceWithRoot=1 )	
	
	
def export(controls):
	if not cmds.objExists('modules'):
		cmds.warning("Export is already done")
		return
	
	root = controls["root"][0]
	
	cmds.select(root)
	mel.eval("string $minTime = `playbackOptions -q -minTime`;")
	mel.eval("string $maxTime = `playbackOptions -q -maxTime`;")
	mel.eval('string $range = $minTime + ":" + $maxTime;')
	mel.eval('bakeResults -simulation true -t $range -hierarchy below -sampleBy 1 -disableImplicitControl true -preserveOutsideKeys false -sparseAnimCurveBake false -removeBakedAttributeFromLayer false -bakeOnOverrideLayer false -minimizeRotation true -at "tx" -at "ty" -at "tz" -at "rx" -at "ry" -at "rz";')			

	cmds.delete("main")
	
	print "Done"
	
def set_path():
	global path
	path = cmds.file(q=True, sn=True)
	
'''