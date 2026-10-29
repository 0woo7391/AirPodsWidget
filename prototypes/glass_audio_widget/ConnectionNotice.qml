import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Window

Window {
    id: notice
    objectName: "connectionNotice"
    width: 320; height: 112; color: "transparent"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
    function offer() {
        widgetHost.positionNotice(notice)
        show(); lifetime.restart()
    }
    Rectangle {
        anchors.fill: parent; radius: 18; color: "#1E263B"; border.color: "#98A9C4"
        Text {
            x: 16; y: 12; width: 248; height: 22
            text: deviceBackend.state.name || "등록된 에어팟"
            elide: Text.ElideRight; color: "#F0F3F8"; font.family: previewFont; font.pixelSize: 14
        }
        Text {
            x: 16; y: 39; width: 286; height: 20
            text: deviceBackend.state.pending ? "연결 중…" : "등록된 장치가 연결되지 않았음"
            color: "#98A9C4"; font.family: previewFont; font.pixelSize: 12
        }
        GlassButton {
            x: 16; y: 68; width: 80; height: 32; text: "연결"
            description: "저장한 에어팟 연결"; enabled: !deviceBackend.state.pending
            onClicked: { deviceBackend.connectDevice(); notice.close() }
        }
        GlassButton { x: 274; y: 8; width: 32; height: 32; text: "×"; description: "안내 닫기"; onClicked: notice.close() }
    }
    Timer { id: lifetime; interval: 12000; onTriggered: notice.close() }
    onVisibleChanged: if (!visible) lifetime.stop()
}
