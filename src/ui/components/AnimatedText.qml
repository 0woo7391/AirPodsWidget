import QtQuick

// Fixed-frame text swap. The parent owns the geometry; only the glyph layer
// moves, so a changing label cannot resize a row into another control.
Item {
    id: root

    property string text: ""
    property string displayedText: ""
    property color color: "white"
    property string fontFamily: "Pretendard"
    property int pixelSize: 13
    property int fontWeight: Font.Normal
    property real letterSpacing: 0
    property int horizontalAlignment: Text.AlignLeft
    property int verticalAlignment: Text.AlignVCenter
    property int elide: Text.ElideNone
    property bool animateChanges: true
    property int changeDuration: 170
    property real changeOffset: 3
    property bool ready: false

    implicitWidth: Math.max(front.implicitWidth, back.implicitWidth)
    implicitHeight: Math.max(front.implicitHeight, back.implicitHeight)
    clip: true

    Text {
        id: front
        anchors.fill: parent
        text: root.displayedText
        color: root.color
        font.family: root.fontFamily
        font.pixelSize: root.pixelSize
        font.weight: root.fontWeight
        font.letterSpacing: root.letterSpacing
        horizontalAlignment: root.horizontalAlignment
        verticalAlignment: root.verticalAlignment
        elide: root.elide
        renderType: Text.NativeRendering
    }

    Text {
        id: back
        anchors.fill: parent
        text: root.text
        color: root.color
        font.family: root.fontFamily
        font.pixelSize: root.pixelSize
        font.weight: root.fontWeight
        font.letterSpacing: root.letterSpacing
        horizontalAlignment: root.horizontalAlignment
        verticalAlignment: root.verticalAlignment
        elide: root.elide
        opacity: 0
        y: root.changeOffset
        renderType: Text.NativeRendering
    }

    function applyImmediately() {
        changeAnimation.stop()
        root.displayedText = root.text
        front.opacity = 1
        front.y = 0
        back.opacity = 0
        back.y = root.changeOffset
    }

    Component.onCompleted: {
        root.displayedText = root.text
        root.ready = true
    }

    onTextChanged: {
        if (!root.ready || root.displayedText === root.text)
            return
        if (!root.animateChanges) {
            root.applyImmediately()
            return
        }
        changeAnimation.stop()
        front.opacity = 1
        front.y = 0
        back.opacity = 0
        back.y = root.changeOffset
        changeAnimation.restart()
    }

    ParallelAnimation {
        id: changeAnimation
        NumberAnimation {
            target: front
            property: "opacity"
            to: 0
            duration: root.changeDuration
            easing.type: Easing.InCubic
        }
        NumberAnimation {
            target: front
            property: "y"
            to: -root.changeOffset
            duration: root.changeDuration
            easing.type: Easing.InCubic
        }
        NumberAnimation {
            target: back
            property: "opacity"
            to: 1
            duration: root.changeDuration
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: back
            property: "y"
            to: 0
            duration: root.changeDuration
            easing.type: Easing.OutCubic
        }
        onFinished: root.applyImmediately()
    }
}
