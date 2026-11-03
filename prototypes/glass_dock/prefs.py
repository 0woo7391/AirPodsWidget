"""Dock settings: one place for every key, its default, and a change signal.

The dock, the island, the features and the settings window all read and write
through DockPrefs, so a change made anywhere applies everywhere at once.
"""
from __future__ import annotations

import json

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot
from PySide6.QtGui import QGuiApplication

MODULES = ["airpods", "media", "volume", "output", "launcher", "clock", "memo", "mic", "mixer", "system"]
MODULE_NAMES = {"airpods": "AirPods", "media": "미디어", "volume": "볼륨", "output": "출력 장치",
                "launcher": "빠른 실행", "clock": "시계", "memo": "메모", "mic": "마이크",
                "mixer": "앱별 볼륨", "system": "시스템"}
# Sizes each module comes in: "half" pairs with a neighbouring half card, "full" spans the dock.
# The first is the default.
MODULE_SIZES = {"airpods": ["full"], "media": ["full"], "volume": ["half"], "output": ["half"],
                "launcher": ["full"], "clock": ["half", "full"], "memo": ["full"], "mic": ["half"],
                "mixer": ["full", "half"], "system": ["half"]}
# Shown until the user edits the dock; the rest wait in the edit mode's gallery.
DEFAULT_VISIBLE = ["airpods", "media", "volume", "output", "launcher"]

DEFAULTS = {
    # Dock: "auto" screen is the outermost one on the chosen edge, so the dock never
    # sits on the seam between two monitors.
    "dock/screen": "auto", "dock/edge": "right", "dock/position": 0.5,
    # Line the dock up with the desktop icon grid, "dock/columns" icon cells wide.
    "dock/grid": True, "dock/columns": 3, "dock/minimized": False, "dock/alwaysOnTop": False,
    "dock/modules": json.dumps([{"id": m, "visible": m in DEFAULT_VISIBLE} for m in MODULES]),
    "memo/text": "",
    # Island: primary | dock | all | cursor | <screen name>
    "island/screens": "primary", "island/align": "center", "island/offset": 0, "island/scale": 1.0,
    "island/connect": True, "island/disconnect": True, "island/lowBattery": True,
    "island/suppressDuringGames": True, "island/mic": True,
    "battery/threshold": 20, "battery/sound": True, "battery/soundVolume": 60, "battery/soundDuringGames": True,
    "media/autoPause": True, "media/autoResume": False, "media/followAny": True,
    "system/startWithWindows": False,
}


def screens_in_order() -> list:
    """Screens left to right (then top to bottom), the order people number them by."""
    return sorted(QGuiApplication.screens(), key=lambda s: (s.geometry().x(), s.geometry().y()))


def screen_info(screen, index: int) -> dict:
    g = screen.geometry()
    model = (screen.model() or screen.manufacturer() or "").strip()
    return dict(name=screen.name(), number=index + 1, model=model, x=g.x(), y=g.y(), width=g.width(),
                height=g.height(), primary=screen is QGuiApplication.primaryScreen(),
                label=f"{index + 1} · {model}" if model else f"화면 {index + 1}")


