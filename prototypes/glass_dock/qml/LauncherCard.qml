import QtQuick

// Quick launch. Tiles work straight from the summary, so this cell does not
// grow; its detail is the caption line that names the tile under the pointer.
// Drop files or shortcuts on it to add them; right-click a tile twice to remove it.
DockCard {
    id: card
    cardId: "launcher"
    expandable: false
    readonly property var apps: launcherBackend.apps || []
    readonly property int columns: 3
    readonly property int tile: 42
    readonly property int rows: Math.max(1, Math.ceil(apps.length / columns))
    property string caption: ""
    property int armedRemoval: -1
    summaryHeight: Theme.pad + rows * tile + (rows - 1) * 8 + 32

    Timer { id: disarm; interval: 3000; onTriggered: { card.armedRemoval = -1; card.caption = "" } }

    summary: Component {
        Item {
            Grid {
                id: grid
                x: Theme.pad; y: Theme.pad
                columns: card.columns
                columnSpacing: (parent.width - Theme.pad * 2 - card.columns * card.tile) / (card.columns - 1)
                rowSpacing: 8
                Repeater {
                    model: card.apps
                    Rectangle {
                        id: tileItem
                        required property var modelData
                        width: card.tile; height: card.tile; radius: Theme.radiusInner
                        color: mouse.pressed ? Theme.wellPressed : mouse.containsMouse ? Theme.wellHover : Theme.well
                        border.width: card.armedRemoval === modelData.index ? 1 : 0
                        border.color: Theme.bad
                        scale: mouse.pressed ? 0.94 : 1
                        Behavior on color { ColorAnimation { duration: 110 } }
                        Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
                        Image {
                            id: appIcon
                            anchors.centerIn: parent
                            width: 26; height: 26
                            sourceSize: Qt.size(52, 52)
                            source: modelData.hasIcon ? "image://appicon/" + modelData.index + "?" + modelData.path : ""
                            visible: status === Image.Ready
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: appIcon.status !== Image.Ready
                            text: (modelData.name || "?").slice(0, 1).toUpperCase()
                            color: Theme.ink; font.family: dockFont; font.pixelSize: 16; font.weight: Font.DemiBold
                        }
                        MouseArea {
                            id: mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            onContainsMouseChanged: {
                                if (containsMouse && card.armedRemoval < 0) card.caption = modelData.name
                                else if (!containsMouse && card.armedRemoval < 0) card.caption = ""
                            }
                            onClicked: function(event) {
                                if (event.button === Qt.RightButton) {
                                    if (card.armedRemoval === modelData.index) {
                                        card.armedRemoval = -1; card.caption = ""
                                        launcherBackend.remove(modelData.index)
                                    } else {
                                        card.armedRemoval = modelData.index
                                        card.caption = "한 번 더 우클릭하면 제거"
                                        disarm.restart()
                                    }
                                    return
                                }
                                card.armedRemoval = -1
                                launcherBackend.launch(modelData.index)
                            }
                        }
                    }
                }
            }
            Text {
                x: Theme.pad; width: parent.width - Theme.pad * 2
                y: parent.height - 26; height: 16
                text: card.caption.length ? card.caption
                    : card.apps.length ? "" : "앱을 끌어다 놓아 추가"
                color: card.armedRemoval >= 0 ? Theme.bad : Theme.inkSecondary
                horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                font.family: dockFont; font.pixelSize: 11
            }
            DropArea {
                anchors.fill: parent
                onDropped: function(drop) {
                    if (drop.hasUrls) {
                        launcherBackend.addUrls(drop.urls)
                        drop.acceptProposedAction()
                    }
                }
            }
        }
    }
}
