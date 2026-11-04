import QtQuick

// Time and date. Half: time over date. Full: a larger time with the weekday, the date
// and the next event beside it.
// The flyout is a month calendar: today marked, weekends tinted, arrows to page months,
// a coloured dot under a day for each one-day event and a bar across the days of a longer
// one (rounded only where it really starts and ends). Clicking a day lists its events below;
// "＋ 일정" (or an event) opens a form: title, time or all day, last day, colour, reminder.
// Reminders show on the island (events.py).
DockCard {
    id: card
    cardId: "clock"
    summaryHeight: 84

    property date now: new Date()
    Timer { interval: 1000; repeat: true; running: true; triggeredOnStart: true; onTriggered: card.now = new Date() }
    readonly property string time: Qt.formatTime(now, "hh:mm")
    readonly property string date: Qt.formatDate(now, "M월 d일")
    readonly property string weekday: ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"][now.getDay()]

    // ---- events ----
    function iso(d) { return Qt.formatDate(d, "yyyy-MM-dd") }
    function fromIso(s) { const p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]) }
    property int revision: 0
    Connections { target: eventStore; function onChanged() { card.revision++ } }
    readonly property var next: { revision; now.getMinutes(); return eventStore.next }
    readonly property var marks: { revision; return eventStore.marks }
    readonly property var ranges: { revision; return eventStore.ranges }
    // While on, the next click in the calendar sets the form's last day.
    property bool pickingEnd: false
    readonly property int dayCellHeight: 40
    property string selected: iso(now)
    readonly property var dayEvents: { revision; return eventStore.forDay(selected) }
    // The open form's values, or null: {id, date, end, title, allDay, time, color, remind}.
    property var form: null
    property bool formError: false
    pinned: form !== null
    readonly property var reminders: [[-1, "없음"], [0, "정시"], [5, "5분"], [10, "10분"], [30, "30분"], [60, "1시간"], [1440, "1일"]]
    readonly property int calendarHeight: 74 + 6 * dayCellHeight + 6
    readonly property int dayHeight: 40 + (form ? 244 : Math.max(1, dayEvents.length) * 30)
    detailHeight: calendarHeight + dayHeight + Theme.pad

    function openForm(event) {
        dockHost.requestActivate()
        formError = false
        pickingEnd = false
        if (event) {
            form = { id: event.id, date: event.date, end: event.end, title: event.title, allDay: !event.time,
                     time: event.time || "09:00", color: event.color, remind: event.remind }
        } else {
            const soon = new Date(now.getTime() + 60 * 60 * 1000)
            form = { id: "", date: selected, end: selected, title: "", allDay: false,
                     time: selected === iso(now) ? Qt.formatTime(soon, "hh") + ":00" : "09:00",
                     color: eventStore.colors[0], remind: 10 }
        }
    }
    function setForm(key, value) { const f = Object.assign({}, form); f[key] = value; form = f }
    function saveForm() {
        const id = eventStore.save({ id: form.id, date: form.date, end: form.end, title: form.title,
                                     time: form.allDay ? "" : form.time, color: form.color, remind: form.remind })
        if (id.length) form = null
        else formError = true
    }
    onFormChanged: if (!form) pickingEnd = false
    onExpandedChanged: if (!expanded) { form = null; selected = iso(now) }
    function shortDate(s) { const d = fromIso(s); return (d.getMonth() + 1) + "/" + d.getDate() }
    // The bars of one week row: [{col, cols, lane, color, roundL, roundR}], two lanes, plus how many
    // events each day could not show ({col: count}).
    function rowBars(rowStart) {
        const day = 86400000, bars = [], laneEnd = [], hidden = {}
        for (const r of ranges) {
            const s = Math.round((fromIso(r.date) - rowStart) / day), e = Math.round((fromIso(r.end) - rowStart) / day)
            if (e < 0 || s > 6) continue
            const col = Math.max(0, s), last = Math.min(6, e)
            let lane = laneEnd.findIndex(end => end < col)
            if (lane < 0) { lane = laneEnd.length; laneEnd.push(last) } else laneEnd[lane] = last
            if (lane > 1) { for (let c = col; c <= last; c++) hidden[c] = (hidden[c] || 0) + 1; continue }
            bars.push({ col: col, cols: last - col + 1, lane: lane, color: r.color, roundL: s >= 0, roundR: e <= 6 })
        }
        return { bars: bars, hidden: hidden }
    }
    function dayLabel(s) {
        const d = fromIso(s)
        return Qt.formatDate(d, "M월 d일 ") + ["일", "월", "화", "수", "목", "금", "토"][d.getDay()] + "요일"
            + (s === iso(now) ? " · 오늘" : "")
    }
    readonly property string nextLine: !next.title ? ""
        : (next.date === iso(now) ? (next.time || "종일") : next.when) + " " + next.title

    // On the rail the time itself is the icon.
    railIconComponent: Component {
        Text {
            text: card.time
            color: Theme.ink; font.family: dockFont; font.pixelSize: 12; font.weight: Font.DemiBold
            font.features: Theme.numberFeatures
        }
    }
    railLabel: time
    railStatus: date + " " + weekday + (nextLine.length ? " · " + nextLine : "")

    // A small chip: the reminder choices, the all-day switch.
    component Chip: Rectangle {
        id: chip
        property string label
        property bool on: false
        signal picked()
        width: chipText.implicitWidth + 14; height: 22; radius: 11
        color: on ? Theme.ink : chipMouse.containsMouse ? Theme.wellHover : Theme.well
        Text {
            id: chipText
            anchors.centerIn: parent
            text: chip.label
            color: chip.on ? "#16161A" : Theme.inkSecondary
            font.family: dockFont; font.pixelSize: 11; font.weight: chip.on ? Font.DemiBold : Font.Normal
        }
        MouseArea { id: chipMouse; anchors.fill: parent; hoverEnabled: true; onClicked: chip.picked() }
    }
    component Field: Rectangle {
        property alias input: field
        property string placeholder
        height: 30; radius: 9
        color: Theme.well
        border.width: 1; border.color: field.activeFocus ? Theme.strokeLit : card.formError ? Theme.bad : "transparent"
        TextInput {
            id: field
            anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
            verticalAlignment: TextInput.AlignVCenter
            color: Theme.ink; selectionColor: "#558FD0FF"
            font.family: dockFont; font.pixelSize: 13
            selectByMouse: true; clip: true
            Keys.onEscapePressed: card.form = null
        }
        Text {
            anchors.fill: field
            verticalAlignment: Text.AlignVCenter
            visible: !field.text.length
            text: parent.placeholder
            color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 13
        }
    }

    summary: Component {
        Item {
            readonly property bool wide: card.size === "full"
            Text {
                x: Theme.pad; y: wide ? 16 : 14
                text: card.time
                color: Theme.ink; font.family: dockFont; font.weight: Font.DemiBold
                font.pixelSize: wide ? 40 : 28
                font.features: Theme.numberFeatures
            }
            Text {
                visible: !parent.wide
                x: Theme.pad; y: parent.height - Theme.pad - height + 2
                width: parent.width - Theme.pad * 2; elide: Text.ElideRight
                text: card.date + " " + card.weekday.charAt(0)
                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
            }
            Column {
                visible: parent.wide
                anchors.right: parent.right; anchors.rightMargin: Theme.pad
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width / 2 - Theme.pad
                spacing: 2
                Text {
                    anchors.right: parent.right
                    text: card.weekday
                    color: Theme.ink; font.family: dockFont; font.pixelSize: 14; font.weight: Font.DemiBold
                }
                Text {
                    anchors.right: parent.right
                    text: card.date
                    color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                }
                // The next event: its colour, when, and title.
                Row {
                    visible: card.nextLine.length > 0
                    anchors.right: parent.right
                    spacing: 5
                    Rectangle {
                        width: 6; height: 6; radius: 3
                        anchors.verticalCenter: parent.verticalCenter
                        color: card.next.color || Theme.charge
                    }
                    Text {
                        width: Math.min(implicitWidth, parent.parent.width - 11)
                        elide: Text.ElideRight
                        text: card.nextLine
                        color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 11
                    }
                }
            }
        }
    }

    detail: Component {
        Item {
            id: calendar
            // Months away from this one; the grid slides the way you page.
            property int offset: 0
            property int direction: 0
            readonly property date month: new Date(card.now.getFullYear(), card.now.getMonth() + offset, 1)
            readonly property int firstDay: month.getDay()
            readonly property int days: new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
            function page(step) { direction = step; offset += step; slide.restart() }
            Connections { target: card; function onExpandedChanged() { if (!card.expanded) calendar.offset = 0 } }

            Text {
                x: Theme.pad; y: Theme.pad
                text: calendar.month.getFullYear() + "년 " + (calendar.month.getMonth() + 1) + "월"
                color: Theme.ink; font.family: dockFont; font.pixelSize: 15; font.weight: Font.DemiBold
                opacity: card.reveal(0)
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: Theme.pad - 4; y: Theme.pad - 6
                spacing: 4
                opacity: card.reveal(0)
                GlassButton { width: 28; height: 28; text: "‹"; onClicked: calendar.page(-1) }
                GlassButton {
                    width: 44; height: 28; text: "오늘"
                    enabled: calendar.offset !== 0 || card.selected !== card.iso(card.now)
                    onClicked: { card.selected = card.iso(card.now); card.form = null; calendar.page(-calendar.offset) }
                }
                GlassButton { width: 28; height: 28; text: "›"; onClicked: calendar.page(1) }
            }
            Row {
                id: weekdays
                x: Theme.pad; y: 52
                opacity: card.reveal(1)
                Repeater {
                    model: ["일", "월", "화", "수", "목", "금", "토"]
                    Text {
                        required property string modelData
                        required property int index
                        width: (calendar.width - Theme.pad * 2) / 7
                        horizontalAlignment: Text.AlignHCenter
                        text: modelData
                        color: index === 0 ? "#FF8A80" : index === 6 ? "#8FB8FF" : Theme.inkTertiary
                        font.family: dockFont; font.pixelSize: 10; font.weight: Font.DemiBold
                    }
                }
            }
            Grid {
                id: grid
                x: Theme.pad; y: 74
                columns: 7
                opacity: card.reveal(2)
                transform: Translate { id: shift }
                SequentialAnimation {
                    id: slide
                    ParallelAnimation {
                        NumberAnimation { target: shift; property: "x"; to: -18 * calendar.direction; duration: 0 }
                        NumberAnimation { target: grid; property: "opacity"; to: 0.2; duration: 0 }
                    }
                    ParallelAnimation {
                        NumberAnimation { target: shift; property: "x"; to: 0; duration: 260; easing.type: Easing.OutCubic }
                        NumberAnimation { target: grid; property: "opacity"; to: 1; duration: 220 }
                    }
                }
                Repeater {
                    model: 42
                    Item {
                        id: cell
                        required property int index
                        readonly property int day: index - calendar.firstDay + 1
                        readonly property bool inMonth: day >= 1 && day <= calendar.days
                        readonly property date date: new Date(calendar.month.getFullYear(), calendar.month.getMonth(), day)
                        readonly property string key: card.iso(date)
                        readonly property bool today: inMonth && date.toDateString() === card.now.toDateString()
                        readonly property bool chosen: inMonth && key === card.selected
                        readonly property var dots: (card.marks[key] || []).slice(0, 3)
                        readonly property bool inPeriod: !!card.form && inMonth && key >= card.form.date && key <= card.form.end
                        width: (calendar.width - Theme.pad * 2) / 7
                        height: card.dayCellHeight
                        // The form's period, while choosing it.
                        Rectangle {
                            visible: cell.inPeriod && card.form.end !== card.form.date
                            x: 1; y: 2; width: parent.width - 2; height: 26; radius: 6
                            color: "#1F8FD0FF"
                        }
                        Rectangle {
                            x: (parent.width - width) / 2; y: 2
                            width: 26; height: 26; radius: 13
                            color: cell.today ? Theme.charge : cellMouse.containsMouse && cell.inMonth ? Theme.wellHover : "transparent"
                            border.width: cell.chosen && !cell.today ? 1 : 0
                            border.color: Theme.strokeLit
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: 15 - height / 2 + (cell.dots.length ? -2 : 0)
                            text: cell.date.getDate()
                            color: cell.today ? "#16161A" : !cell.inMonth ? "#33F5F5F7"
                                : index % 7 === 0 ? "#FF8A80" : index % 7 === 6 ? "#8FB8FF" : Theme.ink
                            font.family: dockFont; font.pixelSize: 12
                            font.weight: cell.today ? Font.DemiBold : Font.Normal
                            font.features: Theme.numberFeatures
                        }
                        Row {
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: 21
                            spacing: 2
                            opacity: cell.inMonth ? 1 : 0.35
                            Repeater {
                                model: cell.dots
                                Rectangle {
                                    required property string modelData
                                    width: 4; height: 4; radius: 2
                                    color: cell.today ? "#16161A" : modelData
                                }
                            }
                        }
                        MouseArea {
                            id: cellMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (card.pickingEnd) {
                                    if (cell.key >= card.form.date) card.setForm("end", cell.key)
                                    card.pickingEnd = false
                                    return
                                }
                                if (!cell.inMonth) calendar.page(cell.day < 1 ? -1 : 1)
                                card.selected = cell.key
                                card.form = null
                            }
                        }
                    }
                }
            }

            // Bars of events over several days, one row per week, sliding with the grid.
            Item {
                x: grid.x; y: grid.y
                width: calendar.width - Theme.pad * 2
                opacity: grid.opacity
                transform: Translate { x: shift.x }
                readonly property real cellWidth: width / 7
                Repeater {
                    model: 6
                    Item {
                        id: week
                        required property int index
                        readonly property var layout: card.rowBars(new Date(calendar.month.getFullYear(),
                            calendar.month.getMonth(), 1 - calendar.firstDay + index * 7))
                        y: index * card.dayCellHeight
                        Repeater {
                            model: week.layout.bars
                            Rectangle {
                                required property var modelData
                                x: modelData.col * parent.parent.cellWidth + (modelData.roundL ? 4 : 0)
                                width: modelData.cols * parent.parent.cellWidth - (modelData.roundL ? 4 : 0) - (modelData.roundR ? 4 : 0)
                                y: 30 + modelData.lane * 5
                                height: 4
                                color: modelData.color
                                topLeftRadius: modelData.roundL ? 2 : 0; bottomLeftRadius: topLeftRadius
                                topRightRadius: modelData.roundR ? 2 : 0; bottomRightRadius: topRightRadius
                            }
                        }
                        Repeater {
                            model: Object.keys(week.layout.hidden)
                            Text {
                                required property string modelData
                                x: (+modelData + 1) * parent.parent.cellWidth - width - 2; y: 1
                                text: "+" + week.layout.hidden[modelData]
                                color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 8
                            }
                        }
                    }
                }
            }

            // ---- the selected day ----
            Item {
                id: dayPanel
                x: Theme.pad; y: card.calendarHeight
                width: parent.width - Theme.pad * 2
                height: card.dayHeight
                opacity: card.reveal(3)
                Rectangle { width: parent.width; height: 1; color: Theme.stroke }
                Text {
                    y: 12
                    text: card.pickingEnd ? "달력에서 마지막 날을 누르세요" : card.dayLabel(card.selected)
                    color: Theme.ink; font.family: dockFont; font.pixelSize: 13; font.weight: Font.DemiBold
                }
                Chip {
                    anchors.right: parent.right; y: 9
                    visible: card.form === null
                    label: "＋ 일정"
                    onPicked: card.openForm(null)
                }
                // Events of the day.
                Column {
                    y: 40; width: parent.width
                    visible: card.form === null
                    Text {
                        visible: card.dayEvents.length === 0
                        height: 30; verticalAlignment: Text.AlignVCenter
                        text: "일정 없음"
                        color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 12
                    }
                    Repeater {
                        model: card.dayEvents
                        Rectangle {
                            required property var modelData
                            width: parent.width; height: 30; radius: 8
                            color: rowMouse.containsMouse ? Theme.well : "transparent"
                            Rectangle {
                                x: 6; width: 4; height: 16; radius: 2
                                anchors.verticalCenter: parent.verticalCenter
                                color: modelData.color
                            }
                            Text {
                                x: 18; width: 58
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.span || modelData.time || "하루 종일"
                                color: Theme.inkSecondary; font.family: dockFont; font.pixelSize: 12
                                font.features: Theme.numberFeatures
                            }
                            Text {
                                x: 78; width: parent.width - x - 24
                                anchors.verticalCenter: parent.verticalCenter
                                elide: Text.ElideRight
                                text: modelData.title
                                color: Theme.ink; font.family: dockFont; font.pixelSize: 13
                            }
                            Text {
                                anchors.right: parent.right; anchors.rightMargin: 6
                                anchors.verticalCenter: parent.verticalCenter
                                visible: modelData.remind >= 0
                                text: "⏰"
                                color: Theme.inkTertiary; font.pixelSize: 10
                            }
                            MouseArea { id: rowMouse; anchors.fill: parent; hoverEnabled: true; onClicked: card.openForm(modelData) }
                        }
                    }
                }
                // Add / edit.
                Column {
                    y: 40; width: parent.width
                    spacing: 9
                    visible: card.form !== null
                    Field {
                        id: titleField
                        width: parent.width
                        placeholder: "일정 제목"
                        input.text: card.form ? card.form.title : ""
                        input.onTextEdited: card.setForm("title", input.text)
                        input.onAccepted: card.saveForm()
                        Connections {
                            target: card
                            function onFormChanged() {
                                if (card.form && !titleField.input.activeFocus) Qt.callLater(() => titleField.input.forceActiveFocus())
                            }
                        }
                    }
                    Row {
                        spacing: 6
                        Chip {
                            label: "하루 종일"
                            on: !!card.form && card.form.allDay
                            onPicked: card.setForm("allDay", !card.form.allDay)
                        }
                        Field {
                            visible: !!card.form && !card.form.allDay
                            width: 70; height: 22
                            input.font.pixelSize: 12
                            input.inputMask: "99:99"
                            input.text: card.form ? card.form.time : ""
                            input.onTextEdited: card.setForm("time", input.text)
                            input.onAccepted: card.saveForm()
                        }
                    }
                    // Last day: one day, or a period picked in the calendar.
                    Row {
                        spacing: 6
                        Chip {
                            readonly property bool long: !!card.form && card.form.end !== card.form.date
                            label: card.pickingEnd ? "날짜 고르는 중…" : long
                                ? card.shortDate(card.form.date) + " – " + card.shortDate(card.form.end) : "하루"
                            on: long || card.pickingEnd
                            onPicked: card.pickingEnd = !card.pickingEnd
                        }
                        Chip {
                            visible: !!card.form && card.form.end !== card.form.date && !card.pickingEnd
                            label: "하루로"
                            onPicked: card.setForm("end", card.form.date)
                        }
                    }
                    Row {
                        spacing: 8
                        Repeater {
                            model: eventStore.colors
                            Rectangle {
                                required property string modelData
                                width: 20; height: 20; radius: 10
                                color: modelData
                                border.width: card.form && card.form.color === modelData ? 2 : 0
                                border.color: Theme.ink
                                MouseArea { anchors.fill: parent; onClicked: card.setForm("color", parent.modelData) }
                            }
                        }
                    }
                    Text {
                        text: "미리 알림"
                        color: Theme.inkTertiary; font.family: dockFont; font.pixelSize: 11
                    }
                    Flow {
                        width: parent.width
                        spacing: 4
                        Repeater {
                            model: card.reminders
                            Chip {
                                required property var modelData
                                label: modelData[1]
                                on: !!card.form && card.form.remind === modelData[0]
                                onPicked: card.setForm("remind", modelData[0])
                            }
                        }
                    }
                    Item {
                        width: parent.width; height: 28
                        Chip {
                            visible: !!card.form && card.form.id.length > 0
                            anchors.verticalCenter: parent.verticalCenter
                            label: "삭제"
                            onPicked: { eventStore.remove(card.form.id); card.form = null }
                        }
                        Row {
                            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                            spacing: 6
                            Chip { label: "취소"; onPicked: card.form = null }
                            Chip { label: "저장"; on: true; onPicked: card.saveForm() }
                        }
                    }
                }
            }
        }
    }
}
