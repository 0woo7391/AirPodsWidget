"""Own native window/QtTest, fake audio/media, temporary preferences only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from PySide6.QtCore import QObject, Property, Signal, Slot, QEventLoop, QTimer, QSettings, QUrl, Qt, QPoint, QPointF, QRectF, QMetaObject
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from widget import BASE, GlassWidget


def wait(ms):
    loop = QEventLoop(); QTimer.singleShot(ms, loop.quit); loop.exec()


class FakeAudio(QObject):
    changed = Signal()
    devicesChanged = Signal()
    def __init__(self):
        super().__init__()
        self.calls = []
        self.data = dict(available=True, currentId="one", name="테스트 출력", kind="speaker", volume=54,
                         muted=False, pendingId="", error="", status="")

    @Property("QVariantMap", notify=changed)
    def state(self): return dict(self.data)

    @Property("QVariantList", notify=devicesChanged)
    def devices(self): return [dict(id="one", name="테스트 출력", kind="headphones", available=True), dict(id="two", name="테스트 두 번째", kind="speaker", available=True)]

    @Property("QVariantList", notify=devicesChanged)
    def quickOutputs(self): return self.devices

    @Slot(int)
    def setVolume(self, value):
        self.calls.append(("volume", value)); self.data.update(volume=value, muted=False); self.changed.emit()

    @Slot()
    def toggleMute(self):
        self.calls.append(("mute",)); self.data["muted"] = not self.data["muted"]; self.changed.emit()

    @Slot(str)
    def selectOutput(self, key):
        self.calls.append(("select", key)); self.data["currentId"] = key; self.changed.emit()


class FakeMedia(QObject):
    changed = Signal()
    contentChanged = Signal()
    appsChanged = Signal()
    sessionsChanged = Signal()
    preferencesChanged = Signal()
    def __init__(self):
        super().__init__()
        self.calls = []
        self.data = dict(available=True, token="session-test", identity="track-one", title="검증용 트랙",
                         artist="검증용 아티스트", sourceName="test", artwork="", playing=False,
                         pending=False, error="", status="", canPlay=True, canNext=True, canPrevious=True)
        self.selection = dict(allowed=["test"], sourceId="test")
        self.catalog=[dict(id="test",name="테스트 앱",present=True)]

    @Property("QVariantMap", notify=changed)
    def state(self): return dict(self.data)

    @Property("QVariantMap", notify=contentChanged)
    def content(self): return dict(self.data)

    @Property("QVariantList", notify=appsChanged)
    def apps(self): return self.catalog

    @Property("QVariantList", notify=sessionsChanged)
    def sessions(self): return [dict(token="session-test",sourceId="test",name="테스트 앱",title=self.data["title"])]

    @Property("QVariantMap", notify=preferencesChanged)
    def preferences(self): return self.selection

    @Slot(str, str, str)
    def command(self, action, token, identity): self.calls.append((action, token, identity))

    @Slot(bool)
    def inspectSessions(self, enabled): self.calls.append(("inspect", enabled))

    @Slot("QVariantList", str, str, result=bool)
    def saveSelection(self, allowed, source, token):
        self.calls.append(("save", list(allowed), source, token)); return True


class FakeTray(QObject):
    activated=Signal(object)
    def __init__(self,parent=None): super().__init__(parent); self.visible=False
    def setIcon(self,icon): assert not icon.isNull()
    def setToolTip(self,value): pass
    def setContextMenu(self,value): pass
    def show(self): self.visible=True
    def hide(self): self.visible=False
    def isVisible(self): return self.visible


def main():
    app=QApplication([]); app.setQuitOnLastWindowClosed(False)
    QQuickStyle.setStyle("Basic")
    checks=[]; callback_errors=[]; prior=sys.excepthook
    sys.excepthook=lambda kind,value,trace: callback_errors.append(str(value))
    temp=tempfile.TemporaryDirectory()
    settings=QSettings(str(Path(temp.name)/"window.ini"),QSettings.IniFormat)
    fixture=QQuickView()
    fixture.setFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
    fixture.setSource(QUrl.fromLocalFile(str(BASE.parent/"desktop_glass_lab"/"Fixture.qml")))
    fixture.resize(640,460)
    fixture.setPosition(fixture.screen().availableGeometry().center()-QPoint(320,230))
    fixture.show()
    audio,media=FakeAudio(),FakeMedia()
    view=GlassWidget(audio,media,settings)
    view.setPosition(fixture.position()+QPoint(100,50));view.show();view.raise_()
    root=view.rootObject(); artifacts=BASE/"artifacts";artifacts.mkdir(exist_ok=True)
    scale=os.environ.get("QT_SCALE_FACTOR","1")
    def check(value,label):
        if not value: raise AssertionError(label)
        checks.append(label)
    def until(condition,label,timeout=1.5):
        deadline=time.perf_counter()+timeout
        while not condition() and time.perf_counter()<deadline: wait(15)
        check(condition(),label)
    def item(name):
        found=root.findChild(QObject,name)
        if found is None:
            pending=[view.contentItem()]
            while pending:
                node=pending.pop();pending.extend(node.childItems())
                if node.objectName()==name:found=node;break
        if found is None: raise AssertionError("Missing item "+name)
        return found
    def click(name):
        target=item(name)
        point=target.mapToScene(QPointF(target.width()/2,target.height()/2)).toPoint()
        QTest.mouseClick(view,Qt.LeftButton,Qt.NoModifier,point);wait(20)
    def visible_control(node):
        current=node
        while current:
            if not current.isVisible() or current.opacity()<.01:return False
            current=current.parentItem()
        return True
    def layout(label):
        pending=[root]; controls=[]
        while pending:
            node=pending.pop();pending.extend(node.childItems())
            if node.property("auditControl") and visible_control(node):
                rect=QRectF(node.mapToScene(QPointF()),node.size())
                controls.append((node.objectName(),rect))
                check(QRectF(0,0,440,root.property("bodyHeight")).contains(rect),label+" bounds "+node.objectName())
        for at,(name,rect) in enumerate(controls):
            for other,bounds in controls[at+1:]:
                check(not rect.intersects(bounds),label+" no overlap "+name+"/"+other)
    try:
        until(lambda:view.capture.serial>0 and not view.capture.moving,"native desktop capture ready")
        view.capture.togglePause();wait(140)
        check(not audio.calls and not media.calls,"startup sends no commands")
        check(item("glassPin").property("glyph")=="pin" and not item("glassPin").property("text"),"pin uses icon")
        check(item("glassOutput").property("glyph")=="output" and item("glassOutput").property("dropdown"),"output role distinguished from mute")
        check(item("glassMute").parentItem()==item("glassVolumeDial").parentItem(),"mute belongs to volume module")
        check(item("glassCaptureMode").window()!=view,"capture mode lives in settings")
        check(root.findChild(QObject,"quickOutput-one") is None,"duplicate footer routes removed")
        layout("expanded")
        for name in ("glassPlay","glassEditModules"):
            button=item(name);check(button.property("jellyEnabled") is None,"ordinary button "+name)
        click("glassMute")
        check(audio.data["muted"] and audio.data["volume"]==54 and item("glassMute").property("pose")=="muted"
              and item("glassMute").property("selected"),"mute keeps volume and persistent slashed/selected cue")
        click("glassMute")
        audio.data.update(volume=0,muted=False);audio.changed.emit();wait(30)
        check(not item("glassMute").property("selected") and item("glassVolumeDial").property("value")==0,"zero differs from mute")
        audio.data.update(volume=54);audio.changed.emit()
        button=item("glassEditModules")
        point=button.mapToScene(QPointF(18,18)).toPoint()
        icon=item("glassEditModules-glyph")
        bounds=QRectF(button.mapToScene(QPointF()),button.size())
        glyph_bounds=QRectF(icon.mapToScene(QPointF()),icon.size())
        QTest.mousePress(view,Qt.LeftButton,Qt.NoModifier,point);wait(35)
        check(0<button.property("pressure")<=1,"ordinary button responds on press")
        check(bounds==QRectF(button.mapToScene(QPointF()),button.size())
              and glyph_bounds==QRectF(icon.mapToScene(QPointF()),icon.size()),"hit and glyph remain fixed")
        QTest.mouseRelease(view,Qt.LeftButton,Qt.NoModifier,point)
        samples=[]
        for _ in range(15):wait(15);samples.append(button.property("pressure"))
        check(min(samples)>=0 and all(a>=b-.001 for a,b in zip(samples,samples[1:])),"button recovery has no spring overshoot")
        until(lambda:button.property("pressure")==0,"button settles")
        check(root.property("editing") and button.property("selected"),"edit has persistent selection")
        click("glassEditModules")
        click("glassOutput");until(lambda:item("glassOutputPopup").property("visible"),"output chooser opens")
        click("glassOutput-two")
        check(audio.calls[-1]==("select","two"),"output action carries endpoint")
        audio.data.update(pendingId="one");audio.changed.emit()
        check(not item("glassVolumeDial").isEnabled() and not item("glassMute").isEnabled()
              and not item("glassOutput").isEnabled(),"pending output blocks conflicting controls")
        audio.data.update(pendingId="",name="긴 출력 이름 "*20);audio.changed.emit();wait(220)
        layout("long output")
        check(item("glassDeviceName").property("width")==300,"long header reserves action space")
        audio.data.update(name="테스트 출력");audio.changed.emit()
        media.data.update(available=False,canPlay=False);media.catalog=[]
        media.changed.emit();media.contentChanged.emit();media.appsChanged.emit()
        until(lambda:item("glassChooseMedia").isVisible(),"empty media has actionable search")
        check(not item("glassPlay").isEnabled(),"unavailable media stays disabled")
        layout("no media")
        click("glassChooseMedia")
        until(lambda:item("glassSettings").property("visible"),"empty action opens separate settings")
        check(item("settingsTabs").property("currentIndex")==0,"media action selects correct tab")
        check("감지된 앱 0개" in item("mediaDetectionStatus").property("text"),"zero sessions shown honestly")
        QMetaObject.invokeMethod(item("glassSettings"),"close");wait(30)
        check(("inspect",True) in media.calls and media.calls[-1]==("inspect",False),"inspection follows settings lifetime")
        media.catalog=[dict(id="test",name="테스트 앱",present=True)]
        media.data.update(available=True,canPlay=True);media.appsChanged.emit()
        media.changed.emit();media.contentChanged.emit()
        until(lambda:not item("glassChooseMedia").isVisible(),"selected media restores player")
        wait(150);click("glassPlay")
        check(media.calls[-1]==("toggle","session-test","track-one"),"playback uses displayed identity")
        from device_backend import bluetooth_status
        records=[bluetooth_status.BluetoothDeviceStatus("등록 테스트",0xAABBCCDDEEFF,True,False)]
        view.devices._received(dict(records=records,command="",error=""))
        view.devices.selectDevice("AABBCCDDEEFF")
        notice=root.findChild(QObject,"connectionNotice")
        if notice:QMetaObject.invokeMethod(notice,"close")
        click("glassConnect")
        check(view.devices.state["pending"] and item("glassConnect").property("busy")
              and not item("glassConnect").isEnabled(),"connection pending has spinner and duplicate block")
        view.devices._received(dict(records=None,command="AABBCCDDEEFF",error="검사용 연결 실패"))
        check(item("glassConnect").property("text")=="재시도" and item("glassConnect").isEnabled(),"connection failure exposes retry")
        records[0].connected=True
        view.devices._received(dict(records=records,command="AABBCCDDEEFF",error=""))
        check(item("glassConnect").property("selected") and item("glassConnect").property("text")=="연결됨","confirmed connection static cue")
        for source,target in (("volume","media"),("battery","media"),("volume","media")):
            view.preferences.moveModule(source,target)
            until(lambda:root.property("moduleOpacity")==1 and root.property("layoutOrder")==view.preferences.order,
                  "module reorder settles")
            layout("reordered")
        view.preferences.moveModule("battery","media")
        wait(30);view.preferences.setReducedMotion(True);wait(30)
        check(root.property("moduleOpacity")==1,"reduced motion settles active reorder")
        view.preferences.setReducedMotion(False)
        # Pixel proof: local blur changes the real captured patterned scene.
        QTest.mouseMove(view,QPoint(5,290));wait(140)
        plate=item("mediaPlate")
        view.preferences.setBlur(0);wait(60);sharp=view.grabWindow()
        view.preferences.setBlur(8);wait(60);soft=view.grabWindow()
        origin=plate.mapToScene(QPointF());ratio=soft.devicePixelRatio()
        changed=0
        for x in range(32,220,3):
            px,py=round((origin.x()+x)*ratio),round((origin.y()+148)*ratio)
            changed+=sum(abs(a-b) for a,b in zip(sharp.pixelColor(px,py).getRgb()[:3],soft.pixelColor(px,py).getRgb()[:3]))>6
        check(changed>8,"actual local blur changes background pixels")
        view.preferences.setBlur(3.5);view.preferences.setReadability(.70);view.preferences.flush()
        check(settings.value("appearance/blur",type=float)==3.5 and settings.value("appearance/readability",type=float)==.70,
              "appearance settings persist")
        view.preferences.setBlur(4);view.preferences.setReadability(.64);view.preferences.flush()
        frame=view.capture.serial
        fixture_nodes=[fixture.rootObject()]+fixture.rootObject().childItems()
        colors=[(node,node.property("color")) for node in fixture_nodes if node.property("color") is not None]
        from PySide6.QtGui import QColor
        luminance=[]
        def linear(c):
            c=c/255
            return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
        for background in ("#F0F0F0","#181818"):
            for node,_ in colors:node.setProperty("color",QColor(background))
            old_frame=view.capture.serial;view.capture.togglePause()
            until(lambda:view.capture.serial>old_frame,"new real fixture frame")
            wait(60);view.capture.togglePause();wait(140)
            image=view.grabWindow();point=plate.mapToScene(QPointF(200,8))
            rgb=image.pixelColor(round(point.x()*ratio),round(point.y()*ratio)).getRgb()[:3]
            y=.2126*linear(rgb[0])+.7152*linear(rgb[1])+.0722*linear(rgb[2])
            contrast=(linear(228)+.05)/(y+.05)
            check(contrast>=4.5,"text contrast on "+background+": "+str(round(contrast,2)))
            luminance.append(dict(background=background,plate_rgb=rgb,contrast=round(contrast,2)))
            image.save(str(artifacts/("readability-"+background[1:]+"-"+scale+".png")))
        for node,color in colors:node.setProperty("color",color)
        anchor=view.position()+QPoint(408,38)
        QMetaObject.invokeMethod(root,"toggleMode")
        until(lambda:root.property("transitioning"),"fold begins")
        wait(100);check(view.position()+QPoint(408,38)==anchor,"fold anchor stable")
        until(lambda:not root.property("transitioning"),"compact settles")
        check(view.height()==76,"native compact size");layout("compact")
        click("glassCompactOutput")
        view.hideForTray();wait(400)
        check(not item("glassOutputPopup").property("visible") and not root.property("outputRequested"),"hide cancels pending output")
        view.showFromTray();wait(180)
        if root.property("compactMode"):QMetaObject.invokeMethod(root,"toggleMode")
        until(lambda:not root.property("transitioning"),"expanded restored")
        if item("glassOutputPopup").property("visible"):QMetaObject.invokeMethod(item("glassOutputPopup"),"close")
        click("glassSettingsButton");until(lambda:item("glassSettings").property("visible"),"settings button opens preferences")
        item("settingsTabs").setProperty("currentIndex",2);wait(30)
        check(item("glassReadabilitySlider").isVisible() and item("glassBlurSlider").isVisible(),"appearance controls available")
        item("settingsTabs").setProperty("currentIndex",3);wait(30)
        check(item("glassCaptureMode").isVisible(),"diagnostics isolated in settings")
        QMetaObject.invokeMethod(item("glassSettings"),"close")
        check(not callback_errors and not view.qml_warnings and not view.icons.failures,"warning-free render: "+str(callback_errors+view.qml_warnings+view.icons.failures))
        report=dict(result="PASS",scale=scale,assertions=len(checks),local_blur_changed_pixels=changed,readability=luminance,
                    checks=checks,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.iterdir()
                                                if p.suffix in (".py",".qml",".frag",".qsb")},
                    not_verified=["physical audio/Bluetooth acceptance","subjective design quality","fold fluid material","EXE distribution"])
        (artifacts/("controls-"+scale+".json")).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k not in ("checks","source_sha256")}),flush=True)
    finally:
        sys.excepthook=prior
        view.devices.stop();view.preferences.flush();view.capture.timer.stop();view.capture.settle.stop()
        view.setTrayMode(False);view.close();fixture.close();app.processEvents();temp.cleanup()


if __name__=="__main__":main()
