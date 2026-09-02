# AirPods Widget for Windows

AirPods Pro 3 상태와 Windows 미디어를 한 화면에서 확인·제어하는 데스크톱 위젯입니다.
별도 Bluetooth 커널 드라이버, Windows Test Mode, Secure Boot 변경, 무음 오디오 반복 재생을
사용하지 않습니다.

## 들어간 기능

이번 UI 개편의 기준과 검증 항목은 [UI_REDESIGN_SPEC.md](UI_REDESIGN_SPEC.md)와
[UI_V2_DESIGN_BRIEF.md](UI_V2_DESIGN_BRIEF.md)에 정리되어 있습니다. 두 문서에는
정보 우선 레이아웃, 컴팩트/최소화 모드, 모션 규칙, 다크·라이트·미디어 없음 상태의
완료 조건이 기록되어 있습니다.

- AirPods Pro 3 자동 감지
- 왼쪽·오른쪽·케이스 배터리와 애니메이션 막대
- 좌우 착용 상태와 충전 상태
- R과 CASE 사이에 배터리 기반 예상 잔여시간 (`6h 35m` 형식)
- 현재 미디어 제목·아티스트·앱 표시
- 긴 제목의 느린 전광판 애니메이션
- 이전 곡·재생/일시정지·다음 곡
- 신선한 BLE 패킷으로 양쪽 이어버드 제거가 확인된 뒤 0.6초 후 자동 일시정지
- 데스크톱 위젯과 트레이 팝업 동시 사용
- 연결 팝업과 저전력 팝업
- 테두리 없는 창모드를 포함한 게임 프로세스 기반 팝업 차단
- 사용자가 제공한 MP3 저전력 경고음
- 알림 볼륨 조절과 테스트 재생
- 위젯/트레이에서 설정한 출력 장치 아이콘으로 Windows 기본 출력 전환
- 페어링된 AirPods 출력 버튼을 누르면 Windows 기본 A2DP 오디오 서비스를 재연결한 뒤 출력 전환
- 미디어 플레이어와 분리된 Windows 기본 출력 볼륨 슬라이더와 수치 표시
- 설정에서 출력 버튼별 장치 지정·추가·삭제 (최대 3개)
- 위젯 크기·투명도·위치 잠금·시작 프로그램 설정
- 위젯 우측 하단 드래그 크기 조절과 전체 UI 비율 자동 맞춤
- 위젯 항상 위 표시 옵션 (게임 활성 시에는 게임 위를 덮지 않도록 하단 우선)
- 설정창은 위젯 헤더가 아니라 시스템 트레이 메뉴에서만 엶
- 데모 모드

재생 중인 미디어는 일시정지해도 플레이어와 재생 버튼을 유지합니다. 버튼은 일시정지 상태에서
다시 재생 명령을 보냅니다. 페어링된 AirPods가 현재 연결되지 않은 경우 출력 버튼이 사용자 모드
Windows Bluetooth Audio Sink 재협상을 요청하며, 오디오 엔드포인트가 나타날 때까지 잠시 재시도합니다.

## 화면 모드

- **흐름형**: 배터리, 볼륨, 출력 장치, 미디어를 정보 우선 순서로 표시합니다.
- **컴팩트형**: 작은 창에 맞춰 배터리 요약·볼륨 trigger·출력 장치·미디어를 압축합니다.
- **최소화**: 고정된 토글 위치를 기준으로 작은 상태 capsule만 남깁니다. 볼륨 버튼을 누르면
  부모 위젯을 이동하거나 키우지 않는 세로 볼륨 popover가 열립니다.

접기·복원은 하나의 전환 progress와 고정된 토글 anchor를 사용합니다. 실제 Windows 화면의
중간 프레임 검증이 필요한 항목은 [UI_REDESIGN_SPEC.md](UI_REDESIGN_SPEC.md)의 완료 조건에
명시되어 있습니다.

## 중요한 배터리 제한

AirPods의 공개 Continuity BLE 광고는 배터리를 일반적으로 `0, 10, 20 ... 100%` 단계로
보냅니다. 따라서 정확한 `9%`를 확인할 수 없습니다. 기본 저전력 기준은 실사용상 놓치지
않도록 **첫 10% 데이터에서 알림**을 발생시키며, 다음 20% 단계 이상으로 회복된 후 다시 알림할 수
있습니다. UI에 표시되는 퍼센트도 수신한 단계값 그대로이며, 임의 보간하지 않습니다.

