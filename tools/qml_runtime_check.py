from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl, Qt, QObject
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from controller import AppController


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
                if abs(float(widget.property("baseHeight")) - 464.0) > 1.0:
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
                controller.setWidgetScale(1.0)

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

                # Turning the player off must remove only the media player;
                # the always-visible audio output section remains in place.
                controller.setMediaVisible(False)
                QTest.qWait(1200)
                app.processEvents()
                if controller.mediaAvailable:
                    errors.append("Player visibility setting did not hide the media section.")
                if abs(float(widget.property("baseHeight")) - 302.0) > 1.0:
                    errors.append("Desktop widget did not switch to the compact no-media height.")
                if abs(widget.height() - 302.0) > 1.0:
                    errors.append("Desktop widget retained excess height with no media session.")
                if capture_dir is not None:
                    widget.grabWindow().save(str(capture_dir / "widget-no-media-dark.png"))
                    controller.setTheme("light")
                    QTest.qWait(240)
                    widget.grabWindow().save(str(capture_dir / "widget-no-media-light.png"))
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
                if abs(tray.height() - 340.0) > 1.0:
                    errors.append("Tray popup retained excess height with no media session.")
                controller.showTrayPopupRequested.emit(120, 120)
                app.processEvents()
                if tray.isVisible():
                    errors.append("Second tray activation did not hide the tray popup.")
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
