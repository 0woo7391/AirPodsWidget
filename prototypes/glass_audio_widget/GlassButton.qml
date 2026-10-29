import QtQuick
import QtQuick.Controls.Basic

Button {
    id: control
    property string glyph: ""
    property string pose: ""
    property string description: ""
    property bool selected: false
    property bool reduced: false
    property bool busy: false
    property bool flipIcon: false
    property real glyphRotation: 0
    property bool pill: false
    property bool dropdown: false
    property real pressure: 0
    property bool auditControl: true
    implicitWidth: 36; implicitHeight: 36; padding: 0
    hoverEnabled: true; focusPolicy: Qt.StrongFocus
    opacity: enabled || selected || busy ? 1 : 0.35
    Accessible.name: description
    function retarget() {
        press.stop()
        if (reduced) { pressure=0; return }
        press.from=pressure; press.to=down ? 1 : 0
        press.duration=down ? 80 : 160; press.start()
    }
    onDownChanged: retarget()
    onReducedChanged: retarget()
    NumberAnimation {
        id: press; target: control; property: "pressure"
        easing.type: Easing.BezierSpline
        easing.bezierCurve: [0.2,0,0,1,1,1]
    }
    background: Rectangle {
        radius: control.pill ? 12 : Math.min(width,height)/2
        color: control.down ? "#66484848" : control.selected ? "#555F5F5F"
            : control.hovered ? "#443F3F3F" : "#24242424"
        border.width: control.activeFocus ? 1.5 : 1
        border.color: control.activeFocus ? "#E8E8E8" : control.selected ? "#99FFFFFF" : "#22FFFFFF"
        transform: Scale {
            origin.x: control.width/2; origin.y: control.height/2
            xScale: 1-control.pressure*.04; yScale: 1-control.pressure*.04
        }
        Behavior on color { ColorAnimation { duration: control.reduced ? 0 : 100 } }
    }
    contentItem: Item {
        Image {
            objectName: control.objectName+"-glyph"
            x: control.text.length ? 12 : (parent.width-width)/2
            y: (parent.height-height)/2
            width: 18; height: 18; sourceSize.width: 36; sourceSize.height: 36
            mirror: control.flipIcon; rotation: control.glyphRotation
            visible: control.glyph.length>0 && !["bluetooth","pin","output"].includes(control.glyph) && !control.busy
            source: visible ? "image://lucian/"+control.glyph+"?color=%23F0F0F0&state="+control.pose : ""
        }
        ControlGlyph {
            x: control.text.length ? 12 : (parent.width-width)/2
            y: (parent.height-height)/2
            visible: ["pin","output"].includes(control.glyph) && !control.busy
            kind: control.glyph; selected: control.selected
        }
        BluetoothGlyph {
            x: control.text.length ? 12 : (parent.width-width)/2
            y: (parent.height-height)/2
            ink: "#F0F0F0"; visible: control.glyph==="bluetooth" && !control.busy
        }
        Text {
            anchors.fill: parent
            leftPadding: control.glyph.length ? 40 : 0
            rightPadding: control.dropdown ? 28 : control.glyph.length ? 10 : 0
            text: control.text; visible: text.length>0; elide: Text.ElideRight
            color: "#F0F0F0"; font.family: previewFont; font.pixelSize: 11
            horizontalAlignment: control.glyph.length ? Text.AlignLeft : Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        Image {
            x: parent.width-23; y: (parent.height-14)/2
            width: 14; height: 14; sourceSize.width: 28; sourceSize.height: 28
            visible: control.dropdown
            source: visible ? "image://lucian/chevron?color=%23CFCFCF" : ""
        }
        BusyIndicator {
            x: control.text.length ? 10 : (parent.width-width)/2
            y: (parent.height-height)/2
            width: 22; height: 22; running: control.busy; visible: running
        }
    }
}
