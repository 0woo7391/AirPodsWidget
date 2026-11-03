import QtQuick
import QtQuick.Effects

// The playing track's artwork, heavily blurred, as a wash of its colours behind a card
// (Apple-Music style). Without artwork, a gradient in the source app's colour.
// Clipped to the card's rounded shape; quieter while paused.
Item {
    id: backdrop
    property string source: ""
    property string sourceName: ""
    property bool playing: false
    property real radius: Theme.radius
    readonly property color appColor: {
        const name = sourceName.toLowerCase()
        return name.indexOf("spotify") >= 0 ? "#1DB954" : name.indexOf("youtube") >= 0 ? "#FF2D55"
            : name.indexOf("chrome") >= 0 || name.indexOf("edge") >= 0 || name.indexOf("whale") >= 0 ? "#5E7BFF"
            : name.indexOf("apple") >= 0 || name.indexOf("itunes") >= 0 ? "#FA2D55" : "#7A6CFF"
    }
    opacity: playing ? 0.62 : 0.32
    Behavior on opacity { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }

    Item {
        id: content
        anchors.fill: parent
        layer.enabled: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: shape
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
        }
        Rectangle {
            anchors.fill: parent
            visible: art.status !== Image.Ready
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: Qt.darker(backdrop.appColor, 1.6) }
                GradientStop { position: 1; color: Qt.rgba(backdrop.appColor.r, backdrop.appColor.g, backdrop.appColor.b, 0.25) }
            }
        }
        Image {
            id: art
            // Larger than the card so the blur has no dark edges.
            anchors.centerIn: parent
            width: parent.width * 1.4; height: width
            source: backdrop.source
            fillMode: Image.PreserveAspectCrop
            sourceSize: Qt.size(96, 96)          // small on purpose: it is blurred anyway
            visible: false
        }
        MultiEffect {
            source: art
            anchors.fill: art
            visible: art.status === Image.Ready
            blurEnabled: true
            blur: 1.0
            blurMax: 48
            saturation: 0.25
            brightness: -0.12
        }
        // Darken towards the text side so white type always reads.
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#33000000" }
                GradientStop { position: 1; color: "#8C000000" }
            }
        }
    }
    Item {
        id: shape
        anchors.fill: parent
        layer.enabled: true
        visible: false
        Rectangle { anchors.fill: parent; radius: backdrop.radius; color: "black" }
    }
}
