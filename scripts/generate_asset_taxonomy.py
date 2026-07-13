from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zsxq_pipeline.config import load_config
from src.zsxq_pipeline.xlsx_parser import read_first_sheet
from dashboard.config import load_dashboard_config
from dashboard.data_loader import load_market_map_rows


PRIMARY = [
    ("equity", "Equity", "股票"),
    ("bond", "Bond", "债券"),
    ("fx", "FX", "外汇"),
    ("commodity", "Commodity", "商品"),
    ("alternative", "Alternative", "另类资产"),
    ("unclassified", "Unclassified", "未分类"),
]

GICS_SECTORS = [
    ("10", "Energy", "能源"),
    ("15", "Materials", "原材料"),
    ("20", "Industrials", "工业"),
    ("25", "Consumer Discretionary", "可选消费"),
    ("30", "Consumer Staples", "日常消费"),
    ("35", "Health Care", "医疗保健"),
    ("40", "Financials", "金融"),
    ("45", "Information Technology", "信息技术"),
    ("50", "Communication Services", "通信服务"),
    ("55", "Utilities", "公用事业"),
    ("60", "Real Estate", "房地产"),
]

GICS_GROUPS = [
    ("1010", "Energy", "能源", "10"),
    ("1510", "Materials", "原材料", "15"),
    ("2010", "Capital Goods", "资本品", "20"),
    ("2020", "Commercial & Professional Services", "商业及专业服务", "20"),
    ("2030", "Transportation", "运输", "20"),
    ("2510", "Automobiles & Components", "汽车与零部件", "25"),
    ("2520", "Consumer Durables & Apparel", "耐用消费品与服装", "25"),
    ("2530", "Consumer Services", "消费者服务", "25"),
    ("2550", "Consumer Discretionary Distribution & Retail", "可选消费经销与零售", "25"),
    ("3010", "Consumer Staples Distribution & Retail", "日常消费经销与零售", "30"),
    ("3020", "Food, Beverage & Tobacco", "食品饮料与烟草", "30"),
    ("3030", "Household & Personal Products", "家庭与个人用品", "30"),
    ("3510", "Health Care Equipment & Services", "医疗设备与服务", "35"),
    ("3520", "Pharmaceuticals, Biotechnology & Life Sciences", "制药生物科技与生命科学", "35"),
    ("4010", "Banks", "银行", "40"),
    ("4020", "Financial Services", "金融服务", "40"),
    ("4030", "Insurance", "保险", "40"),
    ("4510", "Software & Services", "软件与服务", "45"),
    ("4520", "Technology Hardware & Equipment", "科技硬件与设备", "45"),
    ("4530", "Semiconductors & Semiconductor Equipment", "半导体与设备", "45"),
    ("5010", "Telecommunication Services", "电信服务", "50"),
    ("5020", "Media & Entertainment", "媒体与娱乐", "50"),
    ("5510", "Utilities", "公用事业", "55"),
    ("6010", "Equity Real Estate Investment Trusts", "权益房地产投资信托", "60"),
    ("6020", "Real Estate Management & Development", "房地产管理与开发", "60"),
]

SW_SECTORS = [
    ("110000", "Agriculture, Forestry, Animal Husbandry & Fishery", "农林牧渔"),
    ("220000", "Basic Chemicals", "基础化工"),
    ("230000", "Steel", "钢铁"),
    ("240000", "Non-ferrous Metals", "有色金属"),
    ("270000", "Electronics", "电子"),
    ("280000", "Automobiles", "汽车"),
    ("330000", "Home Appliances", "家用电器"),
    ("340000", "Food & Beverage", "食品饮料"),
    ("350000", "Textiles & Apparel", "纺织服饰"),
    ("360000", "Light Manufacturing", "轻工制造"),
    ("370000", "Pharmaceuticals & Biotechnology", "医药生物"),
    ("410000", "Utilities", "公用事业"),
    ("420000", "Transportation", "交通运输"),
    ("430000", "Real Estate", "房地产"),
    ("450000", "Commerce & Retail", "商贸零售"),
    ("460000", "Social Services", "社会服务"),
    ("480000", "Banks", "银行"),
    ("490000", "Non-bank Financials", "非银金融"),
    ("510000", "Conglomerates", "综合"),
    ("610000", "Building Materials", "建筑材料"),
    ("620000", "Building Decoration", "建筑装饰"),
    ("630000", "Power Equipment", "电力设备"),
    ("640000", "Machinery", "机械设备"),
    ("650000", "Defense", "国防军工"),
    ("710000", "Computers", "计算机"),
    ("720000", "Media", "传媒"),
    ("730000", "Communications", "通信"),
    ("740000", "Coal", "煤炭"),
    ("750000", "Petroleum & Petrochemicals", "石油石化"),
    ("760000", "Environmental Protection", "环保"),
    ("770000", "Beauty Care", "美容护理"),
]

