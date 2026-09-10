"""macOS 系统减少动态效果监控测试。"""

from xuying_toolbox.platform.macos.visual_effect import MacMotionMonitor


class FakeVisualEffectAdapter:
    def __init__(self) -> None:
        self.reduce_motion = False

    def system_reduce_motion(self) -> bool:
        return self.reduce_motion


def test_motion_monitor_emits_only_when_system_setting_changes(qtbot) -> None:
    adapter = FakeVisualEffectAdapter()
    monitor = MacMotionMonitor(adapter, interval_ms=60_000)  # type: ignore[arg-type]

    with qtbot.waitSignal(monitor.policyChanged, timeout=1000) as initial:
        monitor.start()
    assert initial.args == ["full"]

    monitor.refresh()
    adapter.reduce_motion = True
    with qtbot.waitSignal(monitor.policyChanged, timeout=1000) as changed:
        monitor.refresh()
    assert changed.args == ["reduced"]
    monitor.stop()
