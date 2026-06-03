from __future__ import annotations

import re


def _normalize(text: str, case_sensitive: bool) -> str:
    return text if case_sensitive else text.lower()


def match_filename(filename: str, filter_config: dict) -> bool:
    include_patterns = filter_config.get("include_patterns", [])
    exclude_patterns = filter_config.get("exclude_patterns", [])
    mode = filter_config.get("match_mode", "contains")
    case_sensitive = filter_config.get("case_sensitive", False)

    normalized_name = _normalize(filename, case_sensitive)

    def matches(pattern: str) -> bool:
        prepared = _normalize(pattern, case_sensitive)
        if mode == "exact":
            return normalized_name == prepared
        if mode == "regex":
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.search(pattern, filename, flags=flags) is not None
        return prepared in normalized_name

    if any(matches(pattern) for pattern in exclude_patterns):
        return False
    if not include_patterns:
        return False
    return any(matches(pattern) for pattern in include_patterns)


def classify_dataset(filename: str, rules: dict[str, list[str]]) -> str:
    for dataset_type, patterns in rules.items():
        for pattern in patterns:
            if pattern in filename:
                return dataset_type
    raise ValueError(f"无法根据文件名识别数据集类型: {filename}")