SECONDARY_BASE = [
    ("bond.corporate", "Corporate", "公司债", ["bond"]),
    ("bond.sovereign", "Sovereign", "主权债", ["bond"]),
    ("bond.municipal", "Municipal", "市政债", ["bond"]),
    ("bond.aggregated", "Aggregated", "综合债", ["bond"]),
    ("equity.large_cap", "Large Cap", "大盘", ["equity"]),
    ("equity.mid_cap", "Mid Cap", "中盘", ["equity"]),
    ("equity.small_cap", "Small Cap", "小盘", ["equity"]),
    ("equity.broad_market", "Broad Market", "宽基", ["equity"]),
    ("equity.strategy", "Strategy", "策略", ["equity"]),
    ("equity.thematic", "Thematic", "主题", ["equity"]),
    ("commodity.precious_metals", "Precious Metals", "贵金属", ["commodity"]),
    ("commodity.industrial_metals", "Industrial Metals", "工业金属", ["commodity"]),
    ("commodity.agriculture", "Agriculture", "农产品", ["commodity"]),
    ("commodity.energy_chemicals", "Energy & Chemicals", "能源化工", ["commodity"]),
    ("commodity.broad", "Broad Commodity", "综合商品", ["commodity"]),
    ("alternative.real_estate", "Real Estate", "房地产", ["alternative"]),
    ("alternative.crypto", "Crypto", "加密货币", ["alternative"]),
]

TERTIARY_BASE = [
    ("style.growth", "Growth", "成长", []),
    ("style.value", "Value", "价值", []),
    ("style.dividend", "Dividend", "红利", []),
    ("style.quality", "Quality", "质量", []),
    ("style.momentum", "Momentum", "动量", []),
    ("style.low_volatility", "Low Volatility", "低波动", []),
    ("style.equal_weight", "Equal Weight", "等权", []),
    ("style.factor", "Factor", "因子", []),
    ("style.esg", "ESG", "ESG", []),
    ("style.covered_call", "Covered Call", "备兑看涨", []),
    ("style.leveraged_inverse", "Leveraged / Inverse", "杠杆或反向", []),
    ("style.preferred", "Preferred", "优先股", []),
    ("bond.money_market", "Money Market", "货币市场", []),
    ("bond.inflation_linked", "Inflation Linked", "通胀挂钩", []),
    ("bond.high_yield", "High Yield", "高收益", []),
    ("bond.securitized", "Securitized", "证券化债券", []),
    ("bond.floating_rate", "Floating Rate", "浮息", []),
    ("commodity.gold", "Gold", "黄金", ["commodity.precious_metals"]),
    ("commodity.silver", "Silver", "白银", ["commodity.precious_metals"]),
    ("commodity.platinum_group", "Platinum Group", "铂族金属", ["commodity.precious_metals"]),
    ("commodity.copper", "Copper", "铜", ["commodity.industrial_metals"]),
    ("commodity.aluminium", "Aluminium", "铝", ["commodity.industrial_metals"]),
    ("commodity.steel", "Steel", "钢铁", ["commodity.industrial_metals"]),
    ("commodity.energy_metals", "Energy Metals", "能源金属", ["commodity.industrial_metals"]),
    ("commodity.grains", "Grains", "谷物", ["commodity.agriculture"]),
    ("commodity.softs", "Soft Commodities", "软性商品", ["commodity.agriculture"]),
    ("commodity.livestock", "Livestock", "畜牧", ["commodity.agriculture"]),
    ("commodity.crude_oil", "Crude Oil", "原油", ["commodity.energy_chemicals"]),
    ("commodity.natural_gas", "Natural Gas", "天然气", ["commodity.energy_chemicals"]),
    ("commodity.refined_products", "Refined Products", "成品油", ["commodity.energy_chemicals"]),
    ("commodity.chemicals", "Chemicals", "化工品", ["commodity.energy_chemicals"]),
    ("theme.ai_hardware", "AI Hardware", "AI 硬件", []),
    ("theme.clean_energy", "Clean Energy", "清洁能源", []),
    ("theme.cybersecurity", "Cybersecurity", "网络安全", []),
    ("theme.cloud", "Cloud Computing", "云计算", []),
    ("theme.robotics", "Robotics & Automation", "机器人与自动化", []),
    ("theme.aerospace_defense", "Aerospace & Defense", "航空航天与国防", []),
    ("theme.infrastructure", "Infrastructure", "基础设施", []),
    ("theme.water", "Water", "水资源", []),
    ("theme.shipping", "Shipping", "航运", []),
    ("theme.uranium", "Uranium", "铀", []),
    ("theme.battery", "Battery", "电池", []),
    ("theme.biotech", "Biotechnology", "生物科技", []),
]

