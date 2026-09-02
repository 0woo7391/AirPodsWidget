from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMetaObject, QUrl, Qt, QObject, QPoint, QPointF
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from controller import AppController
from models import AirPodsState, MediaState


def load_application_fonts() -> list[str]:
    errors: list[str] = []
    for relative_path in (
        "assets/fonts/Pretendard-Regular.otf",
        "assets/fonts/Pretendard-Medium.otf",
        "assets/fonts/Pretendard-SemiBold.otf",
    ):
        font_path = ROOT / relative_path
        if QFontDatabase.addApplicationFont(str(font_path)) < 0:
            errors.append(f"Failed to load application font: {relative_path}")
    return errors


def item_global_center(item: QObject) -> tuple[float, float]:
    point = item.mapToGlobal(QPointF(item.width() / 2.0, item.height() / 2.0))
    return float(point.x()), float(point.y())


def sample_global_centers(app: QApplication, item: QObject, frames: int = 28) -> list[tuple[float, float]]:
    samples: list[tuple[float, float]] = []
    for _ in range(frames):
        QTest.qWait(16)
        app.processEvents()
        samples.append(item_global_center(item))
    return samples


def sample_morph_frames(
    app: QApplication,
    widget: QObject,
    toggle: QObject,
    expanded_content: QObject,
    minimized_content: QObject,
    reveal_items: dict[str, QObject] | None = None,
    frames: int = 28,
    capture_dir: Path | None = None,
    capture_prefix: str = "",
    shell: QObject | None = None,
    collision_items: dict[str, QObject] | None = None,
) -> list[dict[str, float | tuple[float, float]]]:
    samples: list[dict[str, float | tuple[float, float]]] = []
    trace_morph = os.environ.get("AIRPODSWIDGET_TRACE_MORPH") == "1"
    trace_indices = {0, 4, 8, 12, 16, 20, 24, frames - 1}
    previous_sample_time = time.perf_counter()
    for index in range(frames):
        QTest.qWait(16)
        app.processEvents()
        sample_time = time.perf_counter()
        toggle_center = item_global_center(toggle)
        sample: dict[str, float | tuple[float, float]] = {
            "center": toggle_center,
            "progress": float(widget.property("morphProgress")),
            "width": float(widget.width()),
            "base_width": float(widget.property("baseWidth")),
            "base_height": float(widget.property("baseHeight")),
            "expanded_opacity": float(expanded_content.property("opacity")),
            "minimized_opacity": float(minimized_content.property("opacity")),
            "expanded_visible": float(bool(expanded_content.property("visible"))),
            "minimized_visible": float(bool(minimized_content.property("visible"))),
            "sample_interval_ms": (sample_time - previous_sample_time) * 1000,
        }
        previous_sample_time = sample_time
        for name, item in (reveal_items or {}).items():
            sample[f"reveal_{name}"] = float(item.property("opacity"))
        if shell is not None:
            shell_rect = item_global_rect(shell)
            sample["shell_rect"] = shell_rect
            for name, item in (reveal_items or {}).items():
                if not bool(expanded_content.property("visible")):
                    continue
                if float(expanded_content.property("opacity")) < 0.08:
                    continue
                if not bool(item.property("visible")) or float(item.property("opacity")) < 0.25:
                    continue
                rect = item_global_rect(item)
                sample[f"rect_{name}"] = rect
                shell_right = shell_rect[0] + shell_rect[2]
                shell_bottom = shell_rect[1] + shell_rect[3]
                if (
                    rect[0] < shell_rect[0] - 1
                    or rect[1] < shell_rect[1] - 1
                    or rect[0] + rect[2] > shell_right + 1
                    or rect[1] + rect[3] > shell_bottom + 1
                ):
                    sample[f"clip_{name}"] = 1.0
        if collision_items:
            toggle_rect = item_global_rect(toggle)
            scene_live = bool(expanded_content.property("visible")) and float(
                expanded_content.property("opacity")
            ) >= 0.08
            if scene_live:
                for name, item in collision_items.items():
                    if bool(item.property("visible")) and float(item.property("opacity")) >= 0.08:
                        if rects_overlap(toggle_rect, item_global_rect(item)):
                            sample[f"overlap_{name}"] = 1.0
            if bool(minimized_content.property("visible")) and float(
                minimized_content.property("opacity")
            ) >= 0.08 and rects_overlap(toggle_rect, item_global_rect(minimized_content)):
                sample["overlap_minimized"] = 1.0
        samples.append(sample)
        if trace_morph and index in trace_indices:
            anchor_x = float(widget.property("morphAnchorGlobalX"))
            anchor_y = float(widget.property("morphAnchorGlobalY"))
            base_width = float(widget.property("baseWidth"))
            desired_width = float(widget.property("desiredWidth"))
            scale = desired_width / base_width if base_width else 0.0
            rect_trace = ""
            if shell is not None:
                shell_rect = item_global_rect(shell)
                rect_trace = f" shell=({shell_rect[0]:.1f},{shell_rect[1]:.1f},{shell_rect[2]:.1f},{shell_rect[3]:.1f})"
                for name, item in (reveal_items or {}).items():
                    rect = item_global_rect(item)
                    rect_trace += (
                        f" {name}=({rect[0]:.1f},{rect[1]:.1f},{rect[2]:.1f},{rect[3]:.1f};"
                        f"o={float(item.property('opacity')):.2f})"
                    )
            print(
                f"{capture_prefix}-{index:02d} "
                f"p={float(sample['progress']):.4f} "
                f"window=({float(widget.property('x')):.1f},"
                f"{float(widget.property('y')):.1f}) "
                f"size=({float(widget.width()):.1f},"
                f"{float(widget.height()):.1f}) "
                f"toggle=({toggle_center[0]:.1f},{toggle_center[1]:.1f}) "
                f"anchor=({anchor_x:.1f},{anchor_y:.1f}) "
                f"drift=({toggle_center[0] - anchor_x:.1f},"
                f"{toggle_center[1] - anchor_y:.1f}) "
                f"dt={float(sample['sample_interval_ms']):.1f}ms "
                f"content=({float(sample['expanded_opacity']):.2f},"
                f"{float(sample['minimized_opacity']):.2f}) "
                f"reveal=({float(sample.get('reveal_header', 0.0)):.2f},"
                f"{float(sample.get('reveal_battery', 0.0)):.2f},"
                f"{float(sample.get('reveal_audio', 0.0)):.2f},"
                f"{float(sample.get('reveal_media', 0.0)):.2f}) "
                f"scale={scale:.2f} "
                f"edge=({'L' if bool(widget.property('morphExpandLeft')) else 'R'},"
                f"{'U' if bool(widget.property('morphExpandUp')) else 'D'}) "
                f"active={bool(widget.property('morphTransitionActive'))}"
                f"{rect_trace}",
                flush=True,
            )
        if trace_morph:
            overlap_keys = [key for key in sample if key.startswith("overlap_")]
            if overlap_keys:
                print(
                    f"{capture_prefix}-{index:02d} overlap={','.join(overlap_keys)} "
                    f"toggle_rect={item_global_rect(toggle)}",
                    flush=True,
                )
        if capture_dir is not None:
            widget.grabWindow().save(str(capture_dir / f"{capture_prefix}-{index:02d}.png"))
    if trace_morph and len(samples) > 1:
        geometry_jumps = [
            max(
                abs(float(second["base_width"]) - float(first["base_width"])),
                abs(float(second["base_height"]) - float(first["base_height"])),
            )
            for first, second in zip(samples, samples[1:])
        ]
        if geometry_jumps:
            jump_index = max(range(len(geometry_jumps)), key=geometry_jumps.__getitem__)
            print(
                f"{capture_prefix}-geometry-max index={jump_index + 1:02d} "
                f"step={geometry_jumps[jump_index]:.1f} "
                f"from=({float(samples[jump_index]['base_width']):.1f},"
                f"{float(samples[jump_index]['base_height']):.1f}) "
                f"to=({float(samples[jump_index + 1]['base_width']):.1f},"
                f"{float(samples[jump_index + 1]['base_height']):.1f})",
                flush=True,
            )
    return samples


