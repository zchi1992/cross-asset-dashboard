#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", ".venv", "node_modules", "dist", "data", "logs", "state"}
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MAKE_TARGET_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+):", re.MULTILINE)
REQUIRED_DOCS = {
    ROOT / "ARCHITECTURE.md",
    ROOT / "docs" / "index.md",
    ROOT / "docs" / "product" / "dashboard.md",
    ROOT / "docs" / "data-contracts.md",
    ROOT / "docs" / "testing.md",
    ROOT / "docs" / "reliability.md",
    ROOT / "docs" / "security.md",
    ROOT / "docs" / "quality-score.md",
    ROOT / "docs" / "exec-plans" / "tech-debt.md",
}
REQUIRED_MAKE_TARGETS = {"setup", "check", "smoke", "e2e"}


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)
    )


def local_link_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().strip("<>")
    if not target or target.startswith("#"):
        return None
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
        return None
    path_part = unquote(target.split("#", 1)[0])
    if not path_part:
        return None
    return (source.parent / path_part).resolve()


def main() -> int:
    errors: list[str] = []
    for required in sorted(REQUIRED_DOCS):
        if not required.is_file():
            errors.append(f"missing required document: {required.relative_to(ROOT)}")

    for source in markdown_files():
        text = source.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = local_link_target(source, raw_target)
            if target is not None and not target.exists():
                errors.append(
                    f"{source.relative_to(ROOT)}: broken link {raw_target!r}"
                )

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = set(MAKE_TARGET_PATTERN.findall(makefile))
    for target in sorted(REQUIRED_MAKE_TARGETS - targets):
        errors.append(f"Makefile is missing required target: {target}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        f"docs-check: ok ({len(markdown_files())} markdown files, "
        f"{len(REQUIRED_MAKE_TARGETS)} required make targets)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
