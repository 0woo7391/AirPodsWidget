import QtQuick
import QtQuick.Effects

// AirPods (or calendar) notice that grows out of a small pill at the top of the screen.
// One show runs 4 s: spring open from a = 0, spring closed from a = 3.3, then
// the resting pill fades; a calendar reminder stays open 4 s longer. The window is input-transparent, so the island
// never takes a click. It wears the dock's glass: dark tint, hairline rim,
// top sheen, neutral shadow; colour only in the small status marks.
Item {
    id: island
    // Size from the settings (island/scale); the window follows the root's size.
    property real s: dockPrefs.get("island/scale")
    Connections {
        target: dockPrefs
        function onChanged(key) { if (key === "island/scale") island.s = dockPrefs.get(key) }
    }
    width: Math.round(470 * s)
    height: Math.round(228 * s)
    // One-shot on the desktop, not a loop: the resting pill fades instead of popping off.
    opacity: 1 - Theme.seg(t, closeAt + 0.45, duration)

    property string title: ""
    property string subtitle: ""
    property string tone: "connected"   // connected | disconnected | low | micOn | micOff | event
    property var batteries: []          // [{label, value, charging}] for L, R, case
    property color mark: Theme.charge   // an event's colour
    readonly property bool eventTone: tone === "event"


    // Seconds since the notification appeared; driven by the frame clock.
    property real a: 4
    // Preview/check hook: render one moment of the animation without the clock.
    property real forcedTime: -1
    readonly property real t: forcedTime >= 0 ? forcedTime : a
    readonly property real closeAt: eventTone ? 7.3 : 3.3
    readonly property real duration: closeAt + 0.7

    signal finished()

    function show(newTitle, newSubtitle, newTone, newBatteries, newMark) {
        title = newTitle
        subtitle = newSubtitle
        tone = newTone
        batteries = newBatteries || []
        mark = newMark || Theme.charge
        a = 0
    }

    function clamp01(v) { return Math.max(0, Math.min(1, v)) }
    readonly property real p: t < closeAt ? Theme.spring(13, 0.6, t) : 1 - Theme.spring(15, 0.62, t - closeAt)
    readonly property real contentOpacity: Theme.seg(t, 0.16, 0.36) * (1 - Theme.seg(t, closeAt, closeAt + 0.12))
    // The same status colours as the dock's dots.
    readonly property color accent: eventTone ? mark : tone === "low" ? Theme.warn : tone === "disconnected" ? Theme.inkTertiary
        : tone === "micOff" ? Theme.bad : Theme.good
    readonly property bool micTone: tone === "micOn" || tone === "micOff"

    function levelColor(part) {
        return part.charging ? Theme.charge : part.value <= 10 ? Theme.bad : part.value <= 20 ? Theme.warn : Theme.good
    }

    FrameAnimation {
        running: island.forcedTime < 0 && island.a < island.duration
        onTriggered: {
            island.a = Math.min(island.duration, island.a + frameTime)
            if (island.a >= island.duration) island.finished()
        }
    }

    // Laid out at 470 x 228 and scaled as a whole.
    Item {
        id: stage
        width: 470
        height: 228
        scale: island.s
        transformOrigin: Item.TopLeft

        Rectangle {
            id: card
            // Whole pixels keep the rim crisp while the size springs.
            width: Math.round(128 + 282 * island.p)
            height: Math.round(36 + 88 * island.p)
            x: Math.round((stage.width - width) / 2)
            y: 16
            radius: Math.min(18 + 22 * island.clamp01(island.p), height / 2)
            color: "#1C1C22"
            border.width: 1
            border.color: Theme.strokeLit
            clip: true
            visible: false

            // Top sheen and lit top edge, as on the dock's glass.
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#1FFFFFFF" }
                    GradientStop { position: 0.45; color: "#05FFFFFF" }
                    GradientStop { position: 1.0; color: "#00FFFFFF" }
                }
            }
            Rectangle {
                x: parent.radius * 0.7; y: 1
                width: parent.width - parent.radius * 1.4; height: 1
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#00FFFFFF" }
                    GradientStop { position: 0.5; color: "#73FFFFFF" }
                    GradientStop { position: 1.0; color: "#00FFFFFF" }
                }
            }

            Rectangle {
                width: 10; height: 10; radius: 5
                x: parent.width - 22 - 5
                anchors.verticalCenter: parent.verticalCenter
                color: island.accent
                opacity: island.clamp01(1 - island.p / 0.3) * (0.55 + 0.45 * Math.sin(2 * Math.PI * island.t / 2))
            }

            Item {
                anchors.fill: parent
                opacity: island.contentOpacity

                Rectangle {
                    id: avatar
                    width: 62; height: 62; radius: 31
                    x: 55 - 31
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.wellHover
                    border.width: 1; border.color: Theme.stroke
                    DockIcon {
                        anchors.centerIn: parent
                        opacity: island.eventTone ? 0 : 1
                        size: 30
                        name: island.micTone ? "microphone" : "headphones"
                        pose: island.tone === "micOff" ? "muted" : ""
                        color: island.tone === "disconnected" ? Theme.inkSecondary : Theme.ink
                    }
                }
                // A calendar leaf for reminders: today's date under a band in the event's colour.
                Item {
                    opacity: island.eventTone ? 1 : 0
                    anchors.centerIn: avatar
                    width: 34; height: 36
                    Rectangle {
                        anchors.fill: parent
                        radius: 8
                        color: "#2A2A32"
                        border.width: 1; border.color: Theme.stroke
                    }
                    Rectangle {
                        width: parent.width; height: 11; radius: 8
                        color: island.mark
                        Rectangle { y: 5; width: parent.width; height: 6; color: island.mark }
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 13
                        text: new Date().getDate()
                        color: Theme.ink
                        font.family: dockFont; font.pixelSize: 17; font.weight: Font.DemiBold
                        font.features: Theme.numberFeatures
                    }
                }
                // Status badge on the avatar: check when connected, ! when low.
                Rectangle {
                    // Opacity, not visible: an item turning visible inside the hidden effect source
                    // is not redrawn when the same island window is reused.
                    opacity: island.tone === "connected" || island.tone === "low" ? 1 : 0
                    width: 22; height: 22; radius: 11
                    x: avatar.x + 44; y: avatar.y + 42
                    color: island.accent
                    border.width: 3; border.color: "#1C1C22"
                    Text {
                        anchors.centerIn: parent
                        text: island.tone === "low" ? "!" : "✓"
                        color: "#1C1C22"
                        font.family: dockFont; font.pixelSize: 12; font.weight: Font.Bold
                    }
                }

                Text {
                    x: 102
                    width: batteryRow.x - x - 10
                    // Baseline 4 px above the card's center.
                    y: parent.height / 2 - 4 - baselineOffset
                    text: island.title
                    elide: Text.ElideRight
                    color: Theme.ink
                    font.family: dockFont
                    font.pixelSize: 24
                    font.weight: Font.DemiBold
                }
                Text {
                    x: 102
                    width: batteryRow.x - x - 10
                    y: parent.height / 2 + 20 - baselineOffset
                    text: island.subtitle
                    elide: Text.ElideRight
                    color: island.tone === "low" ? Theme.warn : island.tone === "micOff" ? Theme.bad : Theme.inkSecondary
                    font.family: dockFont
                    font.pixelSize: 18
                    font.weight: Font.Medium
                }

                // L / R / case levels on the right.
                Row {
                    id: batteryRow
                    x: parent.width - width - 24
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    opacity: island.batteries.length > 0 ? 1 : 0
                    Repeater {
                        model: island.batteries
                        Column {
                            required property var modelData
                            required property int index
                            spacing: 5
                            opacity: Theme.seg(island.t, 0.3 + 0.06 * index, 0.5 + 0.06 * index)
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: ["L", "R", "C"][index]
                                color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 11; font.weight: Font.DemiBold
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.value < 0 ? "—" : modelData.value
                                color: Theme.ink; font.family: dockFont; font.pixelSize: 17; font.weight: Font.DemiBold
                                font.features: Theme.numberFeatures
                            }
                            Rectangle {
                                width: 24; height: 4; radius: 2; color: Theme.well
                                Rectangle {
                                    width: modelData.value < 0 ? 0 : Math.max(4, 24 * Math.min(100, modelData.value) / 100 * Theme.seg(island.t, 0.35, 0.8))
                                    height: 4; radius: 2
                                    color: island.levelColor(modelData)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Neutral drop shadow, like the dock's raised flyout.
        MultiEffect {
            source: card
            anchors.fill: card
            shadowEnabled: true
            shadowColor: "#000000"
            shadowOpacity: 0.55 * island.clamp01(island.p)
            shadowBlur: 1.0
            blurMax: 32
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 8
            visible: island.t < island.duration
        }
    }
}
