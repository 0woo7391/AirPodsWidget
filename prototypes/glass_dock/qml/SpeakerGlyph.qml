import QtQuick
import QtQuick.Shapes

// A speaker whose sound waves follow the volume (none, one, two, three) and brighten
// with what is actually playing (`level`, 0..1). Muted: the waves go and an X is drawn.
Item {
    id: glyph
    property real size: 18
    property int volume: 50
    property bool muted: false
    property real level: 0
    property color color: Theme.ink
    readonly property real stroke: Math.max(1.3, size * 0.085)
    readonly property int waves: muted ? 0 : volume <= 0 ? 0 : volume < 34 ? 1 : volume < 67 ? 2 : 3
    width: size
    height: size

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        // Body: a small box and its cone.
        ShapePath {
            strokeColor: glyph.color; strokeWidth: glyph.stroke; fillColor: "transparent"
            joinStyle: ShapePath.RoundJoin; capStyle: ShapePath.RoundCap
            startX: glyph.size * 0.12; startY: glyph.size * 0.38
            PathLine { x: glyph.size * 0.28; y: glyph.size * 0.38 }
            PathLine { x: glyph.size * 0.48; y: glyph.size * 0.2 }
            PathLine { x: glyph.size * 0.48; y: glyph.size * 0.8 }
            PathLine { x: glyph.size * 0.28; y: glyph.size * 0.62 }
            PathLine { x: glyph.size * 0.12; y: glyph.size * 0.62 }
            PathLine { x: glyph.size * 0.12; y: glyph.size * 0.38 }
        }
    }
    Repeater {
        model: 3
        Shape {
            id: wave
            required property int index
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            opacity: index < glyph.waves ? 0.55 + 0.45 * Math.min(1, glyph.level * 1.6) : 0
            Behavior on opacity { NumberAnimation { duration: 160 } }
            scale: index < glyph.waves ? 1 : 0.8
            transformOrigin: Item.Left
            Behavior on scale { NumberAnimation { duration: 220; easing.type: Easing.OutBack } }
            ShapePath {
                strokeColor: glyph.color; strokeWidth: glyph.stroke; fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: glyph.size * 0.48; centerY: glyph.size * 0.5
                    radiusX: glyph.size * (0.16 + 0.15 * wave.index); radiusY: radiusX
                    startAngle: -40; sweepAngle: 80
                }
            }
        }
    }
    // Muted: an X where the waves were.
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        opacity: glyph.muted ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 160 } }
        ShapePath {
            strokeColor: glyph.color; strokeWidth: glyph.stroke; capStyle: ShapePath.RoundCap
            startX: glyph.size * 0.64; startY: glyph.size * 0.36
            PathLine { x: glyph.size * 0.9; y: glyph.size * 0.64 }
            PathMove { x: glyph.size * 0.9; y: glyph.size * 0.36 }
            PathLine { x: glyph.size * 0.64; y: glyph.size * 0.64 }
        }
    }
}