SW_GROUPS = [
    ("240300", "Industrial Metals", "工业金属", "240000"),
    ("240400", "Precious Metals", "贵金属", "240000"),
    ("240600", "Energy Metals", "能源金属", "240000"),
    ("270100", "Semiconductors", "半导体", "270000"),
    ("270500", "Consumer Electronics", "消费电子", "270000"),
    ("280200", "Auto Parts", "汽车零部件", "280000"),
    ("370300", "Biological Products", "生物制品", "370000"),
    ("370500", "Medical Devices", "医疗器械", "370000"),
    ("630300", "Photovoltaic Equipment", "光伏设备", "630000"),
    ("630400", "Wind Power Equipment", "风电设备", "630000"),
    ("630600", "Battery", "电池", "630000"),
    ("640600", "Automation Equipment", "自动化设备", "640000"),
    ("650300", "Aviation Equipment", "航空装备", "650000"),
    ("650600", "Defense Electronics", "军工电子", "650000"),
    ("710100", "Computer Equipment", "计算机设备", "710000"),
    ("710300", "Software Development", "软件开发", "710000"),
    ("720300", "Gaming", "游戏", "720000"),
    ("730100", "Communication Services", "通信服务", "730000"),
    ("730200", "Communication Equipment", "通信设备", "730000"),
]

REGION_LABELS = {
    "US": ("US", "美国"),
    "US_CA": ("Canada", "加拿大"),
    "LATAM": ("LatAm", "拉丁美洲"),
    "EUROPE": ("Europe", "欧洲"),
    "JP": ("Japan", "日本"),
    "KR": ("South Korea", "韩国"),
    "CN": ("China", "中国"),
    "APAC": ("APAC", "亚太"),
    "EM": ("Emerging Markets", "新兴市场"),
}

REGION_ORDER = ["US", "CN", "US_CA", "LATAM", "EUROPE", "JP", "KR", "APAC", "EM"]

CURRENCY_REGIONS = {
    "USD": "US", "CAD": "US_CA", "CNY": "CN", "CNH": "CN", "JPY": "JP",
    "EUR": "EUROPE", "GBP": "EUROPE", "CHF": "EUROPE", "BRL": "LATAM", "MXN": "LATAM",
    "AUD": "APAC", "NZD": "APAC", "HKD": "APAC", "SGD": "APAC", "INR": "APAC",
    "KRW": "KR", "ZAR": "EM",
}

GS_REGION_MAP = {
    "USA": ["US"], "CA": ["US_CA"], "Global": [], "International": [],
    "Europe": ["EUROPE"], "Asia": ["APAC"], "JP": ["JP"], "IN": ["APAC"], "CN": ["CN"],
}

OFFICIAL_SOURCE_URLS = {
    "CTA": "https://www.simplify.us/etfs/cta-simplify-managed-futures-strategy-etf",
    "DBMF": "https://imgpfunds.com/wp-content/uploads/2025/10/DBMF-September-2025-Deck-Final-V2.pdf",
    "FMF": "https://www.ftportfolios.com/Retail/Etf/EtfSummary.aspx?Ticker=FMF",
    "KMLM": "https://kraneshares.com/etf/kmlm/",
    "IVOL": "https://kraneshares.com/etf/ivol/",
}


@dataclass(frozen=True)
class Asset:
    dataset_type: str
    symbol: str
    name: str


@dataclass(frozen=True)
class Classification:
    primary: str
    secondary: str | None
    tertiary: tuple[str, ...]
    regions: tuple[str, ...]
    basis: str
    source_url: str = ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the versioned dashboard asset taxonomy")
    parser.add_argument("--config", required=True, help="Config whose processed-series inventory is the source universe")
    parser.add_argument("--output-dir", default="metadata")
    args = parser.parse_args()

    config = load_config(args.config)
    assets = load_assets(args.config)
    gs_rows = load_gs_rows(config.storage_root)
    classifications = [(asset, classify(asset, gs_rows.get(asset.symbol.upper()))) for asset in assets]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_registry(output_dir / "taxonomy_registry.json", classifications)
    write_catalog(output_dir / "asset_taxonomy.csv", classifications)
    print(json.dumps(summary(classifications), ensure_ascii=False, sort_keys=True))


