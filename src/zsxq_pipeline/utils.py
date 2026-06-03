from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


DATE_IN_FILENAME = re.compile(r"(?P<yy>\d{2})-(?P<mm>\d{2})-(?P<dd>\d{2})")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_code(code: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", code.strip())
    return cleaned or "UNKNOWN"


def slugify_name(name: str) -> str:
    text = name.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def parse_date_from_filename(filename: str) -> str | None:
    match = DATE_IN_FILENAME.search(filename)
    if not match:
        return None
    yy = int(match.group("yy"))
    year = 2000 + yy
    return f"{year:04d}-{int(match.group('mm')):02d}-{int(match.group('dd')):02d}"


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            if text.endswith("Z") and "%z" in fmt:
                dt = datetime.strptime(text.replace("Z", "+0000"), fmt)
            else:
                dt = datetime.strptime(text, fmt)
            return dt.date().isoformat()
        except ValueError:
            continue
    return None


def copy_file(src: Path, dest: Path) -> None:
    ensure_dir(dest.parent)
    shutil.copy2(src, dest)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
