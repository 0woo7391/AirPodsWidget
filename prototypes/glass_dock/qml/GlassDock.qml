import QtQuick

// The dock column on the right edge of the window. The window is wider than
// the column so a hovered card has room to grow left; dockHost masks input to
// the column (and a grown card), so the rest passes clicks to the desktop.
// Two layouts: bento cards, or a minimized rail of icons (dockHost.minimized)
// that widens into labels on hover. Cards morph between the two.
Item {
    id: dock
    width: 340
    height: 900

    // Preview/check hooks: expand one card, place a pointer, or open the rail without a mouse.
    property string forcedCard: ""
    property real forcedPointerY: -1
    property real forcedRailOpen: -1
    readonly property var cards: [airpods, media, volume, output, launcher]
    readonly property string activeCard: {
        for (const card of cards) if (card.expanded) return card.cardId
        return ""
    }

    property real railness: dockHost.minimized ? 1 : 0
    Behavior on railness { NumberAnimation { duration: 420; easing.type: Easing.InOutCubic } }
    readonly property bool rail: railness > 0.5
    readonly property real railOpen: forcedRailOpen >= 0 ? forcedRailOpen : railOpenAnimated
    property real railOpenAnimated: rail && pointer.hovered ? 1 : 0
    Behavior on railOpenAnimated { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
    // Pointer height in dock coordinates for the magnification, -1 when away.
    readonly property real pointerY: forcedPointerY >= 0 ? forcedPointerY
        : pointer.hovered ? pointer.point.position.y : -1

    HoverHandler { id: pointer; onHoveredChanged: dock.scheduleMask() }

    function scheduleMask() { maskTimer.restart() }
    function pushMask() {
        const morphing = railness > 0 && railness < 1
        const widest = rail && (pointer.hovered || railOpen > 0) ? Theme.railWidth + Theme.railLabelWidth : column.width
        const w = morphing ? Theme.dockWidth : widest
        const top = morphing ? 0 : column.y
        const h = morphing ? height : column.height
        // Outset so magnified cells and antialiased rims are never clipped.
        const rects = [[column.x + column.width - w - 10, top - 6, w + 20, h + 12]]
        for (const card of cards) {
            const r = card.maskRect()
            if (r) rects.push(r)
        }
        dockHost.updateMask(rects)
    }
    Timer { id: maskTimer; interval: 0; onTriggered: dock.pushMask() }
    Component.onCompleted: scheduleMask()
    onWidthChanged: scheduleMask()
    onHeightChanged: scheduleMask()
    onRailnessChanged: if (railness === 0 || railness === 1 || railness > 0.001 && railness < 0.05) scheduleMask()
    onRailOpenChanged: if (railOpen === 0 || railOpen > 0.99) scheduleMask()

    // Stand-in wallpaper for previews only; the real dock sits on the desktop.
    Loader {
        anchors.fill: parent
        active: previewBackdrop
        sourceComponent: Rectangle {
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#3B4A6B" }
                GradientStop { position: 0.5; color: "#7A5C7E" }
                GradientStop { position: 1.0; color: "#D08C6A" }
            }
            Rectangle { x: 40; y: 120; width: 220; height: 220; radius: 110; color: "#55F2C14E" }
            Rectangle { x: 210; y: 470; width: 180; height: 180; radius: 90; color: "#4433A1C9" }
        }
    }

    Item {
        id: column
        readonly property real gapBento: Theme.gap
        readonly property real gapRail: 6
        readonly property real railW: Theme.railWidth + Theme.railLabelWidth * dock.railOpen
        readonly property real half: (Theme.dockWidth - gapBento) / 2
        function mix(a, b) { return a + (b - a) * dock.railness }

        // Bento: AirPods, media, volume | output, launcher. Rail: all five stacked.
        readonly property real bentoY1: airpods.cellHeight + gapBento
        readonly property real bentoY2: bentoY1 + media.cellHeight + gapBento
        readonly property real bentoY3: bentoY2 + Math.max(volume.cellHeight, output.cellHeight) + gapBento
        readonly property real bentoHeight: bentoY3 + launcher.cellHeight
        readonly property real railY1: airpods.cellHeight + gapRail
        readonly property real railY2: railY1 + media.cellHeight + gapRail
        readonly property real railY3: railY2 + volume.cellHeight + gapRail
        readonly property real railY4: railY3 + output.cellHeight + gapRail
        readonly property real railHeight: railY4 + launcher.cellHeight

        width: mix(Theme.dockWidth, railW)
        height: mix(bentoHeight, railHeight)
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        onYChanged: if (!(dock.railness > 0 && dock.railness < 1)) dock.scheduleMask()
        onHeightChanged: if (!(dock.railness > 0 && dock.railness < 1)) dock.scheduleMask()

        AirPodsCard {
            id: airpods
            dock: dock; railIndex: 0
            width: column.width; x: 0; y: 0
            dockLeft: column.x + x; dockTop: column.y + y
        }
        MediaCard {
            id: media
            dock: dock; railIndex: 1
            width: column.width; x: 0; y: column.mix(column.bentoY1, column.railY1)
            dockLeft: column.x + x; dockTop: column.y + y
        }
        VolumeCard {
            id: volume
            dock: dock; railIndex: 2
            width: column.mix(column.half, column.railW)
            x: column.width - width - (column.half + column.gapBento) * (1 - dock.railness)
            y: column.mix(column.bentoY2, column.railY2)
            dockLeft: column.x + x; dockTop: column.y + y
        }
        OutputCard {
            id: output
            dock: dock; railIndex: 3
            width: column.mix(column.half, column.railW)
            x: column.width - width
            y: column.mix(column.bentoY2, column.railY3)
            dockLeft: column.x + x; dockTop: column.y + y
        }
        LauncherCard {
            id: launcher
            dock: dock; railIndex: 4
            width: column.width; x: 0; y: column.mix(column.bentoY3, column.railY4)
            dockLeft: column.x + x; dockTop: column.y + y
        }
    }
}
