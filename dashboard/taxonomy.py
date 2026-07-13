from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


TAXONOMY_COLUMNS = [
    "dataset_type",
    "symbol",
    "asset_name",
    "primary_category",
    "secondary_category",
    "tertiary_categories",
    "regions",
    "classification_basis",
    "source_url",
]

UNCLASSIFIED_METADATA: dict[str, Any] = {
    "primary_category": "unclassified",
    "secondary_category": None,
    "tertiary_categories": [],
    "regions": [],
}


def normalize_asset_identity(dataset_type: object, symbol: object, asset_name: object) -> tuple[str, str, str]:
    return (
        str(dataset_type).strip().lower(),
        str(symbol).strip().upper(),
        _normalize_name(asset_name),
    )


def load_taxonomy_registry(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    if not source_path.exists():
        return _empty_registry()
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"taxonomy registry must be a JSON object: {source_path}")
    for group in ("primary_categories", "secondary_categories", "tertiary_categories", "regions"):
        options = raw.get(group)
        if not isinstance(options, list):
            raise ValueError(f"taxonomy registry field {group!r} must be a list")
        seen: set[str] = set()
        for option in options:
            if not isinstance(option, dict):
                raise ValueError(f"taxonomy registry {group!r} contains a non-object option")
            code = str(option.get("code", "")).strip()
            if not code or code in seen:
                raise ValueError(f"taxonomy registry {group!r} contains an empty or duplicate code: {code!r}")
            seen.add(code)
            if not str(option.get("label_en", "")).strip() or not str(option.get("label_zh", "")).strip():
                raise ValueError(f"taxonomy option {code!r} must define label_en and label_zh")
            parents = option.get("parent_codes", [])
            if not isinstance(parents, list) or any(not str(parent).strip() for parent in parents):
                raise ValueError(f"taxonomy option {code!r} has invalid parent_codes")
    return raw


def load_asset_taxonomy(
    path: str | Path,
    registry: dict[str, Any],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    source_path = Path(path)
    if not source_path.exists():
        return {}
    if not registry.get("primary_categories"):
        raise ValueError(f"taxonomy catalog exists but registry is missing or empty: {source_path}")

    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != TAXONOMY_COLUMNS:
            raise ValueError(
                f"taxonomy catalog columns must be exactly {TAXONOMY_COLUMNS!r}; got {reader.fieldnames!r}"
            )
        rows = list(reader)

    valid_primary = _option_map(registry, "primary_categories")
    valid_secondary = _option_map(registry, "secondary_categories")
    valid_tertiary = _option_map(registry, "tertiary_categories")
    valid_regions = _option_map(registry, "regions")
    catalog: dict[tuple[str, str, str], dict[str, Any]] = {}

    for line_number, row in enumerate(rows, start=2):
        key = normalize_asset_identity(row["dataset_type"], row["symbol"], row["asset_name"])
        if not all(key):
            raise ValueError(f"taxonomy catalog line {line_number} has an incomplete asset identity")
        if key in catalog:
            raise ValueError(f"taxonomy catalog line {line_number} duplicates asset identity {key!r}")

        primary = row["primary_category"].strip()
        secondary = row["secondary_category"].strip() or None
        tertiary = _split_codes(row["tertiary_categories"])
        regions = _split_codes(row["regions"])
        if primary not in valid_primary:
            raise ValueError(f"taxonomy catalog line {line_number} has unknown primary code {primary!r}")
        if secondary is not None and secondary not in valid_secondary:
            raise ValueError(f"taxonomy catalog line {line_number} has unknown secondary code {secondary!r}")
        if len(tertiary) > 3:
            raise ValueError(f"taxonomy catalog line {line_number} has more than three tertiary categories")
        unknown_tertiary = [code for code in tertiary if code not in valid_tertiary]
        if unknown_tertiary:
            raise ValueError(f"taxonomy catalog line {line_number} has unknown tertiary codes {unknown_tertiary!r}")
        unknown_regions = [code for code in regions if code not in valid_regions]
        if unknown_regions:
            raise ValueError(f"taxonomy catalog line {line_number} has unknown region codes {unknown_regions!r}")
        if secondary is not None:
            parents = {str(value) for value in valid_secondary[secondary].get("parent_codes", [])}
            if parents and primary not in parents:
                raise ValueError(
                    f"taxonomy catalog line {line_number} secondary code {secondary!r} is not valid for {primary!r}"
                )
        if secondary is not None:
            for code in tertiary:
                parents = {str(value) for value in valid_tertiary[code].get("parent_codes", [])}
                if parents and secondary not in parents:
                    raise ValueError(
                        f"taxonomy catalog line {line_number} tertiary code {code!r} is not valid for {secondary!r}"
                    )

        catalog[key] = {
            "primary_category": primary,
            "secondary_category": secondary,
            "tertiary_categories": tertiary,
            "regions": regions,
        }
    return catalog


def taxonomy_metadata_for(
    catalog: dict[tuple[str, str, str], dict[str, Any]],
    dataset_type: object,
    symbol: object,
    asset_name: object,
) -> dict[str, Any]:
    matched = catalog.get(normalize_asset_identity(dataset_type, symbol, asset_name))
    if matched is None:
        return {
            "primary_category": UNCLASSIFIED_METADATA["primary_category"],
            "secondary_category": UNCLASSIFIED_METADATA["secondary_category"],
            "tertiary_categories": [],
            "regions": [],
        }
    return {
        "primary_category": matched["primary_category"],
        "secondary_category": matched["secondary_category"],
        "tertiary_categories": list(matched["tertiary_categories"]),
        "regions": list(matched["regions"]),
    }


def taxonomy_api_options(registry: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        group: [
            {
                "code": str(option["code"]),
                "label_en": str(option["label_en"]),
                "label_zh": str(option["label_zh"]),
                "parent_codes": [str(value) for value in option.get("parent_codes", [])],
            }
            for option in registry.get(group, [])
        ]
        for group in ("primary_categories", "secondary_categories", "tertiary_categories", "regions")
    }


def _option_map(registry: dict[str, Any], group: str) -> dict[str, dict[str, Any]]:
    return {str(option["code"]): option for option in registry.get(group, [])}


def _split_codes(value: object) -> list[str]:
    codes = [part.strip() for part in str(value or "").split("|") if part.strip()]
    if len(codes) != len(set(codes)):
        raise ValueError(f"taxonomy multi-value field contains duplicate codes: {value!r}")
    return codes


def _normalize_name(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _empty_registry() -> dict[str, Any]:
    return {
        "version": "missing",
        "standards": {},
        "primary_categories": [],
        "secondary_categories": [],
        "tertiary_categories": [],
        "regions": [],
    }
