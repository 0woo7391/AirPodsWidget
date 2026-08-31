import QtQuick

Item {
    id: root
    property string text: ""
    property string displayedText: ""
    property color color: "white"
    property string fontFamily: "Pretendard"
    property int pixelSize: 15
    property int fontWeight: Font.DemiBold
    property bool running: true
    property int speedPixelsPerSecond: 18
    property bool ready: false

    clip: true
    implicitHeight: label.implicitHeight

    Text {
        id: label
        x: 0
        y: 0
        text: root.displayedText
        color: root.color
        font.family: root.fontFamily
        font.pixelSize: root.pixelSize
        font.weight: root.fontWeight
        renderType: Text.NativeRendering
    }

    readonly property bool overflowing: label.implicitWidth > width + 2
    readonly property real travel: Math.max(0, label.implicitWidth - width)

    function syncAnimation() {
        marquee.stop()
        label.x = 0
        if (root.running && root.overflowing && root.visible)
            restartTimer.restart()
    }

    Component.onCompleted: {
        displayedText = text
        ready = true
        syncAnimation()
    }

    onTextChanged: {
        if (!ready) {
            displayedText = text
            return
        }
        if (displayedText !== text)
            titleSwap.restart()
    }

    Timer {
        id: restartTimer
        interval: 0
        onTriggered: {
            if (root.running && root.overflowing && root.visible)
                marquee.start()
        }
    }

    SequentialAnimation {
        id: titleSwap
        NumberAnimation { target: label; property: "opacity"; to: 0; duration: 90; easing.type: Easing.InCubic }
        ScriptAction {
            script: {
                root.displayedText = root.text
                root.syncAnimation()
            }
        }
        NumberAnimation { target: label; property: "opacity"; to: 1; duration: 150; easing.type: Easing.OutCubic }
    }

    SequentialAnimation {
        id: marquee
        loops: Animation.Infinite
        // Hold the readable starting position long enough for a user to scan
        // the title before the slow marquee begins.
        PauseAnimation { duration: 3000 }
        NumberAnimation {
            target: label
            property: "x"
            to: -root.travel
            duration: Math.max(1800, root.travel / root.speedPixelsPerSecond * 1000)
            easing.type: Easing.Linear
        }
        PauseAnimation { duration: 1500 }
        NumberAnimation {
            target: label
            property: "x"
            to: 0
            duration: 650
            easing.type: Easing.InOutCubic
        }
        PauseAnimation { duration: 800 }
    }

    onWidthChanged: syncAnimation()
    onRunningChanged: syncAnimation()
    onOverflowingChanged: syncAnimation()
    onVisibleChanged: syncAnimation()
}
