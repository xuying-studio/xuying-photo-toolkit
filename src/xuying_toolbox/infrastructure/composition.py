"""本地无界面用例的依赖装配；不放业务规则。"""

from __future__ import annotations

from collections.abc import Callable

from send2trash import send2trash

from xuying_toolbox.application.cleanup import CleanupUseCase
from xuying_toolbox.application.quickcut import QuickCutUseCase
from xuying_toolbox.application.rename import RenameUseCase
from xuying_toolbox.application.xmp_sync import XmpSyncUseCase
from xuying_toolbox.domain.ports.metadata import MetadataReader
from xuying_toolbox.infrastructure.filesystem.catalog import LocalPhotoCatalog
from xuying_toolbox.infrastructure.filesystem.quickcut_input import LocalQuickCutInputExpander
from xuying_toolbox.infrastructure.filesystem.rename_transaction import LocalRenameTransaction
from xuying_toolbox.infrastructure.imaging.quickcut_renderer import QtQuickCutRenderer
from xuying_toolbox.infrastructure.metadata.exif_reader import ExifMetadataReader
from xuying_toolbox.infrastructure.metadata.xmp_repository import LocalXmpRepository
from xuying_toolbox.infrastructure.metadata.xmp_transaction import LocalXmpTransaction
from xuying_toolbox.infrastructure.ocr.macos_vision import MacVisionOCRAdapter
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.infrastructure.persistence.rename_journal import JsonRenameJournal
from xuying_toolbox.infrastructure.video.ffmpeg_export import FFmpegQuickCutExporter
from xuying_toolbox.platform.macos.trash import (
    MacTrashAdapter,
    locate_trashed_file,
    restore_with_finder,
)


def create_rename_use_case(
    paths: SupportPaths,
    metadata_reader: MetadataReader | None = None,
) -> RenameUseCase:
    return RenameUseCase(
        LocalPhotoCatalog(),
        metadata_reader or ExifMetadataReader(),
        LocalRenameTransaction(),
        JsonRenameJournal(paths),
    )


def create_macos_cleanup_use_case(
    paths: SupportPaths,
    *,
    send_to_trash: Callable[[str], None] = send2trash,
    restore_fallback=restore_with_finder,
) -> CleanupUseCase:
    return CleanupUseCase(
        LocalPhotoCatalog(),
        MacTrashAdapter(
            paths,
            send_to_trash=send_to_trash,
            restore_fallback=restore_fallback,
            trash_locator=locate_trashed_file,
        ),
    )


def create_xmp_sync_use_case(paths: SupportPaths) -> XmpSyncUseCase:
    return XmpSyncUseCase(
        LocalPhotoCatalog(),
        LocalXmpRepository(),
        LocalXmpTransaction(paths),
    )


def create_macos_quickcut_use_case(
    renderer: QtQuickCutRenderer | None = None,
) -> QuickCutUseCase:
    shared_renderer = renderer or QtQuickCutRenderer()
    return QuickCutUseCase(
        MacVisionOCRAdapter(),
        FFmpegQuickCutExporter(shared_renderer),
        LocalQuickCutInputExpander(),
    )
