import QtQuick

// The dock column on the chosen edge of the window. Cells never grow over each
// other: an open card's detail shows in one shared flyout beside the column,
// which slides from card to card as the pointer moves, so every cell stays
// visible and reachable. The window is wide enough for the flyout; dockHost
// masks input to the column, its drag grip and an open flyout, so the rest
// passes clicks to the desktop.
// Two layouts: bento cards, or a minimized rail of icons (dockHost.minimized)
// that widens into labels on hover. Which modules show, and in what order,
// comes from dockPrefs.modules; the grip above the column moves the dock up
// and down its edge (dock/position).
Item {
    id: dock
    width: 540
    height: 900

    // Preview/check hooks: open one card, place a pointer, or open the rail without a mouse.
    property string forcedCard: ""
    property real forcedPointerY: -1
    property real forcedRailOpen: -1
    readonly property bool mirrored: dockHost.edge === "left"
    // Desktop icon grid (from dockHost): the bento block fills whole icon cells, so desktop
    // icons line up beside, above and below it. Empty when off or not found.
    readonly property var grid: dockHost.grid
    readonly property bool gridOn: !!grid && grid.cellW > 0
    readonly property real cellH: gridOn ? grid.cellH : 0
    readonly property real bentoWidth: column.bentoW
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
    onRailChanged: openCard = ""
    readonly property real railOpen: forcedRailOpen >= 0 ? forcedRailOpen : railOpenAnimated
    property real railOpenAnimated: rail && pointer.hovered ? 1 : 0
    Behavior on railOpenAnimated { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
    // Pointer height in dock coordinates for the magnification, -1 when away.
    readonly property real pointerY: forcedPointerY >= 0 ? forcedPointerY
        : pointer.hovered && !grip.dragging ? pointer.point.position.y : -1

    HoverHandler { id: pointer; onHoveredChanged: dock.scheduleMask() }

    // ---- which card is open ---------------------------------------------------
    // Resting on a card opens it; moving to another card while one is open
    // switches after a short pause, unless the pointer reaches the flyout first
    // (it may cross a neighbour on its way there). Leaving everything closes it.
    property string openCard: ""
    property string pendingCard: ""
    onOpenCardChanged: scheduleMask()

    function anyCardHovered() {
        for (const card of cards) if (card.visible && card.expandable && card.hovered) return true
        return false
    }
    function cardHover(card, on) {
        if (on) {
            if (!card.expandable) {
                pendingCard = ""; openTimer.stop(); switchTimer.stop()
                if (openCard.length) closeTimer.restart()
                return
            }
            closeTimer.stop()
            pendingCard = card.cardId
            if (openCard === card.cardId) switchTimer.stop()
            else if (openCard.length) switchTimer.restart()
            else if (!rail) openTimer.restart()   // on the rail a click opens
        } else {
            if (pendingCard === card.cardId) { pendingCard = ""; openTimer.stop(); switchTimer.stop() }
            closeTimer.restart()
        }
    }
    function openNow(id) { closeTimer.stop(); switchTimer.stop(); openCard = id }
    Timer { id: openTimer; interval: Theme.hoverOpenDelay; onTriggered: if (dock.pendingCard.length) dock.openCard = dock.pendingCard }
    Timer {
        id: switchTimer; interval: 160
        onTriggered: if (dock.pendingCard.length && !flyoutHover.hovered) dock.openCard = dock.pendingCard
    }
    Timer {
        id: closeTimer; interval: Theme.hoverCloseDelay
        onTriggered: if (!flyoutHover.hovered && !dock.anyCardHovered()) dock.openCard = ""
    }

    // ---- input mask -------------------------------------------------------------
    function scheduleMask() { maskTimer.restart() }
    function pushMask() {
        // Moving or morphing: open the column's whole vertical band so nothing is clipped
        // mid-motion; the tight shape comes back once it has settled.
        const morphing = railness > 0 && railness < 1 || moving
        const widest = rail && (pointer.hovered || railOpen > 0) ? Theme.railWidth + Theme.railLabelWidth : column.width
        const w = morphing ? Math.max(column.bentoW, widest) : widest
        const top = morphing ? 0 : column.y - 24        // the grip sits above the column
        const h = morphing ? height : column.height + 30
        const left = mirrored ? column.x : column.x + column.width - w
        // Outset so magnified cells, antialiased rims and the lifted shadow are never clipped.
        const pad = moving ? 40 : 10
        const rects = [[left - pad, top - 6, w + 2 * pad, h + 12]]
        if (activeCard.length || flyout.visible) {
            // The flyout's whole lane, so it can slide between cards without reshaping the window.
            const laneLeft = mirrored ? column.x + column.width : column.x - Theme.detailWidth - 60
            rects.push([laneLeft, 0, Theme.detailWidth + 60, height])
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
    onMovingChanged: scheduleMask()

    // ---- vertical position ------------------------------------------------------
    property real position: dockPrefs.get("dock/position")
    // Dragging, or the cards still springing into place after the drop.
    readonly property bool moving: grip.held || settle.running
    // Cards spring only here, after the drop; a new grab stops it (see the grip).
    readonly property bool settling: settle.running
    readonly property real columnY: column.y
    // Picked-up feel while the grip is held: the column swells a touch and casts a shadow.
    property real dragLift: grip.dragging ? 1 : 0
    Behavior on dragLift { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Timer { id: settle; interval: 700 }
    // Past either end the dock gives way less and less, like a rubber band.
    function rubber(value, low, high) {
        if (value < low) return low - (low - value) * 0.35 / (1 + (low - value) / 160)
        if (value > high) return high + (value - high) * 0.35 / (1 + (value - high) / 160)
        return value
    }
    Connections {
        target: dockPrefs
        function onChanged(key) { if (key === "dock/position") dock.position = dockPrefs.get(key) }
    }

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
            Rectangle { x: 410; y: 470; width: 180; height: 180; radius: 90; color: "#4433A1C9" }
        }
    }

    Item {
        id: column
        readonly property real gapBento: Theme.gap
        readonly property real gapRail: 6
        readonly property real railW: Theme.railWidth + Theme.railLabelWidth * dock.railOpen
        // Bento width: whole icon cells less a 5 px inset on each side, or the default width.
        readonly property real bentoW: dock.gridOn ? dock.grid.width - 10 : Theme.dockWidth
        readonly property real half: (bentoW - gapBento) / 2
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
                bento[id] = { x: 0, y: y, w: bentoW }
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
            return mix(b.x, 0)   // on the rail every cell spans the column
        }

        width: mix(bentoW, railW)
        height: mix(layout.bentoHeight, layout.railHeight)
        // Plain x, not anchors: switching left/right anchors at run time leaves both attached.
        // On the grid the column sits in its icon cells, flush with the outer edge of the block.
        x: dock.gridOn ? (dock.mirrored ? dock.grid.x + 5 : dock.grid.x + dock.grid.width - 5 - width)
                       : (dock.mirrored ? 12 : dock.width - width - 12)
        // Centre at the saved position along the edge, kept fully on screen (room for the grip above).
        readonly property real minY: dock.gridOn ? dock.grid.y + 5 : 30
        readonly property real maxY: dock.height - height - 12
        readonly property real wantY: (grip.held ? grip.dragPosition : dock.position) * dock.height - height / 2
        // On the grid the bento block rests on a row of icon cells.
        readonly property int blockRows: dock.gridOn ? Math.round((layout.bentoHeight + 10) / dock.cellH) : 0
        function rowY(y) {
            const row = Math.round((y - dock.grid.y - 5) / dock.cellH)
            return dock.grid.y + 5 + Math.max(0, Math.min(dock.grid.rows - blockRows, row)) * dock.cellH
        }
        readonly property real restY: dock.gridOn && !dock.rail ? rowY(wantY) : Math.max(minY, Math.min(maxY, wantY))
        y: grip.held ? dock.rubber(wantY, minY, maxY) : restY
        scale: 1 + 0.02 * dock.dragLift
        transformOrigin: dock.mirrored ? Item.Left : Item.Right
        onYChanged: if (!(dock.railness > 0 && dock.railness < 1) && !dock.moving) dock.scheduleMask()
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

    // ---- drag grip: move the dock up and down its edge --------------------------
    Item {
        id: grip
        objectName: "grip"
        readonly property bool dragging: drag.active
        // Follows the drag, but is released only after the drop position is saved, so the
        // column never flashes back to its old place between the two.
        property bool held: false
        property real dragPosition: 0.5
        property real startPosition: 0.5
        width: 56; height: 20
        x: column.x + (column.width - width) / 2
        // Above the dock, or below it when the dock rests on the top row.
        y: column.y - height - 4 >= 0 ? column.y - height - 4 : column.y + column.height + 4
        opacity: dragging ? 1 : gripHover.hovered ? 0.95 : pointer.hovered ? 0.5 : 0
        Behavior on opacity { NumberAnimation { duration: 160 } }
        Rectangle {
            anchors.centerIn: parent
            width: grip.dragging ? 48 : gripHover.hovered ? 40 : 30; height: 5; radius: 2.5
            color: grip.dragging ? Theme.charge : Theme.ink
            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on width { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
        HoverHandler { id: gripHover; cursorShape: Qt.SizeVerCursor }
        DragHandler {
            id: drag
            target: null
            xAxis.enabled: false
            onActiveChanged: {
                if (active) {
                    grip.startPosition = dock.position
                    grip.dragPosition = dock.position
                    settle.stop()
                    grip.held = true
                    dock.openCard = ""
                } else {
                    // Drop: back inside the screen and onto the nearest icon row (or, off the
                    // grid, onto the top, middle or bottom when close); the cards spring the
                    // rest of the way (settle).
                    const h = column.height
                    let y = Math.max(column.minY, Math.min(column.maxY, grip.dragPosition * dock.height - h / 2))
                    if (dock.gridOn && !dock.rail)
                        y = column.rowY(y)
                    else
                        for (const stop of [column.minY, (dock.height - h) / 2, column.maxY])
                            if (Math.abs(y - stop) < 36) { y = stop; break }
                    settle.restart()
                    dockPrefs.set("dock/position", (y + h / 2) / dock.height)
                    grip.held = false
                }
            }
            onActiveTranslationChanged: grip.dragPosition = grip.startPosition + activeTranslation.y / dock.height
        }
    }

    // ---- the shared flyout ------------------------------------------------------
    readonly property real flyoutOpen: {
        let open = 0
        for (const card of cards) if (card.visible) open = Math.max(open, card.progress)
        return open
    }
    // The card whose detail is on show; kept through the close animation.
    property Item shownCard: null
    onActiveCardChanged: {
        scheduleMask()
        if (activeCard.length) shownCard = cardsById[activeCard]
    }

    Item {
        id: flyout
        objectName: "flyout"
        readonly property real open: Math.min(1, dock.flyoutOpen)
        visible: dock.shownCard !== null && dock.flyoutOpen > 0.002
        width: dock.shownCard ? dock.shownCard.detailWidth : Theme.detailWidth
        height: dock.shownCard ? dock.shownCard.detailHeight : 180
        Behavior on width { enabled: flyout.open > 0.3; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        Behavior on height { enabled: flyout.open > 0.3; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        // Level with its card, kept on screen; slides when the open card changes.
        y: dock.shownCard ? Math.max(10, Math.min(dock.height - height - 10, column.y + dock.shownCard.y)) : 0
        Behavior on y { enabled: flyout.open > 0.3; SpringAnimation { spring: 5; damping: 0.42; epsilon: 0.25 } }
        // Beside the column on the screen side, easing out from the dock as it opens.
        readonly property real slide: 14 * (1 - Math.min(1, dock.flyoutOpen))
        x: dock.mirrored ? column.x + column.width + 12 - slide : column.x - 12 - width + slide
        opacity: Math.min(1, dock.flyoutOpen * 1.6)
        scale: 0.94 + 0.06 * open
        transformOrigin: dock.mirrored ? Item.Left : Item.Right

        GlassSurface {
            anchors.fill: parent
            lifted: true
            lift: flyout.open
        }
        Item {
            anchors.fill: parent
            clip: true
            Loader {
                width: dock.shownCard ? dock.shownCard.detailWidth : 0
                height: dock.shownCard ? dock.shownCard.detailHeight : 0
                sourceComponent: dock.shownCard ? dock.shownCard.detail : null
                enabled: dock.activeCard.length > 0 && dock.flyoutOpen > 0.9
            }
        }
        HoverHandler {
            id: flyoutHover
            onHoveredChanged: {
                if (hovered) { closeTimer.stop(); switchTimer.stop(); dock.pendingCard = "" }
                else closeTimer.restart()
            }
        }
    }
}
