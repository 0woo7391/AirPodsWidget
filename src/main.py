from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


_qt_dll_handles = []


def _relaunch_with_project_venv() -> None:
    """Keep source launches on the same Python environment as the app."""
    if os.name != "nt" or getattr(sys, "frozen", False):
        return

    project_root = Path(__file__).resolve().parents[1]
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.is_file():
        return

    if Path(sys.executable).resolve() == venv_python.resolve():
        return

    os.execv(
        str(venv_python),
        [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
    )


def _configure_qt_dll_search_path() -> None:
    """Prefer the PySide6/shiboken6 DLLs from the active Python environment."""
    if os.name != "nt":
        return

    try:
        import importlib.util

        package_paths: list[Path] = []
        for package_name in ("PySide6", "shiboken6"):
            spec = importlib.util.find_spec(package_name)
            if spec and spec.submodule_search_locations:
                package_paths.extend(
                    Path(location) for location in spec.submodule_search_locations
                )

        for package_path in package_paths:
            for dll_path in (package_path, package_path / "Qt" / "bin"):
                if dll_path.is_dir():
                    _qt_dll_handles.append(os.add_dll_directory(str(dll_path)))

        pyside_path = next(
            (path for path in package_paths if path.name == "PySide6"), None
        )
        shiboken_path = next(
            (path for path in package_paths if path.name == "shiboken6"), None
        )
        preload_paths = []
        if pyside_path:
            preload_paths.append(pyside_path / "Qt6Core.dll")
        if shiboken_path:
            preload_paths.append(shiboken_path / "shiboken6.abi3.dll")
        if pyside_path:
            preload_paths.append(pyside_path / "pyside6.abi3.dll")
        for dll_path in preload_paths:
            if dll_path.is_file():
                _qt_dll_handles.append(__import__("ctypes").WinDLL(str(dll_path)))
    except (ImportError, OSError):
        # PySide6 will provide the normal import error if no usable installation exists.
        pass


_relaunch_with_project_venv()
_configure_qt_dll_search_path()

from PySide6.QtCore import QCoreApplication, Qt, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from controller import AppController, resource_path


def configure_logging() -> None:
    log_dir = Path(os.getenv("LOCALAPPDATA", Path.home())) / "AirPodsWidget"
    handlers: list[logging.Handler]
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers = [logging.FileHandler(log_dir / "app.log", encoding="utf-8")]
    except OSError:
        # Logging must never prevent the widget from starting. This can happen
        # when a previous log file is locked or the app-data directory is read-only.
        handlers = [logging.NullHandler()]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def load_application_fonts() -> None:
    """Register the bundled UI font before QML components are created."""
    for relative_path in (
        "assets/fonts/Pretendard-Regular.otf",
        "assets/fonts/Pretendard-Medium.otf",
        "assets/fonts/Pretendard-SemiBold.otf",
    ):
        font_id = QFontDatabase.addApplicationFont(str(resource_path(relative_path)))
        if font_id < 0:
            logging.getLogger(__name__).warning(
                "Failed to load application font: %s", relative_path
            )


def main() -> int:
    configure_logging()
    QCoreApplication.setOrganizationName("AirPodsWidget")
    QCoreApplication.setApplicationName("AirPods Widget")
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QQuickStyle.setStyle("Basic")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(resource_path("assets/app.ico"))))
    load_application_fonts()

    controller = AppController(app)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    qml_path = resource_path("src/ui/Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 2

    app.aboutToQuit.connect(controller.shutdown)
    controller.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
