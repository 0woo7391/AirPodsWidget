import QtQuick

// A number whose digits roll to their new value like an odometer, and pop a little
// when it changes.
Item {
    id: number
    property int value: 0
    property color color: Theme.ink
    property int pixelSize: 22
    readonly property string digits: String(Math.max(0, value))
    readonly property real digitWidth: metrics.advanceWidth
    implicitWidth: digits.length * digitWidth
    implicitHeight: metrics.height
    width: implicitWidth
    height: implicitHeight
    Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    TextMetrics {
        id: metrics
        text: "0"
        font.family: dockFont; font.pixelSize: number.pixelSize; font.weight: Font.DemiBold
        font.features: Theme.numberFeatures
    }
    onValueChanged: pop.restart()
    SequentialAnimation {
        id: pop
        NumberAnimation { target: row; property: "scale"; to: 1.08; duration: 90; easing.type: Easing.OutQuad }
        NumberAnimation { target: row; property: "scale"; to: 1; duration: 220; easing.type: Easing.OutBack }
    }

    Row {
        id: row
        transformOrigin: Item.Left
        Repeater {
            model: number.digits.length
            Item {
                required property int index
                readonly property int digit: Number(number.digits.charAt(index))
                width: number.digitWidth
                height: metrics.height
                clip: true
                Column {
                    y: -parent.digit * metrics.height
                    Behavior on y { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                    Repeater {
                        model: 10
                        Text {
                            required property int index
                            width: number.digitWidth; height: metrics.height
                            horizontalAlignment: Text.AlignHCenter
                            text: index
                            color: number.color
                            font: metrics.font
                        }
                    }
                }
            }
        }
    }
}
