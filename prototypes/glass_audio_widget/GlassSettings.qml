import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Window

Window {
    id: settings
    objectName: "glassSettings"
    width: 416; height: 552; minimumWidth: 300; minimumHeight: 400
    flags: Qt.Dialog; title: "Glass Audio · 설정"; color: "#1D1D1D"
    property var allowed: []
    property string targetApp: ""
    property string targetSession: ""
    property string feedback: ""
    property var sourceDraft: []
    function openSettings(section) {
        allowed=mediaBackend.preferences.allowed.slice()
        targetApp=mediaBackend.preferences.sourceId
        targetSession=mediaBackend.state.token || ""
        if (section!==undefined) tabs.currentIndex=section
        sourceDraft=deviceBackend.batterySources.slice()
        devices.syncSaved()
        feedback=""
        widgetHost.positionSettings(settings)
        show(); raise(); requestActivate()
    }
    onVisibleChanged: mediaBackend.inspectSessions(visible)
    Control {
        anchors.fill: parent; anchors.margins: 16
        font.family: previewFont; font.pixelSize: 12
        palette.windowText: "#EEEEEE"; palette.buttonText: "#EEEEEE"; palette.text: "#EEEEEE"
        palette.button: "#343434"; palette.base: "#262626"; palette.highlight: "#777777"
        TabBar {
            id: tabs; objectName: "settingsTabs"; width: parent.width; height: 38
            TabButton { text: "미디어" }
            TabButton { text: "장치 · 배터리" }
            TabButton { text: "모양" }
            TabButton { text: "진단" }
        }
        Item {
            y: 50; width: parent.width; height: parent.height-140
            visible: tabs.currentIndex===0
            Text {
                width: parent.width; height: 48; wrapMode: Text.Wrap
                objectName: "mediaDetectionStatus"
                text: "감지된 앱 "+mediaBackend.apps.filter(app=>app.present).length+"개 · 허용 앱 "+settings.allowed.length+"개\n앱을 허용하고 조작할 대상을 선택하세요."
                font.family: previewFont; font.pixelSize: 12; color: "#B8B8B8"
            }
            ListView {
                id: apps; objectName: "glassMediaApps"
                y: 48; width: parent.width; height: 144; clip: true
                model: mediaBackend.apps; ScrollBar.vertical: ScrollBar {}
                delegate: Item {
                    required property var modelData
                    width: apps.width-12; height: 44
                    CheckBox {
                        id: allowCheck; width: parent.width-80; height: 44
                        checked: settings.allowed.indexOf(modelData.id)>=0
                        text: modelData.name+(modelData.present ? "" : " · 미감지")
                        contentItem: Text {
                            leftPadding: 34; text: allowCheck.text; elide: Text.ElideRight
                            color: "#EEEEEE"; font: allowCheck.font; verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            const list=settings.allowed.slice(), at=list.indexOf(modelData.id)
                            if (checked && at<0) list.push(modelData.id)
                            if (!checked && at>=0) list.splice(at,1)
                            settings.allowed=list
                            if (!checked && settings.targetApp===modelData.id) { settings.targetApp="";settings.targetSession="" }
                        }
                    }
                    RadioButton {
                        x: parent.width-80; width: 80; height: 44; text: "대상"
                        checked: settings.targetApp===modelData.id
                        enabled: settings.allowed.indexOf(modelData.id)>=0
                        onClicked: { settings.targetApp=modelData.id;settings.targetSession="" }
                    }
                }
                Text {
                    anchors.centerIn: parent; visible: apps.count===0
                    text: "Windows 미디어 세션 없음\n앱에서 재생한 뒤 확인하세요"; color: "#BDBDBD"; font.family: previewFont; font.pixelSize: 12
                }
            }
            Text {
                y: 208; text: "같은 앱의 재생 대상"; color: "#D0D0D0"
                font.family: previewFont; font.pixelSize: 12
            }
            ListView {
                id: sessions; objectName: "glassMediaSessions"
                y: 238; width: parent.width; height: 128; clip: true
                model: mediaBackend.sessions.filter(session=>session.sourceId===settings.targetApp)
                ScrollBar.vertical: ScrollBar {}
                delegate: RadioButton {
                    required property var modelData
                    width: sessions.width-12; height: 40
                    text: modelData.title || modelData.name
                    checked: settings.targetSession===modelData.token
                    onClicked: settings.targetSession=modelData.token
                }
                Text {
                    anchors.centerIn: parent; visible: sessions.count===0
                    text: "허용 설정을 저장하면 선택 가능한 대상이 표시됨"
                    color: "#AFAFAF"; font.family: previewFont; font.pixelSize: 10
                }
            }
        }
        Flickable {
            y: 50; width: parent.width; height: parent.height-140
            visible: tabs.currentIndex===1; clip: true; contentWidth: width; contentHeight: 430
            ScrollBar.vertical: ScrollBar {}
            Text {
                width: parent.width; height: 22; text: "재부팅 후에도 사용할 등록 장치"
                color: "#EEEEEE"; font.family: previewFont; font.pixelSize: 13
            }
            ComboBox {
                id: devices; objectName: "pairedDeviceChoice"; y: 30; width: parent.width; height: 36
                model: deviceBackend.devices; textRole: "name"; valueRole: "id"
                enabled: !deviceBackend.state.pending
                function syncSaved() {
                    const saved=deviceBackend.state.targetId
                    currentIndex=saved ? deviceBackend.devices.findIndex(item=>item.id===saved) : (count ? 0 : -1)
                }
                displayText: currentIndex<0 ? "저장된 장치 미감지 · 목록에서 선택" : currentText
                Component.onCompleted: syncSaved()
            }
            Connections { target: deviceBackend; function onDevicesChanged() { Qt.callLater(devices.syncSaved) } }
            Button {
                objectName: "savePairedDevice"; y: 74; width: 112; height: 34; text: "이 장치 저장"
                enabled: devices.currentIndex>=0 && !deviceBackend.state.pending
                onClicked: {
                    settings.feedback=deviceBackend.selectDevice(devices.currentValue) ? "연결 대상 저장됨" : "장치 저장 실패"
                    settings.sourceDraft=deviceBackend.batterySources.slice()
                }
            }
            Button {
                y: 74; x: 122; width: 104; height: 34; text: "연결"
                enabled: deviceBackend.state.paired && !deviceBackend.state.pending && !deviceBackend.state.connected
                onClicked: deviceBackend.connectDevice()
            }
            Text {
                y: 116; width: parent.width; height: 24; elide: Text.ElideRight
                text: (deviceBackend.state.name || "—")+" · "+deviceBackend.state.status
                color: "#B8B8B8"; font.family: previewFont; font.pixelSize: 11
            }
            Text {
                y: 150; width: parent.width; height: 70; wrapMode: Text.Wrap
                text: "배터리 광고 출처를 직접 지정하세요(최대 2개).\n다른 에어팟과 혼동하지 않도록 본인 장치인지 확인하세요.\n주소가 바뀌면 다시 지정해야 함."
                color: "#B8B8B8"; font.family: previewFont; font.pixelSize: 11
            }
            ListView {
                id: sources; objectName: "batterySourceChoices"; y: 224; width: parent.width; height: 148
                model: deviceBackend.candidates; clip: true; ScrollBar.vertical: ScrollBar {}
                delegate: CheckBox {
                    id: sourceChoice; required property var modelData
                    width: sources.width-12; height: 40
                    text: modelData.name+" · "+modelData.address
                    checked: settings.sourceDraft.indexOf(modelData.address)>=0
                    contentItem: Text {
                        leftPadding: 34; text: sourceChoice.text; elide: Text.ElideRight
                        color: "#EEEEEE"; font: sourceChoice.font; verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: {
                        const list=settings.sourceDraft.slice(), at=list.indexOf(modelData.address)
                        if (checked && at<0) list.push(modelData.address)
                        if (!checked && at>=0) list.splice(at,1)
                        settings.sourceDraft=list
                    }
                }
                Text {
                    anchors.centerIn: parent; visible: sources.count===0
                    text: "케이스를 열고 광고 수신을 기다리세요"; color: "#B8B8B8"; font.family: previewFont; font.pixelSize: 11
                }
            }
            Button {
                objectName: "saveBatterySources"; y: 384; width: 136; height: 34; text: "배터리 출처 저장"
                onClicked: settings.feedback=deviceBackend.bindSources(settings.sourceDraft) ? "배터리 출처 저장됨" : "출처를 다시 선택하세요"
            }
            Button {
                y: 384; x: 146; width: 80; height: 34; text: "초기화"
                onClicked: { if (deviceBackend.bindSources([])) settings.sourceDraft=[] }
            }
        }
        Item {
            y: 50; width: parent.width; height: parent.height-140
            visible: tabs.currentIndex===2
            CheckBox {
                objectName: "reduceMotion"; width: parent.width; height: 36
                text: "모션 줄이기"; checked: widgetPreferences.reducedMotion
                onClicked: widgetPreferences.setReducedMotion(checked)
            }
            Text {
                y: 62; width: parent.width; height: 20; text: "유리 색 농도 · 글자 투명도는 유지"
                color: "#B8B8B8"; font.family: previewFont; font.pixelSize: 12
            }
            Slider {
                objectName: "glassTintSlider"; y: 90; width: parent.width; height: 36
                from: .05; to: .45; stepSize: .01; value: widgetPreferences.tint
                onMoved: widgetPreferences.setTint(value)
                Accessible.name: "유리 색 농도"
            }
            Text { y: 148; text: "글자 뒤 명암"; color: "#CFCFCF"; font.family: previewFont; font.pixelSize: 12 }
            Slider {
                objectName: "glassReadabilitySlider"; y: 174; width: parent.width; height: 36
                from: .45; to: .8; stepSize: .01; value: widgetPreferences.readability
                onMoved: widgetPreferences.setReadability(value)
                Accessible.name: "글자 뒤 명암"
            }
            Text { y: 236; text: "배경 흐림"; color: "#CFCFCF"; font.family: previewFont; font.pixelSize: 12 }
            Slider {
                objectName: "glassBlurSlider"; y: 262; width: parent.width; height: 36
                from: 0; to: 8; stepSize: .5; value: widgetPreferences.blur
                onMoved: widgetPreferences.setBlur(value)
                Accessible.name: "글자 뒤 배경 흐림"
            }
        }
        Item {
            y: 50; width: parent.width; height: parent.height-140; visible: tabs.currentIndex===3
            Text {
                width: parent.width; height: 112; wrapMode: Text.Wrap
                text: "실제 바탕화면 캡처 · "+(desktopCapture.paused ? "HOLD" : "LIVE")+"\n프레임 "+desktopCapture.frame+"\n"+(desktopCapture.error || "캡처 오류 없음")
                color: "#CFCFCF"; font.family: previewFont; font.pixelSize: 12
            }
            Button {
                objectName: "glassCaptureMode"; y: 124; width: parent.width; height: 40
                text: desktopCapture.paused ? "LIVE로 전환" : "HOLD로 전환"
                onClicked: desktopCapture.togglePause()
            }
            Text {
                y: 184; width: parent.width; wrapMode: Text.Wrap
                text: "LIVE는 원격 화면에 위젯이 보이지 않을 수 있음.\n굴절 비교 R · 캡처 전환 F8"
                color: "#AFAFAF"; font.family: previewFont; font.pixelSize: 11
            }
        }
        Text {
            y: parent.height-80; width: parent.width; height: 38; wrapMode: Text.Wrap
            text: settings.feedback || widgetPreferences.error || deviceBackend.state.error || mediaBackend.state.error || mediaBackend.state.status
            color: "#B8B8B8"; font.family: previewFont; font.pixelSize: 11
        }
        Row {
            anchors.right: parent.right; anchors.bottom: parent.bottom; spacing: 8
            Button { text: "닫기"; width: 80; height: 36; onClicked: settings.close() }
            Button {
                objectName: "glassSaveMedia"; text: "미디어 저장"; width: 112; height: 36
                visible: tabs.currentIndex===0
                onClicked: settings.feedback=mediaBackend.saveSelection(settings.allowed,settings.targetApp,settings.targetSession) ? "저장됨" : "저장 실패"
            }
        }
    }
}
