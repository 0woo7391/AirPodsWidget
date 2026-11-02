import QtQuick

// The dock column on the chosen edge of the window. The window is wider than
// the column so a hovered card has room to grow inward; dockHost masks input
// to the column (and a grown card), so the rest passes clicks to the desktop.
// Two layouts: bento cards, or a minimized rail of icons (dockHost.minimized)
// that widens into labels on hover. Cards morph between the two. Which modules
// show, and in what order, comes from dockPrefs.modules.
Item {
    id: dock
    width: 340
    height: 900

    // Preview/check hooks: expand one card, place a pointer, or open the rail without a mouse.
    property string forcedCard: ""
    property real forcedPointerY: -1
    property real forcedRailOpen: -1
    readonly property bool mirrored: dockHost.edge === "left"
    readonly property var cardsById: ({ airpods: airpods, media: media, volume: volume, output: output, launcher: launcher })
    readonly property var cards: [airpods, media, volume, output, launcher]
    readonly property var order: dockPrefs.modules.filter(m => m.visible).map(m => m.id)
    readonly property string activeCard: {
        for (const card of cards) if (card.visible && card.expanded) return card.cardId
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
        const left = mirrored ? column.x : column.x + column.width - w
        // Outset so magnified cells and antialiased rims are never clipped.
        const rects = [[left - 10, top - 6, w + 20, h + 12]]
        for (const card of cards) {
            const r = card.visible ? card.maskRect() : null
            if (r) rects.push(r)
        }
        dockHost.updateMask(rects)
    }
    Timer { id: maskTimer; interval: 0; onTriggered: dock.pushMask() }
    Component.onCompleted: scheduleMask()
    onWidthChanged: scheduleMask()
    onHeightChanged: scheduleMask()
    onMirroredChanged: scheduleMask()
    onOrderChanged: scheduleMask()
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

        // Cell rectangles for both layouts. Bento: modules in order, full width,
        // except that volume and output share a row when they are next to each other.
        // Rail: all stacked. Rail x/width follow the widening labels.
        readonly property var layout: {
            const halves = ["volume", "output"]
            const bento = {}, rail = {}
            let y = 0, r = 0
            const ids = dock.order
            for (let i = 0; i < ids.length; i++) {
                const id = ids[i], card = dock.cardsById[id]
                const next = ids[i + 1]
                if (halves.indexOf(id) >= 0 && next && halves.indexOf(next) >= 0) {
                    const other = dock.cardsById[next]
                    bento[id] = { x: 0, y: y, w: half }
                    bento[next] = { x: half + gapBento, y: y, w: half }
                    y += Math.max(card.cellHeight, other.cellHeight) + gapBento
                    rail[id] = { y: r }
                    r += card.cellHeight + gapRail
                    rail[next] = { y: r }
                    r += other.cellHeight + gapRail
                    i++
                    continue
                }
                bento[id] = { x: 0, y: y, w: Theme.dockWidth }
                y += card.cellHeight + gapBento
                rail[id] = { y: r }
                r += card.cellHeight + gapRail
            }
            return { bento: bento, rail: rail, bentoHeight: Math.max(0, y - gapBento), railHeight: Math.max(0, r - gapRail) }
        }
        function place(id, key) {
            const b = layout.bento[id], r = layout.rail[id]
            if (!b) return 0
            if (key === "y") return mix(b.y, r.y)
            if (key === "w") return mix(b.w, railW)
            // On the rail every cell spans the column.
            return mix(b.x, 0)
        }

        width: mix(Theme.dockWidth, railW)
        height: mix(layout.bentoHeight, layout.railHeight)
        anchors.right: dock.mirrored ? undefined : parent.right
        anchors.left: dock.mirrored ? parent.left : undefined
        anchors.rightMargin: 12
        anchors.leftMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        onYChanged: if (!(dock.railness > 0 && dock.railness < 1)) dock.scheduleMask()
        onHeightChanged: if (!(dock.railness > 0 && dock.railness < 1)) dock.scheduleMask()

        AirPodsCard {
            id: airpods
            dock: dock; railIndex: dock.order.indexOf(cardId)
            visible: railIndex >= 0
            x: column.place(cardId, "x"); y: column.place(cardId, "y"); width: column.place(cardId, "w")
            dockLeft: column.x + x; dockTop: column.y + y
        }
        MediaCard {
            id: media
            dock: dock; railIndex: dock.order.indexOf(cardId)
            visible: railIndex >= 0
            x: column.place(cardId, "x"); y: column.place(cardId, "y"); width: column.place(cardId, "w")
            dockLeft: column.x + x; dockTop: column.y + y
        }
        VolumeCard {
            id: volume
            dock: dock; railIndex: dock.order.indexOf(cardId)
            visible: railIndex >= 0
            x: column.place(cardId, "x"); y: column.place(cardId, "y"); width: column.place(cardId, "w")
            dockLeft: column.x + x; dockTop: column.y + y
        }
        OutputCard {
            id: output
            dock: dock; railIndex: dock.order.indexOf(cardId)
            visible: railIndex >= 0
            x: column.place(cardId, "x"); y: column.place(cardId, "y"); width: column.place(cardId, "w")
            dockLeft: column.x + x; dockTop: column.y + y
        }
        LauncherCard {
            id: launcher
            dock: dock; railIndex: dock.order.indexOf(cardId)
            visible: railIndex >= 0
            x: column.place(cardId, "x"); y: column.place(cardId, "y"); width: column.place(cardId, "w")
            dockLeft: column.x + x; dockTop: column.y + y
        }
    }
}
