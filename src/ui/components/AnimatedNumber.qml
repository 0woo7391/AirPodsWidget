import QtQuick

Text {
    id: root
    property int value: -1
    property int previousValue: -1
    property real animatedValue: value < 0 ? 0 : value
    property string suffix: "%"
    property color foreground: "white"
    property string fontFamily: "Pretendard"
    property int pixelSize: 13
    property int fontWeight: Font.Medium
    property int animationDuration: 360
    property bool revealOnAvailability: true
    property real revealOpacity: value < 0 ? 0.58 : 1
    property real revealScale: 1

    text: value < 0 ? "—" : Math.round(animatedValue) + suffix
    color: foreground
    font.family: root.fontFamily
    font.pixelSize: root.pixelSize
    font.weight: root.fontWeight
    horizontalAlignment: Text.AlignRight
    transformOrigin: Item.Right
    opacity: root.revealOpacity
    scale: root.revealScale

    onValueChanged: {
        var oldValue = root.previousValue
        root.previousValue = value
        if (value >= 0) {
            animatedValue = value
            if (root.revealOnAvailability && oldValue < 0) {
                root.revealOpacity = 0
                root.revealScale = 0.94
                availabilityReveal.restart()
            }
        } else {
            root.revealOpacity = 0.58
            root.revealScale = 1
        }
    }

    Behavior on animatedValue {
        NumberAnimation { duration: root.animationDuration; easing.type: Easing.OutCubic }
    }

    ParallelAnimation {
        id: availabilityReveal
        NumberAnimation { target: root; property: "revealOpacity"; to: 1; duration: 150; easing.type: Easing.OutCubic }
        NumberAnimation { target: root; property: "revealScale"; to: 1; duration: 180; easing.type: Easing.OutCubic }
    }
}
