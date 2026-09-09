from __future__ import annotations

import re
from pathlib import Path


_STRUCTURAL_TERMS = ("morph", "collapse", "restore", "geometry")
_REPLACEMENTS = {
    "QEasingCurve.OutBack": "QEasingCurve.InOutCubic",
    "QEasingCurve.InBack": "QEasingCurve.InOutCubic",
    "QEasingCurve.InOutBack": "QEasingCurve.InOutCubic",
    "QEasingCurve.OutBounce": "QEasingCurve.InOutCubic",
    "QEasingCurve.InOutBounce": "QEasingCurve.InOutCubic",
    "QEasingCurve.OutElastic": "QEasingCurve.InOutCubic",
    "QEasingCurve.InOutElastic": "QEasingCurve.InOutCubic",
}


def patch_structural_easing(path: Path) -> bool:
    """Remove structural overshoot without touching local button feedback."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False

    original = text

    def safe_at(pos: int) -> bool:
        line_start = text.rfind("\n", 0, pos) + 1
        line_end = text.find("\n", pos)
        if line_end < 0:
            line_end = len(text)
        line = text[line_start:line_end].casefold()
        if any(term in line for term in _STRUCTURAL_TERMS):
            return True

        prefix = text[:pos]
        suffix = path.suffix.casefold()
        if suffix == ".py":
            matches = list(
                re.finditer(
                    r"(?m)^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                    prefix,
                )
            )
            if not matches:
                return False
            name = matches[-1].group(1).casefold()
            return any(term in name for term in _STRUCTURAL_TERMS)

        if suffix in {".qml", ".js"}:
            matches = list(
                re.finditer(
                    r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                    prefix,
                )
            )
            if not matches:
                return False
            name = matches[-1].group(1).casefold()
            return any(term in name for term in _STRUCTURAL_TERMS)

        return False

    for old, new in _REPLACEMENTS.items():
        positions = [match.start() for match in re.finditer(re.escape(old), text)]
        for pos in reversed(positions):
            if safe_at(pos):
                text = text[:pos] + new + text[pos + len(old) :]

    if text == original:
        return False
    path.write_text(text, encoding="utf-8")
    return True
