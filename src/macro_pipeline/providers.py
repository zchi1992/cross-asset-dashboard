from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import requests

from src.zsxq_pipeline.xlsx_parser import read_sheet


TENORS = (2.0, 5.0, 10.0, 30.0)


class UnconfiguredSource(RuntimeError):
    pass


def fetch_us_treasury(session: requests.Session, start: date, end: date):
    rows = []
    payloads = []
    fields = {2.0: "BC_2YEAR", 5.0: "BC_5YEAR", 10.0: "BC_10YEAR", 30.0: "BC_30YEAR"}
    for year in range(start.year, end.year + 1):
        url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
        response = session.get(
            url,
            params={"data": "daily_treasury_yield_curve", "field_tdr_date_value": year},
            timeout=45,
        )
        response.raise_for_status()
        payloads.append(response.text)
        root = ET.fromstring(response.content)
        for properties in root.iter():
            if properties.tag.rsplit("}", 1)[-1] != "properties":
                continue
            values = {child.tag.rsplit("}", 1)[-1]: child.text for child in properties}
            observed_at = str(values.get("NEW_DATE", ""))[:10]
            if not observed_at or observed_at < start.isoformat() or observed_at > end.isoformat():
                continue
            for tenor, field in fields.items():
                if values.get(field):
                    rows.append(_curve_row(observed_at, "US", "美国", tenor, values[field], "us_treasury", "US Treasury", url, "par government curve"))
    return rows, "\n".join(payloads).encode()


def fetch_ecb(session: requests.Session, start: date, end: date):
    url = "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y+SR_5Y+SR_10Y+SR_30Y"
    response = session.get(url, params={"startPeriod": start, "endPeriod": end, "format": "csvdata"}, timeout=45)
    response.raise_for_status()
    rows = []
    for item in csv.DictReader(StringIO(response.text)):
        data_type = item.get("DATA_TYPE_FM", "")
        tenor_text = data_type.removeprefix("SR_").removesuffix("Y")
        if tenor_text.isdigit() and float(tenor_text) in TENORS and item.get("OBS_VALUE"):
            rows.append(_curve_row(item["TIME_PERIOD"], "EU", "欧元区", float(tenor_text), item["OBS_VALUE"], "ecb", "ECB", url, "AAA zero-coupon spot curve"))
    return rows, response.content


