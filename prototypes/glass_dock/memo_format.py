"""Live formatting for the memo editor: the note is edited as a formatted document (no
Markdown marks on screen) and saved as Markdown.

QML hands over its TextEdit's `textDocument` with cursor positions. Character styles
(bold, italic, strikethrough) toggle on a selection, or apply to what is typed next.
Block styles (heading, bullet, numbered, checkbox) come from typing their Markdown
prefix at the start of a line ("# ", "- ", "1. ", "[] "), and leave again with Backspace
at the start of the line or Enter on an empty item. "**x**" and "~~x~~" typed inline
turn into the style, and a typed web address becomes a link once a space follows it.
"""
from __future__ import annotations

import re

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QColor, QFont, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextFormat, QTextListFormat

LINK_COLOR = QColor("#8FD0FF")
HEADING_SIZE = 2           # QTextFormat.FontSizeAdjustment for a heading line
PREFIXES = [("# ", "heading"), ("- [ ] ", "check"), ("[] ", "check"), ("[ ] ", "check"),
            ("- ", "bullet"), ("* ", "bullet"), ("1. ", "number")]
INLINE = [(re.compile(r"\*\*([^*\n]+)\*\*$"), 2, "bold"), (re.compile(r"~~([^~\n]+)~~$"), 2, "strike")]
URL = re.compile(r"(?:https?://|www\.)\S+\.\S+$")
Marker = QTextBlockFormat.MarkerType


def _doc(handle):
    return handle.textDocument() if hasattr(handle, "textDocument") else handle


def _char(kind: str, on: bool) -> QTextCharFormat:
    fmt = QTextCharFormat()
    if kind == "bold":
        fmt.setFontWeight(QFont.Bold if on else QFont.Normal)
    elif kind == "italic":
        fmt.setFontItalic(on)
    elif kind == "strike":
        fmt.setFontStrikeOut(on)
    return fmt


def _has(fmt: QTextCharFormat, kind: str) -> bool:
    return {"bold": fmt.fontWeight() >= QFont.Bold, "italic": fmt.fontItalic(),
            "strike": fmt.fontStrikeOut()}.get(kind, False)


def block_kind(block) -> str:
    fmt = block.blockFormat()
    if fmt.headingLevel() > 0:
        return "heading"
    if fmt.marker() == Marker.Checked:
        return "checked"
    if fmt.marker() == Marker.Unchecked:
        return "check"
    if block.textList() is not None:
        style = block.textList().format().style()
        return "number" if style in (QTextListFormat.ListDecimal, QTextListFormat.ListLowerAlpha) else "bullet"
    return "plain"


def _block_text_cursor(block) -> QTextCursor:
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
    return cursor


def set_block(doc, pos: int, kind: str) -> None:
    cursor = QTextCursor(doc)
    cursor.setPosition(pos)
    block = cursor.block()
    was_heading = block_kind(block) == "heading"
    cursor.beginEditBlock()
    if block.textList() is not None:
        block.textList().remove(block)
    fmt = block.blockFormat()
    fmt.setHeadingLevel(0)
    fmt.setMarker(Marker.NoMarker)
    fmt.setIndent(0)
    cursor.setBlockFormat(fmt)
    size = QTextCharFormat()
    size.setProperty(QTextFormat.FontSizeAdjustment, HEADING_SIZE if kind == "heading" else 0)
    if kind == "heading" or was_heading:   # a line's own bold words stay when it changes kind
        size.setFontWeight(QFont.Bold if kind == "heading" else QFont.Normal)
    _block_text_cursor(block).mergeCharFormat(size)
    cursor.mergeBlockCharFormat(size)
    if kind == "heading":
        fmt.setHeadingLevel(1)
        cursor.setBlockFormat(fmt)
    elif kind in ("bullet", "number", "check"):
        style = QTextListFormat.ListDecimal if kind == "number" else QTextListFormat.ListDisc
        previous = block.previous()
        joined = previous.isValid() and previous.textList() is not None \
            and previous.textList().format().style() == style
        if joined:
            previous.textList().add(block)
        else:
            cursor.createList(style)
        if kind == "check":
            fmt = cursor.block().blockFormat()
            fmt.setMarker(Marker.Unchecked)
            cursor.setBlockFormat(fmt)
    cursor.endEditBlock()


def normalize(doc) -> None:
    """Headings loaded from Markdown get the editor's own heading size."""
    block = doc.begin()
    while block.isValid():
        if block.blockFormat().headingLevel() > 0:
            size = QTextCharFormat()
            size.setProperty(QTextFormat.FontSizeAdjustment, HEADING_SIZE)
            size.setFontWeight(QFont.Bold)
            _block_text_cursor(block).mergeCharFormat(size)
        block = block.next()


