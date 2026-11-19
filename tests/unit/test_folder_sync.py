"""工具间共享文件夹路径同步的单元测试。"""

from __future__ import annotations

from pathlib import Path

from xuying_toolbox.presentation.folder_sync import bind_shared_folder
from xuying_toolbox.presentation.viewmodels.cleanup import CleanupViewModel
from xuying_toolbox.presentation.viewmodels.rename import RenameViewModel
from xuying_toolbox.presentation.viewmodels.xmp_sync import XmpSyncViewModel


class _RenameUseCaseStub:
    """RenameViewModel 构造所需的最小桩（初始化会读取可撤回状态）。"""

    can_undo = False

    def has_undo(self) -> bool:
        return False


class _CleanupUseCaseStub:
    """CleanupViewModel 构造所需的最小桩（初始化会读取可撤回状态）。"""

    def has_restore(self) -> bool:
        return False


class _XmpUseCaseStub:
    """XmpSyncViewModel 构造所需的最小桩（初始化会读取可撤回状态）。"""

    def has_undo(self) -> bool:
        return False


def _build_view_models() -> tuple[RenameViewModel, CleanupViewModel, XmpSyncViewModel]:
    return (
        RenameViewModel(_RenameUseCaseStub()),
        CleanupViewModel(_CleanupUseCaseStub()),
        XmpSyncViewModel(_XmpUseCaseStub()),
    )


def test_folder_selected_on_rename_syncs_to_other_tools(qtbot, tmp_path: Path) -> None:
    rename, cleanup, xmp = _build_view_models()
    bind_shared_folder([rename, cleanup, xmp])

    rename.folderPath = str(tmp_path)

    assert cleanup.folderPath == str(tmp_path)
    assert xmp.folderPath == str(tmp_path)


def test_folder_selected_on_any_tool_syncs_to_all_others(qtbot, tmp_path: Path) -> None:
    rename, cleanup, xmp = _build_view_models()
    bind_shared_folder([rename, cleanup, xmp])
    cleanup.folderPath = str(tmp_path)

    # 换路径：在任一工具里重选，其余工具全部跟随。
    rename.folderPath = str(tmp_path)

    assert cleanup.folderPath == str(tmp_path)
    assert xmp.folderPath == str(tmp_path)


def test_repeated_folder_set_does_not_loop(qtbot, tmp_path: Path) -> None:
    rename, cleanup, xmp = _build_view_models()
    bind_shared_folder([rename, cleanup, xmp])

    # 同步链依赖 setter 的同值守卫收敛；重复设置不应触发无限循环或异常。
    rename.folderPath = str(tmp_path)
    rename.folderPath = str(tmp_path)
    cleanup.folderPath = str(tmp_path)

    assert rename.folderPath == str(tmp_path)
    assert cleanup.folderPath == str(tmp_path)
    assert xmp.folderPath == str(tmp_path)


def test_busy_tool_is_not_disturbed_by_sync(
    qtbot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    rename, cleanup, xmp = _build_view_models()
    bind_shared_folder([rename, cleanup, xmp])

    # 模拟配对清理正在执行任务：busy 为 True 时，文件夹不被同步打扰。
    # 单测不经过 QML，用普通 property 替换 PySide6 Property 即可。
    monkeypatch.setattr(CleanupViewModel, "busy", property(lambda self: True))

    rename.folderPath = str(tmp_path)

    assert cleanup.folderPath == ""  # busy 守卫生效，路径保持原状
    assert rename.folderPath == str(tmp_path)
    assert xmp.folderPath == str(tmp_path)