def validate_morph_frames(
    samples: list[dict[str, float | tuple[float, float]]],
    increasing: bool,
    scale: float,
    label: str,
    errors: list[str],
) -> None:
    progress = [float(sample["progress"]) for sample in samples]
    for first, second in zip(progress, progress[1:]):
        if increasing and second + 0.002 < first:
            errors.append(f"{label} morph progress reversed direction.")
            break
        if not increasing and second - 0.002 > first:
            errors.append(f"{label} morph progress reversed direction.")
            break
    if any(abs(second - first) > 0.18 for first, second in zip(progress, progress[1:])):
        errors.append(f"{label} morph progress contains an abrupt frame jump.")
    for sample in samples:
        overlap_keys = [key for key in sample if key.startswith("overlap_")]
        if any(float(sample[key]) > 0 for key in overlap_keys):
            errors.append(f"{label} morph placed a visible control over another UI element.")
            break
        clip_keys = [key for key in sample if key.startswith("clip_")]
        if any(float(sample[key]) > 0 for key in clip_keys):
            errors.append(
                f"{label} morph revealed content outside the shell bounds "
                f"({clip_keys[0]}, progress={float(sample['progress']):.3f})."
            )
            break
        expanded_opacity = float(sample["expanded_opacity"])
        minimized_opacity = float(sample["minimized_opacity"])
        opacity_sum = expanded_opacity + minimized_opacity
        if bool(sample.get("expanded_visible", 0)) and bool(sample.get("minimized_visible", 0)) \
                and abs(opacity_sum - 1.0) > 0.20:
            errors.append(
                f"{label} morph crossfade lost both scenes at once "
                f"(progress={float(sample['progress']):.3f}, opacity={opacity_sum:.3f})."
            )
            break
        if opacity_sum < 0.75 and (
                float(sample["base_height"]) > 160
                or float(sample["base_width"]) > 260
        ):
            errors.append(
                f"{label} morph created a low-content large-surface frame "
                f"(progress={float(sample['progress']):.3f}, "
                f"height={float(sample['base_height']):.1f}, opacity={opacity_sum:.3f})."
            )
            break
        expected_width = float(sample["base_width"]) * scale
        if abs(float(sample["width"]) - expected_width) > 1.5:
            errors.append(f"{label} morph window geometry fell behind its progress value.")
            break
    geometry_steps = [
        max(
            abs(float(second["base_width"]) - float(first["base_width"])),
            abs(float(second["base_height"]) - float(first["base_height"])),
        )
        for first, second in zip(samples, samples[1:])
    ]
    if any(step > 48 for step in geometry_steps):
        errors.append(
            f"{label} morph geometry jumped more than 48 base pixels in one 16ms sample."
        )


def validate_reveal_order(
    samples: list[dict[str, float | tuple[float, float]]],
    names: tuple[str, ...],
    opening: bool,
    label: str,
    errors: list[str],
) -> None:
    values = {
        name: [float(sample[f"reveal_{name}"]) for sample in samples]
        for name in names
    }
    for name, series in values.items():
        for first, second in zip(series, series[1:]):
            if opening and second + 0.06 < first:
                errors.append(f"{label} {name} reveal reversed direction.")
                break
            if not opening and second - 0.06 > first:
                errors.append(f"{label} {name} reveal reversed direction.")
                break

    first_visible = {
        name: next((index for index, value in enumerate(series) if value >= 0.08), None)
        for name, series in values.items()
    }
    if opening:
        ordered = [first_visible[name] for name in names]
        if all(index is not None for index in ordered) and ordered != sorted(ordered):
            errors.append(f"{label} groups did not reveal in the intended order.")
    else:
        last_visible = {
            name: max(
                (index for index, value in enumerate(series) if value >= 0.08),
                default=None,
            )
            for name, series in values.items()
        }
        ordered = [last_visible[name] for name in names]
        if all(index is not None for index in ordered) and ordered != sorted(ordered):
            errors.append(f"{label} groups did not leave in the intended order.")


def max_anchor_deviation(samples: list[tuple[float, float]], origin: tuple[float, float]) -> float:
    return max(
        ((x - origin[0]) ** 2 + (y - origin[1]) ** 2) ** 0.5
        for x, y in samples
    ) if samples else 0.0


def max_frame_jump(samples: list[tuple[float, float]]) -> float:
    return max(
        ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        for (x1, y1), (x2, y2) in zip(samples, samples[1:])
    ) if len(samples) > 1 else 0.0


def item_global_rect(item: QObject) -> tuple[float, float, float, float]:
    top_left = item.mapToGlobal(QPointF(0, 0))
    bottom_right = item.mapToGlobal(QPointF(item.width(), item.height()))
    return (
        float(top_left.x()),
        float(top_left.y()),
        float(bottom_right.x() - top_left.x()),
        float(bottom_right.y() - top_left.y()),
    )


def item_window_point(
    item: QObject,
    window: QObject,
    x_ratio: float,
    y_ratio: float,
) -> QPoint:
    point = item.mapToGlobal(
        QPointF(item.width() * x_ratio, item.height() * y_ratio)
    )
    return window.mapFromGlobal(QPoint(round(point.x()), round(point.y())))


