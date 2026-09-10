"""集中检测平台，禁止业务层到处判断 sys.platform。"""

from __future__ import annotations

import platform as platform_module
from dataclasses import dataclass
from enum import StrEnum


class PlatformKind(StrEnum):
    MACOS = "macos"
    WINDOWS = "windows"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    kind: PlatformKind
    system_name: str
    architecture: str
    release: str
    supported: bool
    motion_policy: str
    effect_policy: str


def detect_platform(
    *,
    system_name: str | None = None,
    architecture: str | None = None,
    release: str | None = None,
) -> PlatformInfo:
    """返回稳定的平台信息，参数注入仅用于合同测试。"""

    system = (system_name or platform_module.system()).casefold()
    machine = (architecture or platform_module.machine()).casefold()
    detected_release = release or platform_module.release()

    if system == "darwin":
        supported = machine in {"arm64", "aarch64"}
        return PlatformInfo(
            kind=PlatformKind.MACOS,
            system_name="macOS",
            architecture=machine,
            release=detected_release,
            supported=supported,
            motion_policy="full",
            effect_policy="native",
        )
    if system == "windows":
        supported = machine in {"amd64", "x86_64"}
        return PlatformInfo(
            kind=PlatformKind.WINDOWS,
            system_name="Windows",
            architecture=machine,
            release=detected_release,
            supported=supported,
            motion_policy="reduced",
            effect_policy="solid",
        )
    return PlatformInfo(
        kind=PlatformKind.UNSUPPORTED,
        system_name=system or "unknown",
        architecture=machine or "unknown",
        release=detected_release,
        supported=False,
        motion_policy="none",
        effect_policy="solid",
    )