def load_assets(config_path: str | Path) -> list[Asset]:
    config = load_dashboard_config(config_path)
    rows = load_market_map_rows(config.storage_root, config.market_map)
    assets = {
        Asset(
            str(row["asset_class"]).strip().lower(),
            str(row["asset_id"]).strip(),
            re.sub(r"\s+", " ", str(row["asset_name"]).strip()),
        )
        for row in rows
    }
    return sorted(assets, key=lambda item: (item.dataset_type, item.symbol.upper(), item.name.casefold()))


def load_gs_rows(storage_root: Path) -> dict[str, dict[str, str]]:
    candidates = [
        storage_root / "gs_exempt_list" / "gs_exempt_list.xlsx",
        storage_root / "gs_exempt_list" / "gs_exempt_list.csv",
    ]
    source = next((path for path in candidates if path.exists()), None)
    if source is None:
        return {}
    if source.suffix.lower() == ".xlsx":
        _, rows = read_first_sheet(source)
    else:
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    if not rows:
        return {}
    headers = [str(value).strip() for value in rows[0]]
    result: dict[str, dict[str, str]] = {}
    for raw in rows[1:]:
        item = {header: str(raw[index]).strip() if index < len(raw) else "" for index, header in enumerate(headers)}
        ticker = item.get("Ticker", "").upper()
        if ticker:
            result[ticker] = item
    return result


def classify(asset: Asset, gs: dict[str, str] | None) -> Classification:
    name = asset.name.casefold()
    symbol = asset.symbol.upper()
    regions = classify_regions(symbol, name, gs)
    basis = "gs_exempt" if gs else "instrument_name"

    primary = classify_primary(symbol, name, gs)
    if primary == "bond":
        secondary, tertiary = classify_bond(name, gs)
    elif primary == "fx":
        secondary, tertiary = None, []
    elif primary == "commodity":
        secondary, tertiary = classify_commodity(name, gs)
        regions = []
    elif primary == "alternative":
        secondary, tertiary = classify_alternative(name, gs)
        if secondary == "alternative.crypto":
            regions = []
    else:
        secondary, tertiary = classify_equity(name, regions, gs)

    source_url = OFFICIAL_SOURCE_URLS.get(symbol, "")
    if source_url:
        basis = "official_source"
    return Classification(
        primary,
        secondary,
        tuple(_dedupe(tertiary)[:3]),
        tuple(_dedupe(regions)),
        basis,
        source_url,
    )


def classify_primary(symbol: str, name: str, gs: dict[str, str] | None) -> str:
    gs_type = (gs or {}).get("资产类型", "")
    gs_detail = (gs or {}).get("细分类别", "")
    if gs_type == "Cash":
        return "bond"
    if gs_type == "Bond":
        return "bond"
    if gs_type == "Commodity":
        return "commodity"
    if gs_type == "Alternative":
        if any(word in gs_detail for word in ("Defined Outcome", "Inverse / Leveraged", "Index / Derivative")):
            return "equity"
        if "Volatility" in gs_detail and "low volatility" in name:
            return "equity"
        return "alternative"
    if gs_type == "Equity":
        if _contains(name, "real estate", "reit"):
            return "alternative"
        return "equity"

    if _is_fx(symbol, name):
        return "fx"
    if _contains(name, "bitcoin", "ethereum", "ether ", "crypto", "dogecoin", "solana", "xrp", "tetherus", "binance coin") or re.search(r"(?:BTC|ETH|DOGE|SOL|BNB|XRP)(?:USD|USDT|1!)$", symbol):
        return "alternative"
    if _contains(name, "real estate", "reit"):
        return "alternative"
    if _contains(name, "bond", "treasury", "government yield", "government bonds yield", "yield futures", "t-bill", "municipal", "fixed income", "senior loan", "credit fund", "sofr", "cgb futures", "t-note", "federal funds") or re.search(r"(?:US|CN|DE|GB|JP)\d{2}Y$", symbol):
        return "bond"
    if "low volatility" in name:
        return "equity"
    if _contains(name, "managed futures strategy", "managed futures index strategy"):
        return "alternative"
    if _contains(name, "volatility", "vix", "multi-asset allocation", "baltic dry index"):
        return "alternative"
    if "futures" in name and _contains(name, "e-mini", "nikkei", "s&p 500", "nasdaq-100", "midcap 400"):
        return "equity"
    if _is_commodity(name):
        return "commodity"
    return "equity"


