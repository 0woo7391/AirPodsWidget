import QtQuick
import QtQuick.Window
import "components"

Item {
    id: root

    property WidgetWindow widget: WidgetWindow {}
    property TrayPopup trayPopup: TrayPopup {}
    property SettingsWindow settingsWindow: SettingsWindow {}
    property NotificationPopup notificationPopup: NotificationPopup {}
    readonly property bool desktopWidgetFlagsValid:
        (widget.flags & Qt.WindowDoesNotAcceptFocus) === Qt.WindowDoesNotAcceptFocus
        && (((widget.flags & Qt.WindowStaysOnBottomHint) === Qt.WindowStaysOnBottomHint)
            || ((widget.flags & Qt.WindowStaysOnTopHint) === Qt.WindowStaysOnTopHint))

    Connections {
        target: appController
        function onShowTrayPopupRequested(x, y) {
            if (trayPopup.visible)
                trayPopup.hide()
            else
                trayPopup.reveal(x, y)
        }
        function onShowSettingsRequested(x, y) { settingsWindow.reveal(x, y) }
        function onShowConnectionPopupRequested(x, y) { notificationPopup.reveal(x, y) }
        function onShowLowBatteryPopupRequested(x, y) { notificationPopup.reveal(x, y) }
    }
}
