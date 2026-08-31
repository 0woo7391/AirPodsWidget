import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property string label: "L"
    property int value: -1
    property bool charging: false
    property bool inEar: false
    property int alertThreshold: 10
    property UiTheme theme
    readonly property int warningThreshold: Math.max(20, root.alertThreshold + 10)

    // Keep one aligned grid for the label/dot, track, and value. The battery
    // card owns the larger side padding; this row only controls the columns.
    implicitHeight: 24

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Every row uses the same fixed columns. CASE gets its charging icon
        // inside the same status column, so its track starts exactly where
        // L/R tracks start.
        Item {
            Layout.preferredWidth: 38
            Layout.fillHeight: true

            Text {
                width: 30
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: root.label
                color: root.theme.textSecondary
                font.family: root.theme.fontText
                font.pixelSize: root.theme.labelSize
                font.weight: root.theme.labelWeight
                font.letterSpacing: 0.3
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 21
                width: 5
                height: 5
                anchors.verticalCenter: parent.verticalCenter
                radius: 3
                color: root.theme.green
                opacity: root.label !== "CASE" && root.inEar && !root.charging ? 1 : 0

                Behavior on color { ColorAnimation { duration: 240 } }
                Behavior on opacity { NumberAnimation { duration: 180 } }
            }

            MediaIcon {
                x: root.label === "CASE" ? 31 : 20
                width: 9
                height: 12
                anchors.verticalCenter: parent.verticalCenter
                icon: "bolt"
                foreground: root.theme.yellow
                opacity: root.charging ? 1 : 0
                scale: root.charging ? 1 : 0.86

                Behavior on opacity { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
                Behavior on scale { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
            }
        }

        Item { Layout.preferredWidth: 8 }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 4

            Rectangle {
                anchors.fill: parent
                radius: height / 2
                color: root.theme.track
                opacity: root.value < 0 ? 0.6 : 1
            }

            Rectangle {
                id: fill
                height: parent.height
                width: root.value < 0 ? 0 : parent.width * Math.max(0, Math.min(100, root.value)) / 100
                radius: height / 2
                color: root.value < 0 ? root.theme.track
                     : root.value <= root.alertThreshold ? root.theme.red
                     : root.value <= root.warningThreshold ? root.theme.orange
                     : root.theme.batteryHealthy

                Behavior on width {
                    NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
                }
                Behavior on color { ColorAnimation { duration: 280 } }
            }
        }

        Item { Layout.preferredWidth: 8 }

        AnimatedNumber {
            Layout.preferredWidth: 38
            value: root.value
            fontFamily: root.theme.fontText
            pixelSize: root.theme.valueSize
            fontWeight: root.theme.valueWeight
            revealOnAvailability: true
            animationDuration: root.theme.motionStandard
            foreground: root.value >= 0 && root.value <= root.alertThreshold ? root.theme.red
                        : root.value >= 0 && root.value <= root.warningThreshold ? root.theme.orange
                        : root.theme.batteryValue
        }
    }
}
