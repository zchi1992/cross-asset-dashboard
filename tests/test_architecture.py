from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def python_files(relative_root: str) -> list[Path]:
    return sorted(
        path
        for path in (ROOT / relative_root).rglob("*.py")
        if "__pycache__" not in path.parts
    )


def test_pipeline_does_not_depend_on_dashboard_or_backend() -> None:
    violations: list[str] = []
    for path in python_files("src/zsxq_pipeline"):
        for module in imported_modules(path):
            if module == "dashboard" or module.startswith("dashboard."):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
            if module == "backend" or module.startswith("backend."):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert not violations, "\n".join(violations)


def test_dashboard_does_not_depend_on_backend() -> None:
    violations: list[str] = []
    for path in python_files("dashboard"):
        for module in imported_modules(path):
            if module == "backend" or module.startswith("backend."):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert not violations, "\n".join(violations)


def test_backend_uses_dashboard_only_through_data_service() -> None:
    allowed_modules = {"dashboard.config", "dashboard.data_loader", "dashboard.macro_loader"}
    violations: list[str] = []
    for path in python_files("backend"):
        dashboard_imports = {
            module
            for module in imported_modules(path)
            if module == "dashboard" or module.startswith("dashboard.")
        }
        if not dashboard_imports:
            continue
        if path != ROOT / "backend" / "app" / "data_service.py":
            violations.append(
                f"{path.relative_to(ROOT)} imports dashboard outside data_service"
            )
            continue
        unexpected = dashboard_imports - allowed_modules
        for module in sorted(unexpected):
            violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert not violations, "\n".join(violations)
