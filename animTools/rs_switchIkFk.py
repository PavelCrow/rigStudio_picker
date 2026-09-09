# Совместимость: rs_switchIkFk слит с switchIkFk.
#
# Раньше это были два почти одинаковых модуля - старые персонажи (Bear и те,
# что на _outJoint/initScale*_mult) были настроены в сценах на rs_switchIkFk,
# новые на switchIkFk. Реализация теперь одна, в switchIkFk.py, и различия
# поколений ригов определяются в момент вызова (см. getModuleName,
# getModuleScale, getControlNameFromInternal, isReversedAttr).
#
# Файл оставлен, потому что item-скрипты внутри Maya-сцен импортируют модуль
# по имени, и переделывать сцены не нужно:
#     import rigStudio_picker.animTools.rs_switchIkFk
#
# Подменяем себя в sys.modules, а не делаем "from .switchIkFk import *":
# import * скопировал бы привязки, и глобалы модуля (ns, m_name, control,
# footM_name) разъехались бы на две независимые копии. Так же обе имени
# ссылаются на ОДИН объект модуля, и importlib.reload работает корректно.

import sys

try:
	from . import switchIkFk as _impl
except (ImportError, ValueError):
	import rigStudio_picker.animTools.switchIkFk as _impl

sys.modules[__name__] = _impl
