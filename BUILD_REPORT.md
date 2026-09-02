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
- Neutral surfaces, hairline borders, restrained radii, and a separate compact controller layout
- Source-aligned spacing grid for battery rows, volume controls, output buttons, and media timeline
- Paired AirPods shortcut availability even while its remembered audio endpoint is inactive
- Paired AirPods shortcut requests a user-mode A2DP Audio Sink reconnect and retries the endpoint
- Paused media sessions retain the player and use an explicit play command to resume
- Stale Chrome media rejection using source, title and artist identity
- BLE expiry clears stale in-ear flags without discarding the last battery readings,
  and never treats that expiry alone as a physical removal for auto-pause
- No custom Bluetooth/kernel driver, Test Mode, Secure Boot change or silent audio loop
- UI redesign specification with source-to-component mapping and a repeatable spec check
- Reworked widget shell, typography roles, surface hierarchy, compact no-media layout, and
  fixed-slot output selector with a sliding active indicator
- Synchronized slider track/thumb geometry and external-value animation
- Shared battery label/status/track/value columns with a centered remaining-time estimate
- Battery values use a smaller adjacent numeric column instead of a floating right-edge value
- Charging state uses a small borderless amber status dot; the old bolt glyph is not used
- Minimize motion uses a single eased window transition, pixel-snapped anchor correction, and
  zero-delay coalesced native window-shape updates matched to the morph geometry
- Minimized volume popover draws an explicit vertical rail and progress fill in a separate
  `WindowDoesNotAcceptFocus` popup window without resizing the parent widget
- Saved Windows startup preference is reconciled with the HKCU Run entry on every normal launch
- Minimize/restore uses one shared toggle anchor, coordinate-based expansion direction, and
  dropdown-menu-morph timing without duplicate buttons or content geometry jumps
- Windows 11 DWM transient Acrylic backdrop with a safe QML alpha fallback on older Windows

## Verification run on 2026-09-01 (single-progress staged morph and corrected minimized spacing 0.1.20.0)

- 36 Python unit tests passed
- Python source compilation passed
- QML delimiter/structure validation passed
- QML runtime loading passed on the current Windows host, including demo media layout and the
  desktop widget's no-focus/bottom-stack flags
- QML morph runtime measurement passed: one shared toggle, minimize/restore anchor deviation under
  2.5 px and frame jump under 3.5 px across 16 ms samples
- QML demo check passed with the player still visible while paused
- UI redesign specification anchor check passed, including fixed-grid battery rows, shared
  output active indicator, compact no-media layout, and DWM material hook
- Windows Core Audio output enumeration and current-volume read passed on the build host
- MP3 source/volume/playback smoke check passed; no playback error was reported
- PyInstaller Windows x64 one-folder build passed
- MakeAppx Windows x64 package creation passed
- Built EXE startup smoke test passed without an embedded-Python, Qt DLL or QML startup error
- Widget header settings button removed; settings remains available from the tray popup only
- Minimized volume popup runtime check verified the real screen click path, parent window geometry,
  toggle anchor, screen bounds, and no-focus popup flags
- Minimize/restore runtime check verified the expansion direction is resolved before the first
  interaction and remains unchanged across repeated toggles
- Morph frame validation checks monotonic progress, per-frame jumps, progress-derived geometry,
  large empty surfaces, and the actual gap between minimized volume and toggle controls
- Minimize/restore now uses one eased geometry interval with a non-overlapping content handoff;
  width and height no longer wait on separate stages that can read as a snap
- The shared chevron morphs through one interpolated path instead of cross-fading into an X
- MSIX manifest version verified as `0.1.20.0`
- The portable executable and `_internal` runtime were synced to the project root

## Verification run on 2026-09-01 (smooth morph handoff 0.1.21.0)

- Morph geometry uses one `InOutSine` progress curve for both width and height; the previous
  double-eased staged resize was removed
- Expanded and minimized content no longer cross-fades in the same header coordinates; the
  handoff is a single near-complete-size state change to prevent ghosted text and controls
- Native shape radius is clamped to the current window's short dimension during intermediate sizes
- QML 16ms runtime morph check passed for monotonic progress, anchor stability, geometry steps,
  content visibility, and repeated direction stability
- Python tests, project validation, and UI specification checks passed after the morph changes
- MSIX manifest version updated to `0.1.21.0`; installation was not retried in this run

## Verification run on 2026-09-01 (staged content reveal 0.1.22.0)

- Expanded and minimized content now remains mounted during the morph; the old hard opacity
  threshold swap was removed
- Flow mode reveals header, battery, audio, and media as separate ordered groups. Compact mode
  uses the same staged reveal with its denser battery/audio/media timing
- Opening waits for the shell to make room before revealing a group; closing hides each group
  before the shrinking shell can clip it
- Reveal transforms are limited to six pixels and use the existing single morph progress, so
  content does not independently reflow or bounce inside the resizing window
- QML runtime captures passed for flow and compact intermediate frames, reveal direction/order,
  fixed toggle anchor, no clipping/overlap checks, and actual compact volume-button screen click
- 36 Python unit tests passed with the build's `PYTHONPATH=src` environment; project validation,
  UI specification checks, and QML runtime checks passed
- MSIX manifest version updated to `0.1.22.0`; installation was not retried in this run

## Verification run on 2026-09-01 (final staged reveal timing 0.1.23.0)

- Flow and compact morphs use one shell progress with staged logical-group reveals instead of
  swapping complete content layers at hard thresholds
- Opening keeps the compact summary until the expanded header has room, then brings in the
  battery, audio, and media groups in order; closing removes media/audio before the shell can
  clip them
- Header and battery timing overlaps slightly on expansion to avoid a large title-only frame;
  reveal travel is limited to six pixels with no bounce