def rects_overlap(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    first_right = first[0] + first[2]
    first_bottom = first[1] + first[3]
    second_right = second[0] + second[2]
    second_bottom = second[1] + second[3]
    return (
        first[0] < second_right
        and second[0] < first_right
        and first[1] < second_bottom
        and second[1] < first_bottom
    )


def popup_x_matches_anchor_or_work_area_edge(
    popup_x: float,
    popup_width: float,
    anchor_x: float,
    work_left: float,
    work_right: float,
) -> bool:
    """Accept centered placement, or the documented edge clamp when centered
    placement would leave the independent popup outside the work area.
    """
    centered_x = anchor_x - popup_width / 2
    clamped_x = max(work_left + 4, min(work_right - popup_width - 4, centered_x))
    return abs(popup_x - clamped_x) <= 2.0


def main() -> int:
    QQuickStyle.setStyle("Basic")
    app = QApplication([sys.argv[0], "--demo"])
    app.setQuitOnLastWindowClosed(False)
    font_errors = load_application_fonts()
    capture_value = os.environ.get("AIRPODSWIDGET_CAPTURE_DIR", "")
    capture_dir = Path(capture_value) if capture_value else None
    if capture_dir is not None:
        capture_dir.mkdir(parents=True, exist_ok=True)
    original_argv = sys.argv[:]
    sys.argv[:] = [sys.argv[0], "--demo"]
    with tempfile.TemporaryDirectory(prefix="airpods-widget-qml-") as data_dir:
        os.environ["LOCALAPPDATA"] = data_dir
        controller = AppController(app)
        engine = QQmlApplicationEngine()
        qml_messages: list[str] = []
        engine.warnings.connect(
            lambda warnings: qml_messages.extend(error.toString() for error in warnings)
        )
        engine.rootContext().setContextProperty("appController", controller)
        engine.load(QUrl.fromLocalFile(str(SRC / "ui" / "Main.qml")))
        controller.start()
        app.processEvents()

        errors = font_errors + list(qml_messages)
        root_objects = engine.rootObjects()
        if not root_objects:
            errors.append("No root object was created.")
        else:
            flags_valid = root_objects[0].property("desktopWidgetFlagsValid")
            if not flags_valid:
                errors.append("Desktop widget focus/stacking flags are incomplete.")
            widget_windows = [
                child
                for child in root_objects[0].children()
                if type(child).__name__ == "QQuickWindow"
                and child.property("title") == "AirPods Widget"
            ]
            if not widget_windows:
                errors.append("Desktop widget window was not created.")
            elif not widget_windows[0].isVisible():
                errors.append("Desktop widget window was created but is not visible.")
            else:
                widget = widget_windows[0]
                if abs(float(widget.property("baseHeight")) - 428.0) > 1.0:
                    errors.append("Desktop widget media layout height is not large enough for playback controls.")
                controller.setWidgetAlwaysOnTop(True)
                app.processEvents()
                if not int(widget.flags()) & int(Qt.WindowStaysOnTopHint):
                    errors.append("Desktop widget did not apply the always-on-top setting.")
                controller.setWidgetAlwaysOnTop(False)
                controller.setWidgetScale(1.2)
                QTest.qWait(1200)
                app.processEvents()
                expected_width = float(widget.property("baseWidth")) * controller.widgetScale
                if abs(widget.width() - expected_width) > 1.0:
                    errors.append("Desktop widget scale did not resize the complete layout.")
                if os.environ.get("AIRPODSWIDGET_TRACE_MORPH_SCALE") != "1":
                    controller.setWidgetScale(1.0)
                    QTest.qWait(420)
                app.processEvents()

                # Minimize/restore must preserve the toggle button's screen
                # position while the window width changes.
                toggle_buttons = widget.findChildren(QObject, "widgetToggleButton")
                old_flow_buttons = widget.findChildren(QObject, "flowMinimizeButton")
                old_minimized_buttons = widget.findChildren(QObject, "minimizedRestoreButton")
                toggle_button = toggle_buttons[0] if len(toggle_buttons) == 1 else None
                if len(toggle_buttons) != 1:
                    errors.append("Widget did not create exactly one shared minimize/restore button.")
                if old_flow_buttons or old_minimized_buttons:
                    errors.append("Widget still contains duplicate state-specific toggle buttons.")
                elif toggle_button is not None:
                    header_controls = widget.findChildren(QObject, "headerControls")
                    flow_contents = widget.findChildren(QObject, "flowContent")
                    minimized_contents = widget.findChildren(QObject, "minimizedContent")
                    if len(header_controls) != 1:
                        errors.append("Expanded header controls are not addressable for collision testing.")
                    elif rects_overlap(item_global_rect(toggle_button), item_global_rect(header_controls[0])):
                        errors.append("Expanded toggle button overlaps the header status controls.")
                    if len(flow_contents) != 1 or len(minimized_contents) != 1:
                        errors.append("Morph content layers are not addressable for frame testing.")
                    elif float(flow_contents[0].width()) <= 100:
                        errors.append("Expanded flow content did not receive the widget width.")
                    shell_candidates = widget.findChildren(QObject, "widgetShell")
                    if len(shell_candidates) != 1:
                        errors.append("Widget shell is not addressable for clipping checks.")

                    flow_reveal_items: dict[str, QObject] = {}
                    for name, object_name in (
                        ("header", "flowHeader"),
                        ("battery", "flowBatteryOverview"),
                        ("audio", "flowAudioOutput"),
                        ("media", "flowMediaSection"),
                    ):
                        candidates = widget.findChildren(QObject, object_name)
                        if len(candidates) != 1:
                            errors.append(f"{object_name} is not addressable for reveal-order testing.")
                        else:
                            flow_reveal_items[name] = candidates[0]

                    expanded_direction = (
                        bool(widget.property("morphExpandLeft")),
                        bool(widget.property("morphExpandUp")),
                    )
                    if not bool(widget.property("morphPlacementResolved")):
                        errors.append("Widget did not resolve the morph direction before interaction.")
                    flow_anchor = item_global_center(toggle_button)
                    toggle_button.clicked.emit()
                    if len(flow_contents) == 1 and len(minimized_contents) == 1:
                        minimize_frames = sample_morph_frames(
                            app,
                            widget,
                            toggle_button,
                            flow_contents[0],
                            minimized_contents[0],
                            reveal_items=flow_reveal_items,
                            capture_dir=capture_dir,
                            capture_prefix="morph-collapse",
                            shell=shell_candidates[0] if len(shell_candidates) == 1 else None,
                            collision_items={"header": header_controls[0]} if len(header_controls) == 1 else None,
                        )
                        validate_morph_frames(
                            minimize_frames,
                            True,
                            controller.widgetScale,
                            "Minimize",
                            errors,
                        )
                        if len(flow_reveal_items) == 4:
                            validate_reveal_order(
                                minimize_frames,
                                ("media", "audio", "battery", "header"),
                                False,
                                "Minimize",
                                errors,
                            )
                        minimize_samples = [sample["center"] for sample in minimize_frames]
                    else:
                        minimize_samples = sample_global_centers(app, toggle_button)
                    minimize_deviation = max_anchor_deviation(minimize_samples, flow_anchor)
                    minimize_jump = max_frame_jump(minimize_samples)
                    if minimize_deviation > 2.5:
                        errors.append(f"Minimize morph moved the shared toggle anchor ({minimize_deviation:.2f}px).")
                    if minimize_jump > 3.5:
                        errors.append(f"Minimize morph produced a visible frame jump ({minimize_jump:.2f}px).")
                    QTest.qWait(180)
                    if not bool(widget.property("minimized")):
                        errors.append("Minimize transition did not reach the minimized state.")
                    if len(minimized_contents) != 1:
                        errors.append("Minimized content is not addressable for collision testing.")
                    elif rects_overlap(item_global_rect(toggle_button), item_global_rect(minimized_contents[0])):
                        errors.append("Minimized toggle button overlaps the minimized content envelope.")
                    minimized_direction = (
                        bool(widget.property("morphExpandLeft")),
                        bool(widget.property("morphExpandUp")),
                    )
                    if minimized_direction != expanded_direction:
                        errors.append("Minimize transition changed the expansion direction.")

                    minimized_audio_sections = widget.findChildren(QObject, "minimizedAudioOutput")
                    if len(minimized_audio_sections) != 1:
                        errors.append("Minimized audio section is not addressable for spacing testing.")
                    else:
                        minimized_volume_buttons = minimized_audio_sections[0].findChildren(QObject, "volumeButton")
                        if len(minimized_volume_buttons) != 1:
                            errors.append("Minimized volume button is not addressable for spacing testing.")
                        else:
                            toggle_rect = item_global_rect(toggle_button)
                            volume_rect = item_global_rect(minimized_volume_buttons[0])
                            if rects_overlap(toggle_rect, volume_rect):
                                errors.append("Minimized volume and toggle buttons overlap.")
                            elif expanded_direction[0]:
                                gap = toggle_rect[0] - (volume_rect[0] + volume_rect[2])
                                if gap < 6:
                                    errors.append("Minimized right-side controls do not keep a 6px gap.")
                            else:
                                gap = volume_rect[0] - (toggle_rect[0] + toggle_rect[2])
                                if gap < 6:
                                    errors.append("Minimized left-side controls do not keep a 6px gap.")

                    minimized_anchor = item_global_center(toggle_button)
                    toggle_button.clicked.emit()
                    if len(flow_contents) == 1 and len(minimized_contents) == 1:
                        restore_frames = sample_morph_frames(
                            app,
                            widget,
                            toggle_button,
                            flow_contents[0],
                            minimized_contents[0],
                            reveal_items=flow_reveal_items,
                            capture_dir=capture_dir,
                            capture_prefix="morph-restore",
                            shell=shell_candidates[0] if len(shell_candidates) == 1 else None,
                            collision_items={"header": header_controls[0]} if len(header_controls) == 1 else None,
                        )
                        validate_morph_frames(
                            restore_frames,
                            False,
                            controller.widgetScale,
                            "Restore",
                            errors,
                        )
                        if len(flow_reveal_items) == 4:
                            validate_reveal_order(
                                restore_frames,
                                ("header", "battery", "audio", "media"),
                                True,
                                "Restore",
                                errors,
                            )
                        restore_samples = [sample["center"] for sample in restore_frames]
                    else:
                        restore_samples = sample_global_centers(app, toggle_button)
                    restore_deviation = max_anchor_deviation(restore_samples, minimized_anchor)
                    restore_jump = max_frame_jump(restore_samples)
                    if restore_deviation > 2.5:
                        errors.append(f"Restore morph moved the shared toggle anchor ({restore_deviation:.2f}px).")
                    if restore_jump > 3.5:
                        errors.append(f"Restore morph produced a visible frame jump ({restore_jump:.2f}px).")
                    QTest.qWait(180)
                    if bool(widget.property("minimized")):
                        errors.append("Restore transition did not reach the expanded state.")
                    restored_direction = (
                        bool(widget.property("morphExpandLeft")),
                        bool(widget.property("morphExpandUp")),
                    )
                    if restored_direction != expanded_direction:
                        errors.append("Restore transition changed the expansion direction.")
                    expected_direction = expanded_direction

                    for _ in range(2):
                        toggle_button.clicked.emit()
                        QTest.qWait(420)
                        toggle_button.clicked.emit()
                        QTest.qWait(420)
                        repeated_direction = (
                            bool(widget.property("morphExpandLeft")),
                            bool(widget.property("morphExpandUp")),
                        )
                        if repeated_direction != expected_direction:
                            errors.append("Repeated minimize/restore changed the expansion direction.")
                            break

                    if os.environ.get("AIRPODSWIDGET_TRACE_MEDIA_DURING_MORPH") == "1":
                        controller.setMediaVisible(True)
                        QTest.qWait(260)
                        media_morph_anchor = item_global_center(toggle_button)
                        toggle_button.clicked.emit()
                        QTest.qWait(80)
                        controller.setMediaVisible(False)
                        QTest.qWait(700)
                        media_morph_end = item_global_center(toggle_button)
                        print(
                            "media-during-morph "
                            f"anchor=({media_morph_anchor[0]:.1f},{media_morph_anchor[1]:.1f}) "
                            f"end=({media_morph_end[0]:.1f},{media_morph_end[1]:.1f}) "
                            f"window=({float(widget.property('x')):.1f},"
                            f"{float(widget.property('y')):.1f}) "
                            f"size=({float(widget.width()):.1f},"
                            f"{float(widget.height()):.1f})",
                            flush=True,
                        )
                        if not bool(widget.property("minimized")):
                            errors.append("Media change interrupted the minimize morph.")
                        if max_anchor_deviation([media_morph_end], media_morph_anchor) > 1.5:
                            errors.append("Media change moved the shared morph anchor at settle.")
                        toggle_button.clicked.emit()
                        QTest.qWait(700)
                        controller.setMediaVisible(True)
                        QTest.qWait(260)

                # Pausing must keep the media surface and its play control;
                # only the transport icon changes from pause to play.
                controller._media.playing = False
                controller.mediaChanged.emit()
                QTest.qWait(240)
                if not controller.mediaAvailable:
                    errors.append("Pausing the current media session hid the player.")
                controller.togglePlayPause()
                if not controller.mediaPlaying:
                    errors.append("Paused demo media did not switch back to playing.")

                # Output buttons keep fixed slots while the shared indicator
                # slides between them in demo mode.
                indicators = widget.findChildren(QObject, "outputActiveIndicator")
                if not indicators:
                    errors.append("Output selector active indicator was not created.")
                else:
                    indicator = indicators[0]
                    controller.selectAudioOutput("demo-airpods")
                    QTest.qWait(240)
                    first_indicator_x = float(indicator.property("x"))
                    controller.selectAudioOutput("demo-headphones")
                    QTest.qWait(240)
                    second_indicator_x = float(indicator.property("x"))
                    if abs(second_indicator_x - first_indicator_x) < 50:
                        errors.append("Output selector indicator did not slide between fixed slots.")

                # Background opacity must affect only QML material layers;
                # the top-level window and all foreground content stay opaque.
                controller.setWidgetOpacity(0.55)
                app.processEvents()
                if abs(widget.opacity() - 1.0) > 0.01:
                    errors.append("Background opacity faded the complete widget window.")
                controller.setWidgetOpacity(0.90)

                if capture_dir is not None:
                    controller.setWidgetOpacity(0.55)
                    controller.setTheme("dark")
                    QTest.qWait(240)
                    widget.grabWindow().save(str(capture_dir / "widget-dark-clear.png"))
                    controller.setTheme("light")
                    QTest.qWait(240)
                    widget.grabWindow().save(str(capture_dir / "widget-light-clear.png"))
                    controller.setWidgetOpacity(0.90)
                    controller.setTheme("dark")
                    QTest.qWait(240)
                    widget.grabWindow().save(str(capture_dir / "widget-dark.png"))
                    controller.setTheme("light")
                    QTest.qWait(240)
                    widget.grabWindow().save(str(capture_dir / "widget-light.png"))
                    controller.setTheme("dark")

                # The persistent-player preference keeps the flow slot stable
                # without pretending that a media session still exists. The
                # empty surface must be visible, while its transport remains
                # unavailable and the compact composition remains unaffected.
                controller.setMediaVisible(True)
                controller.setMediaAlwaysVisible(True)
                controller._media = MediaState()
                controller.mediaChanged.emit()
                QTest.qWait(420)
                flow_media = widget.findChildren(QObject, "flowMediaSection")
                if controller.mediaAvailable:
                    errors.append("Empty media state was still reported as available.")
                if not bool(widget.property("layoutMediaAvailable")):
                    errors.append("Persistent player setting did not keep the flow media slot.")
                if abs(float(widget.property("baseHeight")) - 428.0) > 1.0:
                    errors.append("Persistent flow player did not retain its expanded height.")
                if len(flow_media) == 1:
                    if bool(flow_media[0].property("available")):
                        errors.append("Persistent empty player exposed media as available.")
                    if not bool(flow_media[0].property("persistent")):
                        errors.append("Flow media section did not receive the persistent flag.")
                    if abs(float(flow_media[0].height()) - 146.0) > 1.0:
                        errors.append("Persistent empty player did not retain its surface height.")
                else:
                    errors.append("Flow media section was not addressable for persistent-player testing.")
                if capture_dir is not None:
                    widget.grabWindow().save(str(capture_dir / "widget-persistent-empty-dark.png"))

                controller.setMediaAlwaysVisible(False)
                QTest.qWait(420)
                if bool(widget.property("layoutMediaAvailable")):
                    errors.append("Disabling persistent player did not remove the empty flow slot.")
                if abs(float(widget.property("baseHeight")) - 276.0) > 1.0:
                    errors.append("Flow widget did not return to the no-media height.")

                controller._media = MediaState(
                    available=True,
                    title="The Adults Are Talking — A Very Long Track Title for Marquee Preview",
                    artist="The Strokes",
                    source_app="Spotify",
                    playing=True,
                    can_previous=True,
                    can_next=True,
                    can_play_pause=True,
                    position_seconds=42.0,
                    duration_seconds=754.0,
                    seekable=True,
                )
                controller.mediaChanged.emit()
                QTest.qWait(420)

                # Turning the player off must remove only the media player;
                # the always-visible audio output section remains in place.
                controller.setMediaVisible(False)
                QTest.qWait(1200)
                app.processEvents()
                if controller.mediaAvailable:
                    errors.append("Player visibility setting did not hide the media section.")
                if abs(float(widget.property("baseHeight")) - 276.0) > 1.0:
                    errors.append("Desktop widget did not switch to the compact no-media height.")
                if abs(widget.height() - 276.0) > 1.0:
                    errors.append("Desktop widget retained excess height with no media session.")
                if capture_dir is not None:
                    widget.grabWindow().save(str(capture_dir / "widget-no-media-dark.png"))
                    controller.setTheme("light")
                    QTest.qWait(240)
                    widget.grabWindow().save(str(capture_dir / "widget-no-media-light.png"))
                    controller.setTheme("dark")

                # Compact mode is a separate composition, and minimized mode
                # must reduce the actual window envelope at the same anchor.
                controller.setMediaVisible(True)
                controller.setWidgetLayoutMode("compact")
                QTest.qWait(700)
                app.processEvents()
                if not bool(widget.property("compact")):
                    errors.append("Compact layout mode did not become active.")
                if abs(float(widget.property("baseHeight")) - 272.0) > 1.0:
                    errors.append("Compact media layout height is incorrect.")
                if capture_dir is not None:
                    controller.setTheme("dark")
                    widget.grabWindow().save(str(capture_dir / "widget-compact-dark.png"))
                    controller.setTheme("light")
                    QTest.qWait(240)
                    widget.grabWindow().save(str(capture_dir / "widget-compact-light.png"))
                    controller.setTheme("dark")

                compact_contents = widget.findChildren(QObject, "compactContent")
                compact_reveal_items: dict[str, QObject] = {}
                for name, object_name in (
                    ("battery", "compactBatteryGroup"),
                    ("audio", "compactAudioOutput"),
                    ("media", "compactMediaStrip"),
                ):
                    candidates = widget.findChildren(QObject, object_name)
                    if len(candidates) != 1:
                        errors.append(f"{object_name} is not addressable for compact reveal testing.")
                    else:
                        compact_reveal_items[name] = candidates[0]
                if toggle_button is not None and len(compact_contents) == 1 and len(compact_reveal_items) == 3:
                    toggle_button.clicked.emit()
                    compact_minimize_frames = sample_morph_frames(
                        app,
                        widget,
                        toggle_button,
                        compact_contents[0],
                        minimized_contents[0],
                        reveal_items=compact_reveal_items,
                        capture_dir=capture_dir,
                        capture_prefix="compact-collapse",
                        shell=shell_candidates[0] if len(shell_candidates) == 1 else None,
                        collision_items={"battery": compact_reveal_items["battery"]},
                    )
                    validate_morph_frames(
                        compact_minimize_frames,
                        True,
                        controller.widgetScale,
                        "Compact minimize",
                        errors,
                    )
                    validate_reveal_order(
                        compact_minimize_frames,
                        ("media", "audio", "battery"),
                        False,
                        "Compact minimize",
                        errors,
                    )
                    QTest.qWait(180)
                    if not bool(widget.property("minimized")):
                        errors.append("Compact minimize transition did not reach the minimized state.")

                    toggle_button.clicked.emit()
                    compact_restore_frames = sample_morph_frames(
                        app,
                        widget,
                        toggle_button,
                        compact_contents[0],
                        minimized_contents[0],
                        reveal_items=compact_reveal_items,
                        capture_dir=capture_dir,
                        capture_prefix="compact-restore",
                        shell=shell_candidates[0] if len(shell_candidates) == 1 else None,
                        collision_items={"battery": compact_reveal_items["battery"]},
                    )
                    validate_morph_frames(
                        compact_restore_frames,
                        False,
                        controller.widgetScale,
                        "Compact restore",
                        errors,
                    )
                    validate_reveal_order(
                        compact_restore_frames,
                        ("battery", "audio", "media"),
                        True,
                        "Compact restore",
                        errors,
                    )
                    QTest.qWait(180)
                    if bool(widget.property("minimized")):
                        errors.append("Compact restore transition did not reach the expanded state.")

                compact_audio_sections = widget.findChildren(QObject, "compactAudioOutput")
                compact_output_panels = compact_audio_sections[0].findChildren(QObject, "outputPanel") if compact_audio_sections else []
                compact_output_rows = compact_audio_sections[0].findChildren(QObject, "outputButtonRow") if compact_audio_sections else []
                if compact_output_panels and compact_output_rows:
                    output_panel = compact_output_panels[0]
                    output_row = compact_output_rows[0]
                    expected_output_x = max(0.0, (float(output_panel.width()) - float(output_row.width())) / 2.0)
                    if abs(float(output_row.x()) - expected_output_x) > 1.0:
                        errors.append("Compact output buttons are not horizontally centered.")

                compact_popovers = widget.findChildren(QObject, "volumePopoverCompact")
                if not compact_popovers:
                    errors.append("Volume popover was not created.")
                else:
                    compact_audio = widget.findChildren(QObject, "compactAudioOutput")
                    if not compact_audio:
                        errors.append("Compact audio output section was not created.")
                    else:
                        compact_volume_buttons = compact_audio[0].findChildren(QObject, "compactVolumeButton")
                        if len(compact_volume_buttons) != 1:
                            errors.append("Compact volume button is not addressable for screen-click testing.")
                        else:
                            global_volume_center = item_global_center(compact_volume_buttons[0])
                            local_volume_center = widget.mapFromGlobal(
                                QPoint(round(global_volume_center[0]), round(global_volume_center[1]))
                            )
                            QTest.mouseClick(
                                widget,
                                Qt.LeftButton,
                                Qt.NoModifier,
                                local_volume_center,
                            )
                    QTest.qWait(240)
                    if not bool(compact_popovers[0].property("visible")):
                        errors.append("Volume popover did not open from the compact volume button.")
                    else:
                        compact_popup = compact_popovers[0]
                        if not int(compact_popup.flags()) & int(Qt.WindowStaysOnTopHint):
                            errors.append("Compact volume popover is not kept above the widget window.")
                        compact_rails = compact_popup.findChildren(QObject, "verticalVolumeRail")
                        if not compact_rails:
                            errors.append("Compact volume popover did not expose its vertical rail.")
                        else:
                            compact_rail = compact_rails[0]
                            compact_before = int(compact_popup.property("displayedValue"))
                            QTest.mouseClick(
                                compact_popup,
                                Qt.LeftButton,
                                Qt.NoModifier,
                                item_window_point(compact_rail, compact_popup, 0.5, 0.10),
                            )
                            QTest.qWait(100)
                            compact_clicked = int(compact_popup.property("displayedValue"))
                            if compact_clicked < 90:
                                errors.append("Compact vertical volume rail did not respond to a screen click.")

                            QTest.mousePress(
                                compact_popup,
                                Qt.LeftButton,
                                Qt.NoModifier,
                                item_window_point(compact_rail, compact_popup, 0.5, 0.86),
                            )
                            QTest.mouseMove(
                                compact_popup,
                                item_window_point(compact_rail, compact_popup, 0.5, 0.18),
                                20,
                            )
                            QTest.mouseRelease(
                                compact_popup,
                                Qt.LeftButton,
                                Qt.NoModifier,
                                item_window_point(compact_rail, compact_popup, 0.5, 0.18),
                            )
                            QTest.qWait(100)
                            compact_dragged = int(compact_popup.property("displayedValue"))
                            if compact_dragged < 70 or compact_dragged == compact_before:
                                errors.append("Compact vertical volume rail did not respond to a drag.")
                        if compact_audio and len(compact_volume_buttons) == 1:
                            compact_trigger = compact_volume_buttons[0]
                            popup_center_x = float(compact_popup.property("x")) + float(compact_popup.property("width")) / 2
                            trigger_center = item_global_center(compact_trigger)
                            popup_screen = widget.screen().availableGeometry()
                            if not popup_x_matches_anchor_or_work_area_edge(
                                float(compact_popup.property("x")),
                                float(compact_popup.property("width")),
                                trigger_center[0],
                                float(popup_screen.x()),
                                float(popup_screen.x() + popup_screen.width()),
                            ):
                                print(
                                    "compact-popup-anchor "
                                    f"popup=({float(compact_popup.property('x')):.1f},"
                                    f"{float(compact_popup.property('y')):.1f}) "
                                    f"size=({float(compact_popup.property('width')):.1f},"
                                    f"{float(compact_popup.property('height')):.1f}) "
                                    f"trigger=({trigger_center[0]:.1f},{trigger_center[1]:.1f})",
                                    flush=True,
                                )
                                errors.append("Compact volume popover is not anchored to the clicked trigger.")
                    compact_value_targets = (
                        compact_audio[0].findChildren(QObject, "compactVolumeValueMouse")
                        if compact_audio else []
                    )
                    if compact_value_targets:
                        errors.append("Compact volume has a duplicate value popup trigger.")
                    if capture_dir is not None:
                        widget.grabWindow().save(str(capture_dir / "widget-compact-volume-dark.png"))
                        if bool(compact_popovers[0].property("visible")):
                            compact_popovers[0].grabWindow().save(
                                str(capture_dir / "volume-popup-compact-dark.png")
                            )
                    QMetaObject.invokeMethod(compact_popovers[0], "closePopup")

                flow_popovers = widget.findChildren(QObject, "volumePopoverFlow")
                if flow_popovers and bool(flow_popovers[0].property("visible")):
                    errors.append("Flow volume popover was open despite the horizontal slider being visible.")

                if toggle_button is not None and not bool(widget.property("minimized")):
                    toggle_button.clicked.emit()
                QTest.qWait(700)
                app.processEvents()
                if not bool(widget.property("minimized")):
                    errors.append("Widget did not enter minimized mode.")
                if abs(float(widget.property("baseWidth")) - 220.0) > 1.0 or abs(float(widget.property("baseHeight")) - 76.0) > 1.0:
                    errors.append("Minimized widget envelope is incorrect.")
                if capture_dir is not None:
                    widget.grabWindow().save(str(capture_dir / "widget-minimized-dark.png"))
                minimized_popovers = widget.findChildren(QObject, "volumePopoverMinimized")
                if minimized_popovers:
                    minimized_audio = widget.findChildren(QObject, "minimizedAudioOutput")
                    popup_anchor = item_global_center(toggle_button) if toggle_button is not None else None
                    minimized_height_before_popup = float(widget.height())
                    minimized_x_before_popup = float(widget.x())
                    minimized_y_before_popup = float(widget.y())
                    if not minimized_audio:
                        errors.append("Minimized audio output section was not created.")
                    else:
                        minimized_volume_buttons = minimized_audio[0].findChildren(QObject, "volumeButton")
                        if not minimized_volume_buttons:
                            errors.append("Minimized volume button was not created.")
                        else:
                            # Exercise the same screen hit path as a user click;
                            # invoking the QML function alone would miss an
                            # overlapping MouseArea regression.
                            global_volume_center = item_global_center(minimized_volume_buttons[0])
                            local_volume_center = widget.mapFromGlobal(
                                QPoint(round(global_volume_center[0]), round(global_volume_center[1]))
                            )
                            QTest.mouseClick(
                                widget,
                                Qt.LeftButton,
                                Qt.NoModifier,
                                local_volume_center,
                            )
                            content_rect = item_global_rect(minimized_contents[0]) if len(minimized_contents) == 1 else None
                            audio_rect = item_global_rect(minimized_audio[0])
                            if content_rect is not None and content_rect[2] < 120:
                                errors.append("Minimized content slot is too narrow for its controls.")
                            if content_rect is not None and abs(
                                (audio_rect[1] + audio_rect[3] / 2)
                                - (content_rect[1] + content_rect[3] / 2)
                            ) > 2.0:
                                errors.append("Minimized volume control is not vertically centered in its slot.")
                    QTest.qWait(700)
                    if not bool(minimized_popovers[0].property("visible")):
                        errors.append("Volume popover did not open in minimized mode.")
                    else:
                        minimized_popup = minimized_popovers[0]
                        minimized_rails = minimized_popup.findChildren(
                            QObject, "minimizedVerticalVolumeRail"
                        )
                        if not minimized_rails:
                            errors.append("Minimized volume popover did not expose its vertical rail.")
                        else:
                            minimized_rail = minimized_rails[0]
                            minimized_before = int(minimized_popup.property("displayedValue"))
                            QTest.mouseClick(
                                minimized_popup,
                                Qt.LeftButton,
                                Qt.NoModifier,
                                item_window_point(minimized_rail, minimized_popup, 0.5, 0.10),
                            )
                            QTest.qWait(100)
                            minimized_clicked = int(minimized_popup.property("displayedValue"))
                            if minimized_clicked < 90:
                                errors.append("Minimized vertical volume rail did not respond to a screen click.")

                            QTest.mousePress(
                                minimized_popup,
                                Qt.LeftButton,
                                Qt.NoModifier,
                                item_window_point(minimized_rail, minimized_popup, 0.5, 0.84),
                            )
                            QTest.mouseMove(
                                minimized_popup,
                                item_window_point(minimized_rail, minimized_popup, 0.5, 0.20),
                                20,
                            )
                            QTest.mouseRelease(
                                minimized_popup,
                                Qt.LeftButton,
                                Qt.NoModifier,
                                item_window_point(minimized_rail, minimized_popup, 0.5, 0.20),
                            )
                            QTest.qWait(100)
                            minimized_dragged = int(minimized_popup.property("displayedValue"))
                            if minimized_dragged < 70 or minimized_dragged == minimized_before:
                                errors.append("Minimized vertical volume rail did not respond to a drag.")
                    if abs(float(widget.height()) - minimized_height_before_popup) > 1.0:
                        errors.append("Minimized volume popover changed the widget window height.")
                    if abs(float(widget.x()) - minimized_x_before_popup) > 1.0 or abs(float(widget.y()) - minimized_y_before_popup) > 1.0:
                        errors.append("Minimized volume popover moved the widget window.")
                    vertical_tracks = minimized_popovers[0].findChildren(QObject, "minimizedVerticalVolumeTrack")
                    if not vertical_tracks:
                        errors.append("Minimized volume popover did not create a visible vertical track.")
                    elif vertical_tracks[0].width() < 4 or vertical_tracks[0].height() < 12:
                        errors.append("Minimized vertical volume track has invalid geometry.")
                    if popup_anchor is not None:
                        expanded_anchor = item_global_center(toggle_button)
                        if abs(expanded_anchor[0] - popup_anchor[0]) > 1.0 or abs(expanded_anchor[1] - popup_anchor[1]) > 1.0:
                            errors.append("Opening minimized volume popover moved the toggle button anchor.")
                    popup_x = float(minimized_popovers[0].property("x"))
                    popup_y = float(minimized_popovers[0].property("y"))
                    popup_width = float(minimized_popovers[0].property("width"))
                    popup_height = float(minimized_popovers[0].property("height"))
                    popup_screen = widget.screen().availableGeometry()
                    work_left = float(popup_screen.x()) if popup_screen.width() > 0 else 0.0
                    work_top = float(popup_screen.y()) if popup_screen.height() > 0 else 0.0
                    work_right = (
                        float(popup_screen.x() + popup_screen.width())
                        if popup_screen.width() > 0 else 1920.0
                    )
                    work_bottom = (
                        float(popup_screen.y() + popup_screen.height())
                        if popup_screen.height() > 0 else 1080.0
                    )
                    if popup_x < work_left + 3 or popup_y < work_top + 3:
                        errors.append("Minimized volume popover opened outside the screen work area.")
                    if popup_x + popup_width > work_right - 3:
                        errors.append("Minimized volume popover exceeds the screen work area horizontally.")
                    if popup_y + popup_height > work_bottom - 3:
                        errors.append("Minimized volume popover exceeds the screen work area vertically.")
                    if minimized_audio and minimized_volume_buttons:
                        minimized_trigger_center = item_global_center(minimized_volume_buttons[0])
                        if not popup_x_matches_anchor_or_work_area_edge(
                            popup_x,
                            popup_width,
                            minimized_trigger_center[0],
                            work_left,
                            work_right,
                        ):
                            errors.append("Minimized volume popover is not anchored to its trigger.")
                        if rects_overlap(
                            (popup_x, popup_y, popup_width, popup_height),
                            item_global_rect(toggle_button),
                        ):
                            errors.append("Minimized volume popover overlaps the fixed toggle button.")
                    popup_windows = [
                        candidate
                        for candidate in QGuiApplication.allWindows()
                        if candidate.isVisible()
                        and candidate is not widget
                        and abs(candidate.width() - popup_width) <= 1
                        and abs(candidate.height() - popup_height) <= 1
                    ]
                    if not popup_windows:
                        errors.append("Minimized volume popover did not create its independent popup window.")
                    else:
                        if not int(popup_windows[0].flags()) & int(Qt.WindowDoesNotAcceptFocus):
                            errors.append("Minimized volume popover can accept focus.")
                        if capture_dir is not None:
                            popup_windows[0].grabWindow().save(str(capture_dir / "volume-popup-minimized-dark.png"))
                    if capture_dir is not None:
                        widget.grabWindow().save(str(capture_dir / "widget-minimized-volume-dark.png"))
                    QMetaObject.invokeMethod(minimized_popovers[0], "closePopup")
                    QTest.qWait(700)
                    if abs(float(widget.height()) - 76.0) > 1.0:
                        errors.append("Minimized widget did not retain its compact window height after closing volume popover.")
                else:
                    errors.append("Minimized volume popover was not created.")
                if toggle_button is not None and bool(widget.property("minimized")):
                    toggle_button.clicked.emit()
                # Compact mode must remove the media strip and its reserved
                # envelope when the player setting is off; otherwise the
                # short mode inherits the old empty-player gap.
                controller.setMediaVisible(False)
                QTest.qWait(700)
                if bool(widget.property("compact")) and abs(float(widget.property("baseHeight")) - 160.0) > 1.0:
                    errors.append("Compact widget retained excess height with no media session.")
                compact_controllers = widget.findChildren(QObject, "compactContent")
                if compact_controllers:
                    compact_controller = compact_controllers[0].findChildren(QObject, "compactController")
                    if compact_controller and abs(float(compact_controller[0].property("implicitHeight")) - 113.0) > 1.0:
                        errors.append("Compact controller retained excess internal height without media.")
                if capture_dir is not None and bool(widget.property("compact")):
                    widget.grabWindow().save(str(capture_dir / "widget-compact-no-media-dark.png"))
                controller.setMediaVisible(True)
                QTest.qWait(420)
                controller.setWidgetLayoutMode("flow")
                QTest.qWait(700)
                controller.setMediaVisible(False)
                QTest.qWait(700)

            # A scan gap must look intentionally empty, not like the last
            # remembered model. Battery rows keep their fixed geometry while
            # their value columns swap to the visual EmptyIndicator.
            demo_timer = getattr(controller, "_demo_timer", None)
            if demo_timer is not None:
                demo_timer.stop()
            controller._airpods = AirPodsState()
            controller._connected_device_name = ""
            controller.airpodsChanged.emit()
            QTest.qWait(260)
            empty_name = widget.findChildren(QObject, "flowDeviceName") if widget is not None else []
            empty_left_row = widget.findChildren(QObject, "leftBatteryRow") if widget is not None else []
            if controller.deviceAvailable:
                errors.append("Empty AirPods state still reported a connected or detected device.")
            if controller.deviceName:
                errors.append("Empty AirPods state retained a device name in the controller.")
            if len(empty_name) == 1 and empty_name[0].property("text") != "":
                errors.append("Empty AirPods state retained a device name in the header slot.")
            if len(empty_left_row) == 1 and int(empty_left_row[0].property("value")) != -1:
                errors.append("Empty AirPods state exposed a stale battery value.")
            if capture_dir is not None and widget is not None:
                widget.grabWindow().save(str(capture_dir / "widget-empty-device-dark.png"))
                controller.setTheme("light")
                QTest.qWait(240)
                widget.grabWindow().save(str(capture_dir / "widget-empty-device-light.png"))
                controller.setTheme("dark")

            windows = {
                child.property("title"): child
                for child in root_objects[0].children()
                if type(child).__name__ == "QQuickWindow"
            }
            tray = windows.get("AirPods")
            settings = windows.get("AirPods Widget 설정")
            notification = windows.get("AirPods 알림")
            if tray is None:
                errors.append("Tray popup window was not created.")
            else:
                controller.showTrayPopupRequested.emit(120, 120)
                app.processEvents()
                if not tray.isVisible():
                    errors.append("Tray popup window did not become visible.")
                if abs(tray.height() - 322.0) > 1.0:
                    errors.append("Tray popup retained excess height with no media session.")
                tray_popovers = tray.findChildren(QObject, "volumePopoverFlow")
                if tray_popovers and bool(tray_popovers[0].property("visible")):
                    errors.append("Tray flow volume popover was open despite the horizontal slider being visible.")
                controller.showTrayPopupRequested.emit(120, 120)
                app.processEvents()
                QTest.qWait(220)
                if tray.isVisible():
                    errors.append("Second tray activation did not hide the tray popup.")
                controller.showTrayPopupRequested.emit(120, 120)
                app.processEvents()
                QTest.qWait(120)
                if not tray.isVisible():
                    errors.append("Tray popup could not be reopened for visual capture.")
                if capture_dir is not None:
                    tray.grabWindow().save(str(capture_dir / "tray-dark.png"))
                    controller.setTheme("light")
                    QTest.qWait(240)
                    tray.grabWindow().save(str(capture_dir / "tray-light.png"))
                    controller.setTheme("dark")
                tray.hide()

            if settings is None:
                errors.append("Settings window was not created.")
            else:
                controller.setTheme("dark")
                settings.reveal(120, 120)
                QTest.qWait(240)
                if not settings.isVisible():
                    errors.append("Settings window did not become visible.")
                if capture_dir is not None:
                    settings.grabWindow().save(str(capture_dir / "settings-dark.png"))
                    controller.setTheme("light")
                    QTest.qWait(240)
                    settings.grabWindow().save(str(capture_dir / "settings-light.png"))
                    controller.setTheme("dark")
                settings.hide()

            if notification is None:
                errors.append("Notification popup window was not created.")
            else:
                notification.reveal(120, 120)
                app.processEvents()
                if not notification.isVisible():
                    errors.append("Notification popup window did not become visible.")
                if not int(notification.flags()) & int(Qt.WindowDoesNotAcceptFocus):
                    errors.append("Notification popup can accept focus.")
                notification.hide()

        if errors:
            print("QML runtime check failed:")
            print("\n".join(errors))
            controller.shutdown()
            sys.argv[:] = original_argv
            return 1
        print("QML runtime check passed.")
        controller.shutdown()
        sys.argv[:] = original_argv
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
