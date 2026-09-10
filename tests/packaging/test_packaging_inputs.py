from pathlib import Path


def test_macos_stage1_spec_references_entrypoint_and_qml() -> None:
    root = Path(__file__).resolve().parents[2]
    spec = (root / "packaging" / "macos" / "stage1-shell.spec").read_text(encoding="utf-8")
    release_spec = (root / "packaging" / "macos" / "release.spec").read_text(
        encoding="utf-8"
    )
    icon_script = (root / "scripts" / "build-macos-icon.sh").read_text(encoding="utf-8")

    assert 'ROOT / "scripts" / "package_entry.py"' in spec
    assert 'str(ROOT / "qml")' in spec
    assert 'libXuyingVision.dylib' in spec
    assert 'libXuyingMacVisuals.dylib' in spec
    assert (root / "qml" / "Assets" / "app_icon.png").is_file()
    assert 'icon=str(APP_ICON)' in spec
    assert 'icon=str(APP_ICON)' in release_spec
    assert 'qml/Assets/app_icon.png' in icon_script