def classify_bond(name: str, gs: dict[str, str] | None) -> tuple[str, list[str]]:
    detail = (gs or {}).get("细分类别", "").casefold()
    combined = f"{name} {detail}"
    tertiary: list[str] = []
    if _contains(combined, "municipal", "muni"):
        secondary = "bond.municipal"
    elif _contains(combined, "treasury", "sovereign", "government", "t-bill"):
        secondary = "bond.sovereign"
    elif _contains(combined, "corporate", "preferred", "senior loan", "high yield"):
        secondary = "bond.corporate"
    else:
        secondary = "bond.aggregated"
    if _contains(combined, "money market", "t-bill", "cash management", "ultra-short", "0-3 month"):
        tertiary.append("bond.money_market")
    if _contains(combined, "inflation", "tips"):
        tertiary.append("bond.inflation_linked")
    if _contains(combined, "high yield", "junk"):
        tertiary.append("bond.high_yield")
    if _contains(combined, "mortgage", "securitized", "mbs"):
        tertiary.append("bond.securitized")
    if _contains(combined, "floating", "frn", "senior loan"):
        tertiary.append("bond.floating_rate")
    return secondary, tertiary


def classify_alternative(name: str, gs: dict[str, str] | None) -> tuple[str | None, list[str]]:
    detail = (gs or {}).get("细分类别", "").casefold()
    combined = f"{name} {detail}"
    if _contains(combined, "crypto", "bitcoin", "ethereum", "ether ", "dogecoin", "solana", "sol /", "xrp", "tetherus", "binance coin"):
        return "alternative.crypto", []
    if _contains(combined, "real estate", "reit"):
        return "alternative.real_estate", []
    return None, []


def classify_commodity(name: str, gs: dict[str, str] | None) -> tuple[str, list[str]]:
    detail = (gs or {}).get("细分类别", "").casefold()
    combined = f"{name} {detail}"
    if _contains(combined, "gold", "silver", "platinum", "palladium", "precious"):
        secondary = "commodity.precious_metals"
    elif _contains(combined, "copper", "aluminium", "aluminum", "zinc", "lead ", "nickel", "tin ", "steel", "iron ore", "hot rolled", "rebar", "flat glass", "ferrosilicon", "manganese silicon", "wire rod", "base metals", "lithium", "uranium", "rare earth", "industrial metal"):
        secondary = "commodity.industrial_metals"
    elif _contains(combined, "corn", "wheat", "soy", "rice", "oat", "cocoa", "coffee", "cotton", "sugar", "orange juice", "apple", "jujube", "peanut", "lumber", "pulp", "livestock", "cattle", "hog", "pork", "canola", "rapeseed", "palm oil", "agriculture"):
        secondary = "commodity.agriculture"
    elif _contains(combined, " oil", "gas", "lng", "gasoline", "diesel", "fuel", "ulsd", "naphtha", "coal", "chemical", "rubber", "plastic", "poly", "propylene", "xylene", "terephthalic", "soda ash", "sodium hydroxide", "urea", "methanol", "bitumen", "crude", "energy"):
        secondary = "commodity.energy_chemicals"
    else:
        secondary = "commodity.broad"

    tertiary: list[str] = []
    for code, words in [
        ("commodity.gold", ("gold",)), ("commodity.silver", ("silver",)),
        ("commodity.platinum_group", ("platinum", "palladium")),
        ("commodity.copper", ("copper",)), ("commodity.aluminium", ("aluminium", "aluminum")),
        ("commodity.steel", ("steel", "iron ore", "rebar", "hot rolled")),
        ("commodity.energy_metals", ("lithium", "nickel", "cobalt", "rare earth", "uranium")),
        ("commodity.grains", ("corn", "wheat", "soy", "rice", "oat", "canola", "rapeseed", "peanut")),
        ("commodity.softs", ("cocoa", "coffee", "cotton", "sugar", "orange juice", "apple", "jujube", "lumber", "pulp")),
        ("commodity.livestock", ("cattle", "hog", "pork", "livestock")),
        ("commodity.crude_oil", ("crude", "brent", "wti")),
        ("commodity.natural_gas", ("natural gas", "lng")),
        ("commodity.refined_products", ("gasoline", "diesel", "fuel oil", "ulsd", "naphtha")),
        ("commodity.chemicals", ("chemical", "rubber", "plastic", "poly", "propylene", "xylene", "terephthalic", "soda ash", "sodium hydroxide", "urea", "methanol", "bitumen")),
    ]:
        if any(word in combined for word in words):
            tertiary.append(code)
    if secondary == "commodity.industrial_metals" and _contains(combined, "copper", "aluminium", "aluminum"):
        tertiary.append("theme.ai_hardware")
    return secondary, tertiary


