from pathlib import Path

from xuying_toolbox.infrastructure.persistence.paths import SupportPaths


def test_support_paths_use_isolated_v2_root(tmp_path: Path) -> None:
    paths = SupportPaths.from_root(tmp_path / "v2")

    paths.ensure_directories()

    assert paths.root == tmp_path / "v2"
    assert paths.rename_backups == paths.root / "rename_backups"
    assert paths.cleanup_undo == paths.root / "cleanup_undo.json"
    assert paths.xmp_backups == paths.root / "xmp_backups"
    assert paths.application_settings == paths.root / "application_settings.json"
    assert paths.migration_report == paths.root / "migration_report.json"
    assert paths.rename_backups.is_dir()
    assert paths.xmp_backups.is_dir()
    assert not paths.cleanup_undo.exists()
