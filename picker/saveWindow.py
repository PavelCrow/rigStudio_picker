# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Pavel\Dropbox\mayaScripts\rigStudio2\picker\saveWindow.ui'
#
# Created: Sat May 15 07:29:13 2021
#      by: pyside2-uic  running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

try:
    from PySide2 import QtWidgets, QtGui, QtCore
except:
    from Qt import QtWidgets, QtGui, QtCore

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(240, 96)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.lineEdit = QtWidgets.QLineEdit(Dialog)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout_2.addWidget(self.lineEdit)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.asNode_btn = QtWidgets.QRadioButton(Dialog)
        self.asNode_btn.setChecked(True)
        self.asNode_btn.setObjectName("asNode_btn")
        self.horizontalLayout.addWidget(self.asNode_btn)
        self.asFile_btn = QtWidgets.QRadioButton(Dialog)
        self.asFile_btn.setChecked(False)
        self.asFile_btn.setObjectName("asFile_btn")
        self.horizontalLayout.addWidget(self.asFile_btn)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.ok_btn = QtWidgets.QPushButton(Dialog)
        self.ok_btn.setObjectName("ok_btn")
        self.horizontalLayout_3.addWidget(self.ok_btn)
        self.cancel_btn = QtWidgets.QPushButton(Dialog)
        self.cancel_btn.setObjectName("cancel_btn")
        self.horizontalLayout_3.addWidget(self.cancel_btn)
        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtWidgets.QApplication.translate("Dialog", "Save As", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("Dialog", "Name", None, -1))
        self.asNode_btn.setText(QtWidgets.QApplication.translate("Dialog", "As Node", None, -1))
        self.asFile_btn.setText(QtWidgets.QApplication.translate("Dialog", "As File", None, -1))
        self.ok_btn.setText(QtWidgets.QApplication.translate("Dialog", "Ok", None, -1))
        self.cancel_btn.setText(QtWidgets.QApplication.translate("Dialog", "Cancel", None, -1))

