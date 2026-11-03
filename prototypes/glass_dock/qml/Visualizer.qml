import QtQuick

// Bars that move with what is actually playing: their height follows the output level
// (audioMeter.level), each bar on its own rhythm so the row ripples rather than pumps.
// It reacts to loudness, not to frequencies. Paused, the bars settle.
Row {
    id: viz
    property bool playing: false
    property int bars: 14
    property real barWidth: 3
    property real maxHeight: 16
    property color color: Theme.ink
    spacing: 2
    height: maxHeight

    // Rises fast, falls slowly, like a VU meter.
    property real level: 0
    property real clock: 0
    FrameAnimation {
        running: viz.visible && (viz.playing || viz.level > 0.01)
        onTriggered: {
            viz.clock += frameTime
            const target = viz.playing ? Math.min(1, audioMeter.level * 1.4) : 0
            viz.level += (target - viz.level) * (target > viz.level ? 0.5 : 0.12)
        }
    }

    Repeater {
        model: viz.bars
        Rectangle {
            required property int index
            readonly property real wobble: 0.45 + 0.55 * Math.abs(Math.sin(viz.clock * (2.1 + (index * 7 % 5) * 0.7) + index * 1.3))
            width: viz.barWidth
            height: Math.max(2, viz.maxHeight * viz.level * wobble)
            radius: width / 2
            anchors.bottom: parent.bottom
            color: viz.color
            opacity: 0.45 + 0.55 * viz.level
        }
    }
}
