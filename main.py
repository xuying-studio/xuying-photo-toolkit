#!/usr/bin/env python3
"""旭影工具箱启动入口。"""

import json
import sys
from pathlib import Path

from photo_assistant.gui import run
from photo_assistant.selftest import run_windows_recycle_self_test


def main() -> int:
    """启动界面，或执行构建流程使用的 Windows 回收站自测。"""

    if len(sys.argv) == 3 and sys.argv[1] == "--windows-recycle-self-test":
        report_path = Path(sys.argv[2])
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = run_windows_recycle_self_test(report_path.parent)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return 0 if report.get("success") else 1

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
