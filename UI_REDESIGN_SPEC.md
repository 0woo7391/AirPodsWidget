# AirPodsWidget UI/UX 재설계 기준서

작성일: 2026-08-31  
대상: Windows x64 / AirPods Pro 3 데스크톱 위젯

이 문서는 제품 동작과 안전성의 기준 문서다. 시각 구조와 모션의 최신 기준은
`UI_V2_DESIGN_BRIEF.md`를 우선한다. 색상값만 바꾸는 것으로는 완료로 간주하지
않으며, 구현 결과는 두 문서의 검증 기준을 만족해야 한다.

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
| [Linear UI refresh](https://linear.app/now/behind-the-latest-design-refresh) | 정보 우선순위, 적은 테두리, 따뜻한 중성 팔레트, 구조가 느껴지되 보이지 않는 구분 | 배터리·오디오를 정렬된 정보 행으로 만들고 미디어만 활동 영역으로 강조 |
| [Raycast Compact Mode](https://www.raycast.com/blog/a-fresh-look-and-feel) | 핵심 동작에 집중하는 컴팩트 레이아웃과 명확한 액션 바 | 흐름형과 다른 컴팩트 구성, 최소화 상태의 정보량 결정 |
| [FluentFlyout](https://fluentflyout.com/) | Windows 미디어/볼륨 flyout, 확장·축소, 게임 중 비노출 | Windows 동작 모델만 참고하고 카드·효과는 그대로 복사하지 않음 |
| [Transitions.dev](https://transitions.dev/) | Card resize, number pop-in, icon swap, modal open/close, tabs sliding, text reveal | 상태 변화별로 지정된 전환만 사용하고 모든 요소를 동시에 튀기지 않음 |
| [shadcn/ui](https://ui.shadcn.com/) | 조합 가능한 primitives, 접근 가능한 기본 상태, 일관된 컴포넌트 | Slider, Switch, Segmented Control, Progress, Dialog 상태를 공통 규칙으로 구성 |
| [UI Skills](https://www.ui-skills.com/) | tabular numbers, nested radius, pressed feedback, 44px target, layout shift 방지 | 숫자 열 정렬, 중첩 반경 일치, 버튼 상태, 설정 터치/클릭 영역을 일관화 |
| [Coss UI](https://coss.com/ui) | Progress, Separator, Empty, Slider, Switch, Segmented Control, Tooltip | 배터리·볼륨·출력장치·미디어 없음 상태에 의미가 맞는 컴포넌트 사용 |
| [ReUI](https://reui.io/components) | 고립된 카드가 아니라 실제 제품 화면에서 조합되는 구성 | 배터리·오디오·미디어를 같은 모양의 카드로 반복하지 않고 정보 계층으로 구분 |
| [Emil Kowalski](https://emilkowal.ski/ui/you-dont-need-animations) | 자주 쓰는 조작은 즉시 반응, 애니메이션은 목적이 있을 때만, 일반 UI는 300ms 이하 | 볼륨·재생·출력 전환은 즉시 반응. 상태 전환만 120~240ms로 제한 |
| [Beautiful UI](https://www.beautifului.dev/) | 상태·메타데이터를 compact row/chip으로 표시 | 연결 상태, 앱 이름, 시간, 장치 상태를 큰 빈 카드 없이 작은 정보 행으로 구성 |

이전 레퍼런스의 임의 비율은 사용하지 않는다. 레퍼런스는 역할별 원칙을 추출하는
자료이며 구현 완료를 판단하는 수치가 아니다.

## 3. 새 시각 시스템

### 표면 계층

현재처럼 같은 색의 둥근 사각형을 위아래로 반복하지 않는다.

1. **Window shell**: 윈도우 가장자리는 완전 투명. 내부 shell만 반투명.
2. **Canvas**: 다크 graphite / 라이트 warm-neutral canvas.
3. **Information surface**: `#161616` 계열. 배터리와 오디오의 정보 그룹에 사용.
4. **Active surface**: `rgba(#D4D4D4, 0.10)` 계열. 떠 있는 미디어와 선택 상태에 사용.
5. **Hairline**: 1px의 낮은 대비 경계. 무거운 그림자와 이중 테두리 금지.

투명도 설정은 텍스트·아이콘·진행 바가 아니라 배경 표면에만 적용한다. 실제
Windows backdrop은 단순 alpha나 gradient만으로 표현하지 않는다. Windows 11은 DWM
backdrop material을 사용하고, 지원하지 않는 Windows 10은 읽을 수 있는 neutral alpha
표면으로 fallback한다. 전체 `Window.opacity`로 글자까지 흐리게 만들지 않는다.

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

중간 굵기와 차분한 수치 리듬을 Windows-native `Segoe UI Variable Display`와
번들 Pretendard로 적용하되 한국어 글리프 안정성을 유지한다.

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
AirPods Pro 3                         ● 연결됨   ⌄
```

- 디바이스 이름은 좌측 기준선에 고정
- 연결 dot와 텍스트는 하나의 status group
- `양쪽 착용 중` 같은 중복 상태 문구는 표시하지 않음
- 헤더 우측에는 접기/복원 버튼만 두고, 접기 전후 화면 좌표를 유지함
- 설정은 위젯 헤더에 넣지 않고 시스템 트레이 메뉴에서만 접근함

### 배터리

```text
L       ●       ━━━━━━━━━━━━━      70
R       ●       ━━━━━━━━━━━━━      70
                         5h 35m
CASE            ━━━━━━━━━━━━━       —
```

- L/R/CASE 라벨 열, 상태 표시 열, 그래프 열, 값 열을 고정
- 그래프 시작점과 끝점을 모든 행에서 동일하게 맞춤
- 착용 중: 작은 초록 dot
- 충전 중: 같은 상태 슬롯의 작고 테두리 없는 노란 벡터 번개. 이모지·배터리 외곽선은 사용하지 않음
- 연결됐지만 아직 배터리 값이 없으면 `—` 유지
- 예상 시간은 별도 박스 없이 L/R과 CASE 사이의 보조 정보

### 오디오

```text
             [volume]    ━━━━━━━━━━━━━    48

             [ AirPods ] [ 스피커 ] [ 헤드폰 ]
```

- 볼륨 영역과 출력 선택 영역은 분리된 두 control surface
- 볼륨 아이콘·바·수치는 상하좌우 기준선에 모두 중앙 정렬
- 출력 버튼은 최대 3개 슬롯을 고정해 선택 시 layout shift가 없음
- AirPods는 paired 상태면 활성화되고 클릭 시 Windows A2DP 재연결을 요청하며, unpaired면 disabled
- 선택 indicator는 [Tabs Sliding] 방식으로 이동

### 미디어

- 설정에서 플레이어 표시 OFF면 플레이어 전체를 숨김
- 일반 모드에서 `미디어 없을 때도 표시`를 켜면 세션이 없어도 빈 플레이어
  surface를 유지한다. 이 옵션은 compact와 트레이 팝업에는 적용하지 않는다.
- 현재 재생 또는 현재 일시정지 세션만 표시
- 오래된 Chrome 세션을 되살리지 않음
- 제목 / 아티스트·앱 / 시간 / timeline / transport controls 순서 유지
- 미디어가 없으면 기본적으로 카드와 높이를 함께 제거하며, 위의 상시 표시
  옵션이 켜진 경우에만 빈 상태 surface와 고정 높이를 유지한다.
- 긴 제목은 재생 중에만 느린 marquee
- timeline은 모노톤이며 지난 구간이 밝음

## 6. 모션 규칙

### 고정 매핑

| 상태 변화 | transition | 적용 규칙 |
|---|---|---|
| 출력장치 선택 | [Tabs Sliding](https://transitions.dev/detail.html?t=tabs-sliding) | 버튼 슬롯은 고정. active indicator만 같은 축으로 이동 |
| AirPods 배터리 값 등장 | [Number Pop-in](https://transitions.dev/detail.html?t=number-pop-in) | `— → 70` 숫자에만 적용. 진행 바는 같은 보간값으로 함께 이동 |
| 위젯 최소화/복원 | [Dropdown Menu Morph](https://transitions.dev/detail.html?t=dropdown-menu-morph) + [Modal Open/Close](https://transitions.dev/detail.html?t=modal-open-close) + [Icon Swap](https://transitions.dev/detail.html?t=icon-swap) | 하나의 토글 앵커를 유지하고, 화면 여유 방향으로 surface·radius·아이콘을 함께 morph |
| 설정 토글 | [Toggle](https://transitions.dev/detail.html?t=toggle) | thumb 이동만 사용. 과한 double bounce 금지 |
| 미디어 표시/숨김 | Card resize / panel reveal | 빈 공간을 남기지 않고 shell 높이도 함께 변경 |

### 성능과 반응

- 볼륨 drag, 재생/정지, 다음/이전, 출력 전환은 입력과 같은 프레임에서 상태를 표시
- 외부 값 갱신 시 진행 바와 thumb는 동일한 target/동일한 easing 사용
- progress width에만 즉시 적용하고 thumb에만 animation을 주는 방식 금지
- 일반 전환 120~240ms. 접기 morph는 중간 프레임을 포함해 열림 400ms·닫힘 400ms를 사용
- 최소화/복원은 하나의 `morphProgress`만 애니메이션하고 surface·radius·content·icon은
  해당 progress에서 파생함. 각 요소에 별도 `Behavior`를 중첩하지 않음
- 접기와 복원의 폭·높이는 하나의 완만한 구간에서 함께 이동함. 콘텐츠 레이어를 통째로
  임계값에서 교체하지 않고, 고정된 슬롯 안에서 header → battery → audio → media 순서로
  짧은 opacity/transform reveal을 실행함
- 펼칠 때는 쉘에 공간이 생긴 뒤 다음 그룹을 보여주고, 접을 때는 출력 버튼 행을 먼저
  숨긴 뒤 볼륨 행과 배터리 요약을 순서대로 정리해 쉘이 해당 그룹을 자르지 않게 함.
  축소 요약은 확장 콘텐츠와 같은 좌표에서 겹치지 않도록 별도 handoff 구간을 사용함
- 반복 노출되는 위젯에 shimmer, 지속적인 glow, 장식성 bounce 금지
- 게임 중에는 팝업 motion도 실행하지 않음
- reduced-motion 설정이 있으면 opacity/transform 전환을 즉시 상태로 축소
- 컴팩트/최소화 볼륨 팝오버는 클릭한 트리거를 기준으로 독립 오버레이로 열리고,
  좁은 painted track 대신 전체 세로 rail을 hit target으로 사용함. 부모 위젯 크기·접기
  버튼 위치를 변경하지 않으며, 작업 영역 하단에 닿으면 팝오버 자체만 위로 전환
- 접기/복원 중 native window shape는 geometry/radius 변화마다 같은 event-loop turn에
  coalesce해 갱신하고, 이전 Region이 새 창 크기를 잘라내지 않게 함

## 7. 기능 상태별 UI

- 연결됨: status dot + `연결됨`, 배터리 값은 들어오는 즉시 표시
- 검색 중: 상태만 표시하고 반복 연결 팝업을 만들지 않음
- 일시적 BLE 광고 유실: 마지막 배터리 값은 유지하되 착용 상태는 stale이면 해제하고,
  해당 상태만으로 자동 일시정지를 실행하지 않음
- 안정적으로 계속 연결된 상태에서는 연결 팝업을 반복하지 않음
- 케이스 충전: CASE 상태 슬롯에 같은 작고 테두리 없는 노란 벡터 번개
- 저전력: 배터리 색상과 설정된 팝업/사운드 정책만 사용
- 게임 foreground: 시각 팝업 숨김, 위젯은 뒤에 유지, 오디오/데이터 갱신은 계속
- 미디어 없음: stale 제목을 보여주지 않고 compact shell로 축소
- AirPods 출력 버튼: paired지만 disconnected면 disabled가 아닌 재연결 가능한 shortcut

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
- 위젯 최소화/복원: 동일한 위치에서 icon과 shell이 함께 전환하며 16ms 간격 중간
  프레임에서 진행 방향 역전·큰 빈 surface·컨트롤 겹침이 없음

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
- MSIX manifest: `0.1.8.0`, 이 문서와 BUILD_REPORT 포함 확인

### 실제 장치에서 남은 검증

- 연결된 AirPods Pro 3의 실시간 BLE 수신·충전·착용 상태
- Chrome YouTube/Spotify의 실제 미디어 세션과 seek/transport 동기화
- 실제 Windows 배경에서 DWM Acrylic 투명도와 contrast
- Borderless League of Legends와 Riot Vanguard 공존

위 항목은 데모 캡처나 정적 검증으로 대체하지 않고, 연결된 AirPods와 설치된 MSIX로
수동 확인해야 한다.

## 12. 2026-09-02 접기·복원 전환 감사 결과

이 절은 접기/복원 관련 최근 점검 결과를 기록한다. 아래의 `부분 구현` 상태를
`완료`로 표현하지 않는다. 이 절과 9장의 시각·Windows 수동 검증을 모두 통과하기
전에는 접기/복원 수정이 완료된 것으로 보고하지 않는다.

### 현재 확인된 사실

- `0.1.25.0` EXE/MSIX 산출물은 존재하며, 현재 실행 중인 프로세스는
  프로젝트 루트의 `AirPodsWidget.exe`이다.
- `src/ui/components/WidgetWindow.qml`에는 토글의 전역 중심 좌표를 저장하고
  창의 `x/y`를 폭·높이에 맞춰 재계산하는 앵커 로직이 있다.
- 오프스크린 QML runtime check에서는 샘플 프레임의 토글 중심 drift가 0으로
  측정되고, 자동 검증이 통과했다.
- 위 결과는 실제 Windows 데스크톱 합성 과정에서의 좌우 스냅, 둥근 Region 교체,
  중간 프레임 테두리 깨짐, 체감상 좌우 이동까지 검증하지 않는다.
- 따라서 현재 상태의 판정은 **부분 구현·오프스크린 검증 통과, 실제 Windows 시각
  검증 미완료**이다. 사용자가 실제 화면에서 같은 문제를 보면 수정 완료가 아니다.

### 의심 원인과 확인할 구조

- native Window의 `x/y`, `width/height`, 둥근 window shape가 서로 다른 Qt event-loop
  시점에 갱신될 수 있다. `onWidthChanged`, `onHeightChanged`,
  `onMorphProgressChanged`, shape update timer를 하나의 시각 프레임으로 묶었는지
  실제 캡처로 확인한다.
- 창의 크기가 변하는 동안 Windows가 새 크기와 이전 원점을 섞어 그리는 중간 프레임이
  없는지 확인한다. 토글 중심 좌표만 볼 것이 아니라 창의 좌우/상하 경계와 shell
  Region도 함께 기록한다.
- `morphExpandLeft`/`morphExpandUp`에 따라 flow/compact content margin이 바뀌면서
  내부 요소가 독립적으로 좌우 이동하지 않는지 확인한다. 토글 고정과 콘텐츠 기준선
  고정은 별도 검증 항목이다.
- 오프스크린 테스트의 통과를 실제 화면 검증으로 대체하지 않는다. 16ms 중간 프레임
  캡처와 실제 바탕화면 좌표가 필요하다.

### 접기·복원 완료 판정표

- [ ] 펼친 상태에서 토글 중심의 실제 화면 좌표를 기준점으로 기록
- [ ] 접기와 복원 양방향에서 토글 중심 drift가 허용 오차 안에 있음
- [ ] 확장 방향이 같은 위치에서 매번 동일하고, 임의로 반대쪽에서 열리지 않음
- [ ] 창 좌우/상하 경계가 한 프레임씩 튀거나 반대로 움직이지 않음
- [ ] shell의 Region/테두리가 새 창 크기보다 늦게 남아 잘라내지 않음
- [ ] header, battery, audio, media가 정해진 순서로 자연스럽게 나타나며 제목만
      먼저 남는 프레임이 없음
- [ ] compact/minimized volume popover가 토글을 가리거나 부모 창을 재배치하지 않음
- [ ] 바탕화면의 서로 다른 좌표(좌상·우상·좌하·우하)에서 반복해도 동일한 기준으로
      동작함
- [ ] 다크/라이트 테마, 미디어 있음/없음, compact/flow 상태에서 겹침·클리핑 없음
- [ ] 위 항목을 실제 Windows 화면 캡처로 확인한 뒤에만 빌드 보고서에 완료로 기록

## 13. 2026-09-02 UI 정렬 감사 기준

배터리·볼륨·플레이어의 각자 내부 정렬만 맞추는 것으로 끝내지 않는다. 하나의
공통 기준선과 숫자 열을 먼저 정한 뒤 모든 모드에 적용한다.

- shell 내부 좌우 padding, 정보 그룹 간 간격, 한 행 내부 간격을 각각 별도 토큰으로
  관리한다. 임의의 `anchors.leftMargin`/`rightMargin`을 컴포넌트마다 새로 만들지
  않는다.
- L/R/CASE의 label, 상태 슬롯, bar 시작점·끝점, 숫자 열을 고정한다. 숫자는 같은
  폭과 같은 정렬을 사용하며, 값이 `—`로 바뀌어도 열이 움직이지 않는다.
- 볼륨 아이콘·progress·thumb·숫자는 같은 행의 세로 중심선에 둔다. progress와
  thumb는 하나의 값·하나의 easing을 사용한다.
- 미디어 제목·subtitle·시간·timeline·transport는 서로 다른 역할의 기준선을
  사용한다. 제목이 바뀌어도 subtitle과 timeline이 위아래로 밀리지 않게 고정한다.
- 배터리 값, 볼륨 값, 미디어 시간은 같은 숫자 스타일 토큰을 검토하되, 정보의
  중요도가 다른 값을 제목보다 크게 만들어 시선이 튀지 않게 한다.
- flow/compact/minimized는 같은 UI를 단순 축소하지 않는다. 각 모드에 별도 grid를
  주되, 공통 토큰과 상태 슬롯을 공유한다.
- 정렬 검증은 스크린샷 한 장으로 판단하지 않는다. 각 컴포넌트의 global rect와
  baseline/centerline을 캡처하고, 0/50/100 값·미디어 없음·라이트/다크를 포함한다.

## 14. 작업 문서·검증 운영 규칙

이 문서가 작업의 기준점이다. 대화의 요약이나 모델의 기억을 기준으로 요구사항을
재구성하지 않는다.

1. 코드 수정 전에 이 문서와 `UI_V2_DESIGN_BRIEF.md`를 먼저 읽는다.
2. 새 요구사항은 구현 전에 이 문서에 `요구사항`, `대상 파일`, `검증 방법`,
   `완료 조건`으로 기록한다.
3. 구현 중에는 항목별 상태를 `대기/구현/자동 검증/실제 Windows 검증/미완료`로
   구분한다.
4. 정적 검사·QML 로드·빌드 성공은 시각적 완료의 증거로 사용하지 않는다.
5. 실제 캡처를 하지 못한 항목은 반드시 `미검증`으로 남긴다.
6. 완료 보고에는 변경 파일, 산출물 버전, 테스트 결과, 캡처 경로, 미검증 항목을
   함께 기록한다.
7. 외부 레퍼런스는 원문을 확인한 뒤 출처 URL, 추출한 원칙, 프로젝트 적용 위치,
   적용하지 않을 항목을 이 문서에 기록한다. 코드를 그대로 복사했다는 식으로
   보고하지 않는다.

### 현재 작업 상태

| 항목 | 상태 | 비고 |
|---|---|---|
| 토글 앵커 로직 | 부분 구현 | 오프스크린 좌표 검증만 통과 |
| 실제 Windows 접기/복원 시각 검증 | 미완료 | 중간 프레임·Region·다중 좌표 캡처 필요 |
| 배터리·볼륨·플레이어 공통 정렬 감사 | 구현 일부·정밀 감사 미완료 | 공통 slot과 offscreen 상태 검사는 반영했으나 실제 global baseline 측정 필요 |
| GitHub 레퍼런스 7종 원문 분석 | 기록 완료 | 아래 15장에 출처·적용·비적용 매핑 기록 |

## 15. 2026-09-02 GitHub 레퍼런스 검토 기록

링크는 작업 지시문이 아니라 참고 자료다. 원문에서 확인한 원칙만 추출하고,
React/CSS/GSAP/HTML 코드를 QML에 그대로 복사하지 않는다. 각 자료의 적용 여부와
적용 위치를 아래에 고정해 둔다.

### 15.1 저장소별 판정

| 저장소 | 원문에서 확인한 성격 | 이 프로젝트에 가져올 것 | 적용 위치 | 가져오지 않을 것 |
|---|---|---|---|---|
| [zzzzshawn/matrix](https://github.com/zzzzshawn/matrix) | Next.js 기반 dotmatrix 로더 컴포넌트와 registry/manual copy 경로를 제공하는 로딩 라이브러리 | 로딩 상태를 별도 상태로 설계한다는 관점만 참고 | 연결 검색 중/재연결 중 상태 검토 | 기본 UI에 dotmatrix 장식, Next.js/shadcn 의존성, 로더 모양 자체 |
| [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 제품 유형에 따라 디자인 시스템·스타일·색상·폰트·효과·반패턴·UX 검수표를 조합하는 설계 지식 저장소 | 한 팔레트, 한 타입 체계, 명시적 anti-pattern, 텍스트 overflow, 대비, reduced motion, 빠른 상호작용의 최종 상태 보장 | `UiTheme.qml`, 각 모드의 grid, 상태/접근성 검수 | 79개 스타일·192개 팔레트를 임의로 섞기, 웹 전용 CSS/폰트 import, generic glass/card preset |
| [taste-skill](https://github.com/Leonxlnx/taste-skill) | 기존 프로젝트는 먼저 scan → diagnose → fix하고, brief와 레퍼런스를 읽은 뒤 variance/motion/density를 결정하도록 하는 anti-slop skill | 구현보다 먼저 현재 UI의 반복 카드, 정렬, 타입, 간격, 상태 누락을 목록화한다. `redesign-skill`의 숫자 tabular, baseline, layout-before-effects 원칙을 채택한다. `minimalist-skill`의 warm monochrome·무거운 그림자/gradient 억제를 참고한다. | 이 문서의 작업 순서, `UiTheme.qml`, `WidgetWindow.qml`, 배터리/오디오/미디어 구조 | 웹 랜딩페이지용 비대칭 hero, bento, scroll/parallax, 임의 premium font 교체, 과한 spring/cinematic 효과 |
| [impeccable](https://github.com/pbakaus/impeccable) | `init`, `shape`, `critique`, `audit`, `typeset`, `layout`, `animate`, `polish` 등으로 설계·검수 단계를 분리하고, detector와 live iteration을 제공 | `shape → layout → typeset → animate → audit → polish` 순서와 “승인 전에는 지적”하는 리뷰 태도를 문서 검수 흐름으로 사용한다. 카드 중첩, bounce, 순수 검정, 과한 기본 폰트/그림자를 반패턴으로 유지한다. | 이 문서의 완료 조건, 변경 기록, 시각 QA 체크리스트 | QML에 Impeccable CLI/hook을 필수 런타임 의존성으로 넣기, 브라우저 detector 통과를 Windows 화면 검증으로 간주하기 |
| [hyperframes](https://github.com/heygen-com/hyperframes) | HTML/CSS와 seekable animation을 정해진 프레임으로 preview/lint/render하여 동일 입력에서 동일 결과를 만드는 영상 프레임워크 | 애니메이션을 시작/끝 스크린샷만 보지 않고 시간축의 중간 프레임과 상태 순서를 기록한다. `frame.md`가 디자인 토큰을 카메라용 시간 규칙으로 바꾸는 방식은 이 문서의 motion map과 대응시킨다. | QML runtime capture/Windows desktop capture 절차, 접기·복원 frame trace | HyperFrames/HTML/FFmpeg를 앱에 포함하기, MP4 결과를 실제 QWidget/QML 동작 검증으로 대체하기 |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | animate/review-animations/apple-design으로 motion의 목적·빈도·origin·interruptibility·성능·reduced motion을 엄격히 검토 | 모든 motion에 목적을 부여하고, enter/exit는 ease-out, 화면상의 morph는 ease-in-out, trigger popover는 trigger origin, 현재 표시값에서 재타깃, pointer-down 즉시 피드백을 적용한다. 자주 쓰는 조작은 불필요한 장식을 삭제한다. | `WidgetWindow.qml`, `VolumePopoverWindow.qml`, `AppleSlider.qml`, `AnimatedText/Number.qml` | 웹 전용 CSS/Pointer Events 코드, 실제 native window geometry를 무조건 transform으로 대체한다는 식의 기계적 적용 |
| [greensock/gsap-skills](https://github.com/greensock/gsap-skills) | GSAP core/timeline/performance와 함께 transform/opacity 우선, batch read/write, 재사용 timeline, cleanup을 가르치는 agent skill | 여러 독립 animation을 누적하지 않고 하나의 전환 coordinator와 명확한 phase를 사용한다. 입력이 잦은 값은 새 animation을 매번 만들지 않고 한 target을 갱신하며, 측정과 쓰기를 분리한다. | morph coordinator, volume drag, media timeline, runtime performance trace | GSAP npm 런타임 추가, ScrollTrigger/React plugin, QML에서 GSAP 코드를 흉내 내기 |

### 15.2 이 프로젝트에 적용할 디자인 판정

외부 자료를 종합한 현재 디자인 판정은 **quiet premium desktop control surface**다.
완전히 정적인 데이터 표도 아니고 홍보용 랜딩페이지도 아니므로, 시각적 변주보다
정렬·상태 인지·직접 조작·짧은 피드백을 우선한다.

- **구조**: 하나의 shell 안에 공통 content rect를 두고, battery/audio/media가 각자
  다른 역할을 가진다. 같은 색·같은 radius의 박스를 반복해 계층을 만들지 않는다.
- **수평 기준**: shell 내부 좌우 padding을 먼저 확정한 다음 모든 flow 요소가 그
  기준을 공유한다. L/R/CASE는 `label / state / track / value` 네 열을 고정하고,
  볼륨 숫자와 미디어 시간은 별도 역할을 유지하되 열 폭과 숫자 리듬을 흔들지 않는다.
- **수직 기준**: 배터리 row의 label/state/bar/value 중심선, 볼륨 icon/bar/thumb/value
  중심선, media title/subtitle/timeline/control baseline을 각각 측정한다. 수치가
  바뀌어도 높이와 다른 요소의 Y 좌표가 바뀌지 않는다.
- **타이포그래피**: 제목·본문·label·value·caption의 역할을 `UiTheme.qml` 토큰으로
  고정한다. 배터리/볼륨/시간은 tabular 숫자 폭과 고정 value slot을 사용하며, 숫자가
  제목보다 시각적으로 튀지 않게 한다. 폰트 변경은 글자 폭과 baseline을 포함한
  캡처 비교 후 승인한다.
- **표면**: 배경 투명도는 표면에만 적용하고 text/icon opacity로 가독성을 훼손하지
  않는다. 무채색 계층과 한정된 semantic state color를 사용하며, decorative
  gradient/glow/noise/card를 기본값으로 추가하지 않는다.
- **밀도**: 사용자가 지적한 “너무 넓음”과 “너무 빡빡함”을 동시에 피하기 위해
  큰 빈 영역을 없애되 row 내부의 최소 hit area와 시각적 breathing room은 유지한다.
  spacing은 token으로만 조정하고 각 컴포넌트의 임의 margin으로 해결하지 않는다.

### 15.3 이 프로젝트에 적용할 모션 판정

- **하나의 상태값**: flow/compact/minimized 전환은 `morphProgress` 하나를 기준으로
  한다. content reveal, icon state, shell radius는 이 값에서 파생하며 각 요소가
  독립적으로 시작·종료하는 animation을 추가하지 않는다.
- **native 창 예외를 분리**: Windows native `width/height/x/y/shape`는 실제 창을
  유지하기 위해 필요하므로, “transform만 사용” 원칙을 그대로 복사하지 않는다.
  대신 native envelope 갱신과 QML content reveal의 event ordering을 분리해 기록하고,
  실제 데스크톱 중간 프레임에서 함께 검증한다.
- **토글 앵커**: 토글의 screen center를 한 번 정한 뒤 접기/복원 동안 바꾸지 않는다.
  확장 방향은 현재 작업 영역에서 한 번 선택하고, content margin이 그 방향 때문에
  독립적으로 좌우 튀지 않는지 별도로 확인한다.
- **등장/퇴장**: shell이 공간을 확보한 뒤 header → battery → audio → media 순으로
  짧게 reveal한다. 제목만 먼저 보이는 프레임, 이전 media가 남는 프레임, shell보다
  content가 먼저 잘리는 프레임을 실패로 판정한다.
- **직접 조작**: volume drag와 media seek는 pointer/input과 같은 프레임에서 값을
  갱신한다. thumb, filled track, 숫자는 동일한 source value를 사용하고, drag 중에는
  외부 polling이 현재 표시값을 덮어쓰지 않는다.
- **시간값**: 1초마다 변하는 미디어 시간은 layout animation이 아니다. 숫자만 교체하고
  timeline/control의 geometry는 고정한다. title/subtitle 변경도 fixed slot 안에서
  crossfade한다.
- **삭제 우선**: 빈 상태, 대기 상태, 연결 상태처럼 자주 보이는 UI에는 shimmer,
  bounce, 무한 glow를 넣지 않는다. 목적을 설명할 수 없는 animation은 추가하지 않는다.
- **검수**: 코드상 duration/easing보다 실제 체감이 우선이다. 16ms frame trace와
  실제 바탕화면 녹화에서 시작·중간·끝을 모두 보고, 중간에 좌우 스냅·속도 단절·깜빡임이
  있으면 통과시키지 않는다.

### 15.4 구현 순서와 파일 매핑

1. **Shape** — 이 문서의 기준선·상태·금지 목록을 먼저 읽고, 현재 화면의 모든
   rect/baseline/겹침을 기록한다. 대상: `WidgetWindow.qml`, `UiTheme.qml`.
2. **Layout** — 공통 content rect와 고정 열을 만든다. 대상:
   `BatteryRow.qml`, `BatteryOverview.qml`, `AudioOutputSection.qml`,
   `MediaSection.qml`, `CompactController.qml`.
3. **Typeset** — 폰트 family/weight/size/line-height/tabular value slot을 함께
   조정하고 다크·라이트에서 baseline을 비교한다. 대상: `UiTheme.qml`와 위 UI.
4. **State** — connected/detected/charging/empty/loading/paused/media absent를
   같은 slot에서 안정적으로 표시한다. 대상: `state_manager.py`,
   `media_service.py`, `AnimatedText.qml`, `AnimatedNumber.qml`, `EmptyIndicator.qml`.
5. **Animate** — 고정된 geometry 위에 필요한 opacity/transform/indicator transition만
   붙인다. 대상: `WidgetWindow.qml`, `AppleSlider.qml`, `VolumePopoverWindow.qml`,
   `SoftButton.qml`, `OutputDeviceButton.qml`.
6. **Audit/Polish** — 코드 검사 후 실제 화면을 반복 캡처한다. 대상: `tools/qml_runtime_check.py`,
   `tools/ui_spec_check.py`, `BUILD_REPORT.md`.
7. **Ship** — 모든 실제 Windows 검증이 끝난 뒤에만 EXE/MSIX를 만들고 버전·캡처·미검증
   항목을 기록한다.

### 15.5 외부 레퍼런스 반영 완료 조건

- [ ] 일곱 저장소의 출처·핵심 원칙·적용 위치·비적용 항목이 이 문서에 기록됨
- [ ] 정렬 기준선과 숫자 slot이 코드 수정 전에 확정됨
- [ ] 외부 레퍼런스의 웹 런타임/라이브러리를 무단으로 프로젝트 의존성에 추가하지 않음
- [ ] 접기/복원은 실제 Windows desktop 중간 프레임으로 검증됨
- [ ] 애니메이션은 목적·빈도·origin·interruptibility·reduced motion 기준으로 검토됨
- [ ] 다크/라이트, flow/compact/minimized, 미디어 있음/없음, paired/disconnected를
      같은 검수표로 확인함
- [ ] 위 항목이 모두 충족되기 전에는 완료/완벽/적용됨으로 보고하지 않음

## 16. 2026-09-02 요구사항 대조 및 다음 수정 계획

이 절은 다음 코드 수정의 작업 계약이다. 아래의 요구사항·현재 증거·수정 방법·검증
방법을 모두 확인하기 전에는 구현 완료로 보고하지 않는다. 리퀴드 글라스 자체를
달성 목표로 삼지 않는다. 목표는 조용하고 정교한 데스크톱 컨트롤 UI이며, 투명 배경은
설정 가능한 배경 표면의 기술적 선택일 뿐 디자인 합격 조건이 아니다.

### 16.1 요구사항 대조표

| 요구사항 | 현재 코드에서 확인된 상태 | 정확한 수정 방향 | 검증 방법 |
|---|---|---|---|
| 접기/복원 때 토글 버튼 screen 좌표 고정 | QML 오프스크린 drift는 0이지만 native x/y와 width/height가 별도 갱신됨. morphAnchorInset과 shell 8px inset을 섞어 계산함 | outer window 기준의 단일 anchor 좌표를 정의하고, 한 morph frame에서 geometry·position·shape를 같은 coordinator가 적용. content margin은 anchor 계산에 관여하지 않게 함 | 실제 Windows에서 좌상·우상·좌하·우하 배치, 양방향 10회 반복. 토글 center와 window/shell 경계를 16ms 간격으로 기록 |
| 접힐 때 좌우로 튀거나 펼침 방향이 매번 달라지는 문제 | chooseMorphPlacement는 복원 시점과 이동 후 시점이 섞일 수 있고, flow/compact content가 방향에 따라 좌우 margin을 바꿈 | morph 시작 전에만 확장 방향을 확정하고 전환 중 변경 금지. 배터리·볼륨·미디어의 공통 content rect는 양쪽 같은 기준을 사용하고, 토글을 피하는 것은 header/compact top slot만 별도로 처리 | 두 방향 및 서로 다른 desktop 좌표에서 시작/끝/중간 frame의 global rect 비교 |
| 테두리/Region이 늦게 바뀌거나 잘리는 문제 | shapeUpdateTimer가 geometry 변경 뒤 별도 event turn에 실행됨. 현재 자동 검사는 QML scene만 확인함 | geometry coordinator가 native geometry를 반영한 직후 같은 frame에 rounded Region을 갱신. 이전 Region이 남는 frame과 shell 여백이 사라지는 frame을 실패 처리 | Windows 캡처에서 모서리·테두리·shell margin을 중간 frame까지 확인 |
| 펼칠 때 이름만 먼저 보이는 문제 | expanded/minimized scene을 morph 동안 모두 visible로 두고, parent/child reveal 곡선이 여러 개임 | morphProgress 하나에서 shell 확보 → summary handoff → header → battery → audio/output → media 순서를 파생. 독립 Behavior와 임계값 visible 교체를 줄이고 모든 slot은 고정 | 16ms frame sequence에서 title-only, blank shell, 이전 media 잔상 여부 확인 |
| 애니메이션이 격렬하고 렉처럼 보이는 문제 | 400ms라도 native window와 child layout이 서로 다른 갱신 경로에 있음. source progress에 easing을 한 번 더 적용하면 height 변화율이 중간에 커짐 | native frame은 선형 단일 progress로 샘플링하고, width/height/content reveal에만 smooth-step을 한 번 적용한다. overshoot/spring/shimmer는 금지하며 native geometry는 frame coordinator로 한 번만 쓴다. 재트리거 시 현재 progress에서 이어감 | 시작/중간/끝 캡처와 frame interval, geometry step, 방향 역전, 깜빡임 검사 |
| 컴팩트 모드 볼륨 조절 | QML에 popover 경로는 있으나 사용자 화면에서 안정적으로 노출·조작된다는 증거가 없음. 숫자/라벨/두 번째 MouseArea가 중복됨 | 전용 compact volume trigger 하나와 독립 vertical rail popover 하나로 단순화. 팝오버는 trigger 아래/위에만 배치하고 부모 width/height·토글 좌표를 절대 변경하지 않음. rail 전체를 hit target으로 사용 | 실제 compact에서 click·drag·0/50/100, 팝오버 위치, 부모 geometry 불변, 토글/다른 UI overlap 확인 |
| 배터리·볼륨·미디어 정렬 | flow 배터리 열 토큰은 있으나 compact Repeater의 고정 폭과 flow의 방향별 margin이 공통 기준을 깨뜨릴 수 있음 | 공통 left/right content rect, 고정 label / state / track / value 열, tabular value slot을 먼저 확정. 볼륨 icon/bar/thumb/value는 한 centerline과 한 source value를 사용 | global rect/baseline 측정: 0/50/100, —, 라이트/다크, compact/flow |
| 큰 빈 공간과 지나치게 빡빡한 공간 동시 해결 | 선택적 media 높이와 여러 고정 margin이 상태별로 다른 밀도를 만듦 | shell padding·group gap·row gap을 theme token으로만 조정. media 없음이면 surface와 높이를 함께 제거하고, 상시 표시 설정일 때만 빈 player slot 유지 | media 있음/없음 및 player setting on/off 캡처에서 빈 영역·clipping·겹침 확인 |
| 미디어는 현재 세션만 표시하고 일시정지해도 유지 | last_session/identity 방어 로직은 있으나 Chrome 실제 세션과 paused fallback은 live 검증 전 | playing 우선, 현재 paused session 유지, stopped/무관한 old identity는 즉시 MediaState()로 clear. 100ms 표시 clock은 command 결과를 덮어쓰지 않도록 source generation을 둠 | Chrome YouTube 실제 재생·정지·일시정지·다음/이전/seek, 세션 교체와 stale title 제거 확인 |
| 출력장치 shortcut과 로딩 상태 | paired AirPods endpoint 재연결 worker와 pending 상태는 구현돼 있음 | 버튼의 available/current/pending을 하나의 상태 전이로 표시하고 클릭 중 중복 command를 막음. 실제 endpoint 생성 전에는 loading만 표시하고 UI thread를 막지 않음 | paired/disconnected, active, 재연결 실패/성공을 실제 장치에서 확인 |
| 연결 안 된 상태의 기본 이름/표시 | deviceName은 빈 문자열이지만 QML header가 AirPods로 fallback하고 demo는 고정 이름을 사용함 | 실제 disconnected/undetected는 이름 대신 명확한 empty indicator와 상태만 표시. demo 고정 이름은 demo 범위로 격리 | BLE 미감지·paired only·connected·demo 네 상태 캡처 |
| 충전 상태 | flow BatteryRow는 yellow dot 경로가 있고 compact와 구현이 중복됨 | L/R/CASE 모두 같은 state slot에서 착용 green dot 또는 충전 중 단순 벡터 번개 하나만 표시. 노란색 번개는 허용하되 테두리·이모지 스타일은 금지 | 충전 시작/종료와 미착용 상태에서 색·slot·baseline 확인 |
| 플레이어 표시 설정과 자동 시작 | 설정/Run 등록 경로는 있으나 기본값이 꺼져 있고 설치본의 startup entry 실제 검증이 없음 | player ON/OFF는 flow에서만 적용하고 compact는 요구한 compact controller를 유지. Windows 시작 옵션은 설정값·등록 경로·재부팅 결과를 분리 검증하며 임의로 기본값을 바꾸지 않음 | 설정 toggle → 재시작 → Run entry → 로그인 후 widget 표시 확인 |
| 설정창·트레이의 가독성 | 설정은 정보가 많은 nested card 구조와 고정 폭을 사용함 | 설정은 좌우 padding과 label/control column을 먼저 고정하고, background opacity는 표면만 변경. 트레이는 위젯과 별도 readable surface 유지 | 다크/라이트, 긴 문자열, 80~150% scale 캡처 및 overlap 검사 |

### 16.2 구현 전에 고정할 파일 순서

1. WidgetWindow.qml, UiTheme.qml: native geometry coordinator, outer anchor,
   공통 content rect, spacing/type token을 확정한다.
2. BatteryRow.qml, BatteryOverview.qml, AudioOutputSection.qml,
   CompactController.qml, MediaSection.qml: slot·baseline·밀도와 compact volume
   trigger를 정리한다.
3. VolumePopoverWindow.qml, AppleSlider.qml, SoftButton.qml,
   OutputDeviceButton.qml, AnimatedText.qml, AnimatedNumber.qml: 같은 source
   value와 목적 있는 transition만 남긴다.
4. controller.py, media_service.py, audio_output.py, startup_manager.py:
   stale session, command generation, paired reconnect, startup entry를 UI와 분리해
   검증한다.
5. SettingsWindow.qml, TrayPopup.qml, tools/qml_runtime_check.py,
   tools/ui_spec_check.py, BUILD_REPORT.md: 설정/정적 검사와 실제 캡처 판정을
   갱신한다.

### 16.3 이번 수정에서 하지 않을 것

- 리퀴드 글라스나 유리 효과를 새 acceptance gate로 부활시키지 않는다.
- 기존 코드가 있다는 이유로 현재 카드 구조·방향별 margin·중복 MouseArea를 보존하지
  않는다. 반대로 기능과 무관한 대규모 프레임워크/웹 의존성도 추가하지 않는다.
- offscreen QML 결과, 정적 검사, 빌드 성공만으로 native Windows motion을 완료 처리하지
  않는다.
- 실제 캡처에서 겹침·clipping·title-only frame·좌우 snap 중 하나라도 남으면 완료 보고를
  하지 않는다.

## 17. 2026-09-02 구현 체크포인트

### 이번 패치에서 실제 코드에 반영한 것

- `WidgetWindow.qml`: 접기/복원의 native `x/y/width/height/Region`을 하나의
  geometry frame coordinator로 적용하고, 전환 중 anchor와 확장 방향을 고정했다.
  native progress는 선형 한 번만 샘플링하고, content reveal은 파생 smooth-step만
  사용한다.
- `AudioOutputSection.qml`, `VolumePopoverWindow.qml`, `AppleSlider.qml`:
  compact/minimized 볼륨 trigger와 세로 popover를 하나로 정리했다. slider의 fill과
  thumb는 같은 `value` timeline을 공유하며, 중복 MouseArea와 파생 geometry
  Behavior를 제거했다.
- `controller.py`: Windows Core Audio endpoint 열거, 현재 볼륨 조회, 볼륨 쓰기,
  paired endpoint 재연결 후 polling, 출력 전환을 worker에서 실행한다. 결과 snapshot과
  상태 전이만 Qt UI thread에서 적용해 timer와 pointer feedback이 화면 애니메이션을
  막지 않게 했다.
- `BatteryRow.qml`, `MediaIcon.qml`, `BatteryOverview.qml`, `WidgetWindow.qml`:
  충전 상태는 테두리 없는 노란 벡터 번개로 통일하고, 미감지 상태에서 임의의
  `AirPods Pro 3` 이름이나 오래된 배터리 값을 재사용하지 않는다.
- `CompactController.qml`, `MediaSection.qml`, `WidgetWindow.qml`: 미디어 없음의
  빈 높이를 줄이고, 미디어 시간은 layout animation 없이 고정 slot에서 갱신한다.

### 이번 패치의 자동 검증 증거

- `python tools/ui_spec_check.py` 통과
- `python tools/validate_project.py` 통과
- `python tools/qml_runtime_check.py` 통과
- `PYTHONPATH=src .venv\\Scripts\\python.exe -m pytest -q` 결과 `39 passed`
- `artifacts/qml-verify/`에 flow/compact/minimized, media 있음/없음, light/dark,
  volume popover 및 접기·복원 중간 frame 캡처가 생성되며, offscreen 검사에서
  toggle center drift·clipping·중복 trigger·부모 geometry 변경을 검사했다.

위 증거는 source/QML 수준의 회귀 방지 증거다. 실제 Windows desktop의 native
composition을 대신하지 않는다.

### 아직 완료로 판정하지 않는 것

- `0.1.26.0` source는 EXE/MSIX로 빌드했고 root EXE의 `--demo` 3초 시작 smoke도
  통과했다. 그러나 원격 세션에서 관리자 UAC 승인창이 노출되지 않아 개발 인증서
  서명과 MSIX 설치는 완료하지 못했다. 현재 MSIX 서명 상태는 `NotSigned`다.
- 실제 Windows 바탕화면에서 16ms 간격으로 녹화한 접기·복원 중간 frame, Region,
  좌상·우상·좌하·우하 배치, 다크·라이트 결과는 미검증이다.
- Chrome YouTube의 실제 현재 세션, pause 후 재생, seek/time sync, 다음·이전은
  새 MSIX를 설치한 뒤 별도 live acceptance가 필요하다.
- paired AirPods를 위젯 버튼으로 재연결하고 A2DP endpoint가 생기는 과정은 실제
  Bluetooth 장치에서 성공·실패·timeout을 각각 확인해야 한다.
