from datetime import datetime
from pathlib import Path

from xuying_toolbox.application.cleanup import CleanupUseCase
from xuying_toolbox.application.rename import RenameUseCase
from xuying_toolbox.application.xmp_sync import XmpSyncUseCase
from xuying_toolbox.infrastructure.composition import (
    create_macos_cleanup_use_case,
    create_rename_use_case,
    create_xmp_sync_use_case,
)
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths


class FixedMetadata:
    def capture_time(self, _path: Path) -> datetime:
        return datetime(2026, 9, 6, 10, 0)


def test_local_composition_builds_all_three_headless_use_cases(tmp_path: Path) -> None:
    paths = SupportPaths.from_root(tmp_path / "support")

    rename = create_rename_use_case(paths, FixedMetadata())
    cleanup = create_macos_cleanup_use_case(
        paths,
        send_to_trash=lambda _path: None,
        restore_fallback=lambda *_args: (False, "fixture"),
    )
    xmp = create_xmp_sync_use_case(paths)

    assert isinstance(rename, RenameUseCase)
    assert isinstance(cleanup, CleanupUseCase)
    assert isinstance(xmp, XmpSyncUseCase)
