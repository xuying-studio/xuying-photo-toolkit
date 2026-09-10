import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../Components"
import "../Dialogs"
import "../Themes" as Themes

Item {
    id: root
    objectName: "renamePage"

    required property var viewModel

    ColumnLayout {
        anchors.fill: parent
        spacing: Themes.Theme.spaceLg

        PageHeader {
            Layout.fillWidth: true
            eyebrow: "工具 01 / 04"
            title: "时间重命名"
            description: "按拍摄时间整理 RAW、JPG 与两种 XMP 侧车，执行前完整检查冲突。"
            statusText: root.viewModel.statusText
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Themes.Theme.spaceLg

            SurfacePanel {
                Layout.preferredWidth: 360
                Layout.minimumWidth: 330
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Themes.Theme.spaceXl
                    spacing: Themes.Theme.spaceMd

                    FolderDropField {
                        objectName: "renameDirectory"
                        Layout.fillWidth: true
                        accessibleName: "照片文件夹"
                        placeholderText: "选择或拖入照片文件夹"
                        text: root.viewModel.folderPath
                        dropEnabled: !root.viewModel.busy
                        onFolderDropped: function(folderUrl) {
                            root.viewModel.setFolderUrl(folderUrl)
                        }
                    }

                    XyButton {
                        objectName: "chooseFolderButton"
                        Layout.fillWidth: true
                        text: "选择照片文件夹"
                        prominent: root.viewModel.folderPath.length === 0
                        enabled: !root.viewModel.busy
                        onClicked: folderDialog.open()
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Themes.Theme.tableGrid
                        Layout.topMargin: Themes.Theme.spaceSm
                    }

                    Label {
                        text: "扫描概览"
                        color: Themes.Theme.secondary
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: Themes.Theme.fontCaption
                        font.weight: Font.DemiBold
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Themes.Theme.spaceSm
                        rowSpacing: Themes.Theme.spaceSm

                        MetricChip {
                            Layout.fillWidth: true
                            label: "照片"
                            value: root.viewModel.stats.totalImages || 0
                        }
                        MetricChip {
                            Layout.fillWidth: true
                            label: "待改名"
                            value: root.viewModel.operationCount
                        }
                        MetricChip {
                            Layout.fillWidth: true
                            label: "RAW / JPG"
                            value: (root.viewModel.stats.rawCount || 0) + " / " +
                                   (root.viewModel.stats.jpgCount || 0)
                        }
                        MetricChip {
                            Layout.fillWidth: true
                            label: "XMP 侧车"
                            value: root.viewModel.stats.xmpCount || 0
                        }
                    }

                    Item { Layout.fillHeight: true }

                    XyProgressBar {
                        objectName: "renameProgress"
                        Layout.fillWidth: true
                        value: root.viewModel.progressValue
                        trackVisible: root.viewModel.busy || root.viewModel.progressValue > 0
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        XyButton {
                            objectName: "scanRenameButton"
                            Layout.fillWidth: true
                            text: "扫描预览"
                            prominent: root.viewModel.canScan
                            enabled: root.viewModel.canScan
                            onClicked: root.viewModel.scan()
                        }
                        XyButton {
                            objectName: "cancelRenameButton"
                            Layout.fillWidth: true
                            visible: root.viewModel.busy && root.viewModel.taskCancellable
                            text: "取消扫描"
                            quiet: true
                            onClicked: root.viewModel.cancel()
                        }
                    }
                }
            }

            SurfacePanel {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Themes.Theme.spaceLg
                    spacing: Themes.Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: "执行前预览"
                            color: Themes.Theme.text
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontTitle
                            font.weight: Font.DemiBold
                        }
                        Item { Layout.fillWidth: true }
                        MetricChip { label: "已命名"; value: root.viewModel.stats.alreadyNamedCount || 0 }
                        MetricChip { label: "跳过"; value: root.viewModel.stats.skippedCount || 0 }
                        MetricChip { label: "冲突"; value: root.viewModel.conflictCount }
                    }

                    DataTable {
                        objectName: "previewTable"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: [
                            { title: "原文件名", key: "source", width: 250 },
                            { title: "新文件名", key: "target", width: 250 },
                            { title: "类型", key: "kind", width: 120 }
                        ]
                        rows: root.viewModel.operationsModel
                        emptyText: root.viewModel.busy ? "正在生成预览…" :
                                   "选择文件夹并扫描后，这里显示新旧名称"
                        emptyHint: "扫描只生成预览，不会立即修改文件"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        Label {
                            Layout.fillWidth: true
                            text: root.viewModel.busy && !root.viewModel.taskCancellable ?
                                      "正在原子提交，完成前不可中断" :
                                      "不会覆盖同名文件"
                            color: Themes.Theme.tertiary
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontCaption
                        }
                        XyButton {
                            objectName: "undoRenameButton"
                            text: "撤回最近一次"
                            quiet: true
                            enabled: root.viewModel.canUndo
                            onClicked: root.viewModel.undo()
                        }
                        XyButton {
                            objectName: "executeRenameButton"
                            text: "确认执行"
                            prominent: true
                            enabled: root.viewModel.canExecute
                            onClicked: root.viewModel.requestExecute()
                        }
                    }
                }
            }
        }
    }

    FolderDialog {
        id: folderDialog
        objectName: "renameFolderDialog"
        title: "选择要按拍摄时间重命名的文件夹"
        onAccepted: root.viewModel.setFolderUrl(selectedFolder)
    }

    ConfirmDialog {
        id: confirmDialog
        objectName: "renameConfirmDialog"
        anchors.centerIn: Overlay.overlay
        onConfirmed: root.viewModel.executeConfirmed()
    }

    FeedbackToast {
        id: toast
        objectName: "renameToast"
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Themes.Theme.spaceXl
        z: 20
    }

    Connections {
        target: root.viewModel

        function onConfirmationRequested(title, description) {
            confirmDialog.titleText = title
            confirmDialog.description = description
            confirmDialog.open()
        }

        function onNotificationRequested(message, level) {
            toast.show(message, level)
        }
    }
}
