"""macOS 原生材质层的真实窗口生命周期测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="仅在 macOS 验证原生材质")
def test_native_visual_effect_reuses_handle_and_never_accepts_clicks() -> None:
    script = r'''
import json
from PySide6.QtGui import QGuiApplication, QWindow
from xuying_toolbox.platform.macos.visual_effect import MacVisualEffectAdapter

app = QGuiApplication(["mac-visual-effect-test"])
window = QWindow()
window.resize(640, 480)
window.show()
app.processEvents()
adapter = MacVisualEffectAdapter()
installed = adapter.install(window)
first = adapter.handle
second_install = adapter.install(window)
second = adapter.handle
adapter.set_active(False)
adapter.set_active(True)
result = {
    "installed": installed,
    "same_handle": first == second and second_install,
    "passes_hit_test": adapter.passes_hit_test(),
    "behind_content": adapter.is_behind_content(),
    "integrated_title_bar": adapter.uses_integrated_title_bar(),
    "background_window_drag": adapter.allows_background_window_drag(),
    "reduce_motion_type": type(adapter.system_reduce_motion()).__name__,
}
adapter.destroy()
result["destroyed"] = not adapter.installed
print(json.dumps(result))
window.close()
'''
    environment = dict(os.environ)
    environment["QT_QPA_PLATFORM"] = "cocoa"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
        timeout=20,
    )
    result = json.loads(completed.stdout.strip().splitlines()[-1])

    assert result == {
        "installed": True,
        "same_handle": True,
        "passes_hit_test": True,
        "behind_content": True,
        "integrated_title_bar": True,
        "background_window_drag": False,
        "reduce_motion_type": "bool",
        "destroyed": True,
    }
