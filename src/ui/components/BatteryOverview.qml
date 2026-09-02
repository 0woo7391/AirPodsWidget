import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property UiTheme theme
    property real materialOpacity: 1.0
    property bool devicePresent: true
    // Driven by the parent morph timeline so the battery group reveals after
    // the shell starts growing, without changing its layout geometry.
    property real revealProgress: 1.0

    implicitHeight: 104
    opacity: root.revealProgress
    transform: Translate {
        y: (1 - root.revealProgress) * (root.theme ? root.theme.motionMorphSlide : 14)
    }

    // The battery group is a quiet aligned block. It does not add another
    // rounded card; shared columns provide the structure inside the shell.
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: root.theme.border
        opacity: 0.42
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 8
        anchors.bottomMargin: 7
        spacing: 0

        BatteryRow {
            objectName: "leftBatteryRow"
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            label: "L"
            value: root.devicePresent ? appController.leftBattery : -1
            charging: root.devicePresent && appController.leftCharging
            inEar: root.devicePresent && appController.leftInEar
            alertThreshold: appController.batteryThreshold
            theme: root.theme
        }

        BatteryRow {
            objectName: "rightBatteryRow"
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            label: "R"
            value: root.devicePresent ? appController.rightBattery : -1
            charging: root.devicePresent && appController.rightCharging
            inEar: root.devicePresent && appController.rightInEar
            alertThreshold: appController.batteryThreshold
            theme: root.theme
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 18
            // Center the estimate under the same track used by L/R. It is a
            // secondary reading, not a right-edge value that floats away.
            Item { Layout.preferredWidth: root.theme.batteryTrackStart }
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                AnimatedText {
                    anchors.fill: parent
                    text: root.devicePresent ? appController.estimatedRemainingUsage : ""
                    color: root.theme.textSecondary
                    fontFamily: root.theme.fontDisplay
                    pixelSize: root.theme.bodySize
                    fontWeight: root.theme.valueWeight
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                EmptyIndicator {
                    anchors.fill: parent
                    theme: root.theme
                    active: !root.devicePresent || appController.estimatedRemainingUsage === "—"
                }
            }
            Item { Layout.preferredWidth: root.theme.batteryValueGap }
            Item { Layout.preferredWidth: root.theme.batteryValueColumn }
        }

        BatteryRow {
            objectName: "caseBatteryRow"
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            label: "CASE"
            value: root.devicePresent ? appController.caseBattery : -1
            charging: root.devicePresent && appController.caseCharging
            alertThreshold: appController.batteryThreshold
            theme: root.theme
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: root.theme.border
        opacity: 0.42
    }
}
