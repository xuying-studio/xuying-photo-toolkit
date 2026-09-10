pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../Components"
import "../Themes" as Themes

Item {
    id: root

    required property var viewModel
    property bool previewPlaying: false
    property int previewFrameIndex: 0
    readonly property int previewTotalFrames: viewModel.itemCount *
                                              Math.max(1, viewModel.framesPerImage)
    readonly property int previewFrameInterval: Math.max(
        1, Math.round(1000 / Math.max(1, viewModel.frameRate)))

    function syncPlaybackToSelection() {
        previewFrameIndex = Math.max(0, viewModel.selectedIndex) *
                            Math.max(1, viewModel.framesPerImage)
    }

    function stopPreviewPlayback(syncSelection) {
        previewTimer.stop()
        previewPlaying = false
        if (syncSelection)
            syncPlaybackToSelection()
    }

    function selectPreviewIndex(index) {
        stopPreviewPlayback(false)
        viewModel.selectIndex(index)
        syncPlaybackToSelection()
    }

    function togglePreviewPlayback() {
        if (previewPlaying) {
            stopPreviewPlayback(false)
            return
        }
        if (viewModel.itemCount <= 0)
            return
        if (viewModel.selectedIndex < 0 || previewFrameIndex >= previewTotalFrames) {
            viewModel.selectIndex(0)
            previewFrameIndex = 0
        }
        previewPlaying = true
        previewTimer.restart()
    }

    function advancePreviewPlayback() {
        previewFrameIndex += 1
        if (previewFrameIndex >= previewTotalFrames) {
            previewFrameIndex = previewTotalFrames
            stopPreviewPlayback(false)
            return
        }
        let nextIndex = Math.floor(previewFrameIndex /
                                   Math.max(1, viewModel.framesPerImage))
        if (nextIndex !== viewModel.selectedIndex)
            viewModel.selectIndex(nextIndex)
    }

    function syncTargetGeometry() {
        targetBox.x = viewModel.targetX * previewFrame.width
        targetBox.y = viewModel.targetY * previewFrame.height
        targetBox.width = viewModel.targetWidth * previewFrame.width
        targetBox.height = viewModel.targetHeight * previewFrame.height
    }

    FileDialog {
        id: fileDialog
        title: "选择关键词截图"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["图片 (*.png *.jpg *.jpeg *.heic)"]
        onAccepted: root.viewModel.addFileUrls(selectedFiles)
    }

    FolderDialog {
        id: inputFolderDialog
        title: "选择截图文件夹（只读取当前层）"
        onAccepted: root.viewModel.addFolderUrl(selectedFolder)
    }

    FolderDialog {
        id: exportFolderDialog
        title: "选择导出位置"
        onAccepted: root.viewModel.exportToFolder(selectedFolder)
    }

    Connections {
        target: root.viewModel
        function onStateChanged() {
            root.syncTargetGeometry()
            if (root.viewModel.itemCount === 0)
                root.stopPreviewPlayback(false)
            else if (!root.previewPlaying)
                root.syncPlaybackToSelection()
        }
    }

    Timer {
        id: previewTimer
        interval: root.previewFrameInterval
        repeat: true
        onTriggered: root.advancePreviewPlayback()
    }

    onEnabledChanged: {
        if (!enabled)
            stopPreviewPlayback(false)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Themes.Theme.spaceMd

        PageHeader {
            Layout.fillWidth: true
            eyebrow: "工具 04 / 04 · MAC VISION"
            title: "关键词快切"
            description: "导入截图，自动锁定同一关键词，再输出对齐图片、帧序列或视频。"
            statusText: root.viewModel.statusText
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Themes.Theme.spaceMd

            SurfacePanel {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Themes.Theme.spaceMd
                    spacing: Themes.Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: "对齐画布"
                            color: Themes.Theme.text
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontTitle
                            font.weight: Font.DemiBold
                        }
                        Item { Layout.fillWidth: true }
                        MetricChip { label: "比例"; value: aspectPicker.currentText }
                        MetricChip {
                            label: "输出"
                            value: root.viewModel.outputWidth + " × " + root.viewModel.outputHeight
                        }
                        MetricChip {
                            label: "总帧"
                            value: String(root.viewModel.itemCount * root.viewModel.framesPerImage)
                        }
                    }

                    Rectangle {
                        id: neutralCanvas
                        objectName: "neutralCanvas"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: Themes.Theme.canvas
                        radius: Math.max(6, Themes.Theme.controlRadius)
                        border.color: Themes.Theme.border
                        clip: true

                        DropArea {
                            anchors.fill: parent
                            onDropped: function(drop) {
                                if (drop.hasUrls) {
                                    root.viewModel.addFileUrls(drop.urls)
                                    drop.acceptProposedAction()
                                }
                            }
                        }

                        Rectangle {
                            id: previewFrame
                            anchors.centerIn: parent
                            height: Math.max(80, Math.min(parent.height - 24,
                                (parent.width - 24) * root.viewModel.outputHeight /
                                root.viewModel.outputWidth))
                            width: Math.max(48, Math.min(parent.width - 24,
                                height * root.viewModel.outputWidth / root.viewModel.outputHeight))
                            color: "#090A0C"
                            border.color: Themes.Theme.border
                            clip: true

                            onWidthChanged: root.syncTargetGeometry()
                            onHeightChanged: root.syncTargetGeometry()
                            Component.onCompleted: root.syncTargetGeometry()

                            Image {
                                anchors.fill: parent
                                source: root.viewModel.previewUrl
                                fillMode: Image.Stretch
                                cache: false
                                asynchronous: false
                            }

                            Rectangle {
                                id: targetBox
                                objectName: "quickCutAlignmentBox"
                                visible: root.viewModel.itemCount > 0 && !root.previewPlaying
                                color: "#182F80ED"
                                border.width: 2
                                border.color: Themes.Theme.focus

                                Label {
                                    objectName: "quickCutAlignmentBoxLabel"
                                    anchors.left: parent.left
                                    anchors.bottom: parent.top
                                    anchors.bottomMargin: 4
                                    text: "关键词对齐框"
                                    color: Themes.Theme.text
                                    font.family: Themes.Theme.fontFamily
                                    font.pixelSize: 10
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    cursorShape: Qt.SizeAllCursor
                                    drag.target: targetBox
                                    drag.minimumX: 0
                                    drag.maximumX: previewFrame.width - targetBox.width
                                    drag.minimumY: 0
                                    drag.maximumY: previewFrame.height - targetBox.height
                                    onReleased: root.viewModel.updateTargetRect(
                                        targetBox.x / previewFrame.width,
                                        targetBox.y / previewFrame.height,
                                        targetBox.width / previewFrame.width,
                                        targetBox.height / previewFrame.height)
                                }

                                Rectangle {
                                    id: resizeHandle
                                    objectName: "quickCutAlignmentResizeHandle"
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    width: 14
                                    height: 14
                                    radius: 3
                                    color: Themes.Theme.focus
                                    property real startWidth: 0
                                    property real startHeight: 0
                                    property real pressX: 0
                                    property real pressY: 0

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.SizeFDiagCursor
                                        onPressed: function(mouse) {
                                            let point = resizeHandle.mapToItem(
                                                previewFrame, mouse.x, mouse.y)
                                            resizeHandle.pressX = point.x
                                            resizeHandle.pressY = point.y
                                            resizeHandle.startWidth = targetBox.width
                                            resizeHandle.startHeight = targetBox.height
                                        }
                                        onPositionChanged: function(mouse) {
                                            if (!pressed)
                                                return
                                            let point = resizeHandle.mapToItem(
                                                previewFrame, mouse.x, mouse.y)
                                            let relativeX = (point.x - resizeHandle.pressX) /
                                                            resizeHandle.startWidth
                                            let relativeY = (point.y - resizeHandle.pressY) /
                                                            resizeHandle.startHeight
                                            let requestedScale = Math.abs(relativeX) >= Math.abs(relativeY) ?
                                                        1 + relativeX : 1 + relativeY
                                            let minimumScale = Math.max(
                                                12 / resizeHandle.startWidth,
                                                12 / resizeHandle.startHeight)
                                            let maximumScale = Math.min(
                                                (previewFrame.width - targetBox.x) /
                                                    resizeHandle.startWidth,
                                                (previewFrame.height - targetBox.y) /
                                                    resizeHandle.startHeight)
                                            let scale = Math.max(minimumScale,
                                                Math.min(maximumScale, requestedScale))
                                            // 统一缩放，保证唯一对齐框始终覆盖完整关键词范围。
                                            targetBox.width = resizeHandle.startWidth * scale
                                            targetBox.height = resizeHandle.startHeight * scale
                                        }
                                        onReleased: root.viewModel.updateTargetRect(
                                            targetBox.x / previewFrame.width,
                                            targetBox.y / previewFrame.height,
                                            targetBox.width / previewFrame.width,
                                            targetBox.height / previewFrame.height)
                                    }
                                }
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: root.viewModel.itemCount === 0
                                text: "拖入截图，或从右侧导入"
                                color: Themes.Theme.secondary
                                font: Themes.Theme.bodyFont
                            }

                            Rectangle {
                                id: previewPlaybackBar
                                objectName: "previewPlaybackBar"
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 48
                                z: 20
                                visible: root.viewModel.itemCount > 0
                                color: "#D9141720"
                                border.color: "#4DFFFFFF"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 10
                                    spacing: Themes.Theme.spaceSm

                                    XyButton {
                                        objectName: "previewPlaybackButton"
                                        implicitWidth: 80
                                        implicitHeight: 36
                                        text: root.previewPlaying ? "暂停" : "播放"
                                        selected: root.previewPlaying
                                        quiet: !root.previewPlaying
                                        enabled: root.viewModel.itemCount > 0 &&
                                                 !root.viewModel.busy
                                        onClicked: root.togglePreviewPlayback()
                                    }
                                    XyProgressBar {
                                        objectName: "previewPlaybackProgress"
                                        Layout.fillWidth: true
                                        value: root.previewTotalFrames > 0 ?
                                                   root.previewFrameIndex /
                                                   root.previewTotalFrames : 0
                                        trackVisible: root.viewModel.itemCount > 0
                                    }
                                    Label {
                                        objectName: "previewPlaybackPosition"
                                        text: root.viewModel.itemCount > 0 ?
                                                  (root.viewModel.selectedIndex + 1) + " / " +
                                                  root.viewModel.itemCount : "0 / 0"
                                        color: "#F5F7FA"
                                        font.family: Themes.Theme.fontFamily
                                        font.pixelSize: Themes.Theme.fontCaption
                                    }
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 8
                        columnSpacing: Themes.Theme.spaceSm
                        rowSpacing: Themes.Theme.spaceXs

                        Label { text: "关键词"; color: Themes.Theme.secondary; font: Themes.Theme.bodyFont }
                        XyTextField {
                            id: keywordField
                            objectName: "quickCutKeywordField"
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            text: root.viewModel.keyword
                            placeholderText: "输入要识别的关键词"
                            onEditingFinished: root.viewModel.setKeyword(text)
                        }
                        Label { text: "候选"; color: Themes.Theme.secondary; font: Themes.Theme.bodyFont }
                        XyComboBox {
                            Layout.columnSpan: 3
                            Layout.fillWidth: true
                            model: root.viewModel.candidateLabels
                            currentIndex: root.viewModel.selectedCandidateIndex
                            enabled: count > 0 && !root.viewModel.busy
                            onActivated: function(index) { root.viewModel.selectCandidate(index) }
                        }
                        XyButton {
                            text: "复位识别框"
                            quiet: true
                            enabled: !root.viewModel.busy
                            onClicked: root.viewModel.resetTargetRect()
                        }

                        Label { text: "画面"; color: Themes.Theme.secondary; font: Themes.Theme.bodyFont }
                        XyComboBox {
                            id: aspectPicker
                            model: ["9:16", "16:9", "1:1", "4:5", "3:4", "自定义"]
                            currentIndex: root.viewModel.aspectRatioIndex
                            onActivated: function(index) { root.viewModel.setAspectRatio(index) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            XyTextField {
                                Layout.preferredWidth: 76
                                text: String(root.viewModel.outputWidth)
                                inputMethodHints: Qt.ImhDigitsOnly
                                onEditingFinished: root.viewModel.setResolution(
                                    text, String(root.viewModel.outputHeight))
                            }
                            Label { text: "×"; color: Themes.Theme.secondary }
                            XyTextField {
                                Layout.preferredWidth: 76
                                text: String(root.viewModel.outputHeight)
                                inputMethodHints: Qt.ImhDigitsOnly
                                onEditingFinished: root.viewModel.setResolution(
                                    String(root.viewModel.outputWidth), text)
                            }
                        }
                        Label { text: "帧率"; color: Themes.Theme.secondary; font: Themes.Theme.bodyFont }
                        XyTextField {
                            Layout.preferredWidth: 76
                            text: String(root.viewModel.frameRate)
                            onEditingFinished: root.viewModel.setFrameRate(text)
                        }
                        Label { text: "每图帧数"; color: Themes.Theme.secondary; font: Themes.Theme.bodyFont }
                        XyTextField {
                            Layout.preferredWidth: 76
                            text: String(root.viewModel.framesPerImage)
                            inputMethodHints: Qt.ImhDigitsOnly
                            onEditingFinished: {
                                root.stopPreviewPlayback(true)
                                root.viewModel.setFramesPerImage(text)
                            }
                        }
                        XyComboBox {
                            model: ["处理后 PNG", "逐帧 PNG", "MP4"]
                            currentIndex: root.viewModel.exportModeIndex
                            onActivated: function(index) { root.viewModel.setExportMode(index) }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        XyProgressBar {
                            Layout.fillWidth: true
                            value: root.viewModel.progressValue
                            trackVisible: root.viewModel.busy || root.viewModel.progressValue > 0
                        }
                        XyButton {
                            objectName: "recognizeQuickCutButton"
                            text: root.viewModel.busy ? "取消" : "开始识别"
                            prominent: !root.viewModel.busy && !root.viewModel.canExport
                            enabled: root.viewModel.busy || root.viewModel.canRecognize
                            onClicked: root.viewModel.busy ? root.viewModel.cancel() :
                                                            root.viewModel.recognizeAll()
                        }
                        XyButton {
                            objectName: "exportQuickCutButton"
                            text: "导出"
                            prominent: true
                            enabled: root.viewModel.canExport
                            onClicked: exportFolderDialog.open()
                        }
                    }
                }
            }

            SurfacePanel {
                Layout.preferredWidth: 310
                Layout.minimumWidth: 280
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Themes.Theme.spaceMd
                    spacing: Themes.Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: "图片队列"
                            color: Themes.Theme.text
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontTitle
                            font.weight: Font.DemiBold
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                            text: root.viewModel.itemCount + " 张"
                            color: Themes.Theme.secondary
                            font: Themes.Theme.bodyFont
                        }
                    }

                    ListView {
                        id: quickCutQueue
                        objectName: "quickCutQueue"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 6
                        boundsBehavior: Flickable.StopAtBounds
                        model: root.viewModel.itemsModel
                        activeFocusOnTab: true
                        currentIndex: root.viewModel.selectedIndex

                        function activateIndex(index) {
                            forceActiveFocus()
                            root.selectPreviewIndex(index)
                            positionViewAtIndex(index, ListView.Contain)
                        }

                        function selectRelative(delta) {
                            root.stopPreviewPlayback(false)
                            root.viewModel.selectRelative(delta)
                            root.syncPlaybackToSelection()
                            if (root.viewModel.selectedIndex >= 0)
                                positionViewAtIndex(root.viewModel.selectedIndex, ListView.Contain)
                        }

                        Keys.onUpPressed: function(event) {
                            selectRelative(-1)
                            event.accepted = true
                        }
                        Keys.onDownPressed: function(event) {
                            selectRelative(1)
                            event.accepted = true
                        }

                        move: Transition {
                            enabled: Themes.Motion.policy !== Themes.Motion.none
                            NumberAnimation {
                                property: "y"
                                duration: Themes.Motion.reorder
                                easing.type: Easing.OutCubic
                            }
                        }
                        displaced: Transition {
                            enabled: Themes.Motion.policy !== Themes.Motion.none
                            NumberAnimation {
                                property: "y"
                                duration: Themes.Motion.reorder
                                easing.type: Easing.OutCubic
                            }
                        }

                        delegate: Rectangle {
                            id: queueRow
                            required property int index
                            required property string name
                            required property string itemId
                            required property url thumbnailUrl
                            required property string recognitionState
                            required property int candidateCount
                            required property bool selected
                            width: quickCutQueue.width
                            height: 64
                            z: dragArea.drag.active ? 2 : 0
                            radius: Themes.Theme.controlRadius
                            color: selected ? Themes.Theme.selection : Themes.Theme.panelAlt
                            border.color: selected ? Themes.Theme.focus : Themes.Theme.border

                            Drag.active: dragArea.drag.active
                            Drag.source: queueRow
                            Drag.keys: [queueRow.itemId]
                            Drag.hotSpot.x: width / 2
                            Drag.hotSpot.y: height / 2

                            DropArea {
                                anchors.fill: parent
                                onEntered: function(drag) {
                                    if (drag.keys.length > 0 && drag.keys[0] !== queueRow.itemId)
                                        root.viewModel.moveItem(drag.keys[0], queueRow.itemId)
                                }
                            }

                            MouseArea {
                                id: dragArea
                                anchors.fill: parent
                                drag.target: queueRow
                                drag.axis: Drag.YAxis
                                cursorShape: drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                                onClicked: quickCutQueue.activateIndex(queueRow.index)
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 6
                                spacing: 6
                                Image {
                                    Layout.preferredWidth: 38
                                    Layout.preferredHeight: 46
                                    source: queueRow.thumbnailUrl
                                    fillMode: Image.PreserveAspectCrop
                                    asynchronous: true
                                    sourceSize.width: 96
                                    sourceSize.height: 96
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1
                                    Label {
                                        Layout.fillWidth: true
                                        text: (queueRow.index + 1) + ". " + queueRow.name
                                        color: Themes.Theme.text
                                        font: Themes.Theme.bodyFont
                                        elide: Text.ElideMiddle
                                    }
                                    Label {
                                        text: queueRow.recognitionState +
                                              (queueRow.candidateCount > 1 ?
                                               " · " + queueRow.candidateCount + " 个候选" : "")
                                        color: queueRow.recognitionState === "识别失败" ?
                                               Themes.Theme.danger : Themes.Theme.secondary
                                        font.family: Themes.Theme.fontFamily
                                        font.pixelSize: 10
                                    }
                                }
                                XyButton {
                                    text: "↑"
                                    implicitWidth: 34
                                    compact: true
                                    quiet: true
                                    enabled: queueRow.index > 0 && !root.viewModel.busy
                                    onClicked: {
                                        root.stopPreviewPlayback(true)
                                        root.viewModel.moveIndex(queueRow.index, -1)
                                    }
                                }
                                XyButton {
                                    text: "↓"
                                    implicitWidth: 34
                                    compact: true
                                    quiet: true
                                    enabled: queueRow.index < root.viewModel.itemCount - 1 &&
                                             !root.viewModel.busy
                                    onClicked: {
                                        root.stopPreviewPlayback(true)
                                        root.viewModel.moveIndex(queueRow.index, 1)
                                    }
                                }
                                XyButton {
                                    text: "×"
                                    implicitWidth: 34
                                    compact: true
                                    quiet: true
                                    destructive: true
                                    enabled: !root.viewModel.busy
                                    onClicked: {
                                        root.stopPreviewPlayback(true)
                                        root.viewModel.removeIndex(queueRow.index)
                                    }
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: root.viewModel.itemCount === 0
                            text: "暂无图片\n支持 PNG / JPG / HEIC"
                            horizontalAlignment: Text.AlignHCenter
                            color: Themes.Theme.secondary
                            font: Themes.Theme.bodyFont
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        XyButton {
                            objectName: "importQuickCutFilesButton"
                            Layout.fillWidth: true
                            text: "导入图片"
                            prominent: root.viewModel.itemCount === 0
                            enabled: !root.viewModel.busy
                            onClicked: fileDialog.open()
                        }
                        XyButton {
                            Layout.fillWidth: true
                            text: "导入文件夹"
                            enabled: !root.viewModel.busy
                            onClicked: inputFolderDialog.open()
                        }
                    }
                }
            }
        }
    }
}
