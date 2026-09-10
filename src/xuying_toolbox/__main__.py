"""应用命令行入口。"""

from __future__ import annotations

from collections.abc import Sequence

from xuying_toolbox.bootstrap import run


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