class DockPrefs(QObject):
    changed = Signal(str)
    modulesChanged = Signal()
    screensChanged = Signal()

    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        app = QGuiApplication.instance()
        if isinstance(app, QGuiApplication):
            for signal in (app.screenAdded, app.screenRemoved, app.primaryScreenChanged):
                signal.connect(lambda *_: self.screensChanged.emit())
            for screen in app.screens():
                screen.geometryChanged.connect(lambda *_: self.screensChanged.emit())
            app.screenAdded.connect(lambda s: s.geometryChanged.connect(lambda *_: self.screensChanged.emit()))

    @Slot(str, result="QVariant")
    def get(self, key):
        default = DEFAULTS[key]
        return self.settings.value(key, default, type=type(default))

    @Slot(str, "QVariant")
    def set(self, key, value):
        default = DEFAULTS[key]
        value = type(default)(value)
        if value == self.get(key):
            return
        self.settings.setValue(key, value)
        self.changed.emit(key)
        if key == "dock/modules":
            self.modulesChanged.emit()

    @Property("QVariantList", notify=modulesChanged)
    def modules(self):
        """[{id, name, visible, size, sizes}] in dock order; unknown ids dropped, new modules
        appended hidden (they wait in the gallery), sizes kept to the ones a module has."""
        try:
            saved = json.loads(self.get("dock/modules"))
        except (ValueError, TypeError):
            saved = []
        order, seen = [], set()
        for item in saved if isinstance(saved, list) else []:
            if isinstance(item, dict) and item.get("id") in MODULES and item["id"] not in seen:
                seen.add(item["id"])
                sizes = MODULE_SIZES[item["id"]]
                order.append(dict(id=item["id"], visible=bool(item.get("visible", True)),
                                  size=item.get("size") if item.get("size") in sizes else sizes[0]))
        order += [dict(id=m, visible=False, size=MODULE_SIZES[m][0]) for m in MODULES if m not in seen]
        return [dict(item, name=MODULE_NAMES[item["id"]], sizes=MODULE_SIZES[item["id"]]) for item in order]

    @Slot(str, int)
    def moveModule(self, module_id, step):
        modules = self.modules
        index = next(i for i, m in enumerate(modules) if m["id"] == module_id)
        self.moveModuleTo(module_id, index + step)

    @Slot(str, int)
    def moveModuleTo(self, module_id, index):
        """Put a module at `index` of the full list (hidden ones included)."""
        modules = self.modules
        current = next(i for i, m in enumerate(modules) if m["id"] == module_id)
        modules.insert(max(0, min(len(modules) - 1, index)), modules.pop(current))
        self._save_modules(modules)

    @Slot(str, bool)
    def setModuleVisible(self, module_id, visible):
        modules = self.modules
        for module in modules:
            if module["id"] == module_id:
                module["visible"] = visible
        if any(m["visible"] for m in modules):  # an empty dock would be impossible to find again
            self._save_modules(modules)

    @Slot(str, str)
    def addModule(self, module_id, size):
        """Show a module from the gallery, after the last visible one, in the chosen size."""
        modules = self.modules
        module = next(m for m in modules if m["id"] == module_id)
        modules.remove(module)
        module.update(visible=True, size=size if size in module["sizes"] else module["sizes"][0])
        last = max((i for i, m in enumerate(modules) if m["visible"]), default=-1)
        modules.insert(last + 1, module)
        self._save_modules(modules)

    @Slot(str, str)
    def setModuleSize(self, module_id, size):
        modules = self.modules
        for module in modules:
            if module["id"] == module_id and size in module["sizes"]:
                module["size"] = size
        self._save_modules(modules)

    def _save_modules(self, modules):
        self.set("dock/modules", json.dumps([dict(id=m["id"], visible=m["visible"], size=m["size"]) for m in modules]))

    @Property("QVariantList", notify=screensChanged)
    def screens(self):
        return [screen_info(s, i) for i, s in enumerate(screens_in_order())]

    def screen_named(self, name):
        return next((s for s in QGuiApplication.screens() if s.name() == name), None)

    def dock_screen(self):
        """The chosen screen, or the outermost one on the chosen edge."""
        chosen = self.get("dock/screen")
        screen = self.screen_named(chosen) if chosen != "auto" else None
        if screen is not None:
            return screen
        ordered = screens_in_order()
        if not ordered:
            return QGuiApplication.primaryScreen()
        if self.get("dock/edge") == "left":
            return min(ordered, key=lambda s: s.geometry().left())
        return max(ordered, key=lambda s: s.geometry().right())

    def island_screens(self) -> list:
        choice = self.get("island/screens")
        primary = QGuiApplication.primaryScreen()
        if choice == "all":
            return list(QGuiApplication.screens())
        if choice == "dock":
            return [self.dock_screen()]
        if choice == "cursor":
            from PySide6.QtGui import QCursor
            return [QGuiApplication.screenAt(QCursor.pos()) or primary]
        if choice not in ("primary", ""):
            named = self.screen_named(choice)
            if named is not None:
                return [named]
        return [primary]
