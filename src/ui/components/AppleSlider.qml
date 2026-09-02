import QtQuick
import QtQuick.Controls

Slider {
    id: control
    property UiTheme theme
    property color progressColor: control.theme ? control.theme.accent : "#FFFFFF"
    property color trackColor: control.theme ? control.theme.track : "#D1D1D6"
    property bool smoothExternalChanges: false
    readonly property int idleHandleSize: control.isVertical && control.height < 40 ? 10 : 15
    readonly property int pressedHandleSize: control.isVertical && control.height < 40 ? 12 : 18
    readonly property int handleSize: control.pressed ? control.pressedHandleSize : control.idleHandleSize
    readonly property int motionDuration: control.theme ? control.theme.motionStandard : 190
    readonly property bool isVertical: control.orientation === Qt.Vertical
    readonly property real visualProgress: control.isVertical ? 1 - control.visualPosition : control.visualPosition

    implicitWidth: control.isVertical ? 28 : 120
    implicitHeight: control.isVertical ? 120 : 28

    background: Rectangle {
        x: control.isVertical
           ? control.leftPadding + control.availableWidth / 2 - width / 2
           : control.leftPadding + control.handleSize / 2
        y: control.isVertical
           ? control.topPadding + control.handleSize / 2
           : control.topPadding + control.availableHeight / 2 - height / 2
        width: control.isVertical ? 4 : Math.max(0, control.availableWidth - control.handleSize)
        height: control.isVertical ? Math.max(0, control.availableHeight - control.handleSize) : 3
        radius: 2
        color: control.trackColor

        Rectangle {
            y: control.isVertical ? parent.height - height : 0
            width: control.isVertical ? parent.width : control.visualProgress * parent.width
            height: control.isVertical ? control.visualProgress * parent.height : parent.height
            radius: parent.radius
            color: control.progressColor

            Behavior on color { ColorAnimation { duration: control.motionDuration } }
        }
    }

    handle: Rectangle {
        x: control.isVertical
           ? control.leftPadding + control.availableWidth / 2 - width / 2
           : control.leftPadding + control.handleSize / 2
             + control.visualPosition * (control.availableWidth - control.handleSize)
        y: control.isVertical
           ? control.topPadding + control.visualPosition * (control.availableHeight - control.handleSize)
           : control.topPadding + control.availableHeight / 2 - height / 2
        width: control.handleSize
        height: width
        radius: width / 2
        color: control.theme ? control.theme.highlight : "white"
        border.width: 1
        border.color: control.theme ? (control.theme.dark ? "#25000000" : "#18000000") : "#18000000"

        Behavior on width {
            NumberAnimation { duration: control.theme ? control.theme.motionFast : 140; easing.type: Easing.OutCubic }
        }
    }

    // One value timeline drives both the fill and the handle. Animating the
    // derived width/x/y properties as well would restart them every frame and
    // makes the thumb visibly lag behind its bar.
    Behavior on value {
        enabled: control.smoothExternalChanges && !control.pressed
        NumberAnimation { duration: control.motionDuration; easing.type: Easing.OutCubic }
    }
}
