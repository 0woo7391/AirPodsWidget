import QtQuick

ShaderEffect {
    id: plate
    property var backdrop
    property vector2d sourceSize: Qt.vector2d(1,1)
    property vector2d origin: Qt.vector2d(0,0)
    property real corner: 18
    property real coating: widgetPreferences.readability
    property real blur: widgetPreferences.blur
    property vector2d resolution: Qt.vector2d(width,height)
    fragmentShader: Qt.resolvedUrl("frost.frag.qsb")
}
