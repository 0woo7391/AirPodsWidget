import QtQuick

// A short note, edited as it looks: no Markdown marks on screen, saved as Markdown
// (memo_format.py does the formatting). The card shows the first two lines; a click opens
// the flyout with the cursor in the note.
// Ctrl+B / Ctrl+I / Ctrl+Shift+X: bold, italic, strikethrough on the selection, or on what
// is typed next (again to turn off). Ctrl+Space clears the selection's styles.
// Line start "# ", "- ", "1. ", "[] ": heading, bullet, numbered, checkbox; Backspace at the
// start of such a line or Enter on an empty item makes it a plain line again.
// Ctrl+Enter or a click on the box checks an item. A typed web address becomes a link
// (Ctrl+click opens it). While the note has focus the flyout stays open (pinned).
DockCard {
    id: card
    cardId: "memo"
    summaryHeight: 84
    detailHeight: 260

    property string text: dockPrefs.get("memo/text")
    signal focusEditor()
    Connections {
        target: dockPrefs
        function onChanged(key) { if (key === "memo/text") card.text = dockPrefs.get(key) }
    }
    function write() {
        dockHost.requestActivate()
        if (card.dock) card.dock.openNow(card.cardId)
        card.focusEditor()
    }
    // The card: the first two lines, headings as bold, links in the dock's link colour
    // (Qt's Markdown ignores linkColor, inline HTML it keeps).
    function display() {
        let md = text.split("\n").filter(l => l.trim().length).slice(0, 2).join("\n\n")   // two paragraphs, two lines
        md = md.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" style="color:#8FD0FF">$1</a>')
        return md.replace(/^\s*#+\s*(.+)$/gm, "**$1**")
    }
    // The first line without its Markdown marks, for the rail.
    function plainFirstLine() {
        const line = text.split("\n").find(l => l.trim().length) || ""
        return line.replace(/^\s*(#+|>|[-*+]\s+\[[ xX]\]|[-*+]|\d+\.)\s*/, "").replace(/[*_`~]/g, "")
    }

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
    railStatus: plainFirstLine() || "비어 있음"

    summary: Component {
        Item {
            Text {
                x: Theme.pad; y: 13
                text: "메모"
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
            }
            Text {
                x: Theme.pad; y: 32; width: parent.width - Theme.pad * 2; height: parent.height - y - 8
                clip: true
                textFormat: card.text.length ? Text.MarkdownText : Text.PlainText
                text: card.text.length ? card.display() : "눌러서 메모 쓰기"
                color: card.text.length ? Theme.ink : Theme.inkTertiary
                font.family: dockFont; font.pixelSize: 12
                wrapMode: Text.NoWrap; elide: Text.ElideRight
            }
            TapHandler { enabled: !card.editing; onTapped: card.write() }
            HoverHandler { cursorShape: Qt.IBeamCursor }
        }
    }

    detail: Component {
        Item {
            id: page
            readonly property var doc: editor.textDocument
            property bool loading: false
            property bool busy: false
            property bool dirty: false
            // Styles for what is typed next: {pos, length, kinds: [{kind, on}]}.
            property var pending: null
            readonly property string pendingLabel: !pending ? "" : pending.kinds.map(k =>
                ({ bold: "굵게", italic: "기울임", strike: "취소선" })[k.kind] + (k.on ? "" : " 끔")).join(", ")

            function load() {
                loading = true
                editor.text = card.text
                memoFormat.normalize(doc)
                loading = false
            }
            function focusNow() { editor.forceActiveFocus(); editor.cursorPosition = editor.length }
            function flush() {
                if (!dirty) return
                dirty = false
                save.stop()
                dockPrefs.set("memo/text", editor.text.replace(/\n+$/, ""))
            }
            Timer { id: save; interval: 700; onTriggered: page.flush() }
            Connections { target: card; function onFocusEditor() { Qt.callLater(page.focusNow) } }
            // A change saved elsewhere reaches the note only while it is not being edited.
            Connections { target: card; function onTextChanged() { if (!editor.activeFocus && !page.dirty) page.load() } }
            Component.onCompleted: load()
            Component.onDestruction: flush()

            // After each edit: carry pending styles onto what was typed, then apply any typed
            // Markdown (line prefix, **bold**, a web address). An inline style just made stops
            // there: what is typed next is plain.
            function afterEdit() {
                busy = true
                const pos = editor.cursorPosition
                if (pending && editor.length > pending.length && pos > pending.pos) {
                    for (const k of pending.kinds) memoFormat.apply(doc, pending.pos, pos, k.kind, k.on)
                    pending = null
                }
                const moved = memoFormat.autoformat(doc, editor.cursorPosition)
                if (moved >= 0) {
                    editor.cursorPosition = moved
                    if (moved === memoFormat.blockStart(doc, moved)) { busy = false; return }   // a line prefix, not an inline style
                    const off = ["bold", "strike"].filter(k => memoFormat.has(doc, moved, k))
                    if (off.length) pending = { pos: moved, length: editor.length, kinds: off.map(k => ({ kind: k, on: false })) }
                }
                busy = false
            }
            function style(kind) {
                const s = editor.selectionStart, e = editor.selectionEnd
                if (s !== e) { memoFormat.toggle(doc, s, e, kind); return }
                const pos = editor.cursorPosition
                const kinds = pending && pending.pos === pos ? pending.kinds.filter(k => k.kind !== kind) : []
                const again = pending && pending.pos === pos && pending.kinds.some(k => k.kind === kind)
                if (!again) kinds.push({ kind: kind, on: !memoFormat.has(doc, pos, kind) })
                pending = kinds.length ? { pos: pos, length: editor.length, kinds: kinds } : null
            }

            Text {
                x: Theme.pad; y: Theme.pad
                text: "메모"
                color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                opacity: card.reveal(0)
            }
            Text {
                anchors.right: parent.right; anchors.rightMargin: Theme.pad; y: Theme.pad + 3
                text: page.pendingLabel.length ? "다음 글자: " + page.pendingLabel
                    : editor.activeFocus ? "# 제목 · - 목록 · [] 할 일 · Ctrl+B" : "눌러서 쓰기"
                color: page.pendingLabel.length ? Theme.charge : Theme.inkTertiary
                font.family: dockFont; font.pixelSize: 10
                opacity: card.reveal(0)
            }
            Rectangle {
                id: box
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
                        textFormat: TextEdit.MarkdownText
                        wrapMode: TextEdit.Wrap
                        color: Theme.ink; selectionColor: "#558FD0FF"
                        font.family: dockFont; font.pixelSize: 13
                        selectByMouse: true
                        onTextChanged: {
                            if (page.loading) return
                            page.dirty = true
                            save.restart()
                            if (!page.busy) Qt.callLater(page.afterEdit)
                        }
                        onCursorPositionChanged: if (page.pending && !page.busy) Qt.callLater(() => {
                            const p = page.pending
                            if (p && editor.length === p.length && editor.cursorPosition !== p.pos) page.pending = null
                        })
                        onActiveFocusChanged: {
                            card.pinned = activeFocus
                            if (!activeFocus) { page.pending = null; page.flush() }
                        }
                        Keys.onPressed: function(event) {
                            const ctrl = event.modifiers & Qt.ControlModifier
                            const shift = event.modifiers & Qt.ShiftModifier
                            const ret = event.key === Qt.Key_Return || event.key === Qt.Key_Enter
                            const d = page.doc, pos = editor.cursorPosition
                            const selected = editor.selectionStart !== editor.selectionEnd
                            if (event.key === Qt.Key_Escape) editor.focus = false
                            else if (ctrl && event.key === Qt.Key_B) page.style("bold")
                            else if (ctrl && event.key === Qt.Key_I) page.style("italic")
                            else if (ctrl && shift && event.key === Qt.Key_X) page.style("strike")
                            else if (ctrl && event.key === Qt.Key_Space) {
                                if (selected) memoFormat.clear(d, editor.selectionStart, editor.selectionEnd)
                                page.pending = null
                            } else if (ctrl && ret) memoFormat.toggleCheck(d, pos)
                            else if (ret && !ctrl && !shift) {
                                if (memoFormat.blockKind(d, pos) !== "plain" && memoFormat.blockEmpty(d, pos)) {
                                    memoFormat.setBlock(d, pos, "plain")
                                } else {
                                    Qt.callLater(() => memoFormat.afterNewline(d, editor.cursorPosition))
                                    return
                                }
                            } else if (event.key === Qt.Key_Backspace && !selected && pos === memoFormat.blockStart(d, pos)
                                       && memoFormat.blockKind(d, pos) !== "plain") {
                                memoFormat.setBlock(d, pos, "plain")
                            } else return
                            event.accepted = true
                        }
                        onCursorRectangleChanged: {
                            if (cursorRectangle.y < scroll.contentY) scroll.contentY = cursorRectangle.y
                            else if (cursorRectangle.y + cursorRectangle.height > scroll.contentY + scroll.height)
                                scroll.contentY = cursorRectangle.y + cursorRectangle.height - scroll.height
                        }
                        // A click left of a checklist item's text checks it; Ctrl+click opens a link.
                        TapHandler {
                            onTapped: function(point) {
                                const p = point.position
                                if (point.modifiers & Qt.ControlModifier) {
                                    const link = editor.linkAt(p.x, p.y)
                                    if (link.length) Qt.openUrlExternally(link)
                                    return
                                }
                                const pos = editor.positionAt(p.x, p.y)
                                const kind = memoFormat.blockKind(page.doc, pos)
                                if (kind !== "check" && kind !== "checked") return
                                const start = editor.positionToRectangle(memoFormat.blockStart(page.doc, pos))
                                if (p.x < start.x - 2 && p.y >= start.y - 4 && p.y <= start.y + start.height + 4)
                                    memoFormat.toggleCheck(page.doc, pos)
                            }
                        }
                        HoverHandler {
                            cursorShape: editor.hoveredLink.length ? Qt.PointingHandCursor : Qt.IBeamCursor
                        }
                    }
                    Text {
                        visible: editor.length === 0
                        text: "메모를 입력하세요"
                        color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 13
                    }
                }
                TapHandler { onTapped: editor.forceActiveFocus() }
            }
        }
    }
}
