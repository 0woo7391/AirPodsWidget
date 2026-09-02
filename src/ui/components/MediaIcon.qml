import QtQuick

Item {
    id: root
    property string icon: "play"
    property color foreground: "white"
    property real progress: 0
    property real strokeWidth: Math.max(1.5, width * 0.08)

    implicitWidth: 18
    implicitHeight: 18

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            const ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.fillStyle = root.foreground
            ctx.strokeStyle = root.foreground
            ctx.lineWidth = root.strokeWidth
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            const w = width
            const h = height
            if (root.icon === "play") {
                ctx.beginPath()
                ctx.moveTo(w * 0.34, h * 0.22)
                ctx.lineTo(w * 0.76, h * 0.50)
                ctx.lineTo(w * 0.34, h * 0.78)
                ctx.closePath()
                ctx.fill()
            } else if (root.icon === "pause") {
                const barW = w * 0.18
                ctx.fillRect(w * 0.28, h * 0.22, barW, h * 0.56)
                ctx.fillRect(w * 0.56, h * 0.22, barW, h * 0.56)
            } else if (root.icon === "previous") {
                ctx.fillRect(w * 0.20, h * 0.24, root.strokeWidth, h * 0.52)
                ctx.beginPath()
                ctx.moveTo(w * 0.72, h * 0.22)
                ctx.lineTo(w * 0.30, h * 0.50)
                ctx.lineTo(w * 0.72, h * 0.78)
                ctx.closePath()
                ctx.fill()
            } else if (root.icon === "next") {
                ctx.fillRect(w * 0.72 - root.strokeWidth, h * 0.24, root.strokeWidth, h * 0.52)
                ctx.beginPath()
                ctx.moveTo(w * 0.28, h * 0.22)
                ctx.lineTo(w * 0.70, h * 0.50)
                ctx.lineTo(w * 0.28, h * 0.78)
                ctx.closePath()
                ctx.fill()
            } else if (root.icon === "speaker" || root.icon === "volume") {
                ctx.beginPath()
                ctx.moveTo(w * 0.16, h * 0.42)
                ctx.lineTo(w * 0.34, h * 0.42)
                ctx.lineTo(w * 0.58, h * 0.22)
                ctx.lineTo(w * 0.58, h * 0.78)
                ctx.lineTo(w * 0.34, h * 0.58)
                ctx.lineTo(w * 0.16, h * 0.58)
                ctx.closePath()
                ctx.fill()
                if (root.icon === "volume") {
                    ctx.beginPath()
                    ctx.arc(w * 0.50, h * 0.50, w * 0.28, -0.72, 0.72)
                    ctx.stroke()
                }
            } else if (root.icon === "headphones") {
                ctx.beginPath()
                ctx.arc(w * 0.50, h * 0.48, w * 0.31, Math.PI, 0)
                ctx.stroke()
                ctx.fillRect(w * 0.15, h * 0.49, w * 0.15, h * 0.27)
                ctx.fillRect(w * 0.70, h * 0.49, w * 0.15, h * 0.27)
            } else if (root.icon === "bluetooth") {
                ctx.beginPath()
                ctx.moveTo(w * 0.49, h * 0.10)
                ctx.lineTo(w * 0.73, h * 0.32)
                ctx.lineTo(w * 0.49, h * 0.50)
                ctx.lineTo(w * 0.73, h * 0.68)
                ctx.lineTo(w * 0.49, h * 0.90)
                ctx.lineTo(w * 0.49, h * 0.10)
                ctx.moveTo(w * 0.25, h * 0.30)
                ctx.lineTo(w * 0.73, h * 0.68)
                ctx.moveTo(w * 0.25, h * 0.70)
                ctx.lineTo(w * 0.73, h * 0.32)
                ctx.stroke()
            } else if (root.icon === "charging") {
                // A small filled lightning mark is clearer at this size than
                // an outlined battery or an emoji glyph. It stays in the
                // shared state column and does not change row geometry.
                ctx.beginPath()
                ctx.moveTo(w * 0.56, h * 0.08)
                ctx.lineTo(w * 0.24, h * 0.52)
                ctx.lineTo(w * 0.48, h * 0.52)
                ctx.lineTo(w * 0.38, h * 0.92)
                ctx.lineTo(w * 0.78, h * 0.40)
                ctx.lineTo(w * 0.52, h * 0.40)
                ctx.closePath()
                ctx.fill()
            } else if (root.icon === "chevron") {
                const progress = Math.max(0, Math.min(1, root.progress))
                const outerY = h * (0.38 + 0.24 * progress)
                const centerY = h * (0.66 - 0.32 * progress)
                ctx.beginPath()
                ctx.moveTo(w * 0.22, outerY)
                ctx.lineTo(w * 0.50, centerY)
                ctx.lineTo(w * 0.78, outerY)
                ctx.stroke()
            } else if (root.icon === "chevron-down" || root.icon === "chevron-up") {
                ctx.beginPath()
                if (root.icon === "chevron-down") {
                    ctx.moveTo(w * 0.22, h * 0.38)
                    ctx.lineTo(w * 0.50, h * 0.66)
                    ctx.lineTo(w * 0.78, h * 0.38)
                } else {
                    ctx.moveTo(w * 0.22, h * 0.62)
                    ctx.lineTo(w * 0.50, h * 0.34)
                    ctx.lineTo(w * 0.78, h * 0.62)
                }
                ctx.stroke()
            }
        }
    }

    onIconChanged: canvas.requestPaint()
    onProgressChanged: canvas.requestPaint()
    onForegroundChanged: canvas.requestPaint()
    onWidthChanged: canvas.requestPaint()
    onHeightChanged: canvas.requestPaint()
}
