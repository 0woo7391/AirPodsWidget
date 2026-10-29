import QtQuick
import QtQuick.Controls.Basic

Dial {
    id: dial
    objectName: "glassVolumeDial"
    property bool muted: false
    property bool valueAvailable: true
    property bool reduced: false
    property bool keyboardFeedback: false
    readonly property real pointerValue: {
        if (!dialHover.hovered) return -1
        const dx=dialHover.point.position.x-width/2, dy=dialHover.point.position.y-height/2
        const distance=Math.hypot(dx,dy)
        if (distance<width*.28 || distance>width*.70) return -1
        let angle=Math.atan2(dy,dx)*180/Math.PI
        if (angle<135) angle+=360
        return angle<=405 ? (angle-135)/270*100 : -1
    }
    readonly property real feedbackValue: !enabled || !valueAvailable ? -1
        : input.pressed || keyboardFeedback ? value : pointerValue
    function feedbackOpacity(mark) {
        return feedbackValue<0 ? 0 : Math.max(0,1-Math.abs(feedbackValue-mark)/13)
    }
    property bool auditControl: true
    signal edited(int requested)
    from: 0; to: 100; stepSize: 1
    startAngle: -135; endAngle: 135; wrap: false
    width: 104; height: 104; padding: 0
    hoverEnabled: true; focusPolicy: Qt.StrongFocus
    Accessible.name: muted ? "출력 음량 · 음소거됨" : "출력 음량"
    onMoved: edited(Math.round(value))
    onValueChanged: arc.requestPaint()
    onMutedChanged: arc.requestPaint()
    Keys.onPressed: function(event) {
        let requested = value
        if (event.key === Qt.Key_Home) requested = 0
        else if (event.key === Qt.Key_End) requested = 100
        else if (event.key === Qt.Key_Left || event.key === Qt.Key_Down) requested--
        else if (event.key === Qt.Key_Right || event.key === Qt.Key_Up) requested++
        else { event.accepted = false; return }
        keyboardFeedback=true; feedbackTimeout.restart()
        edited(Math.max(0, Math.min(100, requested))); event.accepted = true
    }
    background: Item {
        Rectangle {
            anchors.fill: parent; anchors.margins: 7; radius: width / 2
            color: dial.muted ? "#664F343B" : "#10202020"
            border.color: dial.activeFocus ? "#E8E8E8" : "#24FFFFFF"
            border.width: 1
            Behavior on color { ColorAnimation { duration: 100 } }
        }
        Canvas {
            id: arc; anchors.fill: parent
            onPaint: {
                const c = getContext("2d"); c.reset()
                const radius = width / 2 - 4, start = Math.PI * .75, span = Math.PI * 1.5
                c.lineWidth = 3; c.lineCap = "round"; c.strokeStyle = "#777777"
                c.beginPath(); c.arc(width/2, height/2, radius, start, start+span); c.stroke()
                c.strokeStyle = dial.muted ? "#E5BBB2" : "#CCCCCC"
                c.beginPath(); c.arc(width/2, height/2, radius, start, start+span*dial.position); c.stroke()
            }
        }
    }
    handle: Rectangle {
        readonly property real theta: Math.PI * (.75 + 1.5*dial.position)
        x: dial.width/2 + Math.cos(theta)*(dial.width/2-4) - 4
        y: dial.height/2 + Math.sin(theta)*(dial.height/2-4) - 4
        width: 8; height: 8; radius: 4; color: "#E8E8E8"
    }
    contentItem: Column {
        topPadding: (dial.height-53)/2; spacing: 1
        Text {
            width: dial.width; height: 36; text: dial.valueAvailable ? Math.round(dial.value) : "—"
            font.family: previewFont; font.pixelSize: Math.min(30,Math.round(dial.width*.28)); font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter; color: "#F0F0F0"
        }
        Text {
            width: dial.width; height: 16; text: dial.muted ? "MUTE" : "%"
            font.family: previewFont; font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter; color: dial.muted ? "#F1D9D2" : "#E4E4E4"
        }
    }
    Repeater {
        model: 21
        Item {
            required property int index
            readonly property int modelData: index*5
            readonly property bool major: modelData%10===0
            readonly property real theta: Math.PI * (.75+1.5*modelData/100)
            readonly property real inner: dial.width/2-10
            readonly property real length: major ? 6 : 3
            objectName: "dialTick"+modelData
            width: dial.width; height: dial.height
            Rectangle {
                x: dial.width/2+Math.cos(parent.theta)*(parent.inner-parent.length/2)-parent.length/2
                y: dial.height/2+Math.sin(parent.theta)*(parent.inner-parent.length/2)-.5
                width: parent.length; height: 1
                rotation: parent.theta*180/Math.PI
                objectName: "dialTickMark"+parent.modelData
                color: "#CCCCCC"; opacity: dial.feedbackOpacity(parent.modelData)
                Behavior on opacity { NumberAnimation { duration: dial.reduced ? 0 : 100 } }
            }
            Text {
            objectName: "dialLabel"+parent.modelData
            readonly property int modelData: parent.modelData
            x: dial.width/2+Math.cos(parent.theta)*(dial.width/2+10)-9
            y: dial.height/2+Math.sin(parent.theta)*(dial.height/2+10)-6
            width: 18; height: 12; text: modelData
            font.family: previewFont; font.pixelSize: 9
            horizontalAlignment: Text.AlignHCenter; color: "#E4E4E4"
            visible: parent.major
            opacity: dial.feedbackOpacity(modelData)
            Behavior on opacity { NumberAnimation { duration: dial.reduced ? 0 : 100 } }
            }
        }
    }
    HoverHandler { id: dialHover; margin: 16 }
    Timer { id: feedbackTimeout; interval: 900; onTriggered: dial.keyboardFeedback=false }
    MouseArea {
        id: input; anchors.fill: parent; preventStealing: true
        property bool tracking: false
        property real lastAngle: 0
        property real dragValue: 0
        function track(px, py) {
            const dx=px-width/2, dy=py-height/2
            if (Math.hypot(dx,dy)<width*.15) { tracking=false; return }
            const angle=Math.atan2(dy,dx)*180/Math.PI
            if (tracking) {
                let delta=angle-lastAngle
                if (delta>180) delta-=360
                if (delta< -180) delta+=360
                dragValue=Math.max(0,Math.min(100,dragValue+delta/270*100))
                if (Math.round(dragValue)!==Math.round(dial.value)) dial.edited(Math.round(dragValue))
            }
            lastAngle=angle; tracking=true
        }
        onPressed: function(mouse) {
            dial.keyboardFeedback=false; feedbackTimeout.stop()
            dial.forceActiveFocus(); tracking=false; dragValue=dial.value; track(mouse.x,mouse.y)
        }
        onPositionChanged: function(mouse) { if (pressed) track(mouse.x,mouse.y) }
        onReleased: tracking=false
        onCanceled: tracking=false
        onWheel: function(wheel) {
            const delta=wheel.angleDelta.y || wheel.angleDelta.x
            if (delta) {
                dial.keyboardFeedback=true; feedbackTimeout.restart()
                dial.edited(Math.max(0,Math.min(100,dial.value+(delta>0?1:-1))))
            }
            wheel.accepted=true
        }
    }
}
