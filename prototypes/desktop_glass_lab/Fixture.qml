import QtQuick

Rectangle {
    width: 640; height: 460
    property bool alternate: false
    color: alternate ? "#18405E" : "#D9E2F0"
    Repeater {
        model: 30
        Rectangle {
            required property int index
            x: index * 24; y: 0; width: 10; height: 460
            color: parent.alternate ? "#F0AD63" : "#263B64"
        }
    }
    Repeater {
        model: 20
        Rectangle {
            required property int index
            x: 0; y: index * 24; width: 640; height: 3
            color: parent.alternate ? "#DCB4E8" : "#688085"
        }
    }
}
