"""创建文件名编码正确的 Windows 便携版 ZIP。"""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def create_portable_zip(source_dir: Path, output_path: Path) -> None:
    """将整个程序目录压缩，并保留顶层应用文件夹。"""

    if not source_dir.is_dir():
        raise FileNotFoundError(f"便携版目录不存在：{source_dir}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    with ZipFile(output_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source_dir)
            archive_name = (Path(source_dir.name) / relative).as_posix()
            archive.write(path, archive_name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    create_portable_zip(args.source_dir, args.output_path)


if __name__ == "__main__":
    main()
