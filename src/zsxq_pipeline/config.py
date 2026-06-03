from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Config:
    raw: dict[str, Any]
    path: Path

    @property
    def storage_root(self) -> Path:
        return self.path.parent / self.raw.get("storage_root", "data")

    @property
    def state_root(self) -> Path:
        return self.path.parent / self.raw.get("state_root", "state")

    @property
    def logs_root(self) -> Path:
        return self.path.parent / self.raw.get("logs_root", "logs")


def load_config(path: str | Path = "config.yaml") -> Config:
    config_path = Path(path).resolve()
    raw_text = config_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "config.yaml 当前需要使用 JSON 兼容写法；若要使用普通 YAML，请先安装 PyYAML 并扩展 loader。"
        ) from exc
    return Config(raw=data, path=config_path)
