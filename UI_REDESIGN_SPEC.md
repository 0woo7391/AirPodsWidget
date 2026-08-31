# AirPodsWidget UI/UX 재설계 기준서

작성일: 2026-08-31  
대상: Windows x64 / AirPods Pro 3 데스크톱 위젯

이 문서는 이번 UI 개편의 단일 기준 문서다. 색상값을 바꾸는 것만으로는 완료로
간주하지 않는다. 구현 결과가 이 문서의 구조·타이포그래피·상태·모션·검증 기준을
만족해야 한다.

## 1. 제품 목적과 변하지 않는 범위

### 유지할 제품 목적

- AirPods Pro 3 좌우 유닛과 케이스 배터리 표시
- 배터리 값 옆 얇은 Progress Bar
- 좌우 착용 감지와 충전 상태 표시
- 현재 세션 사용시간과 오늘 누적 사용시간을 내부 상태로 유지
- 배터리 기반 예상 잔여시간을 `@h @@m` 형식으로 표시
- 현재 재생 중인 Windows 미디어의 제목·아티스트·앱 표시
- 긴 미디어 제목의 느린 marquee
- 이전 / 재생·일시정지 / 다음 / 재생 위치 제어
- 데스크톱 위젯과 트레이 팝업 동시 사용
- AirPods 연결 팝업과 저전력 팝업
- 저전력 시 포함 MP3 재생, 알림 볼륨 설정, 테스트 알림
- Borderless Window 게임 위에서 시각 팝업 차단
- 위젯이 게임이나 다른 창의 포커스를 가져가지 않음
- 위젯 위치 잠금, 항상 위 표시, 크기 조절, 배경 투명도, 다크/라이트 테마
- 설정에서 최대 3개의 출력장치 버튼 등록·삭제·장치 지정
- 페어링된 AirPods는 현재 연결 전에도 출력장치 버튼을 활성화

### 금지 범위

- 커널 드라이버, 커스텀 Bluetooth 드라이버, Test Mode, Secure Boot 변경
- Vanguard에 영향을 줄 수 있는 서비스·저수준 후킹·IOCTL·키보드/화면 후킹
- Low Audio Latency 목적의 무음 오디오 반복 재생
- 이어버드 일러스트, 이모티콘풍 아이콘, 과한 glow·bounce·glass 장식
- 실제 기능과 무관한 카드·배지·설정 항목 추가

## 2. 참고 자료와 적용 원칙

참고 자료는 React/CSS 코드를 QML에 그대로 복사하는 용도가 아니다. 각 자료의
시각·컴포넌트·모션 원칙을 QML과 Windows API에 맞춰 구현한다.