def classify_equity(name: str, regions: list[str], gs: dict[str, str] | None) -> tuple[str, list[str]]:
    detail = (gs or {}).get("细分类别", "").casefold()
    combined = f"{name} {detail}"
    tertiary = classify_styles(combined)
    sector = classify_sector(combined, regions)
    if sector is not None:
        secondary, group = sector
        if group:
            tertiary.insert(0, group)
        return secondary, tertiary
    if _contains(combined, "thematic", "innovation", "clean energy", "cyber", "cloud", "robot", "automation", "aerospace", "defense", "infrastructure", "water", "shipping", "uranium", "battery", "biotech"):
        return "equity.thematic", classify_themes(combined) + tertiary
    if tertiary or _contains(combined, "factor", "defined outcome", "inverse", "leveraged", "option income"):
        return "equity.strategy", tertiary
    if _contains(combined, "small cap", "small-cap", "micro cap", "micro-cap", "russell 2000"):
        return "equity.small_cap", tertiary
    if _contains(combined, "mid cap", "mid-cap", "midcap"):
        return "equity.mid_cap", tertiary
    if _contains(combined, "large cap", "large-cap", "s&p 500", "russell 1000"):
        return "equity.large_cap", tertiary
    return "equity.broad_market", tertiary


def classify_styles(text: str) -> list[str]:
    result: list[str] = []
    mapping = [
        ("style.growth", ("growth",)), ("style.value", ("value",)),
        ("style.dividend", ("dividend", "income equity")), ("style.quality", ("quality",)),
        ("style.momentum", ("momentum",)), ("style.low_volatility", ("low volatility", "min vol")),
        ("style.equal_weight", ("equal weight",)), ("style.factor", ("factor", "fundamental", "revenue")),
        ("style.esg", ("esg", "sustainable")), ("style.covered_call", ("covered call", "option income")),
        ("style.leveraged_inverse", ("inverse", "leveraged", "2x", "3x")),
        ("style.preferred", ("preferred",)),
    ]
    for code, words in mapping:
        if any(word in text for word in words):
            result.append(code)
    return result


def classify_themes(text: str) -> list[str]:
    mapping = [
        ("theme.clean_energy", ("clean energy", "solar", "wind")),
        ("theme.cybersecurity", ("cyber",)), ("theme.cloud", ("cloud",)),
        ("theme.robotics", ("robot", "automation")),
        ("theme.aerospace_defense", ("aerospace", "defense")),
        ("theme.infrastructure", ("infrastructure",)), ("theme.water", ("water",)),
        ("theme.shipping", ("shipping", "dry bulk")), ("theme.uranium", ("uranium",)),
        ("theme.battery", ("battery", "lithium")), ("theme.biotech", ("biotech",)),
    ]
    return [code for code, words in mapping if any(word in text for word in words)]


def classify_sector(text: str, regions: list[str]) -> tuple[str, str | None] | None:
    is_china = "CN" in regions or _contains(text, "china", "csi", "a-share")
    if is_china:
        sw_mapping = [
            ("270000", "270100", ("semiconductor", "chip")),
            ("270000", "270500", ("electronics", "consumer electronic")),
            ("630000", "630300", ("solar", "photovoltaic")),
            ("630000", "630600", ("battery",)),
            ("240000", "240300", ("industrial metal", "copper", "aluminium", "aluminum")),
            ("240000", "240600", ("lithium", "energy metal")),
            ("370000", "370300", ("biotech", "biological")),
            ("370000", "370500", ("medical device",)),
            ("710000", "710300", ("software",)),
            ("710000", "710100", ("computer",)),
            ("650000", "650300", ("aerospace", "aviation")),
            ("650000", "650600", ("defense electronic",)),
            ("730000", "730200", ("communication equipment", "5g")),
            ("480000", None, ("bank",)), ("490000", None, ("financial", "broker")),
            ("280000", "280200", ("automobile", "auto ", "vehicle")),
            ("340000", None, ("food", "beverage", "consumer staple")),
        ]
        for sector, group, words in sw_mapping:
            if any(word in text for word in words):
                return f"equity.sw.{sector}", f"sw.{group}" if group else None

    mapping = [
        ("45", "4530", ("semiconductor", "chip")),
        ("45", "4510", ("software", "cloud", "cyber")),
        ("45", "4520", ("technology", "tech ", "hardware", "robot")),
        ("35", "3520", ("biotech", "pharmaceutical", "genomic")),
        ("35", "3510", ("health care", "healthcare", "medical device")),
        ("40", "4010", ("bank",)), ("40", "4030", ("insurance",)),
        ("40", "4020", ("financial", "fintech", "broker")),
        ("10", "1010", ("energy", "oil & gas", "oil and gas", "pipeline")),
        ("15", "1510", ("materials", "mining", "miners", "metal", "timber", "forest")),
        ("20", "2030", ("transportation", "shipping", "airline")),
        ("20", "2010", ("industrial", "aerospace", "defense", "infrastructure")),
        ("25", "2510", ("automobile", "auto ", "vehicle")),
        ("25", "2550", ("retail", "e-commerce", "consumer discretionary")),
        ("30", "3020", ("food", "beverage", "consumer staples")),
        ("50", "5020", ("media", "entertainment", "internet")),
        ("50", "5010", ("telecom", "communication service")),
        ("55", "5510", ("utilities", "utility")),
    ]
    for sector, group, words in mapping:
        if any(word in text for word in words):
            return f"equity.gics.{sector}", f"gics.{group}"
    return None


