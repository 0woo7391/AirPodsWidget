import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPolygonF

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototypes" / "glass_dock"))
from optical import optical_offset  # noqa: E402

_app = QGuiApplication.instance() or QGuiApplication([])


def canvas(draw) -> QImage:
    image = QImage(96, 96, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("white"))
    draw(painter)
    painter.end()
    return image


def test_centered_circle_needs_no_offset():
    dx, dy = optical_offset(canvas(lambda p: p.drawEllipse(QPointF(48, 48), 30, 30)))
    assert abs(dx) < 0.01 and abs(dy) < 0.01


def test_play_triangle_moves_right_beyond_its_box_center():
    # Box-centered triangle: its mass sits left of the box center, so it must move right.
    triangle = QPolygonF([QPointF(21, 18), QPointF(75, 48), QPointF(21, 78)])
    dx, dy = optical_offset(canvas(lambda p: p.drawPolygon(triangle)))
    assert dx > 0.02
    assert abs(dy) < 0.01


def test_off_canvas_shape_is_pulled_back_to_center():
    dx, dy = optical_offset(canvas(lambda p: p.drawRect(0, 0, 40, 40)))
    assert dx > 0.25 and dy > 0.25


def test_empty_image_has_no_offset():
    assert optical_offset(canvas(lambda p: None)) == (0.0, 0.0)
