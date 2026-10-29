import QtQuick
import QtQuick.Shapes

Shape {
    id: glyph
    property string kind: "pin"
    property bool selected: false
    width: 18; height: 18
    ShapePath {
        strokeColor: "#F0F0F0"; strokeWidth: 1.75
        fillColor: glyph.kind==="pin" && glyph.selected ? "#F0F0F0" : "transparent"
        capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
        PathSvg {
            path: glyph.kind==="pin"
                ? "M6 2H12L11 7L14 10V12H10V17H8V12H4V10L7 7Z"
                : "M2 3H16V12H2Z M6 16H12 M9 12V16"
        }
    }
}
