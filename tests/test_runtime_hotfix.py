from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import runtime_easing_guard as guard
import runtime_hotfix as hotfix


@dataclass
class Device:
    name: str
    address: int
    paired: bool = True
    connected: bool = False


def test_address_normalization_is_stable():
    expected = 0xAABBCCDDEEFF
    assert hotfix._normalize_address("AA:BB:CC:DD:EE:FF") == expected
    assert hotfix._normalize_address("aa-bb-cc-dd-ee-ff") == expected
    assert hotfix._normalize_address(expected) == expected
    assert hotfix._normalize_address(True) is None
    assert hotfix._normalize_address(0) is None
    assert hotfix._normalize_address("not-an-address") is None


def test_explicit_selected_address_wins_regardless_of_enumeration_order(monkeypatch):
    first = Device("AirPods A", 0x111111111111, connected=True)
    selected = Device("AirPods B", 0x222222222222)
    monkeypatch.setattr(hotfix, "_selected_identity", lambda: (selected.address, ""))
    monkeypatch.setattr(hotfix, "_recent_identity", lambda: (first.address, first.name))
    assert hotfix._choose_airpods([first, selected]) is selected
    assert hotfix._choose_airpods([selected, first]) is selected


def test_missing_explicit_selection_does_not_silently_switch_pair(monkeypatch):
    present = Device("AirPods A", 0x111111111111, connected=True)
    monkeypatch.setattr(hotfix, "_selected_identity", lambda: (0x999999999999, ""))
    monkeypatch.setattr(hotfix, "_recent_identity", lambda: (present.address, present.name))
    assert hotfix._choose_airpods([present]) is None


def test_recent_address_survives_windows_enumeration_order(monkeypatch):
    first = Device("AirPods A", 0x111111111111)
    recent = Device("AirPods B", 0x222222222222)
    monkeypatch.setattr(hotfix, "_selected_identity", lambda: (None, ""))
    monkeypatch.setattr(hotfix, "_recent_identity", lambda: (recent.address, recent.name))
    assert hotfix._choose_airpods([first, recent]) is recent
    assert hotfix._choose_airpods([recent, first]) is recent


def test_connected_pair_is_fallback_only_without_selection_or_recent(monkeypatch):
    idle = Device("AirPods A", 0x111111111111)
    connected = Device("AirPods B", 0x222222222222, connected=True)
    monkeypatch.setattr(hotfix, "_selected_identity", lambda: (None, ""))
    monkeypatch.setattr(hotfix, "_recent_identity", lambda: (None, ""))
    assert hotfix._choose_airpods([idle, connected]) is connected


def test_recent_store_is_atomic_and_round_trips(tmp_path, monkeypatch):
    monkeypatch.setattr(hotfix, "_recent_path", lambda: tmp_path / "recent_airpods.json")
    device = Device("AirPods Pro", 0xAABBCCDDEEFF, connected=True)
    hotfix._save_recent(device)
    assert hotfix._recent_identity() == (0xAABBCCDDEEFF, "AirPods Pro")
    assert not (tmp_path / "recent_airpods.tmp").exists()


def test_qml_primary_becomes_right_middle_and_native_y_anchor_tracks_center(tmp_path):
    path = tmp_path / "WidgetWindow.qml"
    path.write_text(
        '''Window {\n'
        ' property real morphAnchorInset: 45\n'
        ' function chooseMorphPlacement(anchorX, anchorY) {\n'
        '   morphExpandLeft = false\n'
        '   if (anchorY > 10) { morphExpandUp = true }\n'
        ' }\n'
        ' Rectangle { id: shell\n'
        '   Item { id: toggleSlot; objectName: "widgetToggleSlot"; height: 30\n'
        '     y: window.morphExpandUp\n'
        '        ? parent.height - (window.morphAnchorInset - shell.y) - height / 2\n'
        '        : (window.morphAnchorInset - shell.y) - height / 2\n'
        '   }\n'
        ' }\n'
        ' function applyMorphGeometryFrame(force) {\n'
        '   var offsetY = window.morphExpandUp\n'
        '      ? frameHeight - window.morphAnchorInset * appController.widgetScale\n'
        '      : window.morphAnchorInset * appController.widgetScale\n'
        ' }\n'
        '}\n'''.replace("'\n        '", ""),
        encoding="utf-8",
    )
    assert hotfix._patch_qml_widget(path)
    patched = path.read_text(encoding="utf-8")
    assert "morphExpandLeft = true" in patched
    assert "morphExpandUp = false" in patched
    assert "y: (parent.height - height) / 2" in patched
    assert "var offsetY = frameHeight / 2" in patched
    assert not hotfix._patch_qml_widget(path)


def test_web_primary_patch_does_not_move_unrelated_34px_button(tmp_path):
    path = tmp_path / "widget.css"
    path.write_text(
        ".compact-primary{width:34px;height:34px;right:2px;top:10px;transform:scale(.9);}\n"
        ".ordinary{width:34px;height:34px;right:2px;top:10px;transform:scale(.9);}",
        encoding="utf-8",
    )
    assert hotfix._patch_web_primary(path)
    patched = path.read_text(encoding="utf-8")
    primary, ordinary = patched.split(".ordinary")
    assert "right:12px" in primary
    assert "top:50%" in primary
    assert "translateY(-50%)" in primary
    assert "right:2px" in ordinary
    assert "top:10px" in ordinary
    assert "scale(.9)" in ordinary


def test_structural_easing_guard_changes_only_structural_function(tmp_path):
    path = tmp_path / "motion.py"
    path.write_text(
        "def morph_geometry():\n"
        "    curve = QEasingCurve.OutBack\n\n"
        "def press_button():\n"
        "    curve = QEasingCurve.OutBack\n",
        encoding="utf-8",
    )
    assert guard.patch_structural_easing(path)
    patched = path.read_text(encoding="utf-8")
    structural, local = patched.split("def press_button")
    assert "QEasingCurve.InOutCubic" in structural
    assert "QEasingCurve.OutBack" in local


def test_center_anchor_geometry_has_no_y_drift_and_monotonic_size():
    start_w, start_h = 472.0, 370.0
    end_w, end_h = 318.0, 68.0
    anchor_x, anchor_y = 1000.0, 520.0
    right_inset = 45.0
    prev_w, prev_h = start_w, start_h
    centers = []
    for frame in range(61):
        t = frame / 60.0
        eased = t * t * (3.0 - 2.0 * t)
        width = start_w + (end_w - start_w) * eased
        height = start_h + (end_h - start_h) * eased
        x = anchor_x - (width - right_inset)
        y = anchor_y - height / 2.0
        center_y = y + height / 2.0
        centers.append(center_y)
        assert width <= prev_w + 1e-9
        assert height <= prev_h + 1e-9
        prev_w, prev_h = width, height
    assert max(centers) - min(centers) < 1e-9
    assert abs(prev_w - end_w) < 1e-9
    assert abs(prev_h - end_h) < 1e-9
