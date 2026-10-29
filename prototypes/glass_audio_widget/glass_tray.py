from PySide6.QtGui import QAction, QFontMetrics
from PySide6.QtCore import Qt
from tray import TrayController


class GlassTray(TrayController):
    def __init__(self,view,audio,media,**kwargs):
        super().__init__(view,audio,media,**kwargs)
        self.connection_action=QAction("등록 장치 연결",self.menu)
        self.menu.insertAction(self.mute_action,self.connection_action)
        self.connection_action.triggered.connect(view.devices.connectDevice)
        self.settings_action.setText("위젯 설정")
        view.devices.changed.connect(self.sync)
        self.sync()

    def sync(self):
        super().sync()
        if not hasattr(self,"connection_action"): return
        state=self.view.devices.state
        label="연결 중…" if state["pending"] else "연결됨" if state["connected"] else "연결"
        name=state["name"] or "등록 장치"
        self.connection_action.setText(QFontMetrics(self.menu.font()).elidedText(name+" · "+label,Qt.ElideRight,300))
        self.connection_action.setEnabled(state["paired"] and not state["pending"] and not state["connected"])
        self.connection_action.setToolTip(state["error"] or state["status"])
