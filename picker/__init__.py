import sys, os
import maya.mel as mel

# load mel script
root_path = os.path.dirname(os.path.abspath(__file__))[:-6] + "animTools"
reset_script_file = os.path.join(root_path, "resetToDefaultValues.mel")
cmd = 'source "%s"' %(reset_script_file.replace("\\", "/"))
mel.eval(cmd)


if sys.version[0] == "2":
	import main, data_handler
	reload(main)
	reload(data_handler)
	
else:
	import importlib
	import rigStudio_picker.picker.main as main
	import rigStudio_picker.picker.data_handler as data_handler	
	importlib.reload(main)
	importlib.reload(data_handler)
