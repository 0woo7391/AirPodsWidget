import QtQuick
import QtQuick.Shapes

Shape {
    id: glyph
    property color ink: "#DCE3EF"
    width: 18; height: 18
    ShapePath {
        strokeColor: glyph.ink; strokeWidth: 1.75; fillColor: "transparent"
        capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
        startX: 5.25; startY: 5.25
        PathLine { x: 12.75; y: 12.75 }
        PathLine { x: 9; y: 16.5 }
        PathLine { x: 9; y: 1.5 }
        PathLine { x: 12.75; y: 5.25 }
        PathLine { x: 5.25; y: 12.75 }
    }
}
