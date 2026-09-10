import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../Components"
import "../Dialogs"
import "../Themes" as Themes

Item {
    id: root
    objectName: "cleanupPage"

    required property var viewModel

    ColumnLayout {
        anchors.fill: parent
        spacing: Themes.Theme.spaceLg

        PageHeader {
            Layout.fillWidth: true
            eyebrow: "工具 02 / 04"
            title: "RAW / JPG 配对清理"
            description: "只找出同目录下没有配对的照片，确认后移入系统废纸篓。"
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
                        objectName: "cleanupDirectory"
                        Layout.fillWidth: true
                        accessibleName: "配对清理照片文件夹"
                        placeholderText: "选择或拖入照片文件夹"
                        text: root.viewModel.folderPath
                        dropEnabled: !root.viewModel.busy
                        onFolderDropped: function(folderUrl) {
                            root.viewModel.setFolderUrl(folderUrl)
                        }
                    }

                    XyButton {
                        objectName: "chooseCleanupFolderButton"
                        Layout.fillWidth: true
                        text: "选择照片文件夹"
                        prominent: root.viewModel.folderPath.length === 0
                        enabled: !root.viewModel.busy
                        onClicked: folderDialog.open()
                    }

                    Label {
                        objectName: "cleanupFormatLabel"
                        Layout.topMargin: Themes.Theme.spaceSm
                        text: "选择要清除的格式"
                        color: Themes.Theme.secondary
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: Themes.Theme.fontCaption
                        font.weight: Font.DemiBold
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        XyButton {
                            objectName: "cleanupKindJpgButton"
                            Layout.fillWidth: true
                            checkable: true
                            checked: root.viewModel.deleteKind === "JPG"
                            selected: checked
                            text: "JPG"
                            enabled: !root.viewModel.busy
                            onClicked: root.viewModel.deleteKind = "JPG"
                        }
                        XyButton {
                            objectName: "cleanupKindRawButton"
                            Layout.fillWidth: true
                            checkable: true
                            checked: root.viewModel.deleteKind === "RAW"
                            selected: checked
                            text: "RAW"
                            enabled: !root.viewModel.busy
                            onClicked: root.viewModel.deleteKind = "RAW"
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Themes.Theme.tableGrid
                        Layout.topMargin: Themes.Theme.spaceSm
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
                            label: "待处理"
                            value: root.viewModel.itemCount
                        }
                        MetricChip {
                            Layout.fillWidth: true
                            label: "RAW / JPG"
                            value: (root.viewModel.stats.rawCount || 0) + " / " +
                                   (root.viewModel.stats.jpgCount || 0)
                        }
                        MetricChip {
                            Layout.fillWidth: true
                            label: "已配对"
                            value: root.viewModel.stats.pairedTargetCount || 0
                        }
                    }

                    Item { Layout.fillHeight: true }

                    XyProgressBar {
                        objectName: "cleanupProgress"
                        Layout.fillWidth: true
                        value: root.viewModel.progressValue
                        trackVisible: root.viewModel.busy || root.viewModel.progressValue > 0
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        XyButton {
                            objectName: "scanCleanupButton"
                            Layout.fillWidth: true
                            text: "扫描预览"
                            prominent: root.viewModel.canScan
                            enabled: root.viewModel.canScan
                            onClicked: root.viewModel.scan()
                        }
                        XyButton {
                            objectName: "cancelCleanupButton"
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
                            text: "废纸篓操作前预览"
                            color: Themes.Theme.text
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontTitle
                            font.weight: Font.DemiBold
                        }
                        Item { Layout.fillWidth: true }
                        MetricChip {
                            label: "清除格式"
                            value: root.viewModel.deleteKind
                        }
                        MetricChip {
                            label: "孤立文件"
                            value: root.viewModel.itemCount
                        }
                    }

                    DataTable {
                        objectName: "cleanupPreviewTable"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: [
                            { title: "文件名", key: "name", width: 280 },
                            { title: "缺少配对", key: "missing", width: 160 },
                            { title: "处理方式", key: "action", width: 190 }
                        ]
                        rows: root.viewModel.itemsModel
                        emptyText: root.viewModel.busy ? "正在检查配对…" :
                                   "选择文件夹并扫描后，这里显示孤立文件"
                        emptyHint: "扫描只生成清单，不会立即移入废纸篓"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Themes.Theme.spaceSm

                        Label {
                            Layout.fillWidth: true
                            text: root.viewModel.busy && !root.viewModel.taskCancellable ?
                                      "正在写入恢复记录，完成前不可中断" :
                                      "所有项目只会移入系统废纸篓"
                            color: Themes.Theme.tertiary
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontCaption
                        }
                        XyButton {
                            objectName: "restoreCleanupButton"
                            text: "恢复最近一次"
                            quiet: true
                            enabled: root.viewModel.canRestore
                            onClicked: root.viewModel.restore()
                        }
                        XyButton {
                            objectName: "executeCleanupButton"
                            text: "移入废纸篓"
                            destructive: true
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
        objectName: "cleanupFolderDialog"
        title: "选择要检查 RAW / JPG 配对的文件夹"
        onAccepted: root.viewModel.setFolderUrl(selectedFolder)
    }

    ConfirmDialog {
        id: confirmDialog
        objectName: "cleanupConfirmDialog"
        anchors.centerIn: Overlay.overlay
        destructive: true
        onConfirmed: root.viewModel.executeConfirmed()
    }

    FeedbackToast {
        id: toast
        objectName: "cleanupToast"
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
