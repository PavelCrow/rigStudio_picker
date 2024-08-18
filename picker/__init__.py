import sys 

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