케이스 배터리는 케이스가 실제로 광고하는 순간에만 갱신되므로 뚜껑을 열거나 이어버드를
넣고 뺄 때 가장 잘 들어옵니다.

## 게임 안전성

게임 감지는 화면 모드가 아니라 현재 foreground 프로세스 이름을 기준으로 합니다. 따라서
전체화면뿐 아니라 **테두리 없는 창모드**도 동일하게 처리합니다. 기본 목록에는 League of
Legends와 VALORANT 실행 파일이 들어 있습니다.

이 앱은 BLE 광고를 읽는 사용자 모드 프로그램이며 커널 드라이버를 설치하지 않습니다.
다만 실제 Vanguard 호환성은 Windows와 Vanguard 버전에 따라 달라질 수 있으므로 최초 사용
후 롤 실행·종료·재부팅 회귀 테스트를 권장합니다.

## 저장소에서 처음 시작하기

이 저장소는 Windows x64 개발용 소스 저장소입니다. 개인 실행 파일, PyInstaller
runtime, 캡처 PNG, 로그, 인증서, 설정 파일과 재배포 권한을 확인하지 않은 MP3는
커밋하지 않습니다.

```powershell
git clone https://github.com/0woo7391/AirPodsWidget.git
Set-Location .\AirPodsWidget
```

저전력 알림을 사용하려면 재배포 권한이 있는 MP3 파일을 직접
`assets\low_power_warning.mp3`에 넣어야 합니다. 이 파일은 `.gitignore`로 제외되어
있으며, 파일이 없으면 알림음 검증과 빌드가 중단됩니다.

## 실행

요구사항:

- Windows 10/11 x64
- Bluetooth LE 지원 어댑터
- Python 3.11 x64

`run_windows.bat`을 실행하면 가상환경과 실행용 의존성만 설치한 뒤 앱을 실행합니다. `py.exe`가
없어도 `python.exe`가 있으면 사용할 수 있습니다.

소스 파일을 시스템 Python으로 직접 실행하지 말고 이 런처를 사용하세요. PySide6의 Python 모듈과
Qt DLL 버전이 섞이면 `ImportError: DLL load failed while importing QtCore`가 발생할 수 있습니다.

실제 AirPods 없이 UI를 먼저 보려면 `run_demo_windows.bat`을 실행합니다. 전체 검증은 `verify_windows.bat`으로 실행합니다.

권장 순서:

```powershell
.\run_demo_windows.bat     # AirPods 없이 UI/트레이/미디어 데모 확인
.\verify_windows.bat       # 테스트와 QML 런타임 검사
.\run_windows.bat          # 실제 AirPods BLE 실행
```

## Windows 실행 파일 빌드

PowerShell에서 다음을 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

빌드 과정은 다음을 자동 수행합니다.

1. Python 3.11 가상환경 구성
2. 의존성 설치
3. 단위 테스트
4. Python/QML 정적 검증
5. 실제 Qt 엔진을 이용한 QML 런타임 로딩 검사
6. PyInstaller portable 폴더 빌드
7. 프로젝트 루트에 portable 실행 파일과 `_internal` 갱신
8. `globalMediaControl` 권한이 포함된 `AirPodsWidget.msix` 생성

빌드가 끝나면 미디어 기능까지 사용할 경우 PowerShell에서 아래 설치 스크립트를 실행한 뒤
시작 메뉴의 `AirPodsWidget`을 실행하세요.

```powershell
# 관리자 권한 PowerShell에서 실행
Set-Location "C:\Path\To\AirPodsWidget"
Set-ExecutionPolicy -Scope Process Bypass -Force
.\install_msix.ps1
```

`AirPodsWidget.msix`를 파일 탐색기에서 직접 열면 서명 전 패키지라서 인증서 오류가 납니다.
반드시 위 스크립트를 실행해야 합니다. 스크립트가 현재 사용자용 개발 인증서를 만들고,
서명한 뒤 설치합니다.

`AirPodsWidget.exe`는 패키지 설치 없이 UI/BLE만
확인하는 portable 실행본입니다. `dist\AirPodsWidget`는 빌드 과정에서 사용하는 staging
폴더이며 직접 실행할 필요가 없습니다.

같은 개발 패키지가 이미 설치되어 있고 새 MSIX 설치가 거부되면 앱을 종료한 뒤
현재 사용자 패키지를 제거하고 설치 스크립트를 다시 실행합니다.

