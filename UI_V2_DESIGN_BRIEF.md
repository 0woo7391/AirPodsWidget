# AirPodsWidget UI v2 design brief

> 작업 시작 전 반드시 `UI_REDESIGN_SPEC.md`의 12~15장을 함께 읽는다. 최근 접기·복원
> 감사 결과, 정렬 기준, GitHub 레퍼런스 적용/비적용 매핑과 실제 Windows 검증 규칙은
> 그 문서에 기록한다. 이 brief만 읽고 완료를 판단하지 않는다.

## Direction

The widget is a quiet desktop control surface, not a stack of cards. The
product should feel precise, calm, and considered at a glance. The existing
BLE, media, audio, tray, and no-focus behavior remain product requirements;
the visual structure is allowed to change completely.

## Visual rules

- One outer shell. Battery and audio are aligned information rows, not nested
  rounded cards.
- The media area may use one raised surface because it is the most active
  interaction. When media is unavailable, that surface and its space collapse
  by default; flow mode may opt into a persistent empty player from Settings.
- Use a warm neutral palette: graphite, soft gray, ivory, and semantic green,
  yellow, orange, or red only for state. No default navy or decorative glow.
- Use one typographic family for the visual rhythm, with fixed-width numeric
  roles for battery, volume, and timeline values.
- Keep a consistent left and right content edge. Use 8/12/16/20 spacing, but
  reserve the larger values for boundaries between information groups.
- Controls have visible hit areas, outlined affordances, and hover/pressed/
  disabled states. Decorative borders must not compete with labels.

## Layouts

### Flow

Header -> aligned battery rows -> remaining-time value -> volume rail ->
three-slot output selector -> current media. The header contains the device
name, one connection state, and the collapse control; settings remain in the
tray menu. Output selection never sits inside the media player.

### Compact

The compact layout is a separate composition, not a scaled flow layout. It
keeps a battery summary, current output, volume trigger, and one-line media
controller in a short controller surface. The volume trigger opens an anchored
vertical rail; during a collapse the output-button row leaves before the shell
becomes too narrow.

### Minimized

The minimized state is a small capsule at the same window position. It retains
the most useful status and a volume trigger. Expanding it restores the active
layout without opening a second window or stealing focus.

## Motion map

| State change | Motion | Target |
| --- | --- | --- |
| Open/close | opacity + 0.98-to-1 scale + anchored origin | 190 ms |
| Flow/compact/minimized | one shared 400 ms shell morph and staged group reveal | 400 ms |
| Output change | one shared sliding indicator | 190 ms |
| Volume popover | anchored opacity + scale | 170 ms |
| Volume drag | handle, fill, and number share one value | direct while dragging |
| Battery availability | number reveal and bar interpolation | 180-300 ms |
| Media change | title/subtitle crossfade; fixed control geometry | 180 ms |
| Marquee | delayed, slow, linear movement | after 3 s |

Use OutCubic for entering feedback and InOutCubic for layout changes. Avoid
bounce, overshoot, continuous blinking, and animations that move unrelated
content. A live timeline is data, not a layout transition.

## Acceptance gates

- The three modes are visibly different in a screenshot.
- No card stack, unexplained blank area, clipped text, or drifting baseline.
- L/R/CASE labels, status marks, tracks, and percentages share fixed columns.
- Volume bar and thumb never animate on separate timelines.
- Compact and minimized volume controls open an anchored vertical slider whose
  full rail is the hit target, not only the painted track.
- No stale media title remains after the active session disappears.
- Dark and light themes remain readable at all supported opacity settings.
- Window remains non-activating and popups are suppressed while a game is
  foreground.
- Automated tests, QML runtime captures, and the Windows build pass before
  shipping.
