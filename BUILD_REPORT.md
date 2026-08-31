# Build and verification report

## Implemented

- AirPods Pro 3 (`0x2027`) Continuity BLE advertisement parser
- Left/right/case battery, charge state and in-ear state
- Conservative two-broadcaster merge and 10-second loss handling
- Apple-like scalable desktop widget, tray popup and non-focus notification popup
- Animated battery values/bars and pause-aware slow media-title marquee
- Windows media title/artist/app and previous/play-pause/next controls
- Process-based League of Legends / VALORANT popup suppression, including borderless mode
- Compact battery-based remaining-time estimate between the L/R and CASE rows (`6h 35m`)
- User-supplied MP3 low-battery alert, internal volume control and restartable test playback
- Configurable Windows output shortcut buttons with per-device enable/disable state (up to three,
  ordered AirPods / speaker / headphones by default)
- Windows default-output switching and current-output system-volume slider
- MSIX packaging with Windows `globalMediaControl` capability for media session access
- Multi-monitor-safe popup placement and off-screen widget position recovery
- Optional always-on-top widget mode with no-focus flag retained; game foreground forces bottom stacking
- Bottom-right drag resize using the same persisted scale as the settings slider
- Dark/light translucent material whose opacity setting affects only background layers
- Purposeful volume/output/timeline transitions and tray-click popup toggle behavior
- Dimension-based neutral surfaces, frosted glass alpha, hairline borders, and restrained radii
- Source-aligned spacing grid for battery rows, volume controls, output buttons, and media timeline
- Paired AirPods shortcut availability even while its remembered audio endpoint is inactive
- Stale Chrome media rejection using source, title and artist identity
- BLE expiry clears stale in-ear flags without discarding the last battery readings
- No custom Bluetooth/kernel driver, Test Mode, Secure Boot change or silent audio loop
- UI redesign specification with source-to-component mapping and a repeatable spec check
- Reworked widget shell, typography roles, surface hierarchy, compact no-media layout, and
  fixed-slot output selector with a sliding active indicator
- Synchronized slider track/thumb geometry and external-value animation
- Windows 11 DWM transient Acrylic backdrop with a safe QML alpha fallback on older Windows

## Verification run on 2026-08-31 (UI redesign 0.1.7.0)

- 28 Python unit tests passed
- Python source compilation passed
- QML delimiter/structure validation passed
- QML runtime loading passed on the current Windows host, including demo media layout and the
  desktop widget's no-focus/bottom-stack flags
- UI redesign specification anchor check passed, including fixed-grid battery rows, shared
  output active indicator, compact no-media layout, and DWM material hook
- Windows Core Audio output enumeration and current-volume read passed on the build host
- MP3 source/volume/playback smoke check passed; no playback error was reported
- PyInstaller Windows x64 one-folder build passed
- MakeAppx Windows x64 package creation passed
- Built EXE startup smoke test passed without an embedded-Python, Qt DLL or QML startup error
- MSIX manifest version verified as `0.1.7.0`
- The portable executable and `_internal` runtime were synced to the project root

The root contains the portable executable and runtime, plus `AirPodsWidget.msix`. The MSIX is the
media-capable build because Windows requires package identity and the `globalMediaControl`
capability for the GSMTC manager. The root EXE remains useful for UI/BLE checks but cannot read or
control global media sessions by itself.

## Tests that require the target Windows PC

The current host reports a remembered/paired AirPods device, but it was disconnected during this
verification run. The original portable EXE also did not expose a usable Windows media session to
the probe (`E_ACCESSDENIED`) because it had no package identity. Therefore the following still need
hands-on acceptance with the newly signed MSIX, connected AirPods and a compatible player:

- Live AirPods Pro 3 BLE reception
- Windows media session control against Spotify/Chrome
- Tray behavior across Explorer restarts and multiple Windows monitors
- League of Legends / Riot Vanguard coexistence and borderless-game regression

The Vanguard audit found only user-mode calls: Windows BLE scanning, paired-device enumeration,
foreground-process-name lookup, and media-session APIs. There is no kernel/custom Bluetooth driver,
device-control IOCTL, service installation, Test Mode, Secure Boot change, or low-latency silent
audio loop in this source tree. This is a static audit, not a Vanguard compatibility guarantee.

Run `verify_windows.bat` first. It performs unit tests, static validation and a real offscreen QML load on
the target PC. Then run `run_demo_windows.bat`, followed by `run_windows.bat`.
