from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from dashboard.taxonomy import (
    TAXONOMY_COLUMNS,
    load_asset_taxonomy,
    load_taxonomy_registry,
    taxonomy_metadata_for,
)
from scripts.generate_asset_taxonomy import Asset, classify, classify_regions


def test_ex_china_fund_is_not_classified_as_china() -> None:
    assert classify_regions("XCEM", "columbia em core ex-china etf", None) == ["EM"]


@pytest.mark.parametrize("symbol", ["159601", "510300", "512000", "513000", "518880", "560050", "563000", "588000"])
def test_mainland_listed_fund_prefix_is_china_region(symbol: str) -> None:
    assert classify_regions(symbol, "some fund", None) == ["CN"]


def test_chinese_product_name_is_china_region() -> None:
    assert classify_regions("UNKNOWN", "华夏黄金etf", None) == ["CN"]


def test_english_etf_without_geographic_cue_defaults_to_us() -> None:
    assert classify_regions("ZZZZ", "breakwave dry bulk shipping etf", None) == ["US"]
    assert classify_regions("EFA", "ishares msci eafe etf", {"地区": "International"}) == ["US"]


def test_canadian_fund_keeps_canada_region_code() -> None:
    assert classify_regions("EWC", "ishares msci canada index fund", None) == ["US_CA"]


def test_exact_exchange_identity_distinguishes_colliding_futures_symbols() -> None:
    assert classify_regions("RB1!", "rbob gasoline futures", None) == ["US"]
    assert classify_regions("RB1!", "steel rebar futures", None) == ["CN"]


def test_yahoo_verified_us_listing_and_global_crypto_have_sources() -> None:
    us_fund = classify(Asset("instruments", "GLD", "SPDR Gold Shares"), None)
    crypto = classify(Asset("core", "BNBUSDT", "Binance Coin / TetherUS"), None)

    assert us_fund.regions == ("US",)
    assert us_fund.basis == "yahoo_finance"
    assert us_fund.source_url == "https://finance.yahoo.com/quote/GLD/"
    assert crypto.regions == ("GLOBAL",)
    assert crypto.source_url == "https://finance.yahoo.com/markets/crypto/all/"


def test_catalog_matches_exact_asset_identity_and_preserves_symbol_collisions(tmp_path: Path) -> None:
    registry_path, catalog_path = _write_taxonomy(
        tmp_path,
        [
            ["core", "PL1!", "Platinum Futures", "commodity", "commodity.precious_metals", "commodity.platinum", "APAC", "fixture", ""],
            ["core", "PL1!", "Propylene Futures", "commodity", "commodity.energy_chemicals", "commodity.chemicals", "APAC", "fixture", ""],
        ],
    )
    registry = load_taxonomy_registry(registry_path)
    catalog = load_asset_taxonomy(catalog_path, registry)

    platinum = taxonomy_metadata_for(catalog, "core", "pl1!", "  Platinum   Futures ")
    propylene = taxonomy_metadata_for(catalog, "core", "PL1!", "Propylene Futures")

    assert platinum["secondary_category"] == "commodity.precious_metals"
    assert propylene["secondary_category"] == "commodity.energy_chemicals"
    assert taxonomy_metadata_for(catalog, "core", "PL1!", "Unknown") == {
        "primary_category": "unclassified",
        "secondary_category": None,
        "tertiary_categories": [],
        "regions": [],
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda rows: rows.append(rows[0].copy()), "duplicates asset identity"),
        (lambda rows: rows[0].__setitem__(3, "missing"), "unknown primary code"),
        (lambda rows: rows[0].__setitem__(5, "commodity.platinum|commodity.chemicals|style.growth|style.value"), "more than three"),
    ],
)
def test_catalog_rejects_invalid_rows(tmp_path: Path, mutate, message: str) -> None:
    rows = [
        ["core", "PL1!", "Platinum Futures", "commodity", "commodity.precious_metals", "commodity.platinum", "APAC", "fixture", ""],
    ]
    mutate(rows)
    registry_path, catalog_path = _write_taxonomy(tmp_path, rows)

    with pytest.raises(ValueError, match=message):
        load_asset_taxonomy(catalog_path, load_taxonomy_registry(registry_path))


def _write_taxonomy(tmp_path: Path, rows: list[list[str]]) -> tuple[Path, Path]:
    registry_path = tmp_path / "taxonomy_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "primary_categories": [_option("commodity", "Commodity", "商品", [])],
                "secondary_categories": [
                    _option("commodity.precious_metals", "Precious Metals", "贵金属", ["commodity"]),
                    _option("commodity.energy_chemicals", "Energy & Chemicals", "能源化工", ["commodity"]),
                ],
                "tertiary_categories": [
                    _option("commodity.platinum", "Platinum", "铂", ["commodity.precious_metals"]),
                    _option("commodity.chemicals", "Chemicals", "化工品", ["commodity.energy_chemicals"]),
                    _option("style.growth", "Growth", "成长", []),
                    _option("style.value", "Value", "价值", []),
                ],
                "regions": [_option("APAC", "APAC", "亚太", [])],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    catalog_path = tmp_path / "asset_taxonomy.csv"
    with catalog_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(TAXONOMY_COLUMNS)
        writer.writerows(rows)
    return registry_path, catalog_path


def _option(code: str, label_en: str, label_zh: str, parent_codes: list[str]) -> dict:
    return {"code": code, "label_en": label_en, "label_zh": label_zh, "parent_codes": parent_codes}
