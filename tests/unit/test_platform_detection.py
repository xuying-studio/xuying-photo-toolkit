from xuying_toolbox.platform import PlatformKind, detect_platform


def test_detects_supported_apple_silicon() -> None:
    info = detect_platform(system_name="Darwin", architecture="arm64", release="26.5")

    assert info.kind is PlatformKind.MACOS
    assert info.supported is True
    assert info.motion_policy == "full"
    assert info.effect_policy == "native"


def test_detects_supported_windows_x64() -> None:
    info = detect_platform(system_name="Windows", architecture="AMD64", release="11")

    assert info.kind is PlatformKind.WINDOWS
    assert info.supported is True
    assert info.motion_policy == "reduced"
    assert info.effect_policy == "solid"


def test_rejects_unsupported_platform() -> None:
    info = detect_platform(system_name="Linux", architecture="x86_64", release="test")

    assert info.kind is PlatformKind.UNSUPPORTED
    assert info.supported is False
    assert info.motion_policy == "none"
