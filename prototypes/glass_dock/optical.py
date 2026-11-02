"""Optical centering: place an icon by the ink it draws, not by its square canvas.

A play triangle or a battery with a terminal sits off-center inside its 24x24
viewBox. Centering the canvas in a round button makes such icons look shifted.
The visual center used here blends the ink bounding box (what the eye reads as
the outline) with the alpha-weighted centroid (where the ink mass is), which is
the usual compromise between geometric and optical alignment.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QPointF, QSize, Slot
from PySide6.QtGui import QImage

# 0 = pure bounding-box center, 1 = pure mass centroid.
CENTROID_WEIGHT = 0.5
SAMPLE_SIZE = 96
ALPHA_FLOOR = 8


def optical_offset(image: QImage) -> tuple[float, float]:
    """Offset, as a fraction of the image size, that moves the ink's visual center to the canvas center."""
    image = image.convertToFormat(QImage.Format_ARGB32)
    width, height = image.width(), image.height()
    if width == 0 or height == 0:
        return 0.0, 0.0
    data = bytes(image.constBits())
    stride = image.bytesPerLine()
    total = sum_x = sum_y = 0.0
    left, top, right, bottom = width, height, -1, -1
    for y in range(height):
        row = y * stride
        for x in range(width):
            # Format_ARGB32 is stored as B, G, R, A on little-endian machines.
            alpha = data[row + x * 4 + 3]
            if alpha < ALPHA_FLOOR:
                continue
            total += alpha
            sum_x += (x + 0.5) * alpha
            sum_y += (y + 0.5) * alpha
            left, right = min(left, x), max(right, x)
            top, bottom = min(top, y), max(bottom, y)
    if total == 0:
        return 0.0, 0.0
    box_x, box_y = (left + right + 1) / 2, (top + bottom + 1) / 2
    mass_x, mass_y = sum_x / total, sum_y / total
    visual_x = box_x + (mass_x - box_x) * CENTROID_WEIGHT
    visual_y = box_y + (mass_y - box_y) * CENTROID_WEIGHT
    return (width / 2 - visual_x) / width, (height / 2 - visual_y) / height


class IconMetrics(QObject):
    """QML-facing cache of optical offsets for icons rendered by an image provider."""

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._cache: dict[str, QPointF] = {}

    @Slot(str, str, result=QPointF)
    def offset(self, name: str, pose: str = "") -> QPointF:
        key = f"{name}?state={pose}" if pose else name
        if key not in self._cache:
            request = f"{name}?color=%23FFFFFF" + (f"&state={pose}" if pose else "")
            image = self._provider.requestImage(request, QSize(), QSize(SAMPLE_SIZE, SAMPLE_SIZE))
            dx, dy = optical_offset(image) if not image.isNull() else (0.0, 0.0)
            self._cache[key] = QPointF(dx, dy)
        return self._cache[key]
