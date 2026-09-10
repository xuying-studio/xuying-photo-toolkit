import logging

from xuying_toolbox.infrastructure.logging_config import LOGGER_NAME, configure_logging


def test_configure_logging_writes_utf8_file(tmp_path) -> None:
    log_path = configure_logging(tmp_path)
    logger = logging.getLogger(LOGGER_NAME)

    logger.info("中文日志验证")
    for handler in logger.handlers:
        handler.flush()

    assert log_path.is_file()
    assert "中文日志验证" in log_path.read_text(encoding="utf-8")
