"""工具间共享工作文件夹：任一工具选定路径，其余工具自动同步，切换工具无需重选。"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QObject


def bind_shared_folder(view_models: Iterable[QObject]) -> None:
    """绑定多个工具 ViewModel 的文件夹路径，使它们彼此同步。

    用户诉求：在任一工具页选定要处理的文件夹后，切换到其他工具页
    时路径保持不变，无需每次重新选择；要换路径时在任一工具里重新
    选择即可，其余工具跟随更新。

    各 ViewModel 的 folderPath setter 自带两道守卫：
    - 同值忽略：路径一致时不做任何事，同步链在值收敛后自然终止，
      不会形成无限循环；
    - busy 不打断：正在执行任务的工具不被同步打扰，任务结束后
      下次选择路径时再跟随。

    因此这里只需要简单地把「一个工具的路径变化」转发给其余工具，
    无需额外的去重或互斥逻辑。
    """
    models = list(view_models)
    for view_model in models:
        others = [other for other in models if other is not view_model]

        def forward(folder: str, targets=others) -> None:
            # targets 用默认参数绑定，避免闭包引用同一变量。
            for target in targets:
                target.folderPath = folder

        view_model.folderChanged.connect(forward)


__all__ = ["bind_shared_folder"]
