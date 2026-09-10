"""后台任务共享的纯 Python 取消语义。"""


class TaskCancelledError(Exception):
    """可取消的只读任务已响应取消请求。"""


__all__ = ["TaskCancelledError"]
