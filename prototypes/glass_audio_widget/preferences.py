"""Saved widget-only appearance and span-aware module placement."""
import json

from PySide6.QtCore import QObject, Property, Signal, Slot, QSettings, QTimer

LAYOUTS = (("media","volume","battery"),("volume","media","battery"),
           ("battery","media","volume"),("battery","volume","media"))


class Preferences(QObject):
    changed = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._reduced = settings.value("appearance/reduced_motion", False, type=bool)
        try:
            self._tint = max(.05, min(.45, float(settings.value("appearance/tint", .17))))
        except (TypeError, ValueError): self._tint = .17
        try: self._readability=max(.45,min(.80,float(settings.value("appearance/readability",.64))))
        except (TypeError,ValueError): self._readability=.64
        try: self._blur=max(0,min(8,float(settings.value("appearance/blur",4))))
        except (TypeError,ValueError): self._blur=4
        try:
            layout = tuple(json.loads(settings.value("modules/order", '["media","volume","battery"]')))
        except (ValueError, TypeError): layout = ()
        self._order = layout if layout in LAYOUTS else LAYOUTS[0]
        self._error = ""
        self._saved_tint = self._tint
        self._saved_readability=self._readability
        self._saved_blur=self._blur
        self._tint_timer = QTimer(self)
        self._tint_timer.setSingleShot(True); self._tint_timer.setInterval(200)
        self._tint_timer.timeout.connect(self.flush)

    @Property(bool, notify=changed)
    def reducedMotion(self): return self._reduced

    @Property(float, notify=changed)
    def tint(self): return self._tint

    @Property(float, notify=changed)
    def readability(self): return self._readability

    @Property(float, notify=changed)
    def blur(self): return self._blur

    @Property("QVariantList", notify=changed)
    def order(self): return list(self._order)

    @Property(str, notify=changed)
    def error(self): return self._error

    def _save(self, key, value):
        previous = self.settings.value(key, None)
        self.settings.setValue(key,value); self.settings.sync()
        if self.settings.status() == QSettings.NoError:
            self._error = ""; return True
        if previous is None: self.settings.remove(key)
        else: self.settings.setValue(key,previous)
        self.settings.sync()
        self._error = "설정을 저장하지 못함 · 기존 값 유지"
        self.changed.emit(); return False

    @Slot(bool)
    def setReducedMotion(self,value):
        if self._save("appearance/reduced_motion",value): self._reduced=value; self.changed.emit()

    @Slot(float)
    def setTint(self,value):
        if not .05<=value<=.45: return
        self._tint=value; self.changed.emit(); self._tint_timer.start()

    @Slot(float)
    def setReadability(self,value):
        if not .45<=value<=.80: return
        self._readability=value; self.changed.emit(); self._tint_timer.start()

    @Slot(float)
    def setBlur(self,value):
        if not 0<=value<=8: return
        self._blur=value; self.changed.emit(); self._tint_timer.start()

    @Slot()
    def flush(self):
        self._tint_timer.stop()
        for name in ("tint","readability","blur"):
            value=getattr(self,"_"+name); saved=getattr(self,"_saved_"+name)
            if value==saved: continue
            if self._save("appearance/"+name,value): setattr(self,"_saved_"+name,value)
            else: setattr(self,"_"+name,saved); self.changed.emit()

    @Slot(str,str,result=bool)
    def moveModule(self,source,target):
        if source not in self._order or target not in self._order or source==target: return False
        battery_first = self._order[0]=="battery"
        volume_first = self._order.index("volume")<self._order.index("media")
        if "battery" in (source,target): battery_first=not battery_first
        else: volume_first=not volume_first
        pair=("volume","media") if volume_first else ("media","volume")
        order=("battery",)+pair if battery_first else pair+("battery",)
        if not self._save("modules/order",json.dumps(order)): return False
        self._order=order; self.changed.emit(); return True
