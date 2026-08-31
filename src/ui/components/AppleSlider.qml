import QtQuick
import QtQuick.Controls

Slider {
    id: control
    property UiTheme theme
    property color progressColor: control.theme ? control.theme.accent : "#FFFFFF"
    property color trackColor: control.theme ? control.theme.track : "#D1D1D6"
    property bool smoothExternalChanges: false
    readonly property int idleHandleSize: 16
    readonly property int pressedHandleSize: 18
    readonly property int handleSize: control.pressed ? control.pressedHandleSize : control.idleHandleSize
    readonly property int motionDuration: control.theme ? control.theme.motionStandard : 190

    implicitHeight: 28

    background: Rectangle {
        // The track begins and ends under the centre of the thumb. Both the
        // fill and thumb therefore use the same visual coordinate.
        x: control.leftPadding + control.handleSize / 2
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: Math.max(0, control.availableWidth - control.handleSize)
        height: 3
        radius: 2
        color: control.trackColor

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: control.progressColor

            Behavior on width {
                enabled: control.smoothExternalChanges && !control.pressed
                NumberAnimation { duration: control.motionDuration; easing.type: Easing.OutCubic }
            }
            Behavior on color { ColorAnimation { duration: control.motionDuration } }
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.handleSize / 2
           + control.visualPosition * (control.availableWidth - control.handleSize)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.handleSize
        height: width
        radius: width / 2
        color: "white"
        border.width: 1
        border.color: control.theme ? (control.theme.dark ? "#25000000" : "#18000000") : "#18000000"

        Behavior on width { NumberAnimation { duration: control.theme ? control.theme.motionFast : 140; easing.type: Easing.OutCubic } }
        Behavior on x {
            enabled: control.smoothExternalChanges && !control.pressed
            NumberAnimation { duration: control.motionDuration; easing.type: Easing.OutCubic }
        }
    }

    Behavior on value {
        enabled: control.smoothExternalChanges && !control.pressed
        NumberAnimation { duration: control.motionDuration; easing.type: Easing.OutCubic }
    }
}
