import QtQuick

// Quick launch. Tiles work straight from the summary, so this cell does not
// grow. Tiles swell toward the pointer like an app dock (#208), the one under
// it shows its name in a bubble, and a launched tile hops once.
// Drop files, shortcuts or web links on it to add them; right-click a tile twice to remove it.
// In edit mode the tiles wobble and drag into a new order, "−" removes one, and a field
// below takes a web address (the site's own icon and name are fetched).
// On the rail the apps stack as icons and their names slide in when it widens.
DockCard {
    id: card
    cardId: "launcher"
    expandable: false
    magnifies: false
    editInteractive: true
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
        property real dx: 0
        property real dy: 0
        width: card.tile; height: card.tile; radius: Theme.radiusInner
        color: mouse.pressed ? Theme.wellPressed : mouse.containsMouse ? Theme.wellHover : Theme.well
        border.width: card.armedRemoval === app.index ? 1 : 0
        border.color: Theme.bad
        scale: (1 + magnify) * (mouse.pressed ? 0.94 : 1)
        transform: Translate { x: tileItem.dx; y: tileItem.hop + tileItem.dy }
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
            source: tileItem.app.hasIcon ? "image://appicon/" + tileItem.app.index + "?" + tileItem.app.iconKey : ""
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
            enabled: !card.editing
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: function(event) { if (card.press(event, tileItem.app)) hopAnimation.restart() }
        }
    }

    summary: Component {
        Item {
            id: board
            HoverHandler { id: boardHover; enabled: !card.editing }
            // Tiles sit in slots placed by hand (not a Grid) so a dragged one can open a gap:
            // while it moves, the others shift to where they would end up, and the order is
            // saved when it is let go.
            Item {
                id: grid
                x: Theme.pad; y: Theme.pad
                width: parent.width - Theme.pad * 2
                readonly property real gapX: (width - card.columns * card.tile) / (card.columns - 1)
                property int dragFrom: -1
                property int dragTo: -1
                function slotX(slot) { return slot % card.columns * (card.tile + gapX) }
                function slotY(slot) { return Math.floor(slot / card.columns) * (card.tile + 8) }
                function shown(i) {
                    if (dragFrom < 0 || i === dragFrom) return i
                    if (dragFrom < dragTo && i > dragFrom && i <= dragTo) return i - 1
                    if (dragFrom > dragTo && i >= dragTo && i < dragFrom) return i + 1
                    return i
                }
                function slotAt(px, py) {
                    const col = Math.max(0, Math.min(card.columns - 1, Math.round(px / (card.tile + gapX))))
                    const row = Math.max(0, Math.min(card.rows - 1, Math.round(py / (card.tile + 8))))
                    return Math.min(card.apps.length - 1, row * card.columns + col)
                }
                Repeater {
                    id: tiles
                    model: card.apps
                    AppTile {
                        id: tileView
                        required property var modelData
                        required property int index
                        readonly property bool lifted: tileDrag.active
                        app: modelData
                        x: grid.slotX(lifted ? index : grid.shown(index))
                        y: grid.slotY(lifted ? index : grid.shown(index))
                        Behavior on x { enabled: grid.dragFrom >= 0 && !tileView.lifted; NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        Behavior on y { enabled: grid.dragFrom >= 0 && !tileView.lifted; NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        dx: lifted ? tileDrag.activeTranslation.x : 0
                        dy: lifted ? tileDrag.activeTranslation.y : 0
                        z: lifted ? 10 : hovered ? 2 : magnify > 0.05 ? 1 : 0
                        rotation: card.editing && !lifted && card.dock
                            ? 2 * Math.sin(2 * Math.PI * (card.dock.wobbleClock * 2.6 + index * 0.31)) : 0
                        magnify: lifted ? 0.15
                            : boardHover.hovered
                            ? Theme.magnifyTile * Theme.magnify(Math.hypot(boardHover.point.position.x - grid.x - x - width / 2,
                                                                          boardHover.point.position.y - grid.y - y - height / 2), 70)
                            : 0
                        DragHandler {
                            id: tileDrag
                            enabled: card.editing
                            target: null
                            onActiveChanged: {
                                if (active) {
                                    grid.dragFrom = tileView.index; grid.dragTo = tileView.index
                                } else {
                                    const from = grid.dragFrom, to = grid.dragTo
                                    grid.dragFrom = -1
                                    if (from >= 0 && to !== from) launcherBackend.move(from, to)
                                }
                            }
                            onActiveTranslationChanged: if (active)
                                grid.dragTo = grid.slotAt(grid.slotX(tileView.index) + activeTranslation.x,
                                                          grid.slotY(tileView.index) + activeTranslation.y)
                        }
                        // Remove, like a home-screen icon.
                        Rectangle {
                            visible: card.editing && !tileView.lifted
                            x: -5; y: -5; width: 16; height: 16; radius: 8
                            color: "#E63A3A42"
                            border.width: 1; border.color: Theme.stroke
                            Text {
                                anchors.centerIn: parent; anchors.verticalCenterOffset: -1
                                text: "−"; color: Theme.ink
                                font.family: dockFont; font.pixelSize: 12; font.weight: Font.DemiBold
                            }
                            TapHandler { onTapped: launcherBackend.remove(tileView.index) }
                        }
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
                opacity: target && card.armedRemoval < 0 && !card.editing ? 1 : 0
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
                visible: !card.editing
                x: Theme.pad; width: parent.width - Theme.pad * 2
                y: parent.height - 26; height: 16
                text: card.caption.length ? card.caption : card.apps.length ? "" : "앱이나 웹 주소를 끌어다 놓아 추가"
                color: card.armedRemoval >= 0 ? Theme.bad : Theme.inkSecondary
                horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                font.family: dockFont; font.pixelSize: 11
            }
            // Edit mode: type a web address to add it.
            Rectangle {
                visible: card.editing
                x: Theme.pad; width: parent.width - Theme.pad * 2
                y: parent.height - 28; height: 22; radius: 11
                color: Theme.well
                border.width: address.activeFocus ? 1 : 0; border.color: Theme.stroke
                TextInput {
                    id: address
                    anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.ink
                    font.family: dockFont; font.pixelSize: 11
                    clip: true; selectByMouse: true
                    enabled: card.apps.length < 12
                    onAccepted: if (launcherBackend.addWebsite(text)) text = ""
                }
                Text {
                    anchors.fill: address
                    verticalAlignment: Text.AlignVCenter
                    visible: !address.text.length
                    text: card.apps.length >= 12 ? "최대 12개까지 넣을 수 있어요" : "＋ 웹 주소 (예: naver.com)"
                    color: Theme.inkTertiary; elide: Text.ElideRight
                    font.family: dockFont; font.pixelSize: 11
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
