import QtQuick

// Quick launch. Tiles work straight from the summary, so this cell does not
// grow. Tiles swell toward the pointer like an app dock (#208), the one under
// it shows its name in a bubble, and a launched tile hops once.
// Drop files or shortcuts on it to add them; right-click a tile twice to remove it.
// On the rail the apps stack as icons and their names slide in when it widens.
DockCard {
    id: card
    cardId: "launcher"
    expandable: false
    magnifies: false
    readonly property var apps: launcherBackend.apps || []
    // Tiles fit the bento width (not the morphing cell), so the card keeps its size while it morphs.
    readonly property real gridWidth: dock ? dock.bentoWidth : Theme.dockWidth
    readonly property int columns: gridWidth >= 200 ? 4 : 3
    readonly property int tile: Math.max(28, Math.min(42, Math.floor((gridWidth - Theme.pad * 2 - (columns - 1) * 8) / columns)))
    readonly property int rows: Math.max(1, Math.ceil(apps.length / columns))
    readonly property int railTile: 40
    property string caption: ""
    property int armedRemoval: -1
    summaryHeight: Theme.pad + rows * tile + (rows - 1) * 8 + 32
    railHeight: Math.max(Theme.railRow, 8 + apps.length * railTile)

    Timer { id: disarm; interval: 3000; onTriggered: { card.armedRemoval = -1; card.caption = "" } }

    function press(event, app) {
        if (event.button === Qt.RightButton) {
            if (card.armedRemoval === app.index) {
                card.armedRemoval = -1; card.caption = ""
                launcherBackend.remove(app.index)
            } else {
                card.armedRemoval = app.index
                card.caption = "한 번 더 우클릭하면 제거"
                disarm.restart()
            }
            return false
        }
        card.armedRemoval = -1
        launcherBackend.launch(app.index)
        return true
    }

    // One app tile: icon (or its initial), swell, removal rim and launch hop.
    component AppTile: Rectangle {
        id: tileItem
        property var app
        property real magnify: 0
        readonly property alias hovered: mouse.containsMouse
        property real hop: 0
        width: card.tile; height: card.tile; radius: Theme.radiusInner
        color: mouse.pressed ? Theme.wellPressed : mouse.containsMouse ? Theme.wellHover : Theme.well
        border.width: card.armedRemoval === app.index ? 1 : 0
        border.color: Theme.bad
        scale: (1 + magnify) * (mouse.pressed ? 0.94 : 1)
        transform: Translate { y: tileItem.hop }
        Behavior on color { ColorAnimation { duration: 110 } }
        Behavior on magnify { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
        SequentialAnimation {
            id: hopAnimation
            NumberAnimation { target: tileItem; property: "hop"; to: -10; duration: 140; easing.type: Easing.OutQuad }
            NumberAnimation { target: tileItem; property: "hop"; to: 0; duration: 460; easing.type: Easing.OutBounce }
        }
        Image {
            id: appIcon
            anchors.centerIn: parent
            width: 26; height: 26
            sourceSize: Qt.size(64, 64)
            source: tileItem.app.hasIcon ? "image://appicon/" + tileItem.app.index + "?" + tileItem.app.path : ""
            visible: status === Image.Ready
        }
        Text {
            anchors.centerIn: parent
            visible: appIcon.status !== Image.Ready
            text: (tileItem.app.name || "?").slice(0, 1).toUpperCase()
            color: Theme.ink; font.family: dockFont; font.pixelSize: 16; font.weight: Font.DemiBold
        }
        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: function(event) { if (card.press(event, tileItem.app)) hopAnimation.restart() }
        }
    }

    summary: Component {
        Item {
            id: board
            HoverHandler { id: boardHover }
            Grid {
                id: grid
                x: Theme.pad; y: Theme.pad
                columns: card.columns
                columnSpacing: (parent.width - Theme.pad * 2 - card.columns * card.tile) / (card.columns - 1)
                rowSpacing: 8
                Repeater {
                    id: tiles
                    model: card.apps
                    AppTile {
                        required property var modelData
                        app: modelData
                        z: hovered ? 2 : magnify > 0.05 ? 1 : 0
                        magnify: boardHover.hovered
                            ? Theme.magnifyTile * Theme.magnify(Math.hypot(boardHover.point.position.x - grid.x - x - width / 2,
                                                                          boardHover.point.position.y - grid.y - y - height / 2), 70)
                            : 0
                    }
                }
            }
            // Name bubble over the tile under the pointer.
            Rectangle {
                id: bubble
                property Item target: {
                    for (let i = 0; i < tiles.count; i++) if (tiles.itemAt(i) && tiles.itemAt(i).hovered) return tiles.itemAt(i)
                    return null
                }
                property string name: ""
                onTargetChanged: if (target) name = target.app.name  // keep the text while fading out
                visible: opacity > 0
                opacity: target && card.armedRemoval < 0 ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 120 } }
                z: 5
                width: bubbleText.implicitWidth + 16; height: 22; radius: 11
                color: "#E61C1C22"
                border.width: 1; border.color: Theme.stroke
                x: target ? Math.max(4, Math.min(parent.width - width - 4, grid.x + target.x + target.width / 2 - width / 2)) : x
                y: target ? grid.y + target.y - height - 2 - target.height * target.magnify / 2 : y
                Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                Text {
                    id: bubbleText
                    anchors.centerIn: parent
                    text: bubble.name
                    color: Theme.ink; font.family: dockFont; font.pixelSize: 11; font.weight: Font.DemiBold
                }
            }
            Text {
                x: Theme.pad; width: parent.width - Theme.pad * 2
                y: parent.height - 26; height: 16
                text: card.caption.length ? card.caption : card.apps.length ? "" : "앱을 끌어다 놓아 추가"
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

    railContent: Component {
        Item {
            Repeater {
                model: card.apps
                Item {
                    required property var modelData
                    required property int index
                    readonly property real centerY: 4 + card.railTile * index + card.railTile / 2
                    width: parent.width; height: card.railTile; y: 4 + card.railTile * index
                    z: tileView.magnify > 0.05 ? 1 : 0
                    AppTile {
                        id: tileView
                        app: modelData
                        width: 34; height: 34; radius: 10
                        x: (card.mirrored ? Theme.railWidth / 2 : parent.width - Theme.railWidth / 2) - width / 2
                        anchors.verticalCenter: parent.verticalCenter
                        magnify: card.dock && card.dock.pointerY >= 0
                            ? Theme.magnifyTile * Theme.magnify(card.dock.pointerY - (card.dockTop + parent.centerY), 60)
                            : 0
                    }
                    Text {
                        readonly property real shown: Theme.seg(card.railOpen, 0.4 + 0.05 * index, 0.8 + 0.05 * index)
                        x: (card.mirrored ? Theme.railWidth : Theme.pad) + 6 * (1 - shown)
                        width: parent.width - Theme.railWidth - Theme.pad
                        anchors.verticalCenter: parent.verticalCenter
                        opacity: shown; visible: shown > 0
                        text: card.armedRemoval === modelData.index ? "한 번 더 우클릭" : modelData.name
                        elide: Text.ElideRight
                        color: card.armedRemoval === modelData.index ? Theme.bad : Theme.ink
                        font.family: dockFont; font.pixelSize: 12; font.weight: Font.DemiBold
                    }
                }
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
