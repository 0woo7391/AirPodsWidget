from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PySide6.QtCore import QByteArray, QPointF, QRect, QSize, QUrl, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider, QQuickView
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtTest import QTest

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1]
REFERENCES = PROJECT / "design-previews" / "2026-10-21-palette-concepts"
REFERENCE_GEOMETRY = {
    "rose": {"file": "01-rose-petrol-lemon-v2.png",
             "expanded": (126, 178, 870, 904), "compact": (84, 1139, 955, 158)},
    "paper": {"file": "02-primary-paper-v2.png",
              "expanded": (151, 168, 822, 902), "compact": (88, 1149, 947, 145)},
}


class LucianProvider(QQuickImageProvider):
    """Render selected licensed SVG final poses; no web runtime or animation."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)
        self.definitions = json.loads((BASE / "assets" / "lucian-icons.json").read_text(
            encoding="utf-8"))["icons"]
        self.failures: list[str] = []

    def svg(self, request: str) -> bytes:
        parsed = urlsplit(request)
        definition = self.definitions[parsed.path]
        query = parse_qs(parsed.query)
        color = QColor(query.get("color", ["#314290"])[0]).name()
        surface = QColor(query.get("surface", ["#F1F2ED"])[0]).name()
        solid = query.get("solid", ["0"])[0] == "1"
        state = query.get("state", [definition.get("defaultState") or ""])[0]
        poses = definition.get("poses") or {}
        parts: dict[str, dict] = {}
        for pose in (poses.get("*", {}), poses.get(state, {})):
            for name, values in pose.items():
                parts[name] = {**parts.get(name, {}), **values}
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'fill="none" stroke="{color}" stroke-width="1.75" '
            'stroke-linecap="round" stroke-linejoin="round">'
            + definition["svg"] + "</svg>"
        )
        if query.get("bolt", ["0"])[0] == "1":
            for child in list(root):
                if child.get("data-part") != "bolt":
                    root.remove(child)
            root.set("viewBox", "8 7 7 10")

        for element in root.iter():
            classes = element.get("class", "").split()
            if "s" in classes:
                element.set("fill", color if solid else surface)
            if "f" in classes:
                element.set("fill", color if solid else surface)
                element.set("stroke", "none")
            if "t" in classes:
                element.set("fill", "none")
                element.set("stroke", "none")
            pose = parts.get(element.get("data-part", ""), {})
            if "opacity" in pose:
                element.set("opacity", str(pose["opacity"]))
            if pose.get("draw") == 0:
                element.set("opacity", "0")
            if "rotate" in pose and pose["rotate"]:
                origin = (definition.get("origins") or {}).get(
                    element.get("data-part", ""), [12, 12])
                element.set("transform", f"rotate({pose['rotate']} {origin[0]} {origin[1]})")
        return ET.tostring(root, encoding="utf-8")

    def requestImage(self, request: str, size: QSize, requested_size: QSize) -> QImage:
        try:
            renderer = QSvgRenderer(QByteArray(self.svg(request)))
            if not renderer.isValid():
                raise ValueError("Invalid selected SVG")
            width = requested_size.width() if requested_size.width() > 0 else 24
            height = requested_size.height() if requested_size.height() > 0 else 24
            image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
            image.fill(Qt.transparent)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            renderer.render(painter)
            painter.end()
            size.setWidth(width)
            size.setHeight(height)
            return image
        except Exception as exc:
            self.failures.append(f"{request}: {exc}")
            return QImage()


def load_scene(view: QQuickView, design: str, qml_file: str, audio_backend=None, media_backend=None) -> tuple[LucianProvider, list[str]]:
    warnings: list[str] = []

    font_id = QFontDatabase.addApplicationFont(str(BASE / "assets" / "SUIT-Variable.ttf"))
    if font_id < 0:
        raise RuntimeError("SUIT font did not load; run the documented asset setup")
    family = QFontDatabase.applicationFontFamilies(font_id)[0]
    view.engine().warnings.connect(
        lambda issues: warnings.extend(issue.toString() for issue in issues))
    provider = LucianProvider()
    view.engine().addImageProvider("lucian", provider)
    context = view.rootContext()
    context.setContextProperty("previewFont", family)
    context.setContextProperty("initialDesign", design)
    context.setContextProperty("outputBackend", audio_backend)
    context.setContextProperty("mediaBackend", media_backend)
    context.setContextProperty("assetDirectory", QUrl.fromLocalFile(str(BASE / "assets")).toString())
    view.setSource(QUrl.fromLocalFile(str(BASE / "qml" / qml_file)))
    if view.status() == QQuickView.Error:
        raise RuntimeError("\n".join(error.toString() for error in view.errors()))
    return provider, warnings


def create_view(design: str) -> tuple[QQuickView, LucianProvider, list[str]]:
    view = QQuickView()
    view.setTitle("Audio Widget Concepts — 실제 컨트롤 / 예시 데이터")
    view.setResizeMode(QQuickView.SizeViewToRootObject)
    provider, warnings = load_scene(view, design, "PreviewBoard.qml")
    view.setMinimumSize(QSize(640, 800))
    view.setMaximumSize(QSize(640, 800))
    return view, provider, warnings


def crop_item(view: QQuickView, image: QImage, name: str) -> QImage:
    item = view.rootObject().findChild(type(view.rootObject()), name)
    if item is None:
        from PySide6.QtCore import QObject
        item = view.rootObject().findChild(QObject, name)
    if item is None:
        raise AssertionError(f"Missing QML item: {name}")
    position = item.mapToScene(QPointF(0, 0))
    ratio = image.width() / view.width()
    return image.copy(QRect(round(position.x() * ratio), round(position.y() * ratio),
                            round(item.width() * ratio), round(item.height() * ratio)))


def save_comparison(design: str, actual: dict[str, QImage], target: Path) -> None:
    reference = QImage(str(REFERENCES / REFERENCE_GEOMETRY[design]["file"]))
    pairs = []
    for mode in ("expanded", "compact"):
        original = reference.copy(QRect(*REFERENCE_GEOMETRY[design][mode]))
        rendered = actual[mode]
        # Uniform scaling only; no independent x/y warping to hide discrepancies.
        original = original.scaledToWidth(520, Qt.SmoothTransformation)
        rendered = rendered.scaledToWidth(520, Qt.SmoothTransformation)
        pairs.append((original, rendered))
    height = 104 + sum(max(a.height(), b.height()) + 58 for a, b in pairs)
    comparison = QImage(1120, height, QImage.Format_ARGB32_Premultiplied)
    comparison.fill(QColor("#E5E4DE"))
    painter = QPainter(comparison)
    font = QFont(QFontDatabase.applicationFontFamilies(
        QFontDatabase.addApplicationFont(str(BASE / "assets" / "SUIT-Variable.ttf")))[0])
    font.setPixelSize(18)
    painter.setFont(font)
    painter.setPen(QColor("#383431"))
    painter.drawText(30, 35, "기준 이미지 · 생성 시안")
    painter.drawText(570, 35, "실제 QML · 예시 데이터")
    y = 65
    for original, rendered in pairs:
        painter.drawImage(30, y, original)
        painter.drawImage(570, y, rendered)
        y += max(original.height(), rendered.height()) + 58
    painter.end()
    if not comparison.save(str(target)):
        raise RuntimeError(f"Failed to save comparison: {target}")


def capture(view: QQuickView, design: str, output: Path) -> dict[str, str]:
    output.mkdir(parents=True, exist_ok=True)
    QTest.qWait(250)
    board = view.grabWindow()
    if board.isNull():
        raise RuntimeError("QML rendering returned an empty image")
    paths = {"board": str(output / f"{design}-qml-board.png")}
    board.save(paths["board"])
    crops = {mode: crop_item(view, board, f"{mode}Widget") for mode in ("expanded", "compact")}
    for mode, image in crops.items():
        paths[mode] = str(output / f"{design}-qml-{mode}.png")
        image.save(paths[mode])
    paths["comparison"] = str(output / f"{design}-reference-comparison.png")
    save_comparison(design, crops, Path(paths["comparison"]))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent QML concept preview; fixture data only.")
    parser.add_argument("--design", choices=("rose", "paper"), default="rose")
    parser.add_argument("--render", type=Path)
    parser.add_argument("--scale", type=float, default=1.0)
    args = parser.parse_args()
    if args.render:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"
    os.environ["QT_SCALE_FACTOR"] = str(args.scale)
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("AudioWidgetConceptPreview")
    QQuickStyle.setStyle("Basic")
    view, provider, warnings = create_view(args.design)
    view.show()
    if args.render:
        paths = capture(view, args.design, args.render.resolve())
        print(json.dumps({"design": args.design, "captures": paths,
                          "qml_warnings": warnings, "icon_failures": provider.failures},
                         ensure_ascii=False, indent=2))
        view.close()
        return 1 if warnings or provider.failures else 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
