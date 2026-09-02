import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: window

    // The widget is deliberately non-activating. It may remain visible above
    // the desktop, but it never takes focus from a foreground game or app.
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
           | ((appController.widgetAlwaysOnTop && !appController.gameActive)
              ? Qt.WindowStaysOnTopHint : Qt.WindowStaysOnBottomHint)
    color: "transparent"
    visible: appController.widgetVisible
    property bool compact: appController.widgetLayoutMode === "compact"
    property bool minimized: false
    property real morphProgress: 0
    readonly property real expandedBaseWidth: 388
    readonly property real minimizedBaseWidth: 220
    readonly property real minimizedBaseHeight: 76
    readonly property real expandedBaseHeightTarget: compact
                                                     ? (layoutMediaAvailable ? 272 : 160)
                                                     : (layoutMediaAvailable ? 428 : 276)
    readonly property real expandedBaseHeight: expandedBaseHeightTarget
    // Leave a short hold at the expanded end of the morph. Content can fade
    // out while the shell is still large enough to contain its last row;
    // without that hold the native window starts shrinking on the same frame
    // that the media card begins to leave.
    // The envelope reaches its expanded height before the last content group
    // enters. On restore this gives the media surface room to reveal without
    // being clipped; on collapse it gives the content time to leave before
    // the native rounded region starts shrinking.
    readonly property real morphGeometryStart: 0.10
    readonly property real morphGeometryEnd: 0.82
    readonly property real morphGeometryProgress: Math.max(
        0, Math.min(1, 1 - (expandedRevealProgress - morphGeometryStart)
                     / (morphGeometryEnd - morphGeometryStart))
    )
    readonly property real widthMorphProgress: compact
        ? 1 - smoothStep(0.0, 0.82, expandedRevealProgress)
        : 1 - smoothStep(0.0, 0.86, expandedRevealProgress)
    readonly property real heightMorphProgress: morphGeometryProgress
    readonly property real baseWidth: expandedBaseWidth
                                      + (minimizedBaseWidth - expandedBaseWidth) * widthMorphProgress
    readonly property real baseHeight: expandedBaseHeight
                                       + (minimizedBaseHeight - expandedBaseHeight) * heightMorphProgress
    property bool morphExpandLeft: true
    property bool morphExpandUp: false
    property bool morphTransitionActive: false
    property bool morphOpening: false
    property bool mediaLayoutUpdatePending: false
    readonly property bool devicePresent: appController.deviceAvailable
    // Freeze the optional media slot for the duration of a morph. Media
    // session callbacks arrive from another thread and must not change the
    // native window target while the user is already watching a transition.
    property bool layoutMediaAvailable: false
    // Resolve the expansion edge once for the current placement. Recomputing
    // it on every restore makes the shared toggle jump between edges when the
    // work area, scale, or popup state changes.
    property bool morphPlacementResolved: false
    property real morphAnchorGlobalX: 0
    property real morphAnchorGlobalY: 0
    // The toggle center is 45 logical pixels from either edge (8 shell inset
    // + 22 control offset + 15 half-size). Use that exact inset for native
    // window placement and the QML button.
    readonly property real morphAnchorInset: 45
    property bool shapeUpdateQueued: false
    property bool geometryFrameApplying: false
    readonly property real desiredWidth: baseWidth * appController.widgetScale
    readonly property real desiredHeight: baseHeight * appController.widgetScale
    // The shell and the content share one timeline. A small hand-off gap hides
    // one composition before the other is enabled, preventing stale summary
    // text or controls from ever sitting on top of the expanded scene.
    readonly property real expandedRevealProgress: Math.max(0, Math.min(1, 1 - morphProgress))
    // The compact composition has four horizontal readings. Keep it hidden
    // until the width morph has made a real column layout possible; rendering
    // it in the narrow intermediate envelope makes CASE and the next value
    // touch even though the final layout is correct.
    // Compact's four-column battery row has a real minimum width. Do not
    // expose that scene while the morph envelope is narrower than its layout;
    // the parent opacity fades across the same hand-off window so it never
    // disappears as a hard cut.
    // During a morph both compositions stay mounted. Their complementary
    // opacity curves perform the hand-off; toggling visible between frames
    // was the source of the isolated-header/media captures.
    readonly property real expandedSceneStart: 0.0
    readonly property real minimizedSceneEnd: 1.0
    readonly property real expandedHeaderRevealProgress: smoothStep(0.06, 0.20, expandedRevealProgress)
    readonly property real expandedBatteryRevealProgress: layoutMediaAvailable
        ? smoothStep(0.34, 0.48, expandedRevealProgress)
        : smoothStep(0.34, 0.52, expandedRevealProgress)
    readonly property real expandedAudioRevealProgress: layoutMediaAvailable
        ? smoothStep(0.50, 0.68, expandedRevealProgress)
        : smoothStep(0.78, 0.94, expandedRevealProgress)
    readonly property real expandedMediaRevealProgress: smoothStep(0.84, 0.98, expandedRevealProgress)
    readonly property real expandedContentOpacity: compact
        ? smoothStep(0.42, 0.62, expandedRevealProgress)
        : smoothStep(0.05, 0.20, expandedRevealProgress)
    readonly property real minimizedContentOpacity: compact
        ? 1 - smoothStep(0.42, 0.62, expandedRevealProgress)
        : 1 - smoothStep(0.05, 0.20, expandedRevealProgress)
    readonly property bool expandedSceneVisible: !morphTransitionActive
        ? !minimized
        : true
    readonly property bool minimizedSceneVisible: !morphTransitionActive
        ? minimized
        : true
    width: desiredWidth
    height: desiredHeight
    opacity: 1
    title: "AirPods Widget"
    property UiTheme theme: UiTheme {}
    property int materialInset: Math.round(8 * appController.widgetScale)
    readonly property real shellRadius: theme.shellRadius
                                      + (20 - theme.shellRadius) * morphProgress
    property int materialCornerRadius: Math.round(shellRadius * appController.widgetScale)

    onWidthChanged: {
        if (window.geometryFrameApplying)
            return
        window.requestWindowShapeUpdate()
        window.requestMorphPositionSync()
    }
    onHeightChanged: {
        if (window.geometryFrameApplying)
            return
        window.requestWindowShapeUpdate()
        window.requestMorphPositionSync()
    }
    onMorphProgressChanged: {
        window.applyMorphGeometryFrame(false)
    }
    onCompactChanged: {
        if (minimized)
            window.setMinimized(false, toggleButton)
        else
            window.syncMediaLayoutAvailability()
    }
    onVisibleChanged: {
        if (visible)
            Qt.callLater(window.resolveInitialMorphPlacement)
    }

    function resolveInitialMorphPlacement() {
        if (!window.visible || window.morphPlacementResolved || !toggleButton)
            return
        var point = toggleButton.mapToGlobal(toggleButton.width / 2, toggleButton.height / 2)
        window.chooseMorphPlacement(point.x, point.y)
        window.morphAnchorGlobalX = point.x
        window.morphAnchorGlobalY = point.y
        window.morphPlacementResolved = true
    }

    function smoothStep(edge0, edge1, value) {
        var normalized = Math.max(0, Math.min(1, (value - edge0) / (edge1 - edge0)))
        return normalized * normalized * (3 - 2 * normalized)
    }

    function setMinimized(value, source) {
        if (window.minimized === value)
            return

        // An interrupted morph must keep the original screen anchor. Reading
        // the button's transient position again here feeds compositor error
        // back into the next target and is what caused the lateral snap.
        if (!window.morphTransitionActive) {
            var point = source.mapToGlobal(source.width / 2, source.height / 2)
            if (!window.morphPlacementResolved) {
                window.chooseMorphPlacement(point.x, point.y)
                window.morphPlacementResolved = true
            }
            morphAnchorGlobalX = point.x
            morphAnchorGlobalY = point.y
        }

        if (!window.morphTransitionActive)
            window.layoutMediaAvailable = window.mediaSlotShouldBeVisible()
        else
            window.mediaLayoutUpdatePending = true

        morphOpening = !value
        morphTransitionActive = true
        window.minimized = value
        window.applyMorphGeometryFrame(false)
        morphAnimation.from = window.morphProgress
        morphAnimation.to = value ? 1 : 0
        morphAnimation.duration = value ? theme.motionMorphClose : theme.motionMorphOpen
        morphAnimation.restart()
        window.requestWindowShapeUpdate()
    }

    function stateBaseWidth(stateMinimized) {
        return stateMinimized ? minimizedBaseWidth : expandedBaseWidth
    }

    function stateBaseHeight(stateMinimized) {
        if (stateMinimized)
            return minimizedBaseHeight
        return expandedBaseHeightTarget
    }

    function mediaSlotShouldBeVisible() {
        // The persistent-player preference is intentionally flow-only. The
        // compact composition keeps its short height and only mounts media
        // when a real session exists.
        return appController.mediaAvailable
            || (!window.compact
                && appController.mediaVisibleSetting
                && appController.mediaAlwaysVisible)
    }

    function syncMediaLayoutAvailability() {
        var desired = window.mediaSlotShouldBeVisible()
        if (window.morphTransitionActive) {
            if (window.layoutMediaAvailable !== desired)
                window.mediaLayoutUpdatePending = true
            return
        }
        window.layoutMediaAvailable = desired
        window.mediaLayoutUpdatePending = false
    }

    function availableWorkArea() {
        var geometry = window.screen ? window.screen.availableGeometry : null
        if (geometry && geometry.width > 0 && geometry.height > 0) {
            return { x: geometry.x, y: geometry.y,
                     width: geometry.width, height: geometry.height }
        }
        return { x: 0, y: 0,
                 width: Screen.width > 0 ? Screen.width : 1920,
                 height: Screen.height > 0 ? Screen.height : 1080 }
    }

    function chooseMorphPlacement(anchorX, anchorY) {
        var area = window.availableWorkArea()
        var scale = appController.widgetScale
        var openWidth = window.stateBaseWidth(false) * scale
        var openHeight = window.stateBaseHeight(false) * scale
        var leftX = anchorX - (window.stateBaseWidth(false) - window.morphAnchorInset) * scale
        var rightX = anchorX - window.morphAnchorInset * scale
        var topY = anchorY - (window.stateBaseHeight(false) - window.morphAnchorInset) * scale
        var bottomY = anchorY - window.morphAnchorInset * scale

        var leftFits = leftX >= area.x && leftX + openWidth <= area.x + area.width
        var rightFits = rightX >= area.x && rightX + openWidth <= area.x + area.width
        if (leftFits && !rightFits)
            morphExpandLeft = true
        else if (rightFits && !leftFits)
            morphExpandLeft = false
        else if (leftFits && rightFits)
            morphExpandLeft = (anchorX - area.x) >= (area.x + area.width - anchorX)
        else {
            var leftOverflow = Math.max(0, area.x - leftX)
                         + Math.max(0, leftX + openWidth - area.x - area.width)
            var rightOverflow = Math.max(0, area.x - rightX)
                          + Math.max(0, rightX + openWidth - area.x - area.width)
            morphExpandLeft = leftOverflow <= rightOverflow
        }

        var topFits = topY >= area.y && topY + openHeight <= area.y + area.height
        var bottomFits = bottomY >= area.y && bottomY + openHeight <= area.y + area.height
        if (topFits && !bottomFits)
            morphExpandUp = true
        else if (bottomFits && !topFits)
            morphExpandUp = false
        else if (topFits && bottomFits)
            morphExpandUp = (anchorY - area.y) >= (area.y + area.height - anchorY)
        else {
            var topOverflow = Math.max(0, area.y - topY)
                        + Math.max(0, topY + openHeight - area.y - area.height)
            var bottomOverflow = Math.max(0, area.y - bottomY)
                           + Math.max(0, bottomY + openHeight - area.y - area.height)
            morphExpandUp = topOverflow <= bottomOverflow
        }
    }

    function requestWindowShapeUpdate() {
        shapeUpdateQueued = true
        shapeUpdateTimer.restart()
    }

    function requestMorphPositionSync() {
        if (!window.morphTransitionActive)
            return
        window.applyMorphGeometryFrame(false)
    }

    function applyMorphGeometryFrame(force) {
        if ((!window.morphTransitionActive && !force) || window.geometryFrameApplying)
            return
        var frameWidth = Math.max(1, Math.round(window.desiredWidth))
        var frameHeight = Math.max(1, Math.round(window.desiredHeight))
        var offsetX = window.morphExpandLeft
                     ? frameWidth - window.morphAnchorInset * appController.widgetScale
                     : window.morphAnchorInset * appController.widgetScale
        var offsetY = window.morphExpandUp
                     ? frameHeight - window.morphAnchorInset * appController.widgetScale
                     : window.morphAnchorInset * appController.widgetScale
        var frameX = Math.round(window.morphAnchorGlobalX - offsetX)
        var frameY = Math.round(window.morphAnchorGlobalY - offsetY)
        window.geometryFrameApplying = true
        appController.applyWindowGeometry(window, frameX, frameY, frameWidth, frameHeight)
        window.geometryFrameApplying = false
    }

    NumberAnimation {
        id: morphAnimation
        target: window
        property: "morphProgress"
        // The shell is a native window whose size is sampled by the OS. A
        // Keep the native envelope's timeline linear. The derived width,
        // height, radius, and content reveals apply their own smooth-step
        // curves; easing this source again compounds the curve and creates a
        // large 16ms geometry jump around the middle of the morph.
        easing.type: Easing.Linear
        onFinished: {
            window.morphProgress = window.minimized ? 1 : 0
            morphSettleTimer.restart()
        }
    }

    Timer {
        id: morphSettleTimer
        interval: 16
        repeat: false
        onTriggered: {
            if (window.mediaLayoutUpdatePending
                    || window.layoutMediaAvailable !== window.mediaSlotShouldBeVisible()) {
                window.layoutMediaAvailable = window.mediaSlotShouldBeVisible()
                window.mediaLayoutUpdatePending = false
            }
            // Apply the final geometry while the morph coordinator is still
            // active. The old code queued this update and immediately turned
            // the coordinator off, so the queued callback returned without
            // doing anything; the final edge then depended on stale HWND
            // coordinates.
            window.applyMorphGeometryFrame(true)
            window.morphTransitionActive = false
            window.requestWindowShapeUpdate()
        }
    }

    Timer {
        id: shapeUpdateTimer
        // SetWindowRgn clips the whole HWND. A delayed update leaves the old
        // region in place while the new native window is already larger or
        // smaller, which clips the expanded content and draws bad corners.
        // A zero-delay timer coalesces width/height/radius changes in one Qt
        // event-loop turn while keeping the native region in the same frame.
        interval: 0
        repeat: false
        onTriggered: {
            if (!window.shapeUpdateQueued)
                return
            window.shapeUpdateQueued = false
            appController.updateWindowShape(window)
        }
    }

    Component.onCompleted: {
        window.layoutMediaAvailable = window.mediaSlotShouldBeVisible()
        appController.applyWindowMaterial(window)
        x = appController.widgetX
        y = appController.widgetY
        syncVisibility()
    }

    function syncVisibility() {
        if (appController.widgetVisible) {
            if (!window.visible)
                window.show()
        } else if (window.visible) {
            window.hide()
        }
    }

    function syncStacking() {
        var wasVisible = window.visible
        if (wasVisible) {
            window.hide()
            window.show()
        }
    }

    Connections {
        target: appController
        function onMediaChanged() {
            if (window.morphTransitionActive) {
                window.mediaLayoutUpdatePending = true
                return
            }
            window.syncMediaLayoutAvailability()
        }
        function onSettingsChanged() {
            appController.applyWindowMaterial(window)
            window.syncMediaLayoutAvailability()
            window.syncVisibility()
            window.syncStacking()
        }
        function onGameChanged() { window.syncStacking() }
    }

    onClosing: function(close) {
        close.accepted = false
        appController.setWidgetVisible(false)
    }

    Item {
        id: resizeHandle
        width: 22
        height: 22
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        z: 20
        visible: !appController.widgetLocked && !window.minimized
        opacity: resizeMouse.containsMouse ? 0.9 : 0

        Behavior on opacity { NumberAnimation { duration: theme.motionFast } }

        Canvas {
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.strokeStyle = theme.textTertiary
                ctx.lineWidth = 1.2
                ctx.lineCap = "round"
                ctx.beginPath()
                ctx.moveTo(8, 17); ctx.lineTo(17, 8)
                ctx.moveTo(13, 17); ctx.lineTo(17, 13)
                ctx.stroke()
            }
        }

        MouseArea {
            id: resizeMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.SizeFDiagCursor
            property real startGlobalX: 0
            property real startScale: 1

            onPressed: {
                var point = resizeHandle.mapToGlobal(mouse.x, mouse.y)
                startGlobalX = point.x
                startScale = appController.widgetScale
            }

            onPositionChanged: {
                if (!pressed)
                    return
                var point = resizeHandle.mapToGlobal(mouse.x, mouse.y)
                var nextScale = startScale + (point.x - startGlobalX) / window.baseWidth
                appController.setWidgetScale(Math.max(0.7, Math.min(1.5, nextScale)))
            }
        }
    }

    Item {
        id: scaledContent
        // The native window and every QML layer derive from the same progress
        // value. No child starts a second, independent transition.
        width: window.width / appController.widgetScale
        height: window.height / appController.widgetScale
        scale: appController.widgetScale
        transformOrigin: Item.TopLeft

        Behavior on scale {
            NumberAnimation { duration: theme.motionLayout; easing.type: Easing.OutCubic }
        }

            Rectangle {
                id: shell
                objectName: "widgetShell"
            anchors.fill: parent
            anchors.margins: 8
            radius: window.shellRadius
            color: theme.shellColor(theme.widgetSurface, appController.widgetOpacity)
            border.width: 1
            border.color: theme.border
            clip: true

            // A restrained inner edge gives the shell a finished perimeter;
            // the content itself is deliberately not broken into cards.
            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: parent.radius - 1
                color: "transparent"
                border.width: 1
                border.color: theme.innerBorder
            }

            // One physical toggle owns both states. Its local edge inset is
            // constant in both steady and morph states; only the native
            // window origin changes as its envelope grows or shrinks.
            Item {
                id: toggleSlot
                objectName: "widgetToggleSlot"
                width: 30
                height: 30
                x: window.morphExpandLeft
                   ? parent.width - (window.morphAnchorInset - shell.x) - width / 2
                   : (window.morphAnchorInset - shell.x) - width / 2
                y: window.morphExpandUp
                   ? parent.height - (window.morphAnchorInset - shell.y) - height / 2
                   : (window.morphAnchorInset - shell.y) - height / 2
                z: 30

                SoftButton {
                    id: toggleButton
                    objectName: "widgetToggleButton"
                    anchors.fill: parent
                    theme: window.theme
                    iconName: "chevron"
                    iconProgress: window.morphProgress
                    onClicked: window.setMinimized(!window.minimized, toggleButton)
                }
            }

            Item {
                id: flowContent
                objectName: "flowContent"
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                // Battery/audio/media share one horizontal grid. Only the
                // header reserves the fixed toggle when it is on the left.
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                anchors.topMargin: 16
                // Give the scene graph the real bounds of the flow. Leaving
                // this Item at its default height (0) makes its descendants
                // depend on stale culling data while the top-level window is
                // being resized, which is why isolated header/media frames
                // appeared during the morph.
                height: flowLayout.implicitHeight
                visible: !window.compact && window.expandedSceneVisible
                opacity: !window.compact ? window.expandedContentOpacity : 0
                enabled: !window.minimized && !window.morphTransitionActive

                ColumnLayout {
                    id: flowLayout
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: 8

                    Item {
                        id: flowHeader
                        objectName: "flowHeader"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        opacity: window.expandedHeaderRevealProgress
                        transform: Translate {
                            y: (1 - window.expandedHeaderRevealProgress) * theme.motionMorphSlide
                        }

                        AnimatedText {
                            objectName: "flowDeviceName"
                            anchors.left: parent.left
                            anchors.right: headerControls.left
                            anchors.leftMargin: window.morphExpandLeft ? 0 : 38
                            anchors.verticalCenter: parent.verticalCenter
                            text: window.devicePresent && appController.deviceName
                                  ? appController.deviceName : ""
                            color: theme.textPrimary
                            fontFamily: theme.fontDisplay
                            pixelSize: theme.titleSize
                            fontWeight: theme.titleWeight
                            letterSpacing: -0.2
                            elide: Text.ElideRight
                            changeDuration: 190

                            EmptyIndicator {
                                anchors.fill: parent
                                theme: window.theme
                                active: !window.devicePresent || !appController.deviceName
                            }
                        }

                            Row {
                                id: headerControls
                                objectName: "headerControls"
                                anchors.right: parent.right
                                anchors.rightMargin: window.morphExpandLeft ? 58 : 0
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 5

                            Row {
                                spacing: 6
                                anchors.verticalCenter: parent.verticalCenter

                                Item {
                                    width: 12
                                    height: 16
                                    anchors.verticalCenter: parent.verticalCenter

                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 6
                                        height: 6
                                        radius: 3
                                        color: appController.connected ? theme.green
                                              : appController.detected ? theme.orange : theme.textTertiary
                                        opacity: window.devicePresent ? 1 : 0
                                        Behavior on color { ColorAnimation { duration: theme.motionStandard } }
                                        Behavior on opacity { NumberAnimation { duration: theme.motionFast; easing.type: Easing.OutCubic } }
                                    }

                                    MediaIcon {
                                        anchors.centerIn: parent
                                        width: 12
                                        height: 12
                                        icon: "bluetooth"
                                        foreground: theme.textTertiary
                                        opacity: window.devicePresent ? 0 : 0.72
                                        Behavior on opacity { NumberAnimation { duration: theme.motionFast; easing.type: Easing.OutCubic } }
                                    }
                                }

                                AnimatedText {
                                    objectName: "flowConnectionLabel"
                                    text: appController.connected ? "연결됨"
                                          : appController.detected ? "검색 중" : "대기 중"
                                    color: theme.textSecondary
                                    fontFamily: theme.fontText
                                    pixelSize: theme.bodySize
                                    fontWeight: theme.bodyWeight
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: implicitWidth
                                    changeDuration: 150
                                    changeOffset: 0
                                }
                            }

                        }

                        MouseArea {
                            anchors.left: parent.left
                            anchors.right: headerControls.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            cursorShape: appController.widgetLocked ? Qt.ArrowCursor : Qt.SizeAllCursor
                            onPressed: if (!appController.widgetLocked) window.startSystemMove()
                            onReleased: {
                                appController.saveWidgetPosition(window.x, window.y)
                                // A deliberate move may place the widget on a
                                // different edge; resolve that once on the
                                // next restore, never during the morph.
                                window.morphPlacementResolved = false
                            }
                        }
                    }

                    BatteryOverview {
                        id: flowBatteryOverview
                        objectName: "flowBatteryOverview"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 104
                        theme: window.theme
                        materialOpacity: appController.widgetOpacity
                        revealProgress: window.expandedBatteryRevealProgress
                        devicePresent: window.devicePresent
                    }

                    AudioOutputSection {
                        id: flowAudioOutput
                        objectName: "flowAudioOutput"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        theme: window.theme
                        materialOpacity: appController.widgetOpacity
                        revealProgress: window.expandedAudioRevealProgress
                    }

                    MediaSection {
                        id: flowMediaSection
                        objectName: "flowMediaSection"
                        Layout.fillWidth: true
                        Layout.preferredHeight: window.layoutMediaAvailable ? 146 : 0
                        available: appController.mediaAvailable
                        persistent: window.layoutMediaAvailable
                        playing: appController.mediaPlaying
                        title: appController.mediaTitle
                        subtitle: appController.mediaSubtitle
                        canPrevious: appController.canPrevious
                        canNext: appController.canNext
                        canPlayPause: appController.canPlayPause
                        positionSeconds: appController.mediaPosition
                        durationSeconds: appController.mediaDuration
                        theme: window.theme
                        materialOpacity: appController.widgetOpacity
                        revealProgress: window.expandedMediaRevealProgress
                    }
                }
            }

            Item {
                id: compactContent
                objectName: "compactContent"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                // Compact keeps a small top slot for the toggle. Its side is
                // resolved once per placement and never changes mid-morph.
                anchors.leftMargin: window.morphExpandLeft ? 22 : 58
                anchors.rightMargin: window.morphExpandLeft ? 58 : 22
                anchors.topMargin: 16
                // Keep the compact composition's bounds explicit for the
                // same reason as the flow scene above.
                height: compactController.implicitHeight
                visible: window.compact && window.expandedSceneVisible
                opacity: window.compact ? window.expandedContentOpacity : 0
                enabled: !window.minimized && !window.morphTransitionActive

                CompactController {
                    id: compactController
                    objectName: "compactController"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: implicitHeight
                    theme: window.theme
                    materialOpacity: appController.widgetOpacity
                    devicePresent: window.devicePresent
                    revealProgress: window.expandedRevealProgress
                    opening: window.morphOpening
                    mediaAvailable: window.layoutMediaAvailable
                    playing: appController.mediaPlaying
                    title: appController.mediaTitle
                    subtitle: appController.mediaSubtitle
                    canPrevious: appController.canPrevious
                    canNext: appController.canNext
                    canPlayPause: appController.canPlayPause
                    positionSeconds: appController.mediaPosition
                    durationSeconds: appController.mediaDuration
                }
            }

            Item {
                id: minimizedContent
                objectName: "minimizedContent"
                z: 5
                anchors.top: parent.top
                // The summary occupies the space next to the fixed toggle;
                // anchoring to the toggle itself prevents the compact content
                // from drifting or colliding when the expansion edge changes.
                anchors.left: window.morphExpandLeft ? parent.left : toggleSlot.right
                anchors.right: window.morphExpandLeft ? toggleSlot.left : parent.right
                anchors.leftMargin: window.morphExpandLeft ? 14 : 8
                anchors.rightMargin: window.morphExpandLeft ? 8 : 14
                anchors.topMargin: 19
                height: 38
                visible: window.minimizedSceneVisible
                opacity: window.minimizedContentOpacity
                enabled: window.minimized && !window.morphTransitionActive
                transform: Translate {
                    y: (1 - window.minimizedContentOpacity) * -4
                }

                RowLayout {
                    anchors.fill: parent
                    spacing: 7
                    z: 1

                    Rectangle {
                        Layout.preferredWidth: 6
                        Layout.minimumWidth: 6
                        Layout.maximumWidth: 6
                        Layout.preferredHeight: 6
                        Layout.alignment: Qt.AlignVCenter
                        radius: 3
                        color: appController.connected ? theme.green
                              : appController.detected ? theme.orange : theme.textTertiary
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 50
                        Layout.alignment: Qt.AlignVCenter

                        AnimatedText {
                            anchors.fill: parent
                            text: window.devicePresent
                                  ? ((appController.leftBattery < 0 ? "" : appController.leftBattery)
                                     + "  /  "
                                     + (appController.rightBattery < 0 ? "" : appController.rightBattery))
                                  : ""
                            color: theme.textPrimary
                            fontFamily: theme.fontDisplay
                            pixelSize: theme.captionSize
                            fontWeight: theme.valueWeight
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                            changeDuration: 140
                        }

                        EmptyIndicator {
                            anchors.fill: parent
                            theme: window.theme
                            active: !window.devicePresent
                        }
                    }

                    AudioOutputSection {
                        id: minimizedAudioOutput
                        objectName: "minimizedAudioOutput"
                        Layout.preferredWidth: 56
                        Layout.minimumWidth: 56
                        Layout.maximumWidth: 56
                        Layout.preferredHeight: 38
                        Layout.alignment: Qt.AlignVCenter
                        minimized: true
                        theme: window.theme
                        materialOpacity: appController.widgetOpacity
                    }
                }

                MouseArea {
                    z: 0
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    cursorShape: appController.widgetLocked ? Qt.ArrowCursor : Qt.SizeAllCursor
                    onPressed: if (!appController.widgetLocked) window.startSystemMove()
                    onReleased: {
                        appController.saveWidgetPosition(window.x, window.y)
                        window.morphPlacementResolved = false
                    }
                }
            }
        }
    }
}