def classify_regions(symbol: str, name: str, gs: dict[str, str] | None) -> list[str]:
    gs_region = (gs or {}).get("地区", "")
    if gs_region in GS_REGION_MAP and GS_REGION_MAP[gs_region]:
        return list(GS_REGION_MAP[gs_region])
    compact = re.sub(r"[^A-Z]", "", symbol)
    if len(compact) == 6 and compact[:3] in CURRENCY_REGIONS and compact[3:] in CURRENCY_REGIONS:
        return _dedupe([CURRENCY_REGIONS[compact[:3]], CURRENCY_REGIONS[compact[3:]]])
    # Mainland-listed fund symbols are six digits and these prefixes cover the
    # Shanghai/Shenzhen ETF families in the current asset universe.  The
    # underlying exposure may be overseas, but the fund itself is a China
    # product, so use CN for the region filter.
    if re.fullmatch(r"(?:159|510|512|560|588)\d{3}", symbol):
        return ["CN"]
    if _contains(name, "ex-china", "ex china"):
        return ["EM"] if _contains(name, "em ", "emerging market") else []

    mapping = [
        ("CN", ("china", "chinese", "csi ", "a-share", "cny", "yuan")),
        ("JP", ("japan", "japanese", "nikkei")),
        ("KR", ("south korea", "korean", "kospi")),
        ("LATAM", ("brazil", "brazilian", "mexico", "mexican", "chile", "peru")),
        ("EUROPE", ("united kingdom", "british", "ftse 100", "gilt", "germany", "german", "dax", "france", "french", "cac 40", "switzerland", "swiss")),
        ("APAC", ("hong kong", "hang seng", "india", "nifty", "australia", "australian", "asx", "taiwan", "taiwanese", "singapore", "indonesia", "vietnam", "new zealand")),
        ("EM", ("south africa", "saudi", "uae", "united arab emirates")),
        ("US_CA", ("canada", "canadian", "tsx")),
    ]
    for code, words in mapping:
        if any(word in name for word in words):
            return [code]
    if _contains(name, "emerging market"):
        return ["EM"]
    if _contains(name, "europe", "euro stoxx"):
        return ["EUROPE"]
    if _contains(name, "asia", "asian"):
        return ["APAC"]
    if _contains(name, "s&p 500", "nasdaq", "dow jones", "russell", "u.s.", " us ", "united states"):
        return ["US"]
    if re.search(r"^US\d{2}Y$", symbol):
        return ["US"]
    if re.search(r"^CN\d{2}Y$", symbol):
        return ["CN"]
    # English-named ETFs/funds without a country cue are generally US-listed
    # products in this catalog. This intentionally also covers global and
    # international products because the requested fallback is product
    # domicile rather than inferred underlying exposure.
    if re.search(r"\b(?:etf|fund)\b", name) and name.isascii():
        return ["US"]
    if _contains(name, "international", "eafe", "ex-us", "ex us", "global", "world", "all-country"):
        return []
    return []