| 자료 | 확인한 원칙 | 이 프로젝트에 적용할 내용 |
|---|---|---|
| [Dimension / Refero](https://styles.refero.design/style/fbcf9cbb-7c6b-449d-862a-bce521a8ab1d) | `#0A0A0A` 캔버스, `#161616` 상승 표면, frosted glass, 1px hairline, 거의 무채색, medium weight | 카드마다 다른 표면 단계와 얇은 경계만 사용. 색상은 상태 정보에만 사용 |
| [Transitions.dev](https://transitions.dev/) | Card resize, number pop-in, icon swap, modal open/close, tabs sliding, text reveal | 상태 변화별로 지정된 전환만 사용하고 모든 요소를 동시에 튀기지 않음 |
| [shadcn/ui](https://ui.shadcn.com/) | 조합 가능한 primitives, 접근 가능한 기본 상태, 일관된 컴포넌트 | Slider, Switch, Segmented Control, Progress, Dialog 상태를 공통 규칙으로 구성 |
| [UI Skills](https://www.ui-skills.com/) | tabular numbers, nested radius, pressed feedback, 44px target, layout shift 방지 | 숫자 열 정렬, 중첩 반경 일치, 버튼 상태, 설정 터치/클릭 영역을 일관화 |
| [Coss UI](https://coss.com/ui) | Progress, Separator, Empty, Slider, Switch, Segmented Control, Tooltip | 배터리·볼륨·출력장치·미디어 없음 상태에 의미가 맞는 컴포넌트 사용 |
| [ReUI](https://reui.io/components) | 고립된 카드가 아니라 실제 제품 화면에서 조합되는 구성 | 배터리·오디오·미디어를 같은 모양의 카드로 반복하지 않고 정보 계층으로 구분 |
| [Emil Kowalski](https://emilkowal.ski/ui/you-dont-need-animations) | 자주 쓰는 조작은 즉시 반응, 애니메이션은 목적이 있을 때만, 일반 UI는 300ms 이하 | 볼륨·재생·출력 전환은 즉시 반응. 상태 전환만 120~240ms로 제한 |
| [Beautiful UI](https://www.beautifului.dev/) | 상태·메타데이터를 compact row/chip으로 표시 | 연결 상태, 앱 이름, 시간, 장치 상태를 큰 빈 카드 없이 작은 정보 행으로 구성 |

`Dimension 45% + Air 35% + Linear 20%` 같은 임의 비율은 사용하지 않는다. 이것은
자료의 수치가 아니며 구현 완료를 판단하는 기준도 아니다.

## 3. 새 시각 시스템

### 표면 계층

현재처럼 같은 색의 둥근 사각형을 위아래로 반복하지 않는다.

1. **Window shell**: 윈도우 가장자리는 완전 투명. 내부 shell만 반투명.
2. **Canvas**: Dimension의 `#0A0A0A` / 라이트 테마의 밝은 neutral canvas.
3. **Raised surface**: `#161616` 계열. 배터리와 오디오의 정보 그룹에 사용.
4. **Frosted surface**: `rgba(#D4D4D4, 0.10)` 계열. 떠 있는 미디어와 선택 상태에 사용.
5. **Hairline**: 1px의 낮은 대비 경계. 무거운 그림자와 이중 테두리 금지.

투명도 설정은 텍스트·아이콘·진행 바가 아니라 배경 표면에만 적용한다. 실제
Liquid/Frosted 효과는 단순 alpha나 gradient가 아니다. Windows 11은 DWM backdrop
material을 사용하고, 지원하지 않는 Windows 10은 읽을 수 있는 neutral alpha 표면으로
fallback한다. 전체 `Window.opacity`로 글자까지 흐리게 만들지 않는다.

### 색상

- 기본 색상은 거의 무채색으로 유지한다.
- 다크 본문: `#EDEDED`, 보조: `#C2C2C2`, 메타: `#686868`.
- 라이트 본문: `#161616`, 보조: `#686868`.
- 배터리 상태만 semantic green / yellow / orange / red를 사용한다.
- 볼륨과 재생 위치 바는 파란색을 쓰지 않는 모노톤이다.
- 재생된 구간은 밝은 색, 남은 구간은 어두운/중간 색으로 구분한다.
- 선택된 출력 버튼도 기본은 neutral outline이며, 파란색 강조를 기본 상태로 쓰지 않는다.

### 반경과 간격

- shell: 24px
- 일반 정보 그룹: 14~16px
- control group: 10~12px
- pill button: full pill
- 내부 간격: 8 / 12 / 16 / 20px만 사용
- shell 내부 좌우 padding: 20px 전후
- 주요 섹션 간격: 12px 전후
- 한 행 내부 간격: 8px 전후
- 빈 상태에서 보이지 않는 콘텐츠의 공간을 남기지 않는다.

공간은 충분히 주되 빈 박스가 떠 보이지 않게 한다. 특히 헤더와 배터리,
배터리와 오디오, 오디오와 미디어 사이에 임의의 큰 공백을 두지 않는다.

## 4. 타이포그래피

Dimension의 DM Sans 500 원칙(중간 굵기와 차분한 수치 리듬)을 Windows-native
`Segoe UI Variable Display`로 적용하되 한국어 글리프 안정성을 유지한다.

- 영문 제목·숫자: Segoe UI Variable Display medium
- 한국어 fallback: 번들 Pretendard
- 제목: 18~19px, medium. 과한 bold 금지
- 연결 상태: 13~14px, dot과 세로 중앙 정렬
- 배터리 값: 13~14px medium. 제목보다 튀지 않음
- 배터리 라벨: 12px medium
- 예상 시간: 12~13px, 보조 정보
- 미디어 제목: 15~16px medium
- 미디어 앱/아티스트: 12~13px
- 메타데이터: 11~12px
- 숫자는 tabular 숫자 폭을 사용해 열이 흔들리지 않음
- 제목과 subtitle 사이에는 8~10px의 명확한 간격

## 5. 위젯 레이아웃

### 헤더

```text
AirPods Pro 3                         ● 연결됨   ⋯
```

- 디바이스 이름은 좌측 기준선에 고정
- 연결 dot와 텍스트는 하나의 status group
- `양쪽 착용 중` 같은 중복 상태 문구는 표시하지 않음
- 설정 메뉴는 헤더 우측에 유지하되 과하게 눈에 띄지 않게 함

### 배터리

```text
L       ●       ━━━━━━━━━━━━━      70%
R       ●       ━━━━━━━━━━━━━      70%
                         5h 35m
CASE            ━━━━━━━━━━━━━       —
```

- L/R/CASE 라벨 열, 상태 표시 열, 그래프 열, 값 열을 고정
- 그래프 시작점과 끝점을 모든 행에서 동일하게 맞춤
- 착용 중: 작은 초록 dot
- 충전 중: dot 대신 테두리 없는 노란 번개 아이콘
- 연결됐지만 아직 배터리 값이 없으면 `—` 유지
- 예상 시간은 별도 박스 없이 L/R과 CASE 사이의 보조 정보

### 오디오

```text
             🔊    ━━━━━━━━━━━━━    48%

             [ AirPods ] [ 스피커 ] [ 헤드폰 ]
```

- 볼륨 영역과 출력 선택 영역은 분리된 두 control surface
- 볼륨 아이콘·바·수치는 상하좌우 기준선에 모두 중앙 정렬
- 출력 버튼은 최대 3개 슬롯을 고정해 선택 시 layout shift가 없음
- AirPods는 paired 상태면 활성화, unpaired면 disabled
- 선택 indicator는 [Tabs Sliding] 방식으로 이동

### 미디어

- 설정에서 플레이어 표시 OFF면 플레이어 전체를 숨김
- 현재 재생 또는 현재 일시정지 세션만 표시
- 오래된 Chrome 세션을 되살리지 않음
- 제목 / 아티스트·앱 / 시간 / timeline / transport controls 순서 유지
- 미디어가 없으면 카드와 높이를 함께 제거
- 긴 제목은 재생 중에만 느린 marquee
- timeline은 모노톤이며 지난 구간이 밝음

## 6. 모션 규칙

### 고정 매핑

| 상태 변화 | transition | 적용 규칙 |
|---|---|---|
| 출력장치 선택 | [Tabs Sliding](https://transitions.dev/detail.html?t=tabs-sliding) | 버튼 슬롯은 고정. active indicator만 같은 축으로 이동 |
| AirPods 배터리 값 등장 | [Number Pop-in](https://transitions.dev/detail.html?t=number-pop-in) | `— → 70%` 숫자에만 적용. 진행 바는 같은 보간값으로 함께 이동 |
| 위젯 최소화/복원 | [Icon Swap](https://transitions.dev/detail.html?t=icon-swap) + [Modal Open/Close](https://transitions.dev/detail.html?t=modal-open-close) | 동일한 anchor 위치에서 icon, opacity, size를 함께 변경 |
| 설정 토글 | [Toggle](https://transitions.dev/detail.html?t=toggle) | thumb 이동만 사용. 과한 double bounce 금지 |
| 미디어 표시/숨김 | Card resize / panel reveal | 빈 공간을 남기지 않고 shell 높이도 함께 변경 |

### 성능과 반응

- 볼륨 drag, 재생/정지, 다음/이전, 출력 전환은 입력과 같은 프레임에서 상태를 표시
- 외부 값 갱신 시 진행 바와 thumb는 동일한 target/동일한 easing 사용
- progress width에만 즉시 적용하고 thumb에만 animation을 주는 방식 금지
- 일반 전환 120~240ms, 300ms 초과 금지
- 반복 노출되는 위젯에 shimmer, 지속적인 glow, 장식성 bounce 금지
- 게임 중에는 팝업 motion도 실행하지 않음
- reduced-motion 설정이 있으면 opacity/transform 전환을 즉시 상태로 축소

## 7. 기능 상태별 UI

- 연결됨: status dot + `연결됨`, 배터리 값은 들어오는 즉시 표시
- 검색 중: 상태만 표시하고 반복 연결 팝업을 만들지 않음
- 일시적 BLE 광고 유실: 마지막 배터리 값은 유지하되 착용 상태는 stale이면 해제
- 안정적으로 계속 연결된 상태에서는 연결 팝업을 반복하지 않음
- 케이스 충전: CASE 옆에 노란 번개
- 저전력: 배터리 색상과 설정된 팝업/사운드 정책만 사용
- 게임 foreground: 시각 팝업 숨김, 위젯은 뒤에 유지, 오디오/데이터 갱신은 계속
- 미디어 없음: stale 제목을 보여주지 않고 compact shell로 축소
- AirPods 출력 버튼: paired지만 disconnected면 disabled가 아닌 사용 가능한 shortcut

## 8. 코드 작업 대상

### 새로 재설계할 UI 층

- `src/ui/components/UiTheme.qml`: 색상뿐 아니라 spacing, type, surface, motion 역할
- `src/ui/components/WidgetWindow.qml`: shell, anchor, section rhythm, compact height
- `src/ui/components/BatteryRow.qml`: 고정 grid와 값 등장 모션
- `src/ui/components/AppleSlider.qml`: progress와 thumb의 동일 좌표·동일 애니메이션
- `src/ui/components/AudioOutputSection.qml`: volume/control group과 output segmented group
- `src/ui/components/OutputDeviceButton.qml`: selected/available/disabled/pressed 상태
- `src/ui/components/MediaSection.qml`: title hierarchy, timeline, no-media collapse
- `src/ui/components/SettingsWindow.qml`: 같은 type scale·surface 계층·여백
- `src/ui/components/TrayPopup.qml`: 위젯과 동일한 상태 표현, compact density
- `src/main.py`: 번들 Pretendard 등록과 Windows-native 영문 display fallback
- `src/services/windows_material.py`: Windows backdrop material과 transparent fallback

### 기능 로직 재확인 대상

- `src/services/ble_service.py`, `airpods_protocol.py`, `state_manager.py`: 광고 병합,
  유실, 착용 해제 지연, 연결 팝업 중복
- `src/services/media_service.py`: 현재 재생 세션 선택, Chrome stale state, timeline polling
- `src/controller.py`: 상태 신호, output shortcut, game suppression, widget toggle
- `src/services/audio_output.py`: paired endpoint와 active endpoint 구분

## 9. 완료 조건

### 정적·자동 검증

- Python unit tests 전체 통과
- Python compile 통과
- QML delimiter/structure validation 통과
- QML runtime load 통과
- 배터리 grid의 좌표가 L/R/CASE에서 동일
- volume progress와 thumb가 동일 target/easing을 사용
- top-level window opacity가 1이고 material layer만 opacity를 사용
- `WindowDoesNotAcceptFocus`와 게임 중 bottom stacking 유지

### 시각 검증

- 다크 테마 캡처: 기존 화면과 구조적으로 다름
- 라이트 테마 캡처: 글자와 컨트롤의 contrast가 유지됨
- 미디어 있음 캡처: 제목·subtitle·timeline·controls가 분리됨
- 미디어 없음 캡처: 빈 플레이어 공간이 없음
- 설정창 캡처: 좌우 padding과 section hierarchy가 읽힘
- 출력장치 선택: active indicator가 미끄러지고 버튼 슬롯이 이동하지 않음
- 배터리 등장: 숫자만 pop-in하며 카드 전체가 튀지 않음
- 위젯 최소화/복원: 동일한 위치에서 icon과 shell이 함께 전환

### Windows 수동 검증

- AirPods Pro 3 실제 BLE 값·충전·착용 상태
- Spotify/Chrome YouTube 실제 제목·아티스트·앱·재생 위치
- 이전/재생·일시정지/다음/seek
- 볼륨 외부 변경과 위젯 drag의 즉시 반영
- AirPods paired/disconnected 상태에서 출력 버튼 전환
- 트레이 popup toggle과 widget 동시 사용
- Borderless League of Legends foreground에서 팝업·포커스·최소화 여부
- Vanguard 오류, 서비스 설치, 드라이버 설치, Test Mode 변경 여부

## 10. 구현 후 기록 규칙

완료 보고에는 다음을 반드시 기록한다.

- 이 문서의 항목별 구현 상태
- 실제 변경 파일
- 다크/라이트/미디어 없음 캡처 경로
- 통과한 자동 테스트 수
- 실제 Windows에서 확인하지 못한 항목
- EXE/MSIX 버전과 빌드 결과

“색상 토큰 변경”, “빌드 성공”, “QML 로딩 성공”만으로 UI 개편 완료라고 쓰지 않는다.

## 11. 이번 구현 검증 기록

검증일: 2026-08-31

### 자동 검증 완료

- Python unit tests: 28 passed
- Python/QML 프로젝트 정적 검증: passed
- 이 문서와 구현 anchor 대조(`tools/ui_spec_check.py`): passed
- QML runtime load: passed
- 다크/라이트 위젯 캡처: `.final-runtime-check-v7/widget-dark.png`,
  `.final-runtime-check-v7/widget-light.png`
- 미디어 없음 다크/라이트 캡처: `.final-runtime-check-v7/widget-no-media-dark.png`,
  `.final-runtime-check-v7/widget-no-media-light.png`
- 설정창 다크/라이트 캡처: `.final-runtime-check-v7/settings-dark.png`,
  `.final-runtime-check-v7/settings-light.png`
- 출력장치 fixed slot 및 shared sliding indicator: passed in demo runtime check
- 새 EXE demo startup 8초 유지: passed
- AirPodsWidget 프로세스 테스트 후 잔여 프로세스: 0
- MSIX manifest: `0.1.7.0`, 이 문서와 BUILD_REPORT 포함 확인

### 실제 장치에서 남은 검증

- 연결된 AirPods Pro 3의 실시간 BLE 수신·충전·착용 상태
- Chrome YouTube/Spotify의 실제 미디어 세션과 seek/transport 동기화
- 실제 Windows 배경에서 DWM Acrylic 투명도와 contrast
- Borderless League of Legends와 Riot Vanguard 공존

위 항목은 데모 캡처나 정적 검증으로 대체하지 않고, 연결된 AirPods와 설치된 MSIX로
수동 확인해야 한다.