```powershell
Get-AppxPackage -Name AirPodsWidget | Remove-AppxPackage
```

## 데이터 저장 위치

`%LOCALAPPDATA%\AirPodsWidget`

- `settings.json`: 위젯/알림/미디어 설정
- `usage.json`: 당일 사용시간
- `app.log`: 오류 로그

## 미디어 호환성

Windows Global System Media Transport Controls 세션을 노출하는 앱만 표시·제어할 수 있습니다.
Spotify, 대부분의 Chromium 기반 브라우저 및 일반 미디어 플레이어는 보통 지원하지만, 자체
미디어 세션을 노출하지 않는 프로그램은 나타나지 않습니다.

미디어 제목·재생 시간·재생/일시정지·이전·다음 제어는 Windows의 `globalMediaControl` 패키지
권한이 필요합니다. 일반 EXE는 이 권한을 선언할 수 없으므로, 미디어 기능은 반드시
`AirPodsWidget.msix` 설치본을 실행해야 합니다. 설치 스크립트는 현재 사용자 범위의 개발용
인증서를 만들고 신뢰 저장소에 등록한 뒤 MSIX를 설치합니다. 공개 배포에는 신뢰된 코드 서명
인증서가 필요합니다.

## 라이선스

GPL-3.0-or-later. 자세한 내용은 `LICENSE`와 `THIRD_PARTY_NOTICES.md`를 확인하세요.

## 검증 범위

- AirPods Pro 3 Continuity 패킷 파싱 단위 테스트
- 좌우 광고 병합·유실·RSSI-only 갱신 억제 테스트
- 저전력 알림 재생 방지 및 재무장 테스트
- 사용시간 기록·60초 주기 복구 저장 테스트
- 설정 저장 테스트
- Python 구문 및 QML 구조 정적 검사

최종 BLE 수신, Windows 미디어 세션, 트레이 위치 및 Vanguard 공존은 실제 Windows 11과
AirPods Pro 3에서 한 번 실행해야만 확정할 수 있습니다. 이 저장소에는 그 확인을 위한 데모 모드와
로그 경로 안내가 포함되어 있습니다.

현재 자동 검증은 Python 단위 테스트, 프로젝트/QML 정적 검사, 실제 Qt 엔진을 이용한 QML
오프스크린 상태·중간 프레임 검사로 구성됩니다. 오프스크린 결과만으로 Windows DWM의 실제
창 합성, 다중 모니터 좌표, Chrome의 실제 미디어 세션, AirPods 재연결까지 보증하지 않습니다.
검증 기록과 미완료 항목은 [BUILD_REPORT.md](BUILD_REPORT.md)에 남깁니다.

## 문제 해결

- `ImportError: DLL load failed while importing QtCore`: 시스템 Python으로
  `main.py`를 직접 실행하지 말고 `run_windows.bat` 또는 `run_demo_windows.bat`을
  사용합니다. 계속되면 `.venv`를 삭제한 뒤 런처를 다시 실행합니다.
- `0x800B0109` 또는 게시자 인증서 오류: 서명되지 않은 MSIX를 직접 열지 말고,
  관리자 PowerShell에서 `install_msix.ps1`을 실행합니다. 이 스크립트의 인증서는
  현재 PC의 개발용 자체 서명 인증서이며 공개 배포용 인증서가 아닙니다.
- `0x80073CFB` 또는 같은 패키지 내용 오류: 앱을 완전히 종료하고, `packaging/AppxManifest.xml`의
  패키지 버전이 이전 설치본보다 높은지 확인한 뒤 빌드·설치합니다. 필요하면 현재 사용자
  패키지를 제거하고 다시 설치합니다.
- 위젯이 보이지 않음: 앱이 트레이에 상주할 수 있으므로 트레이 아이콘을 확인하고,
  `run_demo_windows.bat`으로 UI를 먼저 확인합니다.

## 공개 배포

`AirPodsWidget.msix`는 `globalMediaControl` 권한을 위해 패키지 ID가 필요합니다.
로컬 개발 설치는 `install_msix.ps1`이 생성하는 자체 서명 인증서를 사용하지만,
다른 사용자에게 배포하려면 Microsoft Store 또는 신뢰된 코드 서명 인증서로 서명한
패키지가 필요합니다. 자체 서명 인증서와 `.pfx` 파일은 저장소에 업로드하지 않습니다.
