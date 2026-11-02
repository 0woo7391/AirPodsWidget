import QtQuick
import QtQuick.Dialogs

// Settings window. Every control writes through dockPrefs, which applies the
// change to the dock and the island at once; there is no save button.
Rectangle {
    id: root
    width: 860
    height: 640
    color: "#141418"

    property string page: "screen"
    readonly property var pages: [
        { id: "screen", title: "화면", hint: "dock을 어느 모니터, 어느 가장자리에 둘지" },
        { id: "modules", title: "모듈", hint: "보일 카드와 순서, 빠른 실행 앱" },
        { id: "island", title: "알림", hint: "아일랜드가 뜨는 화면과 위치, 알릴 일" },
        { id: "airpods", title: "AirPods", hint: "기기, 배터리 읽기, 배터리 경고" },
        { id: "media", title: "미디어", hint: "따라갈 미디어와 착용 감지" },
        { id: "general", title: "일반", hint: "시작 프로그램과 종료" }
    ]

    // Bindings call pref(); reading `rev` makes them re-evaluate when any setting changes.
    property int rev: 0
    Connections { target: dockPrefs; function onChanged() { root.rev++ } }
    function pref(key) { rev; return dockPrefs.get(key) }

    readonly property var screens: dockPrefs.screens
    function screenByName(name) { return screens.find(s => s.name === name) }
    // The screen the dock is on: the chosen one, or the outermost on the chosen edge.
    function dockScreenName() {
        const chosen = pref("dock/screen")
        if (chosen !== "auto" && screenByName(chosen)) return chosen
        if (!screens.length) return ""
        const left = pref("dock/edge") === "left"
        let best = screens[0]
        for (const s of screens)
            if (left ? s.x < best.x : s.x + s.width > best.x + best.width) best = s
        return best.name
    }
    // True when another monitor touches this edge, i.e. the dock would sit on the seam.
    function onSeam() {
        const s = screenByName(dockScreenName())
        if (!s) return false
        const left = pref("dock/edge") === "left"
        return screens.some(o => o !== s && o.y < s.y + s.height && s.y < o.y + o.height
                            && (left ? o.x + o.width === s.x : o.x === s.x + s.width))
    }
    function islandOn(s) {
        const c = pref("island/screens")
        return c === "all" || (c === "primary" && s.primary) || (c === "dock" && s.name === dockScreenName()) || c === s.name
    }

    // ---- building blocks ---------------------------------------------------

    component Label: Text {
        color: Theme.ink
        font.family: dockFont
        font.pixelSize: 13
    }

    component Toggle: Rectangle {
        id: toggle
        property bool checked: false
        signal toggled(bool value)
        width: 42; height: 24; radius: 12
        color: checked ? Theme.good : Theme.well
        border.width: 1; border.color: checked ? "transparent" : Theme.stroke
        Behavior on color { ColorAnimation { duration: 140 } }
        Rectangle {
            width: 18; height: 18; radius: 9; y: 3
            x: toggle.checked ? toggle.width - width - 3 : 3
            color: toggle.checked ? "#10301C" : Theme.ink
            Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
        }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: toggle.toggled(!toggle.checked) }
    }

    // Toggle bound to a boolean setting.
    component PrefToggle: Toggle {
        property string key
        checked: root.pref(key)
        onToggled: function(value) { dockPrefs.set(key, value) }
    }

    component Segmented: Flow {
        id: seg
        property var options: []     // [{ value, label }]
        property var current
        signal picked(var value)
        spacing: 4
        Repeater {
            model: seg.options
            Rectangle {
                required property var modelData
                readonly property bool on: modelData.value === seg.current
                height: 30; width: optionText.implicitWidth + 24; radius: 9
                color: on ? Theme.ink : optionMouse.containsMouse ? Theme.wellHover : Theme.well
                Behavior on color { ColorAnimation { duration: 110 } }
                Text {
                    id: optionText
                    anchors.centerIn: parent
                    text: modelData.label
                    color: parent.on ? "#16161A" : Theme.ink
                    font.family: dockFont; font.pixelSize: 12; font.weight: parent.on ? Font.DemiBold : Font.Normal
                }
                MouseArea {
                    id: optionMouse
                    anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: seg.picked(modelData.value)
                }
            }
        }
    }

    // Segmented bound to a setting.
    component PrefChoice: Segmented {
        property string key
        current: root.pref(key)
        onPicked: function(value) { dockPrefs.set(key, value) }
    }

    // One line: label and hint on the left, a control on the right.
    component SettingRow: Item {
        id: row
        property string label
        property string hint
        default property alias control: slot.data
        width: parent ? parent.width : 0
        height: Math.max(48, texts.implicitHeight + 18, slot.childrenRect.height + 14)
        Column {
            id: texts
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - slot.childrenRect.width - 24
            spacing: 3
            Label { width: parent.width; text: row.label; wrapMode: Text.Wrap }
            Label {
                width: parent.width; text: row.hint; visible: text.length > 0; wrapMode: Text.Wrap
                color: Theme.inkSecondary; font.pixelSize: 11
            }
        }
        Item {
            id: slot
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: childrenRect.width; height: childrenRect.height
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#0FFFFFFF" }
    }

    component Section: Column {
        property string title
        width: parent ? parent.width : 0
        spacing: 0
        Label {
            text: parent.title; color: Theme.inkSecondary; font.pixelSize: 12; font.weight: Font.DemiBold
            bottomPadding: 6; topPadding: 18
        }
    }

    // Monitors drawn as they are arranged. mode "dock" marks the dock's edge;
    // mode "island" marks where the island appears. Clicking a monitor picks it.
    component ScreenMap: Rectangle {
        id: map
        property string mode: "dock"
        signal picked(string name)
        width: parent ? parent.width : 0
        height: 210
        radius: 14
        color: "#0DFFFFFF"
        border.width: 1; border.color: Theme.stroke
        readonly property real minX: Math.min(...root.screens.map(s => s.x))
        readonly property real minY: Math.min(...root.screens.map(s => s.y))
        readonly property real spanX: Math.max(...root.screens.map(s => s.x + s.width)) - minX
        readonly property real spanY: Math.max(...root.screens.map(s => s.y + s.height)) - minY
        readonly property real k: Math.min((width - 48) / spanX, (height - 40) / spanY)
        readonly property real offsetX: (width - spanX * k) / 2
        readonly property real offsetY: (height - spanY * k) / 2

        Repeater {
            model: root.screens
            Rectangle {
                id: monitor
                required property var modelData
                readonly property bool dockHere: map.mode === "dock" && modelData.name === root.dockScreenName()
                readonly property bool islandHere: map.mode === "island" && root.islandOn(modelData)
                readonly property bool chosen: dockHere || islandHere
                x: map.offsetX + (modelData.x - map.minX) * map.k + 3
                y: map.offsetY + (modelData.y - map.minY) * map.k + 3
                width: modelData.width * map.k - 6
                height: modelData.height * map.k - 6
                radius: 8
                color: chosen ? "#2A2A38" : monitorMouse.containsMouse ? "#22222C" : "#1B1B22"
                border.width: chosen ? 2 : 1
                border.color: chosen ? Theme.charge : Theme.stroke
                Behavior on color { ColorAnimation { duration: 120 } }

                Column {
                    anchors.centerIn: parent
                    spacing: 2
                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: monitor.modelData.number; font.pixelSize: 34; font.weight: Font.DemiBold
                    }
                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: monitor.modelData.model || "화면"
                        color: Theme.inkSecondary; font.pixelSize: 11
                    }
                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: monitor.modelData.width + "×" + monitor.modelData.height + (monitor.modelData.primary ? " · 주 화면" : "")
                        color: Theme.inkTertiary; font.pixelSize: 10
                    }
                }
                // Dock bar on the chosen edge.
                Rectangle {
                    visible: monitor.dockHere
                    width: 7; height: parent.height * 0.62; radius: 3.5
                    anchors.verticalCenter: parent.verticalCenter
                    x: root.pref("dock/edge") === "left" ? 7 : parent.width - width - 7
                    color: Theme.charge
                }
                // Island pill at the top.
                Rectangle {
                    visible: monitor.islandHere
                    width: 44; height: 10; radius: 5
                    y: 7 + root.pref("island/offset") * map.k
                    x: root.pref("island/align") === "left" ? 10
                       : root.pref("island/align") === "right" ? parent.width - width - 10 : (parent.width - width) / 2
                    color: Theme.ink
                }
                MouseArea {
                    id: monitorMouse
                    anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: map.picked(monitor.modelData.name)
                }
            }
        }
    }

    // ---- layout --------------------------------------------------------------

    Rectangle {
        id: sidebar
        width: 196
        height: parent.height
        color: "#101014"
        Column {
            x: 14; y: 22
            width: parent.width - 28
            spacing: 4
            Row {
                spacing: 10; bottomPadding: 18; leftPadding: 6
                DockIcon { size: 20; name: "headphones"; anchors.verticalCenter: parent.verticalCenter }
                Label { text: "Glass Dock"; font.pixelSize: 16; font.weight: Font.DemiBold }
            }
            Repeater {
                model: root.pages
                Rectangle {
                    required property var modelData
                    readonly property bool on: root.page === modelData.id
                    width: parent.width; height: 38; radius: 10
                    color: on ? Theme.wellHover : navMouse.containsMouse ? Theme.well : "transparent"
                    Rectangle {
                        visible: parent.on
                        width: 3; height: 18; radius: 1.5; x: 0
                        anchors.verticalCenter: parent.verticalCenter
                        color: Theme.charge
                    }
                    Label {
                        x: 14; anchors.verticalCenter: parent.verticalCenter
                        text: modelData.title
                        font.weight: parent.on ? Font.DemiBold : Font.Normal
                        color: parent.on ? Theme.ink : Theme.inkSecondary
                    }
                    MouseArea {
                        id: navMouse
                        anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: root.page = modelData.id
                    }
                }
            }
        }
        Label {
            x: 20; anchors.bottom: parent.bottom; anchors.bottomMargin: 18
            width: parent.width - 40; wrapMode: Text.Wrap
            text: "바꾸면 바로 적용됩니다"
            color: Theme.inkTertiary; font.pixelSize: 11
        }
    }

    Flickable {
        id: scroller
        x: sidebar.width
        width: parent.width - sidebar.width
        height: parent.height
        contentHeight: content.height + 48
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: content
            x: 32; y: 26
            width: scroller.width - 64
            readonly property var current: root.pages.find(p => p.id === root.page) || root.pages[0]
            Label { text: content.current.title; font.pixelSize: 22; font.weight: Font.DemiBold }
            Label { text: content.current.hint; color: Theme.inkSecondary; font.pixelSize: 12; topPadding: 4 }
            Loader {
                width: parent.width
                sourceComponent: ({ screen: screenPage, modules: modulesPage, island: islandPage,
                                    airpods: airpodsPage, media: mediaPage, general: generalPage })[root.page] || screenPage
                onLoaded: scroller.contentY = 0
            }
        }
    }

    // ---- pages ---------------------------------------------------------------

    Component {
        id: screenPage
        Column {
            Section {
                title: "Dock 위치"
                ScreenMap {
                    mode: "dock"
                    onPicked: function(name) { dockPrefs.set("dock/screen", name) }
                }
                Item { width: 1; height: 8 }
                SettingRow {
                    label: "화면"
                    hint: "자동은 고른 가장자리 쪽 가장 바깥 모니터입니다. 지도에서 모니터를 눌러도 됩니다."
                    PrefChoice {
                        key: "dock/screen"
                        options: [{ value: "auto", label: "자동" }].concat(root.screens.map(s => ({ value: s.name, label: String(s.number) })))
                    }
                }
                SettingRow {
                    label: "가장자리"
                    PrefChoice { key: "dock/edge"; options: [{ value: "left", label: "왼쪽" }, { value: "right", label: "오른쪽" }] }
                }
                SettingRow {
                    label: "세로 위치"
                    hint: "dock 위에 마우스를 올리면 나오는 손잡이를 끌어 위아래로 옮깁니다."
                    GlassButton {
                        text: "가운데로"
                        enabled: Math.abs(root.pref("dock/position") - 0.5) > 0.005
                        onClicked: dockPrefs.set("dock/position", 0.5)
                    }
                }
                Rectangle {
                    visible: root.onSeam()
                    width: parent.width; height: seamText.implicitHeight + 20; radius: 10
                    color: "#26FFC861"; border.width: 1; border.color: "#66FFC861"
                    Label {
                        id: seamText
                        x: 12; y: 10; width: parent.width - 24; wrapMode: Text.Wrap
                        text: "이 가장자리는 다른 모니터와 맞닿아 있습니다. 마우스가 옆 화면으로 넘어갈 때 dock을 지나가게 됩니다."
                        color: Theme.warn; font.pixelSize: 12
                    }
                }
                SettingRow {
                    label: "화면 식별"
                    hint: "각 모니터에 지도와 같은 번호를 3초 동안 띄웁니다."
                    GlassButton { text: "화면 식별"; onClicked: dockActions.identifyScreens() }
                }
            }
            Section {
                title: "표시 방식"
                SettingRow {
                    label: "레일로 최소화"
                    hint: "카드를 아이콘 줄로 접습니다. 마우스를 올리면 이름이 펼쳐지고, 누르면 열립니다."
                    PrefToggle { key: "dock/minimized" }
                }
                SettingRow {
                    label: "항상 위에 표시"
                    hint: "끄면 dock은 창 뒤, 바탕화면에만 보입니다."
                    PrefToggle { key: "dock/alwaysOnTop" }
                }
            }
        }
    }

    Component {
        id: modulesPage
        Column {
            Section {
                title: "카드"
                Repeater {
                    model: dockPrefs.modules
                    SettingRow {
                        required property var modelData
                        required property int index
                        label: modelData.name
                        hint: modelData.id === "volume" || modelData.id === "output" ? "볼륨과 출력 장치가 이웃하면 한 줄에 나란히 놓입니다." : ""
                        Row {
                            spacing: 6
                            GlassButton {
                                text: "위로"; enabled: index > 0
                                onClicked: dockPrefs.moveModule(modelData.id, -1)
                            }
                            GlassButton {
                                text: "아래로"; enabled: index < dockPrefs.modules.length - 1
                                onClicked: dockPrefs.moveModule(modelData.id, 1)
                            }
                            Toggle {
                                anchors.verticalCenter: parent.verticalCenter
                                checked: modelData.visible
                                onToggled: function(value) { dockPrefs.setModuleVisible(modelData.id, value) }
                            }
                        }
                    }
                }
            }
            Section {
                title: "빠른 실행 앱"
                Repeater {
                    model: launcherBackend.apps
                    SettingRow {
                        required property var modelData
                        label: modelData.name
                        hint: modelData.path
                        GlassButton { text: "제거"; onClicked: launcherBackend.remove(modelData.index) }
                    }
                }
                SettingRow {
                    label: launcherBackend.apps.length ? "앱 추가" : "아직 앱이 없습니다"
                    hint: "실행 파일, 바로 가기, 폴더를 고르거나 빠른 실행 카드에 끌어다 놓으세요."
                    GlassButton { text: "앱 추가"; accent: true; onClicked: picker.open() }
                }
            }
        }
    }

    Component {
        id: islandPage
        Column {
            Section {
                title: "표시 화면"
                ScreenMap {
                    mode: "island"
                    onPicked: function(name) { dockPrefs.set("island/screens", name) }
                }
                Item { width: 1; height: 8 }
                SettingRow {
                    label: "화면"
                    hint: root.pref("island/screens") === "cursor" ? "알림이 올 때 마우스가 있는 모니터에 뜹니다."
                        : "지도에서 모니터를 누르면 그 화면에만 뜹니다."
                    PrefChoice {
                        key: "island/screens"
                        options: [{ value: "primary", label: "주 화면" }, { value: "dock", label: "dock 화면" },
                                  { value: "all", label: "모든 화면" }, { value: "cursor", label: "마우스 위치" }]
                    }
                }
                SettingRow {
                    label: "위치"
                    PrefChoice { key: "island/align"; options: [{ value: "left", label: "왼쪽" }, { value: "center", label: "가운데" }, { value: "right", label: "오른쪽" }] }
                }
                SettingRow {
                    label: "위쪽 여백"
                    PrefChoice { key: "island/offset"; options: [{ value: 0, label: "0" }, { value: 8, label: "8" }, { value: 16, label: "16" }, { value: 32, label: "32 px" }] }
                }
                SettingRow {
                    label: "미리 보기"
                    hint: "지금 설정대로 연결 알림을 띄웁니다."
                    GlassButton { text: "미리 보기"; onClicked: dockActions.previewIsland() }
                }
            }
            Section {
                title: "알릴 일"
                SettingRow { label: "AirPods 연결"; PrefToggle { key: "island/connect" } }
                SettingRow { label: "AirPods 연결 해제"; PrefToggle { key: "island/disconnect" } }
                SettingRow { label: "배터리 부족"; PrefToggle { key: "island/lowBattery" } }
                SettingRow {
                    label: "게임 중에는 숨기기"
                    hint: "League of Legends, VALORANT가 앞에 있을 때"
                    PrefToggle { key: "island/suppressDuringGames" }
                }
            }
        }
    }

    Component {
        id: airpodsPage
        Column {
            id: airpodsRoot
            readonly property bool real: typeof deviceBackend.selectDevice === "function"
            Section {
                title: "기기"
                Repeater {
                    model: airpodsRoot.real ? (deviceBackend.devices || []) : []
                    SettingRow {
                        id: deviceRow
                        required property var modelData
                        readonly property bool selected: modelData.id === deviceBackend.state.targetId
                        label: modelData.name || modelData.id
                        hint: (selected ? "사용 중 · " : "") + (modelData.connected ? "연결됨" : "연결 안 됨")
                        GlassButton {
                            text: deviceRow.selected ? "선택됨" : "선택"
                            selected: deviceRow.selected
                            enabled: !deviceRow.selected
                            onClicked: deviceBackend.selectDevice(modelData.id)
                        }
                    }
                }
                SettingRow {
                    visible: !airpodsRoot.real || !(deviceBackend.devices || []).length
                    label: deviceBackend.state.name || "AirPods"
                    hint: airpodsRoot.real ? "페어링된 블루투스 기기가 없습니다. Windows 설정에서 먼저 페어링하세요." : "샘플 데이터"
                }
            }
            Section {
                title: "배터리 읽기"
                visible: airpodsRoot.real
                SettingRow {
                    label: (deviceBackend.batterySources || []).length ? "직접 고른 출처" : "자동"
                    hint: (deviceBackend.batterySources || []).length
                        ? "아래에서 고른 신호만 씁니다."
                        : "등록한 AirPods가 연결된 동안 가까이 있는 AirPods 신호를 읽습니다. 근처에 다른 AirPods가 많으면 직접 고르세요."
                    GlassButton {
                        visible: (deviceBackend.batterySources || []).length > 0
                        text: "자동으로"
                        onClicked: deviceBackend.bindSources([])
                    }
                }
                Repeater {
                    model: airpodsRoot.real ? (deviceBackend.candidates || []) : []
                    SettingRow {
                        id: sourceRow
                        required property var modelData
                        readonly property bool bound: (deviceBackend.batterySources || []).indexOf(modelData.address) >= 0
                        label: modelData.name || "AirPods"
                        hint: modelData.address
                        Toggle {
                            checked: sourceRow.bound
                            onToggled: function(value) {
                                const list = (deviceBackend.batterySources || []).filter(a => a !== modelData.address)
                                if (value) list.push(modelData.address)
                                deviceBackend.bindSources(list)
                            }
                        }
                    }
                }
            }
            Section {
                title: "배터리 경고"
                SettingRow {
                    label: "기준"
                    hint: "이어폰이나 케이스가 이만큼 남으면 알립니다. 충전하거나 10%p 오르면 다시 알립니다."
                    PrefChoice { key: "battery/threshold"; options: [10, 15, 20, 30].map(v => ({ value: v, label: v + "%" })) }
                }
                SettingRow { label: "경고음"; hint: "assets\\low_power_warning.mp3가 있을 때만 소리가 납니다."; PrefToggle { key: "battery/sound" } }
                SettingRow {
                    label: "경고음 크기"
                    Row {
                        spacing: 8
                        PrefChoice { key: "battery/soundVolume"; options: [30, 60, 100].map(v => ({ value: v, label: v + "%" })) }
                        GlassButton { text: "듣기"; onClicked: dockActions.playAlert() }
                    }
                }
                SettingRow { label: "게임 중에도 경고음"; PrefToggle { key: "battery/soundDuringGames" } }
            }
            Section {
                title: "착용 시간"
                SettingRow {
                    label: "오늘 " + dockFeatures.todayUsage + " · 이번 " + dockFeatures.sessionUsage
                    hint: dockFeatures.remainingUsage.length ? "남은 시간 약 " + dockFeatures.remainingUsage : "AirPods를 끼면 기록됩니다."
                }
            }
        }
    }

    Component {
        id: mediaPage
        Column {
            Section {
                title: "따라갈 미디어"
                SettingRow {
                    label: "재생 중인 아무 앱이나 따라가기"
                    hint: "끄면 예전 glass 위젯에서 고른 앱 하나만 따라갑니다."
                    PrefToggle { key: "media/followAny" }
                }
            }
            Section {
                title: "착용 감지"
                SettingRow { label: "귀에서 빼면 일시정지"; hint: "양쪽 다 뺐을 때"; PrefToggle { key: "media/autoPause" } }
                SettingRow { label: "다시 끼면 재생"; hint: "착용 감지로 멈췄던 것만 다시 재생합니다."; PrefToggle { key: "media/autoResume" } }
            }
        }
    }

    Component {
        id: generalPage
        Column {
            Section {
                title: "시작"
                SettingRow { label: "Windows 시작 시 실행"; PrefToggle { key: "system/startWithWindows" } }
            }
            Section {
                title: "앱"
                SettingRow {
                    label: "Glass Dock 종료"
                    hint: "트레이 아이콘을 눌러 설정을 다시 열 수 있습니다."
                    GlassButton { text: "종료"; onClicked: dockActions.quit() }
                }
            }
        }
    }

    FileDialog {
        id: picker
        title: "빠른 실행에 추가"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["프로그램 및 바로 가기 (*.exe *.lnk *.url *.bat)", "모든 파일 (*)"]
        onAccepted: launcherBackend.addUrls(selectedFiles)
    }
}
