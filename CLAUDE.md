# rigStudio_picker

Пикер контролов рига для Autodesk Maya. Аниматор видит интерактивную картинку
персонажа с кнопками-полигонами и кликами выбирает контролы рига. Работает в двух
режимах: **анимация** (только выбор) и **редактирование** (создание/расстановка кнопок).
UI на PySide (PySide2/PySide6 с фолбэками на Qt.py), интеграция через
`maya.cmds` / `pymel` / `OpenMaya`. Текущая версия — см. [versions.txt](versions.txt).

## Запуск (см. [install.txt](install.txt))

```python
import rigStudio_picker.picker
rigStudio_picker.picker.main.run()            # режим анимации (докируемое окно)
rigStudio_picker.picker.main.run(edit=True)   # режим редактирования (плавающее окно)
```

Модуль ставится в папку scripts Maya под именем `rigStudio_picker`. Кнопка запуска на
статус-баре создаётся из [picker_icon.py](picker_icon.py) (цепляется к `characterControlsButton`).

## Архитектура

| Файл | Роль |
|---|---|
| [picker/main.py](picker/main.py) | Всё UI и логика (~6900 строк) — ядро проекта |
| [picker/picker.py](picker/picker.py) | Класс `Picker` — модель данных (layers/tabs/items), save/load |
| [picker/data_handler.py](picker/data_handler.py) | **Заброшенный дубликат** picker.py (ещё с `unicode`, Python 2). Похоже, не используется — проверять при правках. |
| [picker/match_rig.py](picker/match_rig.py) | Логика "match rig" |
| [utils.py](utils.py) | Хелперы: атрибуты, зеркалирование, mirror_loc |
| [picker_icon.py](picker_icon.py) | Кнопка запуска на статус-баре Maya |
| [animTools/](animTools/) | Скрипты аниматора: switch IK/FK, change parent, keep pos |

### Ключевые классы в main.py
- `MyDockingUI` — главное окно (строка ~3965). `__init_2` — реальная инициализация.
- `GraphicViewWidget` — вьюпорт одной вкладки (QGraphicsView).
- `PickerItem` / `Polygon` / `PointHandle` — кнопки/полигоны/ручки (QGraphicsObject).
- `ContextMenuTabWidget` — вкладки одного персонажа.
- `OrderedGraphicsScene`, `GraphicText`.

### Модель данных и хранение
Данные пикера (layers → tabs → items) пиклятся (`cPickle`) в строковый атрибут `.data`
на ноде `<name>_pkrData` (тип `network`) **прямо внутри Maya-сцены** → пикер едет вместе
с ригом/референсом. Функции `pyToAttr` / `attrToPy` в [picker/picker.py](picker/picker.py).
JSON-экспорт/импорт лежит в [picker/pickers/](picker/pickers/).

Соглашение имён нод: `<namespace>:<basename>_pkrData`, где `<basename>` **может быть
разным** (`picker`, `root_picker`, вариант с оверрайдом `pickerOver`, ...). Не хардкодить
`"picker"` как базовое имя! Ключи `self.pickers` — это `<node>` без суффикса `_pkrData`
(напр. `temp1:root_picker`). Пункты комбобокса добавляются как `name.split(":picker")[0]`.
См. `get_root_name` / `get_picker_names`.

Авто-переключение персонажа по выделенному контролу ([selectionUpdateEvent](picker/main.py#L4211))
находит пикер по **неймспейсу** выделенного контрола (`sel.rpartition(":")[0]`), сопоставляя
его с неймспейсами загруженных пикеров в `self.pickers` — независимо от базового имени пикера.
Тумблер вкл/выкл — `autoLoadPicker_btn` на тулбаре.

## Загрузка пикеров — как это работает (важно для производительности)

- [update_selector()](picker/main.py#L4791) — точка сборки: находит все picker-ноды в
  сцене, наполняет комбобокс персонажей (`char_selector_cb`) и `QStackedWidget`
  (по одному контейнеру на персонажа).
- **Ленивое построение** (сделано ради скорости при многих персонажах): в цикле
  `update_selector` создаётся только пустой контейнер. Реальная загрузка данных
  (`p.load()`) и построение всех view/items ([load_picker_orig](picker/main.py#L5034) /
  `load_picker_panel`) отложены в [build_picker()](picker/main.py#L4942), который
  вызывается из [setCurrentPicker()](picker/main.py) при первом показе персонажа.
  Набор уже построенных — `self.built_pickers`. Итог: время открытия не зависит от
  числа персонажей в сцене.
- Почти весь код обращается к `self.views` / `self.tab_widgets` **по текущему пикеру**
  (`self.cur_picker.name` / `get_root_name()`), глобального перебора построенных пикеров
  нет — поэтому ленивость безопасна. Если добавляешь код, перебирающий ВСЕ пикеры,
  учитывай, что непоказанные ещё не построены.
- Режимы отображения: `panels_mode` (1 = вкладки/`load_picker_orig`, 2/3 =
  панели-сплиттеры/`load_picker_panel`).

### События Maya (в `__init_2`)
`SelectionChanged` → `selectionUpdateEvent` (автопереключение персонажа по выделенному
контролу + подсветка item'ов); `NewSceneOpened`/`SceneOpened` и load/unload/create/remove
reference → `reloadPickers`. `reloadPickers(reload=False)` только пересобирает селектор
при изменении набора нод; `reload=True` — полный перезапуск через `run()`.

## Разработка

- **Нельзя запускать/тестировать вне Maya** (импортит `maya.cmds`, `pymel`, `OpenMaya`).
  Проверка синтаксиса без исполнения:
  `python -c "import ast; ast.parse(open('picker/main.py',encoding='utf-8').read())"`.
  Функционально — только вручную в Maya.
- **Отступы — табы** (не пробелы). Держать консистентно.
- Диагностика IDE про неразрешимые импорты `maya.*` / `pymel` / `imp` — ожидаема, игнор.
- Поддержка Python 2 и 3 + PySide2/PySide6 идёт через ветки `if sys.version[0]=="2"` и
  `try/except` на импортах. Новый код должен работать под обеими версиями PySide.
- В конце `run()` ([main.py](picker/main.py#L6859)) есть недостижимый код после `return` —
  мёртвый, не трогать без нужды.
- В репозитории много мёртвого кода и папок `_old/` — при правках ориентироваться на
  актуальные пути, а не на копии.

## Публикация
Версии описываются в [versions.txt](versions.txt) (последний блок `--- Version X ---`);
`get_version()` парсит именно оттуда. Коммиты — по версиям ("Version 1.0.7 - 3").
