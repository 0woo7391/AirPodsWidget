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

    implicitHeight: 22

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            // L/R/CASE use the same label and status columns. CASE fits in
            // the label column without pushing its track or value sideways.
            Layout.preferredWidth: root.theme.batteryLabelColumn
                                 + root.theme.batteryLabelStatusGap
                                 + root.theme.batteryStatusColumn
            Layout.fillHeight: true

            RowLayout {
                anchors.fill: parent
                spacing: root.theme.batteryLabelStatusGap

                Text {
                    Layout.preferredWidth: root.theme.batteryLabelColumn
                    text: root.label
                    color: root.theme.textSecondary
                    font.family: root.theme.fontText
                    font.pixelSize: root.theme.labelSize
                    font.weight: root.theme.labelWeight
                    font.letterSpacing: 0.2
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                Item {
                    Layout.preferredWidth: root.theme.batteryStatusColumn
                    Layout.preferredHeight: 16

                    Rectangle {
                        anchors.centerIn: parent
                        width: 5
                        height: 5
                        radius: 3
                        color: root.theme.green
                        opacity: root.label !== "CASE" && root.inEar && !root.charging ? 1 : 0

                        Behavior on opacity {
                            NumberAnimation { duration: root.theme.motionFast; easing.type: Easing.OutCubic }
                        }
                    }

                    MediaIcon {
                        anchors.centerIn: parent
                        width: 11
                        height: 13
                        icon: "charging"
                        foreground: root.theme.yellow
                        opacity: root.charging ? 1 : 0
                        scale: root.charging ? 1 : 0.86

                        Behavior on opacity {
                            NumberAnimation { duration: root.theme.motionFast; easing.type: Easing.OutCubic }
                        }
                        Behavior on scale {
                            NumberAnimation { duration: root.theme.motionStandard; easing.type: Easing.OutCubic }
                        }
                    }
                }
            }
        }

        Item { Layout.preferredWidth: root.theme.batteryTrackGap }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 4

            Rectangle {
                anchors.fill: parent
                radius: height / 2
                color: root.theme.track
                opacity: root.value < 0 ? 0.55 : 1
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
                    NumberAnimation { duration: 280; easing.type: Easing.OutCubic }
                }
                Behavior on color {
                    ColorAnimation { duration: 240; easing.type: Easing.OutCubic }
                }
            }
        }

        Item { Layout.preferredWidth: root.theme.batteryValueGap }

        Item {
            // Keep a fixed value column. An unknown reading swaps to a small
            // visual placeholder instead of a literal dash or a width change.
            Layout.preferredWidth: root.theme.batteryValueColumn
            Layout.fillHeight: true

            AnimatedNumber {
                anchors.fill: parent
                visible: root.value >= 0
                value: root.value
                suffix: ""
                fontFamily: root.theme.fontDisplay
                pixelSize: root.theme.captionSize + 1
                fontWeight: root.theme.valueWeight
                revealOnAvailability: true
                animationDuration: root.theme.motionStandard
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                foreground: root.value <= root.alertThreshold ? root.theme.red
                            : root.value <= root.warningThreshold ? root.theme.orange
                            : root.theme.batteryValue
            }

            EmptyIndicator {
                anchors.fill: parent
                theme: root.theme
                active: root.value < 0
            }
        }
    }
}
