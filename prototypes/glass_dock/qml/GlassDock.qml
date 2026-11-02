import QtQuick

// The dock column on the right edge of the window. The window is wider than
// the column so a hovered card has room to grow left; dockHost masks input to
// the cards, so the empty area passes clicks to the desktop.
Item {
    id: dock
    width: 340
    height: 900

    // Preview/check hook: expand one card by id without a pointer.
    property string forcedCard: ""
    readonly property var cards: [airpods, media, volume, output, launcher]
    readonly property string activeCard: {
        for (const card of cards) if (card.expanded) return card.cardId
        return ""
    }

    function scheduleMask() { maskTimer.restart() }
    function pushMask() {
        const rects = []
        for (const card of cards) rects.push(card.maskRect())
        dockHost.updateMask(rects)
    }
    Timer { id: maskTimer; interval: 0; onTriggered: dock.pushMask() }
    Component.onCompleted: scheduleMask()
    onWidthChanged: scheduleMask()
    onHeightChanged: scheduleMask()

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

    Column {
        id: column
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.dockWidth
        spacing: Theme.gap
        onYChanged: dock.scheduleMask()

        AirPodsCard {
            id: airpods
            width: parent.width; dock: dock
            dockLeft: column.x; dockTop: column.y + y
        }
        MediaCard {
            id: media
            width: parent.width; dock: dock
            dockLeft: column.x; dockTop: column.y + y
        }
        Row {
            id: pair
            width: parent.width
            spacing: Theme.gap
            z: volume.z + output.z
            VolumeCard {
                id: volume
                width: (pair.width - pair.spacing) / 2; dock: dock
                dockLeft: column.x; dockTop: column.y + pair.y
            }
            OutputCard {
                id: output
                width: (pair.width - pair.spacing) / 2; dock: dock
                dockLeft: column.x + x; dockTop: column.y + pair.y
            }
        }
        LauncherCard {
            id: launcher
            width: parent.width; dock: dock
            dockLeft: column.x; dockTop: column.y + y
        }
    }
}
