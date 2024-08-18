# Change switch attribute "parent" with store position
#
# select control with "parent" attribute and run in python:
# import pk_changeParent
# reload(pk_changeParent)
# pk_changeParent.run()
#
# Pavel Korolyov
# pavel.crow@gmail.com


import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om
import math


def changeOfParent(o, makeKeys=False, value=None):
	# Get transform
	m = cmds.xform(o, q=1, matrix=1, ws=1)

	# get size of parent attribute enum
	list = mel.eval('attributeQuery -node %s -listEnum "parent"' %o)
	size = len(list[0].split(":"))

	# get current parent
	currParentId = cmds.getAttr(o+".parent")

	enum_string = cmds.attributeQuery("parent", node=o, listEnum=True)[0].split(":")

	# next parent
	if value in enum_string:
		index = enum_string.index(value)
		nextParentId = index
	else:
		nextParentId = int(currParentId) + 1
		if nextParentId >= size:
			nextParentId = 0

	# set next parent
	cmds.setAttr(o+".parent", nextParentId)

	# Set Transform
	cmds.xform(o, matrix=m, ws=1)

	if makeKeys:
		cmds.setKeyframe(o+'.t')
		cmds.setKeyframe(o+'.r')
		cmds.setKeyframe(o+'.parent')


def run(makeKeys=False, value=None):
	sel = cmds.ls(sl=True)

	if len(sel) == 0:
		print ("select control with parent attribute")
		return

	for o in sel:
		if not cmds.attributeQuery( 'parent', node=o, exists=True ):
			print ("control", o, "has not parent attribute")
			return		

		changeOfParent(o, makeKeys, value)


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


def animation_run(value):
	sel = cmds.ls(sl=True)

	if len(sel) == 0:
		print ("select control with parent attribute")
		return

	cmds.undoInfo(openChunk=True)

	for o in sel:
		if not cmds.attributeQuery( 'parent', node=o, exists=True ):
			print ("control", o, "has not parent attribute")
			return		

		enum_string = cmds.attributeQuery("parent", node=o, listEnum=True)[0].split(":")
		if value in enum_string:
			index = enum_string.index(value)
			id = index

		keys = cmds.keyframe(o, q=1) or []

		if len(keys) == 0:
			cmds.warning("object has not animation")
			continue

		keys_filtered = []
		for k in keys:
			if k not in keys_filtered:
				keys_filtered.append(k)

		keys_filtered = sorted(keys_filtered)

		for k in keys_filtered:
			cmds.currentTime(k)
			cmds.setKeyframe(o+'.t')
			cmds.setKeyframe(o+'.r')
			cmds.setKeyframe(o+'.parent')

		for k in keys_filtered:    
			cmds.currentTime(k)

			currParentId = cmds.getAttr(o+".parent")

			attrs = getVisibleAttrs(o)

			if  0.01 > cmds.getAttr(o+'.rotatePivotX') + cmds.getAttr(o+'.rotatePivotY') + cmds.getAttr(o+'.rotatePivotZ') > -0.01:
				#print ("by matrix")
				#cmds.setAttr(o+".parent", currParentId)

				m = cmds.xform(o, q=1, matrix=1, ws=1)
				cmds.setAttr(o+".parent", id)
				cmds.xform(o, matrix=m, ws=1)

				cmds.setKeyframe(o+'.parent')

			elif 'translateX' in attrs and 'translateY' in attrs and 'translateZ' in attrs and 'rotateX' in attrs and 'rotateY' in attrs and 'rotateZ' in attrs and 'parent' in attrs:
				#print ("by constraint")

				l = cmds.spaceLocator()
				c = cmds.parentConstraint(o,l,mo=0)
				cmds.delete(c)
				cmds.setAttr(o+".parent", int(id))
				c = cmds.parentConstraint(l,o,mo=0)
				cmds.setKeyframe(o+'.parent')
				cmds.setKeyframe(o+'.t')
				cmds.setKeyframe(o+'.r')

				cmds.delete(l)

			else:
				cmds.warning("Translate or rotate attributes is not keyable")
				continue

	cmds.select(sel)			

	cmds.undoInfo(closeChunk=True)