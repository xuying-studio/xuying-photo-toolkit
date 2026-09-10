from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_DOMAIN_IMPORTS = {
    "PySide6",
    "exifread",
    "send2trash",
    "tkinter",
    "xuying_toolbox.infrastructure",
    "xuying_toolbox.platform",
    "xuying_toolbox.presentation",
}
FORBIDDEN_APPLICATION_IMPORTS = {
    "PySide6",
    "tkinter",
    "xuying_toolbox.infrastructure",
    "xuying_toolbox.platform",
    "xuying_toolbox.presentation",
}


def imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def assert_no_forbidden_imports(folder: Path, forbidden: set[str]) -> None:
    violations: list[str] = []
    for path in folder.rglob("*.py"):
        for imported in imported_names(path):
            if any(imported == name or imported.startswith(f"{name}.") for name in forbidden):
                violations.append(f"{path}: {imported}")
    assert not violations, "\n".join(violations)


def test_domain_stays_pure_python() -> None:
    root = Path(__file__).resolve().parents[2]
    assert_no_forbidden_imports(
        root / "src" / "xuying_toolbox" / "domain", FORBIDDEN_DOMAIN_IMPORTS
    )


def test_application_depends_only_on_domain_and_ports() -> None:
    root = Path(__file__).resolve().parents[2]
    assert_no_forbidden_imports(
        root / "src" / "xuying_toolbox" / "application",
        FORBIDDEN_APPLICATION_IMPORTS,
    )
