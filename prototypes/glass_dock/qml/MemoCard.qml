import QtQuick

// A short note. The card shows its first lines; the flyout edits it and saves as you type.
// While the editor has focus the flyout stays open (pinned).
DockCard {
    id: card
    cardId: "memo"
    summaryHeight: 84
    detailHeight: 220

    property string text: dockPrefs.get("memo/text")
    Connections {
        target: dockPrefs
        function onChanged(key) { if (key === "memo/text") card.text = dockPrefs.get(key) }
    }
    Timer { id: save; interval: 400; property string pending; onTriggered: dockPrefs.set("memo/text", pending) }
    function edit(value) { save.pending = value; save.restart() }

    // A note glyph: three ruled lines, the last one short.
    railIconComponent: Component {
        Column {
            spacing: 4
            Repeater {
                model: [14, 14, 9]
                Rectangle { required property int modelData; width: modelData; height: 2; radius: 1; color: Theme.ink }
            }
        }
    }
    railLabel: "메모"
    railStatus: text.split("\n")[0] || "비어 있음"

    summary: Component {
        Item {
            Text {
                x: Theme.pad; y: 13
                text: "메모"
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
            }
            Text {
                x: Theme.pad; y: 34; width: parent.width - Theme.pad * 2; height: parent.height - y - 10
                text: card.text.length ? card.text : "눌러서 메모 쓰기"
                color: card.text.length ? Theme.ink : Theme.inkTertiary
                font.family: dockFont; font.pixelSize: 12
                wrapMode: Text.Wrap; elide: Text.ElideRight; maximumLineCount: 2
                lineHeight: 1.15
            }
        }
    }

    detail: Component {
        Item {
            Text {
                x: Theme.pad; y: Theme.pad
                text: "메모"
                color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                opacity: card.reveal(0)
            }
            Rectangle {
                x: Theme.pad; y: 44; width: parent.width - Theme.pad * 2; height: parent.height - y - Theme.pad
                radius: Theme.radiusInner
                color: Theme.well
                border.width: 1; border.color: editor.activeFocus ? Theme.strokeLit : Theme.stroke
                opacity: card.reveal(1)
                Flickable {
                    id: scroll
                    anchors.fill: parent; anchors.margins: 10
                    contentHeight: editor.contentHeight
                    clip: true
                    TextEdit {
                        id: editor
                        width: scroll.width
                        text: card.text
                        wrapMode: TextEdit.Wrap
                        color: Theme.ink; selectionColor: "#558FD0FF"
                        font.family: dockFont; font.pixelSize: 13
                        selectByMouse: true
                        onTextChanged: if (text !== card.text) card.edit(text)
                        onActiveFocusChanged: card.pinned = activeFocus
                        onCursorRectangleChanged: {
                            if (cursorRectangle.y < scroll.contentY) scroll.contentY = cursorRectangle.y
                            else if (cursorRectangle.y + cursorRectangle.height > scroll.contentY + scroll.height)
                                scroll.contentY = cursorRectangle.y + cursorRectangle.height - scroll.height
                        }
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.NoButton
                    cursorShape: Qt.IBeamCursor
                }
                TapHandler { onTapped: { dockHost.requestActivate(); editor.forceActiveFocus() } }
            }
        }
    }
}
