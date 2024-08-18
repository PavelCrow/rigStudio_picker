def incrementName(name):
	suffix = name.split('_')[-1]
	rootName = name[:-len(suffix)-1]
	if suffix.isdigit():
		name = rootName + '_' + str( int(suffix) + 1 )
	else:
		name += '_1'
	return name
