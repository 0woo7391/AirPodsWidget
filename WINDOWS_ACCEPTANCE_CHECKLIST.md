# Windows acceptance checklist

## 1. UI and settings

- Run `verify_windows.bat`; all checks must pass.
- Run `run_demo_windows.bat`.
- Confirm the desktop widget, tray popup, settings window and notification card load without errors.
- Change widget scale, opacity and theme; restart and confirm persistence.
- Move the widget to each monitor; restart and confirm the saved position.
- Play the low-battery test sound at 0%, 30%, 60% and 100%; confirm no overlapping playback.

## 2. AirPods Pro 3

- Pair and connect AirPods Pro 3 before running `run_windows.bat`.
- Confirm left/right/case battery values and charging states.
- Open and close the case and confirm case data refreshes when advertised.
- Remove both earbuds; confirm pause only after the debounce delay.
- Enable auto-resume, wear the earbuds one at a time, and confirm playback resumes only after both are worn.
- Disconnect and reconnect; confirm session time resets while today's time remains.

## 3. Media

- Verify title, artist and source app with Spotify and Chrome/YouTube.
- Verify long titles move slowly and stop moving when playback is paused.
- Verify previous, play/pause and next buttons only enable when the media session supports them.

## 4. League of Legends / Vanguard

- Restart Windows once after the first installation.
- Start League of Legends and enter a Practice Tool game in borderless mode.
- Connect/disconnect AirPods while the game is foreground; the visual connection popup must not appear.
- Confirm the game never minimizes and keyboard focus stays in the game.
- Confirm the widget remains behind the game while tray data continues to update.
- Close and reopen League, then reboot once more to rule out a startup-only Vanguard issue.
- If Vanguard reports an error, close AirPods Widget, save `%LOCALAPPDATA%\AirPodsWidget\app.log`, and do not install any replacement Bluetooth driver.
