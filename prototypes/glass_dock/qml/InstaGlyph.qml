import QtQuick

// A line glyph in the spirit of the Instagram mark (rounded square, lens, dot),
// drawn in the dock's ink at the same stroke weight as the Lucian icons.
Item {
    id: glyph
    property real size: 18
    property color color: Theme.ink
    readonly property real stroke: Math.max(1.2, size * 0.085)
    width: size
    height: size

    Rectangle {
        anchors.fill: parent
        anchors.margins: glyph.size * 0.06
        radius: glyph.size * 0.28
        color: "transparent"
        border.width: glyph.stroke
        border.color: glyph.color
    }
    Rectangle {
        width: glyph.size * 0.44; height: width; radius: width / 2
        anchors.centerIn: parent
        color: "transparent"
        border.width: glyph.stroke
        border.color: glyph.color
    }
    Rectangle {
        width: glyph.size * 0.12; height: width; radius: width / 2
        x: glyph.size * 0.68; y: glyph.size * 0.2
        color: glyph.color
    }
}
