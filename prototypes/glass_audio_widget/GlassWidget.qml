import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Window

Item {
    id: root
    objectName: "glassAudioWidget"
    width: 440; height: 360
    readonly property real expandedHeight: 360
    readonly property real bodyX: 0
    readonly property real bodyWidth: 440
    property real bodyHeight: initialCompact ? 76 : 360
    property bool compactMode: initialCompact
    property bool showingCompact: initialCompact
    property bool transitioning: false
    property bool outputRequested: false
    onBodyHeightChanged: {
        if (ready && transitioning) widgetHost.fitTransitionHeight(bodyHeight)
    }
    onTransitioningChanged: {
        if (!transitioning && outputRequested) {
            outputRequested=false
            if (!compactMode && root.Window.window.visible
                    && root.Window.window.visibility!==Window.Minimized) outputs.open()
        }
    }
    property real contentOpacity: 1
    property bool ready: false
    property bool editing: false
    property bool refractionEnabled: true
    property var layoutOrder: ["media","volume","battery"]
    property var pendingOrder: layoutOrder
    property real moduleOpacity: 1
    readonly property bool batteryFirst: layoutOrder[0]==="battery"
    readonly property bool volumeFirst: layoutOrder.indexOf("volume")<layoutOrder.indexOf("media")
    readonly property real mainY: batteryFirst ? 144 : 88
    property var shownMedia: ({available:false,title:"",artist:"",sourceName:"",artwork:"",token:"",identity:""})
    property var pendingMedia: shownMedia
    property real metadataOpacity: 1
    readonly property var audio: outputBackend.state
    readonly property string deviceName: audio.name || "—"
    property string shownDeviceName: "—"
    property string pendingDeviceName: "—"
    property real deviceNameOpacity: 1
    readonly property var media: mediaBackend.state
    readonly property bool audioReady: audio.available && !audio.pendingId && !editing
    readonly property bool mediaReady: media.available && !media.pending && !metadataMotion.running && !editing
    readonly property bool reduced: widgetPreferences.reducedMotion
    readonly property string problem: desktopCapture.error || deviceBackend.state.error || widgetPreferences.error || audio.error || media.error || widgetHost.windowPreferenceError
    onDeviceNameChanged: {
        if (!ready || root.reduced) { shownDeviceName=deviceName; return }
        nameMotion.stop(); pendingDeviceName=deviceName; nameMotion.start()
    }
    Component.onCompleted: {
        shownMedia=mediaBackend.content; pendingMedia=shownMedia
        shownDeviceName=deviceName; pendingDeviceName=deviceName
        layoutOrder=widgetPreferences.order
        ready=true
    }
    onReducedChanged: {
        if (reduced) {
            layoutMotion.stop(); layoutOrder=pendingOrder; moduleOpacity=1
            metadataMotion.stop(); shownMedia=mediaBackend.content; metadataOpacity=1
            nameMotion.stop(); shownDeviceName=deviceName; deviceNameOpacity=1
            if (transitioning) settleHiddenTransition()
        }
    }

    GlassSettings { id: settings; transientParent: root.Window.window }
    ConnectionNotice { id: notice }
    function offerConnection() { notice.offer() }
    function openMediaSettings() { outputs.close(); settings.openSettings(0) }
    function toggleMode() {
        outputRequested=false
        editing=false
        outputs.close()
        fold.stop()
        compactMode=!compactMode
        transitioning=true
        widgetHost.prepareTransition()
        fold.start()
    }
    function dropModule(source,px,py) {
        if (!ready || !editing || layoutMotion.running) return
        const modules=[mediaModule,volumeModule,batteryModule]
        let best=null, distance=Infinity
        for (const module of modules) {
            if (module.moduleId===source) continue
            const dx=px-(module.x+module.width/2), dy=py-(module.y+module.height/2)
            const next=Math.hypot(dx,dy)
            if (next<distance) { best=module; distance=next }
        }
        if (best && distance<130) widgetPreferences.moveModule(source,best.moduleId)
    }
    function settleHiddenTransition() {
        fold.stop(); showingCompact=compactMode
        bodyHeight=compactMode ? 76 : expandedHeight
        contentOpacity=1; transitioning=false
        widgetHost.finishTransition(compactMode)
    }
    Keys.onPressed: function(event) {
        if (event.key===Qt.Key_F8) { desktopCapture.togglePause(); event.accepted=true }
        if (event.key===Qt.Key_R) { root.refractionEnabled=!root.refractionEnabled; event.accepted=true }
    }

    Image {
        id: desktop; visible: false; anchors.fill: parent
        cache: false; asynchronous: false
        source: "image://desktop/"+desktopCapture.frame
    }
    ShaderEffect {
        id: glass; objectName: "widgetGlassShader"
        anchors.fill: parent
        visible: !desktopCapture.error && desktopCapture.frame>0 && !desktopCapture.moving && !root.transitioning && status!==ShaderEffect.Error
        property var backdrop: desktop
        property vector2d resolution: Qt.vector2d(width,height)
        property vector2d surfaceSize: Qt.vector2d(root.bodyWidth,root.bodyHeight)
        property vector2d sourceSize: Qt.vector2d(desktopCapture.sourceSize.width,desktopCapture.sourceSize.height)
        property real refraction: root.refractionEnabled ? 1 : 0
        property real tint: widgetPreferences.tint
        fragmentShader: Qt.resolvedUrl("widget.frag.qsb")
    }
    Rectangle {
        width: root.bodyWidth; height: root.bodyHeight; radius: 28
        visible: !glass.visible
        color: "#2E2E2E"; border.color: "#668F8F8F"; border.width: 1
    }
    MouseArea {
        x: 20; y: 16; width: 314; height: 44
        enabled: !root.transitioning
        onPressed: widgetHost.beginMove()
    }
    Item {
        id: expanded; objectName: "glassExpanded"
        width: 440; height: 360
        visible: !root.showingCompact
        opacity: root.showingCompact ? 0 : root.contentOpacity
        enabled: !root.transitioning
        ReadabilityPlate {
            objectName: "headerPlate"; x: 20; y: 18; width: 314; height: 40; corner: 14
            backdrop: desktop; sourceSize: glass.sourceSize; origin: Qt.vector2d(x,y)
        }
        ReadabilityPlate {
            x: 340; y: 18; width: 88; height: 40; corner: 18
            backdrop: desktop; sourceSize: glass.sourceSize; origin: Qt.vector2d(x,y)
        }
        Text {
            objectName: "glassDeviceName"; x: 24; y: 22; width: 300; height: 32
            text: root.shownDeviceName; opacity: root.deviceNameOpacity
            elide: Text.ElideRight; color: "#F0F0F0"
            font.family: previewFont; font.pixelSize: 15; font.weight: Font.DemiBold
            verticalAlignment: Text.AlignVCenter
        }
        ModuleFrame {
            id: mediaModule; objectName: "mediaModule"; moduleId: "media"; canvas: root
            x: root.volumeFirst ? 160 : 24; y: root.mainY; width: 256; height: 152
            editing: root.editing && !layoutMotion.running; opacity: root.moduleOpacity
            onDropped: function(source,px,py) { root.dropModule(source,px,py) }
        ReadabilityPlate {
            objectName: "mediaPlate"; anchors.fill: parent
            backdrop: desktop; sourceSize: glass.sourceSize
            origin: Qt.vector2d(mediaModule.x+mediaModule.visualTranslation.x,mediaModule.y+mediaModule.visualTranslation.y)
        }
        Item {
            x: 12; y: 16; width: 76; height: 76
            opacity: root.metadataOpacity
            Rectangle { anchors.fill: parent; radius: 12; color: "#18202020"; border.color: "#1AFFFFFF" }
            Image {
                anchors.fill: parent; anchors.margins: 1
                source: root.shownMedia.artwork || ""; fillMode: Image.PreserveAspectCrop; clip: true
            }
            Image {
                anchors.centerIn: parent; width: 30; height: 30; sourceSize.width: 60; sourceSize.height: 60
                visible: !root.shownMedia.artwork
                source: "image://lucian/music?color=%23B8B8B8"
            }
        }
        Text {
            objectName: "glassTrackTitle"; x: 104; y: 18; width: 140; height: 36
            text: root.shownMedia.available ? root.shownMedia.title || "—" : "—"
            visible: root.shownMedia.available
            color: "#F0F0F0"; font.family: previewFont; font.pixelSize: 14
            wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
            opacity: root.metadataOpacity
        }
        Text {
            x: 104; y: 60; width: 140; height: 18
            text: root.shownMedia.available ? root.shownMedia.artist || root.shownMedia.sourceName : "미디어 설정에서 대상 선택"
            color: "#E4E4E4"; font.family: previewFont; font.pixelSize: 10
            visible: root.shownMedia.available
            elide: Text.ElideRight; opacity: root.metadataOpacity
        }
        GlassButton {
            objectName: "glassChooseMedia"; x: 104; y: 16; width: 140; height: 68
            text: "미디어 찾기"; pill: true; visible: !root.shownMedia.available
            description: "감지된 미디어 앱 선택"; reduced: root.reduced
            onClicked: root.openMediaSettings()
        }
        GlassButton {
            objectName: "glassPrevious"; x: 50; y: 104; glyph: "next"; flipIcon: true
            enabled: root.mediaReady && root.media.canPrevious; description: "이전 곡"; reduced: root.reduced
            onClicked: mediaBackend.command("previous",root.shownMedia.token,root.shownMedia.identity)
        }
        GlassButton {
            objectName: "glassPlay"; x: 106; y: 100; width: 44; height: 44
            glyph: "play"; pose: root.media.playing ? "playing" : "paused"
            selected: root.mediaReady && root.media.playing
            enabled: root.mediaReady && root.media.canPlay
            description: root.media.playing ? "일시 정지" : "재생"; reduced: root.reduced
            onClicked: mediaBackend.command("toggle",root.shownMedia.token,root.shownMedia.identity)
        }
        GlassButton {
            objectName: "glassNext"; x: 170; y: 104; glyph: "next"
            enabled: root.mediaReady && root.media.canNext; description: "다음 곡"; reduced: root.reduced
            onClicked: mediaBackend.command("next",root.shownMedia.token,root.shownMedia.identity)
        }
        }
        ModuleFrame {
            id: volumeModule; objectName: "volumeModule"; moduleId: "volume"; canvas: root
            x: root.volumeFirst ? 24 : 296; y: root.mainY; width: 120; height: 152
            editing: root.editing && !layoutMotion.running; opacity: root.moduleOpacity
            onDropped: function(source,px,py) { root.dropModule(source,px,py) }
        ReadabilityPlate {
            objectName: "volumePlate"; anchors.fill: parent
            backdrop: desktop; sourceSize: glass.sourceSize
            origin: Qt.vector2d(volumeModule.x+volumeModule.visualTranslation.x,volumeModule.y+volumeModule.visualTranslation.y)
        }
        GlassDial {
            x: 16; y: 18; width: 88; height: 88; value: root.audio.volume
            reduced: root.reduced
            enabled: root.audioReady; valueAvailable: root.audio.available; muted: root.audio.muted
            onEdited: function(requested) { outputBackend.setVolume(requested) }
        }
        GlassButton {
            objectName: "glassMute"; x: 72; y: 108; width: 36; height: 36; glyph: "speaker"
            pose: root.audio.muted ? "muted" : "on"; selected: root.audio.muted
            enabled: root.audioReady; reduced: root.reduced
            description: root.audio.muted ? "음소거 해제" : "음소거"
            onClicked: outputBackend.toggleMute()
        }
        Text {
            x: 12; y: 116; width: 56; height: 20; text: "음소거"
            color: "#E4E4E4"
            font.family: previewFont; font.pixelSize: 10; verticalAlignment: Text.AlignVCenter
        }
        }
        ModuleFrame {
            id: batteryModule; objectName: "batteryModule"; moduleId: "battery"; canvas: root
            x: 24; y: root.batteryFirst ? 88 : 248; width: 392; height: 40
            editing: root.editing && !layoutMotion.running; opacity: root.moduleOpacity
            onDropped: function(source,px,py) { root.dropModule(source,px,py) }
        ReadabilityPlate {
            objectName: "batteryPlate"; anchors.fill: parent; anchors.margins: -4; corner: 14
            backdrop: desktop; sourceSize: glass.sourceSize
            origin: Qt.vector2d(batteryModule.x-4+batteryModule.visualTranslation.x,batteryModule.y-4+batteryModule.visualTranslation.y)
        }
        Row {
            objectName: "glassBatteryRow"; spacing: 16
            Repeater {
                model: 3
                Item {
                    required property int index
                    readonly property var modelData: deviceBackend.batteries[index]
                    width: 120; height: 36
                    opacity: modelData.quality==="cached" ? .5 : 1
                    Behavior on opacity { NumberAnimation { duration: root.reduced ? 0 : 120 } }
                    Text {
                        x: 0; y: 0; width: 52; height: 16; text: modelData.label
                        font.family: previewFont; font.pixelSize: 10; color: "#E4E4E4"
                    }
                    Image {
                        x: 34; y: 1; width: 9; height: 13; sourceSize.width: 18; sourceSize.height: 26
                        source: "image://lucian/battery?bolt=1&color=%23C7A9A3"
                        opacity: modelData.charging ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: root.reduced ? 0 : 100 } }
                    }
                    Text {
                        id: batteryValue
                        objectName: "batteryValue"+modelData.label
                        property bool valueReady: false
                        readonly property string desired: modelData.value<0 ? "—" : modelData.value+"%"
                        property string displayed: "—"
                        property string pending: desired
                        Component.onCompleted: { displayed=desired; valueReady=true }
                        onDesiredChanged: {
                            metricMotion.stop()
                            if (!valueReady || root.reduced) { displayed=desired; opacity=1 }
                            else { pending=desired; metricMotion.start() }
                        }
                        x: 68; y: 0; width: 52; height: 16; text: displayed
                        horizontalAlignment: Text.AlignRight
                        font.family: previewFont; font.pixelSize: 13; color: "#F0F0F0"
                        SequentialAnimation {
                            id: metricMotion
                            NumberAnimation { target: batteryValue; property: "opacity"; to: 0; duration: 50 }
                            ScriptAction { script: batteryValue.displayed=batteryValue.pending }
                            NumberAnimation { target: batteryValue; property: "opacity"; to: 1; duration: 80 }
                        }
                        Connections {
                            target: widgetPreferences
                            function onChanged() {
                                if (root.reduced) { metricMotion.stop(); batteryValue.displayed=batteryValue.desired; batteryValue.opacity=1 }
                            }
                        }
                    }
                    Rectangle {
                        x: 0; y: 25; width: 120; height: 3; radius: 1.5; color: "#777777"
                        Rectangle {
                            objectName: "batteryFill"+modelData.label
                            width: parent.width*Math.max(0,modelData.value)/100; height: 3; radius: 1.5
                            color: modelData.charging ? "#C7A9A3" : "#B8B8B8"
                            Behavior on width { NumberAnimation { duration: root.reduced ? 0 : 180; easing.type: Easing.OutCubic } }
                        }
                    }
                    Accessible.name: modelData.label+" "+(modelData.value<0 ? "—" : modelData.value+"%")
                    Accessible.description: modelData.quality==="cached" ? "마지막 수신 값 · 현재 값 확인 중" : modelData.quality==="unknown" ? "선택한 배터리 출처의 새 데이터 없음" : "선택한 출처의 최신 배터리 값"
                }
            }
        }
        }
        ReadabilityPlate {
            x: 20; y: 298; width: 292; height: 48; corner: 16
            backdrop: desktop; sourceSize: glass.sourceSize; origin: Qt.vector2d(x,y)
        }
        ReadabilityPlate {
            x: 324; y: 298; width: 96; height: 48; corner: 16
            backdrop: desktop; sourceSize: glass.sourceSize; origin: Qt.vector2d(x,y)
        }
        GlassButton {
            id: outputButton; objectName: "glassOutput"; x: 24; y: 304; width: 172
            glyph: "output"; text: root.audio.name || "출력 장치"; pill: true; dropdown: true
            busy: !!root.audio.pendingId
            enabled: !root.audio.pendingId
            description: root.audio.name || "출력 장치 선택"; reduced: root.reduced
            onClicked: outputs.open()
        }
        GlassButton {
            objectName: "glassConnect"; x: 204; y: 304; width: 104; glyph: "bluetooth"; pill: true
            text: deviceBackend.state.pending ? "연결 중" : deviceBackend.state.connected ? "연결됨" : deviceBackend.state.error ? "재시도" : "연결"
            selected: deviceBackend.state.connected; busy: deviceBackend.state.pending
            enabled: deviceBackend.state.paired && !deviceBackend.state.pending && !deviceBackend.state.connected
            description: (deviceBackend.state.name || "설정에서 등록 장치 선택")+" · "+deviceBackend.state.status
            reduced: root.reduced; onClicked: deviceBackend.connectDevice()
            Rectangle {
                x: parent.width-8; y: 3; width: 5; height: 5; radius: 2.5
                color: deviceBackend.state.connected ? "#8EB69B" : deviceBackend.state.paired ? "#C7A9A3" : "#4A5C6A"
            }
        }
        GlassButton {
            objectName: "glassEditModules"; x: 328; y: 304; glyph: "grid"
            selected: root.editing; description: root.editing ? "배치 편집 종료" : "모듈 배치 편집"
            reduced: root.reduced; onClicked: root.editing=!root.editing
        }
        GlassButton {
            objectName: "glassSettingsButton"; x: 380; y: 304; glyph: "sliders"
            description: "위젯 설정"; reduced: root.reduced; onClicked: settings.openSettings()
        }
    }
    Item {
        objectName: "glassCompact"; width: 440; height: 76
        visible: root.showingCompact; opacity: root.showingCompact ? root.contentOpacity : 0
        enabled: !root.transitioning
        ReadabilityPlate {
            x: 12; y: 14; width: 416; height: 48; corner: 20
            backdrop: desktop; sourceSize: glass.sourceSize; origin: Qt.vector2d(x,y)
        }
        GlassButton {
            objectName: "glassCompactMute"; x: 20; y: 20; glyph: "speaker"
            pose: root.audio.muted ? "muted" : "on"; selected: root.audio.muted
            enabled: root.audioReady; reduced: root.reduced
            description: root.audio.muted ? "음소거 해제" : "음소거"
            onClicked: outputBackend.toggleMute()
        }
        GlassButton {
            objectName: "glassCompactOutput"; x: 64; y: 22; width: 32; height: 32
            glyph: "output"
            description: "출력 선택 · 펼쳐서 표시"; reduced: root.reduced
            enabled: !root.audio.pendingId
            onClicked: {
                root.toggleMode()
                if (root.transitioning) root.outputRequested=true
                else outputs.open()
            }
        }
        GlassButton {
            objectName: "glassCompactConnect"; x: 104; y: 22; width: 32; height: 32; glyph: "bluetooth"
            selected: deviceBackend.state.connected; busy: deviceBackend.state.pending
            enabled: deviceBackend.state.paired && !deviceBackend.state.pending && !deviceBackend.state.connected
            description: "저장한 에어팟 연결"; reduced: root.reduced; onClicked: deviceBackend.connectDevice()
        }
        Slider {
            id: compactVolume; objectName: "glassCompactVolume"
            property bool auditControl: true
            x: 148; y: 22; width: 184; height: 32; from: 0; to: 100; stepSize: 1
            snapMode: Slider.SnapAlways; live: true; padding: 0
            value: root.audio.volume; enabled: root.audioReady; focusPolicy: Qt.StrongFocus
            Accessible.name: "출력 음량"
            onMoved: outputBackend.setVolume(Math.round(value))
            background: Rectangle {
                x: 6; y: 14; width: compactVolume.width-12; height: 4; radius: 2; color: "#777777"
                Rectangle { width: parent.width*compactVolume.visualPosition; height: 4; radius: 2; color: "#CCCCCC" }
            }
            handle: Rectangle {
                x: compactVolume.visualPosition*(compactVolume.width-12); y: 10
                width: 12; height: 12; radius: 6; color: "#E8E8E8"
                border.color: compactVolume.activeFocus ? "#B8B8B8" : "#202020"
                border.width: 1
            }
        }
        Text {
            objectName: "glassCompactValue"; x: 340; y: 22; width: 34; height: 32
            text: root.audio.available ? root.audio.volume : "—"
            color: root.audio.muted ? "#C7A9A3" : "#E8E8E8"
            font.family: previewFont; font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
    }
    GlassButton {
        objectName: "glassPin"; x: 348; y: 22; glyph: "pin"
        visible: !root.showingCompact
        enabled: !root.transitioning
        selected: widgetHost.alwaysOnTop; description: "항상 위에 표시 전환"; reduced: root.reduced
        onClicked: widgetHost.setAlwaysOnTop(!widgetHost.alwaysOnTop)
    }
    GlassButton {
        objectName: "glassFold"; x: 392; y: 22; width: 32; height: 32
        glyph: "chevron"; glyphRotation: root.compactMode ? 180 : 0
        description: root.compactMode ? "펼치기" : "접기"; reduced: root.reduced
        onClicked: root.toggleMode()
        Behavior on glyphRotation { NumberAnimation { duration: root.reduced ? 0 : 150 } }
    }
    Text {
        x: 24; y: 62; width: 390; height: 18
        visible: !root.showingCompact && root.problem.length>0
        text: root.problem; elide: Text.ElideRight
        color: "#C7A9A3"; font.family: previewFont; font.pixelSize: 10
    }
    Popup {
        id: outputs; objectName: "glassOutputPopup"
        x: 24; y: 78; width: 392; height: 220; padding: 12
        popupType: Popup.Item; modal: true; focus: true
        background: Rectangle { color: "#F0242424"; radius: 18; border.color: "#777777" }
        ListView {
            anchors.fill: parent; clip: true; model: outputBackend.devices
            delegate: ItemDelegate {
                id: outputItem
                required property var modelData
                objectName: "glassOutput-"+modelData.id
                width: 366; height: 42
                text: modelData.name
                enabled: modelData.available && !root.audio.pendingId
                highlighted: modelData.id===root.audio.currentId
                palette.text: "#E8E8E8"; palette.highlight: "#5C5C5C"; palette.highlightedText: "#F0F0F0"
                contentItem: Item {
                    Image {
                        y: (parent.height-20)/2; width: 20; height: 20; sourceSize.width: 40; sourceSize.height: 40
                        source: "image://lucian/"+(modelData.kind==="speaker" ? "speaker" : "headphones")+"?color=%23E8E8E8"
                    }
                    Text {
                        anchors.fill: parent; leftPadding: 30
                        text: outputItem.text; elide: Text.ElideRight
                        color: "#E8E8E8"; font.family: previewFont; font.pixelSize: 12
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                onClicked: { outputBackend.selectOutput(modelData.id); outputs.close() }
            }
        }
    }
    Connections {
        target: widgetPreferences
        function onChanged() {
            if (JSON.stringify(root.layoutOrder)!==JSON.stringify(widgetPreferences.order)) {
                root.pendingOrder=widgetPreferences.order
                if (root.reduced) root.layoutOrder=root.pendingOrder
                else { layoutMotion.stop(); layoutMotion.start() }
            }
        }
    }
    SequentialAnimation {
        id: layoutMotion
        NumberAnimation { target: root; property: "moduleOpacity"; to: 0; duration: 60 }
        ScriptAction { script: root.layoutOrder=root.pendingOrder }
        NumberAnimation { target: root; property: "moduleOpacity"; to: 1; duration: 100 }
    }
    Connections {
        target: mediaBackend
        function onContentChanged() {
            if (root.reduced) { root.shownMedia=mediaBackend.content; return }
            metadataMotion.stop(); root.pendingMedia=mediaBackend.content; metadataMotion.start()
        }
    }
    Connections {
        target: root.Window.window
        function onVisibilityChanged(visibility) {
            if (visibility===Window.Hidden || visibility===Window.Minimized) {
                root.outputRequested=false; outputs.close(); settings.close()
            }
        }
    }
    SequentialAnimation {
        id: nameMotion
        NumberAnimation { target: root; property: "deviceNameOpacity"; to: 0; duration: 70; easing.type: Easing.OutCubic }
        ScriptAction { script: root.shownDeviceName=root.pendingDeviceName }
        NumberAnimation { target: root; property: "deviceNameOpacity"; to: 1; duration: 100; easing.type: Easing.OutCubic }
    }
    SequentialAnimation {
        id: metadataMotion
        NumberAnimation { target: root; property: "metadataOpacity"; to: 0; duration: 70; easing.type: Easing.OutCubic }
        ScriptAction { script: root.shownMedia=root.pendingMedia }
        NumberAnimation { target: root; property: "metadataOpacity"; to: 1; duration: 100; easing.type: Easing.OutCubic }
    }
    SequentialAnimation {
        id: fold
        NumberAnimation { target: root; property: "contentOpacity"; to: 0; duration: root.reduced ? 0 : 70; easing.type: Easing.OutCubic }
        NumberAnimation {
            target: root; property: "bodyHeight"; to: root.compactMode ? 76 : root.expandedHeight
            duration: root.reduced ? 0 : 160; easing.type: Easing.BezierSpline
            easing.bezierCurve: [0.2,0,0,1,1,1]
        }
        ScriptAction { script: root.showingCompact=root.compactMode }
        NumberAnimation { target: root; property: "contentOpacity"; to: 1; duration: root.reduced ? 0 : 100; easing.type: Easing.OutCubic }
        ScriptAction { script: { root.transitioning=false; widgetHost.finishTransition(root.compactMode) } }
    }
}
