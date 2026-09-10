"""应用级外观设置与迁移提示。"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from xuying_toolbox.infrastructure.persistence.application_settings import (
    ApplicationSettings,
    JsonApplicationSettingsStore,
)


class ApplicationSettingsViewModel(QObject):
    settingsChanged = Signal()

    def __init__(
        self,
        store: JsonApplicationSettingsStore,
        *,
        recovery_migration_summary: str = "",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._settings = store.load()
        self._migration_summary = " ".join(
            part for part in (store.migration_summary, recovery_migration_summary) if part
        )

    @Property(str, notify=settingsChanged)
    def themeId(self) -> str:
        return self._settings.theme_id

    @Property(str, constant=True)
    def migrationSummary(self) -> str:
        return self._migration_summary

    @Slot(str)
    def setThemeId(self, theme_id: str) -> None:
        if theme_id == self._settings.theme_id:
            return
        settings = ApplicationSettings(theme_id=theme_id)
        self._store.save(settings)
        self._settings = settings
        self.settingsChanged.emit()


__all__ = ["ApplicationSettingsViewModel"]