def _is_fx(symbol: str, name: str) -> bool:
    if symbol in {"6A1!", "6C1!", "6J1!", "6L1!", "6M1!", "6S1!"}:
        return True
    compact = re.sub(r"[^A-Z]", "", symbol)
    if len(compact) == 6 and compact[:3] in CURRENCY_REGIONS and compact[3:] in CURRENCY_REGIONS:
        return True
    if _contains(name, "currency futures", "dollar index", "dollar futures", "yen futures", "euro futures", "real futures", "peso futures", "franc futures"):
        return True
    return bool(re.search(r"\b(?:AUD|CAD|CHF|CNY|CNH|EUR|GBP|JPY|MXN|BRL|NZD)/(?:AUD|CAD|CHF|CNY|CNH|EUR|GBP|JPY|USD)\b", name.upper()))


def _is_commodity(name: str) -> bool:
    if _contains(name, "commodity index", "commodity fund", "agriculture fund", "base metals fund", "energy fund"):
        return True
    commodity_words = (
        "gold", "silver", "platinum", "palladium", "copper", "aluminium", "aluminum", "zinc", "nickel",
        "tin futures", "steel", "iron ore", "lithium", "rare earth", "crude", "brent", "natural gas",
        "gasoline", "fuel oil", "coal futures", "corn", "wheat", "soy", "rice", "cocoa", "coffee",
        "cotton", "sugar", "cattle", "hog", "rubber futures", "methanol", "urea", "bitumen",
    )
    if any(word in name for word in commodity_words):
        if _contains(name, "miners etf", "mining etf", "producer etf", "equity etf"):
            return False
        return True
    if "futures" in name and not _contains(name, "index futures", "yield futures", "currency futures", "volatility futures"):
        return True
    return False


def write_registry(path: Path, classifications: Iterable[tuple[Asset, Classification]]) -> None:
    primary = [_option(code, en, zh, []) for code, en, zh in PRIMARY]
    secondary = [_option(code, en, zh, parents) for code, en, zh, parents in SECONDARY_BASE]
    secondary.extend(_option(f"equity.gics.{code}", en, zh, ["equity"]) for code, en, zh in GICS_SECTORS)
    secondary.extend(_option(f"equity.sw.{code}", en, zh, ["equity"]) for code, en, zh in SW_SECTORS)
    tertiary = [_option(code, en, zh, parents) for code, en, zh, parents in TERTIARY_BASE]
    tertiary.extend(_option(f"gics.{code}", en, zh, [f"equity.gics.{parent}"]) for code, en, zh, parent in GICS_GROUPS)
    tertiary.extend(_option(f"sw.{code}", en, zh, [f"equity.sw.{parent}"]) for code, en, zh, parent in SW_GROUPS)
    used_regions = {code for _, classification in classifications for code in classification.regions}
    regions = []
    for code in REGION_ORDER:
        if code not in used_regions:
            continue
        label_en, label_zh = REGION_LABELS.get(code, (code, code))
        regions.append(_option(code, label_en, label_zh, []))
    payload = {
        "version": "2026-07-12",
        "standards": {
            "gics": {
                "version": "2024-08",
                "sector_count": 11,
                "industry_group_count": 25,
                "source_url": "https://www.spglobal.com/spdji/en/landing/topic/gics/",
            },
            "shenwan": {
                "version": "2021",
                "level_1_count": 31,
                "level_2_count": 134,
                "source_url": "https://wxweb.swsresearch.com/swsreport/2021_08/328340.pdf",
            },
        },
        "primary_categories": primary,
        "secondary_categories": secondary,
        "tertiary_categories": tertiary,
        "regions": regions,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_catalog(path: Path, classifications: Iterable[tuple[Asset, Classification]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "dataset_type", "symbol", "asset_name", "primary_category", "secondary_category",
            "tertiary_categories", "regions", "classification_basis", "source_url",
        ])
        for asset, classification in classifications:
            writer.writerow([
                asset.dataset_type, asset.symbol, asset.name, classification.primary, classification.secondary or "",
                "|".join(classification.tertiary), "|".join(classification.regions),
                classification.basis, classification.source_url,
            ])


def summary(classifications: list[tuple[Asset, Classification]]) -> dict[str, object]:
    primary_counts: dict[str, int] = {}
    for _, classification in classifications:
        primary_counts[classification.primary] = primary_counts.get(classification.primary, 0) + 1
    return {
        "asset_count": len(classifications),
        "unclassified_count": primary_counts.get("unclassified", 0),
        "primary_counts": primary_counts,
    }


def _option(code: str, label_en: str, label_zh: str, parent_codes: list[str]) -> dict[str, object]:
    return {"code": code, "label_en": label_en, "label_zh": label_zh, "parent_codes": parent_codes}


def _contains(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


if __name__ == "__main__":
    main()