class MemoFormat(QObject):
    @Slot(QObject, int, int, str, result=bool)
    def toggle(self, handle, start: int, end: int, kind: str) -> bool:
        """Turn `kind` on over the selection, or off when all of it already has it; returns the new state."""
        doc = _doc(handle)
        cursor = QTextCursor(doc)
        on = False
        for pos in range(start, end):
            cursor.setPosition(pos + 1)
            if not _has(cursor.charFormat(), kind):
                on = True
                break
        self.apply(handle, start, end, kind, on)
        return on

    @Slot(QObject, int, int, str, bool)
    def apply(self, handle, start: int, end: int, kind: str, on: bool) -> None:
        cursor = QTextCursor(_doc(handle))
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        cursor.mergeCharFormat(_char(kind, on))

    @Slot(QObject, int, str, result=bool)
    def has(self, handle, pos: int, kind: str) -> bool:
        """Whether the character before `pos` (what typing would continue) has `kind`."""
        cursor = QTextCursor(_doc(handle))
        cursor.setPosition(pos)
        return _has(cursor.charFormat(), kind)

    @Slot(QObject, int, int)
    def clear(self, handle, start: int, end: int) -> None:
        cursor = QTextCursor(_doc(handle))
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        for kind in ("bold", "italic", "strike"):
            cursor.mergeCharFormat(_char(kind, False))
        plain = QTextCharFormat()
        plain.setAnchor(False)
        plain.setAnchorHref("")
        plain.setFontUnderline(False)
        plain.clearForeground()
        cursor.mergeCharFormat(plain)

    @Slot(QObject, int, result=str)
    def blockKind(self, handle, pos: int) -> str:
        return block_kind(_doc(handle).findBlock(pos))

    @Slot(QObject, int, result=int)
    def blockStart(self, handle, pos: int) -> int:
        return _doc(handle).findBlock(pos).position()

    @Slot(QObject, int, result=bool)
    def blockEmpty(self, handle, pos: int) -> bool:
        return _doc(handle).findBlock(pos).length() <= 1

    @Slot(QObject, int, str)
    def setBlock(self, handle, pos: int, kind: str) -> None:
        set_block(_doc(handle), pos, kind)

    @Slot(QObject, int)
    def toggleCheck(self, handle, pos: int) -> None:
        doc = _doc(handle)
        kind = block_kind(doc.findBlock(pos))
        if kind not in ("check", "checked"):
            set_block(doc, pos, "check")
            return
        cursor = QTextCursor(doc)
        cursor.setPosition(pos)
        fmt = cursor.block().blockFormat()
        fmt.setMarker(Marker.Checked if kind == "check" else Marker.Unchecked)
        cursor.setBlockFormat(fmt)

    @Slot(QObject, int)
    def afterNewline(self, handle, pos: int) -> None:
        """A line started from a heading is plain; one started from a done item is not done."""
        doc = _doc(handle)
        block = doc.findBlock(pos)
        previous = block.previous()
        kind = block_kind(block)
        if kind == "heading" or (previous.isValid() and block_kind(previous) == "heading"):
            set_block(doc, pos, "plain")
        elif kind == "checked":
            cursor = QTextCursor(doc)
            cursor.setPosition(pos)
            fmt = block.blockFormat()
            fmt.setMarker(Marker.Unchecked)
            cursor.setBlockFormat(fmt)

    @Slot(QObject)
    def normalize(self, handle) -> None:
        normalize(_doc(handle))

    @Slot(QObject, int, result=int)
    def autoformat(self, handle, pos: int) -> int:
        """Apply what was just typed before `pos`: a line prefix, **bold** / ~~strike~~, or a
        web address followed by a space. Returns the new cursor position, or -1 for none."""
        doc = _doc(handle)
        block = doc.findBlock(pos)
        start = block.position()
        before = block.text()[:pos - start]
        # A prefix typed at the start of any line sets its kind ("- " in a list item stays a bullet).
        for prefix, kind in PREFIXES:
            if before == prefix:
                cursor = QTextCursor(doc)
                cursor.setPosition(start)
                cursor.setPosition(pos, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                set_block(doc, start, kind)
                return start
        for pattern, width, kind in INLINE:
            match = pattern.search(before)
            if match:
                begin = start + match.start()
                cursor = QTextCursor(doc)
                cursor.beginEditBlock()
                cursor.setPosition(pos - width)
                cursor.setPosition(pos, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                cursor.setPosition(begin)
                cursor.setPosition(begin + width, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                cursor.setPosition(begin)
                cursor.setPosition(pos - 2 * width, QTextCursor.KeepAnchor)
                cursor.mergeCharFormat(_char(kind, True))
                cursor.endEditBlock()
                # what is typed next is plain again
                return pos - 2 * width
        if before.endswith(" "):
            token = before[:-1].split()[-1] if before[:-1].split() else ""
            if token and URL.search(token):
                begin = pos - 1 - len(token)
                cursor = QTextCursor(doc)
                cursor.setPosition(begin + 1)
                if not cursor.charFormat().isAnchor():
                    link = QTextCharFormat()
                    link.setAnchor(True)
                    link.setAnchorHref(token if "://" in token else "https://" + token)
                    link.setForeground(LINK_COLOR)
                    link.setFontUnderline(True)
                    cursor.setPosition(begin)
                    cursor.setPosition(pos - 1, QTextCursor.KeepAnchor)
                    cursor.mergeCharFormat(link)
        return -1
