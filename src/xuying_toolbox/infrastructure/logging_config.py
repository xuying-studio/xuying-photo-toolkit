"""应用日志目录和处理器配置。"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "xuying_toolbox"


def default_log_dir() -> Path:
    override = os.environ.get("XUYING_LOG_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "旭影工具箱"
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "旭影工具箱" / "logs"
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return base / "xuying-toolbox" / "logs"


def configure_logging(log_dir: Path | None = None) -> Path:
    """配置可轮转文件日志，并返回实际日志文件路径。"""

    directory = log_dir or default_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "xuying-toolbox.log"
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # 测试或二次启动时先关闭旧处理器，避免重复写入同一条日志。
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return log_path