- QML runtime validation passed for flow and compact intermediate frames, monotonic group
  reveals, intended reveal/exit order, stable toggle anchor, repeated direction, and compact
  volume-button screen input
- 36 Python unit tests, project validation, UI specification validation, and QML runtime checks
  passed; the generated portable EXE also stayed alive for a three-second `--demo` smoke run
- MSIX manifest version updated to `0.1.23.0`; installation was not retried in this run

## Verification run on 2026-09-01 (compact volume interaction and morph handoff 0.1.24.0)

- Compact and minimized volume triggers now open an independent, anchored vertical
  volume popover without changing the parent widget envelope or the fixed toggle position
- The painted volume rail remains narrow, but its full rail is the mouse hit target; both
  screen-click and press/drag paths update the same displayed value and preserve the parent
  volume binding
- Compact spacing uses an explicit slot next to the toggle; the summary, volume trigger,
  and fixed toggle are vertically aligned and the compact popover is anchored to the clicked
  trigger rather than a hidden icon slot
- Morph handoff now removes clipped output rows before the shell becomes too narrow, while
  keeping the volume row visible slightly longer; opening delays expanded groups until the
  shell has room
- QML runtime validation passed for compact/minimized popover click and drag, popup bounds,
  fixed toggle anchor, compact spacing, and intermediate reveal/exit ordering
- MSIX manifest version updated to `0.1.24.0`; installation was not retried in this run

## Verification run on 2026-09-01 (compact volume popup visibility and reveal layout 0.1.25.0)

- Compact volume icon, label, and displayed value all use the same anchored popup path;
  the value itself is now a usable trigger instead of a passive number
- The compact/minimized volume popover is transient to the widget and stays above the
  non-activating widget window, preserving the widget envelope and fixed toggle position
- Expanded flow content now has explicit left/right anchors; its children no longer lay out
  against a zero-width parent and clip or appear late at the left edge
- Opening reveal groups overlap in a short sequence and closing reverses the order, removing
  the title-only reveal frame while retaining calm motion
- QML runtime validation passed for compact trigger click, vertical rail click/drag, popup
  topmost flag, popup bounds, parent geometry stability, and reveal ordering
- 36 Python unit tests, project validation, UI specification validation, and QML runtime checks
  passed; the rebuilt portable EXE stayed responsive for a three-second `--demo` smoke run
- MSIX manifest version updated to `0.1.25.0`; installation can update the previous package

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
- Paired AirPods reconnect and delayed A2DP endpoint activation on the target Bluetooth adapter
- Tray behavior across Explorer restarts and multiple Windows monitors
- League of Legends / Riot Vanguard coexistence and borderless-game regression

The Vanguard audit found only user-mode calls: Windows BLE scanning, paired-device enumeration,
the built-in Windows Bluetooth service-state API for A2DP reconnect, foreground-process-name lookup,
and media-session APIs. There is no kernel/custom Bluetooth driver, device-control IOCTL, app service
installation, Test Mode, Secure Boot change, or low-latency silent audio loop in this source tree.
This is a static audit, not a Vanguard compatibility guarantee.

Run `verify_windows.bat` first. It performs unit tests, static validation and a real offscreen QML load on
the target PC. Then run `run_demo_windows.bat`, followed by `run_windows.bat`.

## 2026-09-02 verification status correction

The `0.1.25.0` build record above must not be read as proof that the real desktop
collapse/restore animation is complete. The source includes a shared toggle-anchor
implementation and the offscreen QML runtime check measured zero toggle-center drift,
but that check does not validate Windows native-window composition between frames.

The following remain **incomplete** until captured on the actual Windows desktop:

- toggle center and widget edge coordinates through both collapse and restore
- native rounded Region/border synchronization with changing window size
- absence of one-frame lateral snaps, clipped corners, overlap, or title-only reveal
- repeated behavior at different desktop placements and in both themes

The current authoritative checklist is `UI_REDESIGN_SPEC.md`, sections 12 through 17.
Do not report the morph as complete from build success, QML load success, or the
offscreen test alone.

## 2026-09-02 source and build checkpoint 0.1.26.0

- Moved Windows Core Audio endpoint enumeration, current-volume polling, volume
  writes, paired endpoint polling, and active output switching out of the Qt UI
  thread. Only the resulting snapshot/status is applied on the UI thread.
- Removed the duplicate compact volume trigger path and the per-frame slider
  geometry Behaviors. The fill and thumb now follow one value timeline.
- Added regression coverage for the worker boundary. `PYTHONPATH=src
  .venv\\Scripts\\python.exe -m pytest -q` passed with `39 passed`.
- `python tools/ui_spec_check.py`, `python tools/validate_project.py`, and
  `python tools/qml_runtime_check.py` passed. The QML capture directory is
  `artifacts/qml-verify/` and is ignored from Git.
- `packaging/AppxManifest.xml` is staged at version `0.1.26.0` so a later
  package build is not blocked by the previous `0.1.25.0` content identity.
- PyInstaller one-folder build completed and copied the new executable to the
  project root. A three-second `AirPodsWidget.exe --demo` startup smoke passed
  with the process responsive, then the test process was stopped. A separate
  five-second normal-mode startup smoke also stayed responsive and was stopped.
- The installer reached the administrator UAC request but the consent window was
  not available in the remote session. Signing and installation were therefore
  not completed; `Get-AuthenticodeSignature AirPodsWidget.msix` reports
  `NotSigned` and no installed-package claim is made.
- Native Windows desktop mid-frame animation, live Chrome media control, and
  paired AirPods endpoint reconnection remain unverified until the signed MSIX
  is installed and launched on the desktop.
