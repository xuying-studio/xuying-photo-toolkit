import QtQuick
import "../Themes" as Themes

XyComboBox {
    id: root
    objectName: "themePicker"
    implicitWidth: 174
    model: Themes.Theme.themes
    textRole: "name"
    currentIndex: Themes.Theme.themeIndex
    accessibleName: "界面皮肤"
    onActivated: function(index) {
        Themes.Theme.setTheme(Themes.Theme.themes[index].id)
    }
}
