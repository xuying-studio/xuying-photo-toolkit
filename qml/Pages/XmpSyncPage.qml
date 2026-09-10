import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../Components"
import "../Dialogs"
import "../Themes" as Themes

Item {
    id: root
    objectName: "xmpSyncPage"

    required property var viewModel

    ColumnLayout {
        anchors.fill: parent
        spacing: Themes.Theme.spaceLg

        PageHeader {
            Layout.fillWidth: true
            eyebrow: "工具 03 / 04"
            title: "颜色星标同步"
            description: "在同名 JPG 与 RAW 侧车之间同步星标和颜色标签，RAW 原文件始终不改。"
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
                        objectName: "xmpDirectory"
                        Layout.fillWidth: true
                        accessibleName: "颜色星标同步照片文件夹"
                        placeholderText: "选择或拖入照片文件夹"
                        text: root.viewModel.folderPath
                        dropEnabled: !root.viewModel.busy
                        onFolderDropped: function(folderUrl) {
                            root.viewModel.setFolderUrl(folderUrl)
                        }
                    }

                    XyButton {
                        objectName: "chooseXmpFolderButton"
                        Layout.fillWidth: true
                        text: "选择照片文件夹"
                        prominent: root.viewModel.folderPath.length === 0
                        enabled: !root.viewModel.busy
                        onClicked: folderDialog.open()
                    }

                    Label {
                        Layout.topMargin: Themes.Theme.spaceSm
                        text: "同步方向"
                        color: Themes.Theme.secondary
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: Themes.Theme.fontCaption
                        font.weight: Font.DemiBold
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        XyButton {
                            objectName: "xmpDirectionJpgRawButton"
                            Layout.fillWidth: true
                            checkable: true
                            checked: root.viewModel.direction === "JPG → RAW"
                            selected: checked
                            text: "JPG → RAW"
                            enabled: !root.viewModel.busy
                            onClicked: root.viewModel.direction = "JPG → RAW"
                        }
                        XyButton {
                            objectName: "xmpDirectionRawJpgButton"
                            Layout.fillWidth: true
                            checkable: true
                            checked: root.viewModel.direction === "RAW → JPG"
                            selected: checked
                            text: "RAW → JPG"
                            enabled: !root.viewModel.busy
                            onClicked: root.viewModel.direction = "RAW → JPG"
                        }
                    }

                    Label {
                        text: "同步内容"
                        color: Themes.Theme.secondary
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: Themes.Theme.fontCaption
                        font.weight: Font.DemiBold
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        XyButton {
                            objectName: "syncRatingButton"
                            Layout.fillWidth: true
                            checkable: true
                            checked: root.viewModel.syncRating
                            selected: checked
                            text: checked ? "✓ 星标" : "星标"
                            enabled: !root.viewModel.busy
                            onToggled: root.viewModel.syncRating = checked
                        }
                        XyButton {
                            objectName: "syncLabelButton"
                            Layout.fillWidth: true
                            checkable: true
                            checked: root.viewModel.syncLabel
                            selected: checked
                            text: checked ? "✓ 颜色标签" : "颜色标签"
                            enabled: !root.viewModel.busy
                            onToggled: root.viewModel.syncLabel = checked
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Themes.Theme.tableGrid
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Themes.Theme.spaceSm
                        rowSpacing: Themes.Theme.spaceSm

                        MetricChip {
                            Layout.fillWidth: true
                            label: "全部照片"
                            value: root.viewModel.stats.totalImages || 0
                        }
                        MetricChip {
                            Layout.fillWidth: true
                            label: "待同步"
                            value: root.viewModel.operationCount
                        }
                        MetricChip {
                            Layout.fillWidth: true
                            label: "成功匹配"
                            value: root.viewModel.stats.matchedCount || 0
                        }
                        MetricChip {
                            Layout.fillWidth: true
                            label: "带标记"
                            value: root.viewModel.stats.markedCount || 0
                        }
                    }

                    Item { Layout.fillHeight: true }

                    XyProgressBar {
                        objectName: "xmpProgress"
                        Layout.fillWidth: true
                        value: root.viewModel.progressValue
                        trackVisible: root.viewModel.busy || root.viewModel.progressValue > 0
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        XyButton {
                            objectName: "scanXmpButton"
                            Layout.fillWidth: true
                            text: "扫描预览"
                            prominent: root.viewModel.canScan
                            enabled: root.viewModel.canScan
                            onClicked: root.viewModel.scan()
                        }
                        XyButton {
                            objectName: "cancelXmpButton"
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
                            text: "XMP 写入前差异预览"
                            color: Themes.Theme.text
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontTitle
                            font.weight: Font.DemiBold
                        }
                        Item { Layout.fillWidth: true }
                        MetricChip {
                            label: "同步方向"
                            value: root.viewModel.direction
                        }
                        MetricChip {
                            label: "已是最新"
                            value: root.viewModel.stats.upToDateCount || 0
                        }
                    }

                    DataTable {
                        objectName: "xmpPreviewTable"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: [
                            { title: "来源", key: "source", width: 210 },
                            { title: "目标", key: "target", width: 210 },
                            { title: "星标变化", key: "rating", width: 120 },
                            { title: "颜色标签变化", key: "label", width: 170 }
                        ]
                        rows: root.viewModel.operationsModel
                        emptyText: root.viewModel.busy ? "正在读取 XMP 标记…" :
                                   "选择文件夹并扫描后，这里显示星标与颜色差异"
                        emptyHint: "扫描只比较差异，不会立即写入 XMP"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        Label {
                            Layout.fillWidth: true
                            text: root.viewModel.busy && !root.viewModel.taskCancellable ?
                                      "正在备份或原子写入，完成前不可中断" :
                                      (root.viewModel.direction === "JPG → RAW" ?
                                           "RAW 原文件不会被修改" :
                                           "JPG 将保留完整字节备份")
                            color: Themes.Theme.tertiary
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontCaption
                        }
                        XyButton {
                            objectName: "undoXmpButton"
                            text: "撤回最近一次"
                            quiet: true
                            enabled: root.viewModel.canUndo
                            onClicked: root.viewModel.undo()
                        }
                        XyButton {
                            objectName: "executeXmpButton"
                            text: "确认同步"
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
        objectName: "xmpFolderDialog"
        title: "选择要同步 Adobe XMP 标记的文件夹"
        onAccepted: root.viewModel.setFolderUrl(selectedFolder)
    }

    ConfirmDialog {
        id: confirmDialog
        objectName: "xmpConfirmDialog"
        anchors.centerIn: Overlay.overlay
        onConfirmed: root.viewModel.executeConfirmed()
    }

    FeedbackToast {
        id: toast
        objectName: "xmpToast"
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