def fetch_china(session: requests.Session, start: date, end: date):
    url = "https://yield.chinabond.com.cn/cbweb-czb-web/czb/historyQuery"
    fields = {2.0: "twoYear", 5.0: "fiveYear", 10.0: "tenYear", 30.0: "thirtyYear"}
    rows = []
    payloads = []
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=364))
        response = session.post(
            url,
            params={
                "startDate": cursor.isoformat(),
                "endDate": chunk_end.isoformat(),
                "gjqx": "2,5,10,30",
                "locale": "cn_ZH",
                "qxmc": "1",
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        payloads.append(payload)
        for item in payload.get("heList", []):
            for tenor, field in fields.items():
                if item.get(field) not in {None, ""}:
                    rows.append(_curve_row(item["workTime"], "CN", "中国", tenor, item[field], "chinabond", "财政部 / 中债", "https://yield.chinabond.com.cn/cbweb-czb-web/czb/showHistory?locale=cn_ZH&nameType=1", "government yield curve"))
        cursor = chunk_end + timedelta(days=1)
    return rows, json.dumps(payloads, ensure_ascii=False).encode()


def fetch_japan(session: requests.Session, start: date, end: date):
    urls = [
        "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv",
        "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv",
    ]
    rows = []
    payloads = []
    for url in urls:
        response = session.get(url, timeout=45)
        response.raise_for_status()
        payloads.append(response.content)
        text = response.content.decode("utf-8-sig", errors="replace")
        for item in csv.DictReader(text.splitlines()[1:]):
            try:
                observed_at = datetime.strptime(item["Date"], "%Y/%m/%d").date()
            except (KeyError, ValueError):
                continue
            if not start <= observed_at <= end:
                continue
            for tenor in TENORS:
                value = item.get(f"{int(tenor)}Y")
                if value and value != "-":
                    rows.append(_curve_row(observed_at.isoformat(), "JP", "日本", tenor, value, "japan_mof", "Japan MOF", url, "constant-maturity government curve"))
    return rows, b"\n".join(payloads)


def fetch_uk(session: requests.Session, start: date, end: date):
    latest_only = start >= date.today() - timedelta(days=45)
    filename = "latest-yield-curve-data.zip" if latest_only else "glcnominalddata.zip"
    url = f"https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/{filename}"
    response = session.get(url, timeout=90)
    response.raise_for_status()
    rows = []
    with ZipFile(BytesIO(response.content)) as archive:
        names = [name for name in archive.namelist() if "nominal" in name.lower() and name.lower().endswith(".xlsx")]
        for name in names:
            with tempfile.NamedTemporaryFile(suffix=".xlsx") as handle:
                handle.write(archive.read(name))
                handle.flush()
                try:
                    _, sheet_rows = read_sheet(handle.name, "4. spot curve")
                except ValueError:
                    continue
            if len(sheet_rows) < 5:
                continue
            headers = sheet_rows[2]
            indexes = {tenor: headers.index(str(int(tenor))) for tenor in TENORS if str(int(tenor)) in headers}
            for item in sheet_rows[4:]:
                if not item or not item[0]:
                    continue
                try:
                    observed_at = date(1899, 12, 30) + timedelta(days=int(float(item[0])))
                except ValueError:
                    continue
                if not start <= observed_at <= end:
                    continue
                for tenor, index in indexes.items():
                    if index < len(item) and item[index]:
                        rows.append(_curve_row(observed_at.isoformat(), "GB", "英国", tenor, item[index], "boe", "Bank of England", url, "nominal government spot curve"))
    return rows, response.content


def fetch_fred_credit(session: requests.Session, start: date, end: date):
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise UnconfiguredSource("FRED_API_KEY is not configured")
    url = "https://api.stlouisfed.org/fred/series/observations"
    definitions = {
        "BAMLH0A0HYM2": ("HY_OAS", "HY OAS", "percent", "daily"),
        "BAMLC0A0CM": ("IG_OAS", "IG OAS", "percent", "daily"),
        "NFCI": ("NFCI", "Chicago Fed NFCI", "index", "weekly"),
        "DRTSCILM": ("SLOOS", "SLOOS C&I Tightening", "pp", "quarterly"),
    }
    rows = []
    payloads = {}
    for fred_id, (series_id, label, unit, frequency) in definitions.items():
        response = session.get(
            url,
            params={
                "series_id": fred_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": start,
                "observation_end": end,
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        payloads[fred_id] = payload
        for item in payload.get("observations", []):
            if item.get("value") not in {None, "."}:
                rows.append(_credit_row(item["date"], series_id, label, item["value"], unit, frequency, "fred", "FRED", f"https://fred.stlouisfed.org/series/{fred_id}"))
    return rows, json.dumps(payloads).encode()


def fetch_ofr(session: requests.Session, start: date, end: date):
    url = "https://www.financialresearch.gov/financial-stress-index/data/fsi.csv"
    response = session.get(url, timeout=45)
    response.raise_for_status()
    rows = []
    for item in csv.DictReader(StringIO(response.text)):
        observed_at = item.get("Date", "")
        if start.isoformat() <= observed_at <= end.isoformat() and item.get("OFR FSI"):
            rows.append(_credit_row(observed_at, "OFR_FSI", "OFR Financial Stress Index", item["OFR FSI"], "index", "daily", "ofr", "Office of Financial Research", "https://www.financialresearch.gov/financial-stress-index/"))
    return rows, response.content


def _curve_row(observed_at, region, region_name, tenor, value, source_id, source_name, source_url, curve_type):
    return {
        "date": str(observed_at),
        "region": region,
        "region_name": region_name,
        "tenor_years": f"{float(tenor):g}",
        "value": str(float(value)),
        "unit": "%",
        "curve_type": curve_type,
        "source_id": source_id,
        "source_name": source_name,
        "source_url": source_url,
    }


def _credit_row(observed_at, series_id, label, value, unit, frequency, source_id, source_name, source_url):
    return {
        "date": str(observed_at),
        "series_id": series_id,
        "label": label,
        "value": str(float(value)),
        "unit": unit,
        "frequency": frequency,
        "source_id": source_id,
        "source_name": source_name,
        "source_url": source_url,
    }
