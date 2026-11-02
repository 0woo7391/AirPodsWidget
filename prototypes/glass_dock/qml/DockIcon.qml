import QtQuick

// An icon placed by its optical center. iconMetrics measures where the ink
// actually sits inside the 24x24 canvas and this item shifts the image so the
// ink, not the canvas, is centered in the item.
Item {
    id: icon
    property string name: ""
    property string pose: ""
    property color color: Theme.ink
    property bool solid: true
    property real size: 18
    property bool mirror: false

    implicitWidth: size
    implicitHeight: size
    readonly property point optical: name.length ? iconMetrics.offset(name, pose) : Qt.point(0, 0)

    Image {
        width: icon.size
        height: icon.size
        x: (icon.width - width) / 2 + (icon.mirror ? -icon.optical.x : icon.optical.x) * width
        y: (icon.height - height) / 2 + icon.optical.y * height
        sourceSize: Qt.size(icon.size * 2, icon.size * 2)
        smooth: true
        mirror: icon.mirror
        source: icon.name.length
            ? "image://lucian/" + icon.name + "?color=" + encodeURIComponent(Qt.rgba(icon.color.r, icon.color.g, icon.color.b, 1).toString())
              + (icon.pose.length ? "&state=" + icon.pose : "") + (icon.solid ? "&solid=1" : "")
            : ""
        opacity: icon.color.a
    }
}
