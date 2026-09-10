from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.qml
@pytest.mark.parametrize("scale_factor", ("1", "2"))
def test_module_entrypoint_starts_and_exits(tmp_path: Path, scale_factor: str) -> None:
    root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment.update(
        {
            "QT_QPA_PLATFORM": "offscreen",
            "QT_SCALE_FACTOR": scale_factor,
            "XUYING_AUTO_QUIT_MS": "250",
            "XUYING_LOG_DIR": str(tmp_path / "logs"),
            "XUYING_QML_DIR": str(root / "qml"),
        }
    )

    completed = subprocess.run(
        [sys.executable, "-m", "xuying_toolbox"],
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / "logs" / "xuying-toolbox.log").is_file()
