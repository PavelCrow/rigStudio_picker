import maya.cmds as cmds
import shutil
import os, imp, subprocess

def run(clearPy=False):
    result = cmds.confirmDialog( title='Confirm', message='Export RS Picker to archive?', button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
    if result == "No":
        return
    
    fileName = __name__.split('.')[0] 								#rigStudio_picker
    picker_folder = os.path.abspath(imp.find_module(fileName)[1])	 	#'C:\Users\Pavel\Dropbox\mayaScripts/rigStudio'
    
    # get version
    with open(picker_folder+'/versions.txt') as f:
        lines = f.readlines()
    versions = []
    for l in lines:
        if '---' in l:
            versions.append(l)
    lastVestion = versions[-1].split('---')[1]
    num = lastVestion.split(" ")[1]
    
    # archive full file
    out_folder = os.path.join(picker_folder.split("mayaScripts")[0], "Public", "rs_picker" )
    
    picker_copy_folder = out_folder+"/out/rigStudio_picker"
    os.makedirs(picker_copy_folder)
    
    # Duplicate folder
    def copytree(src, dst, symlinks=False, ignore=None):
        if not os.path.exists(dst):
            os.makedirs(dst)    
    
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)
    
    copytree(picker_folder, picker_copy_folder)    
    
    shutil.rmtree(picker_copy_folder+"/.hg")
    shutil.rmtree(picker_copy_folder+"/.idea")
    os.remove(picker_copy_folder+'/.hgignore')    
    os.remove(picker_copy_folder+'/picker.wpr')    
    os.remove(picker_copy_folder+'/picker.wpu')    
    
    out_file = os.path.join(out_folder, 'rs_picker_'+num)
    shutil.make_archive(out_file, 'zip', out_folder+"/out")
    shutil.rmtree(out_folder+"/out")
    
    subprocess.Popen('explorer "%s"' %out_folder)
    
    print ("Export Done")