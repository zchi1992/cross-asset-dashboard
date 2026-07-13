from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from .constants import BASE_COLUMNS, METRIC_NAME_MAP

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _column_index(cell_ref: str) -> int:
    letters = ""
    for char in cell_ref:
        if char.isalpha():
            letters += char
        else:
            break
    total = 0
    for char in letters:
        total = total * 26 + (ord(char.upper()) - ord("A") + 1)
    return total - 1


def _normalize_target(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return "xl/" + target


def _shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("main:si", NS):
        values.append("".join(node.text or "" for node in item.iterfind(".//main:t", NS)))
    return values


def _sheet_paths(archive: ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: _normalize_target(rel.attrib["Target"])
        for rel in rels.findall("pkgrel:Relationship", NS)
    }
    return [
        (
            sheet.attrib["name"],
            rel_map[
                sheet.attrib[
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                ]
            ],
        )
        for sheet in workbook.find("main:sheets", NS)
    ]


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find("main:v", NS)
    inline = cell.find("main:is", NS)
    if cell_type == "s" and value is not None and value.text is not None:
        return shared_strings[int(value.text)]
    if cell_type == "inlineStr" and inline is not None:
        return "".join(node.text or "" for node in inline.iterfind(".//main:t", NS))
    if value is not None and value.text is not None:
        return value.text
    return ""


def read_first_sheet(path: str | Path) -> tuple[str, list[list[str]]]:
    return read_sheet(path)


def read_sheet(path: str | Path, sheet_name: str | None = None) -> tuple[str, list[list[str]]]:
    file_path = Path(path)
    with ZipFile(file_path) as archive:
        shared = _shared_strings(archive)
        sheets = _sheet_paths(archive)
        if sheet_name is None:
            selected_name, sheet_path = sheets[0]
        else:
            try:
                selected_name, sheet_path = next(item for item in sheets if item[0] == sheet_name)
            except StopIteration as exc:
                raise ValueError(f"Excel 中不存在工作表 {sheet_name}: {path}") from exc
        sheet_xml = ET.fromstring(archive.read(sheet_path))
        rows: list[list[str]] = []
        for row in sheet_xml.findall(".//main:sheetData/main:row", NS):
            sparse_cells = row.findall("main:c", NS)
            if not sparse_cells:
                continue
            rendered: list[str] = []
            for cell in sparse_cells:
                index = _column_index(cell.attrib.get("r", "A1"))
                while len(rendered) <= index:
                    rendered.append("")
                rendered[index] = _cell_value(cell, shared)
            rows.append(rendered)
        return selected_name, rows


def parse_metrics_from_workbook(
    path: str | Path,
    *,
    dataset_type: str,
    as_of_date: str,
) -> list[dict[str, str]]:
    _, rows = read_first_sheet(path)
    if not rows:
        raise ValueError(f"Excel 为空: {path}")

    headers = rows[0]
    if len(headers) < 2 or tuple(headers[:2]) != BASE_COLUMNS:
        raise ValueError(f"表头前两列不符合预期: {headers[:2]}")

    unknown_headers = [header for header in headers[2:] if header not in METRIC_NAME_MAP]
    if unknown_headers:
        raise ValueError(f"发现未映射列名: {unknown_headers}")

    records: list[dict[str, str]] = []
    for row in rows[1:]:
        if len(row) < 2:
            continue
        asset_code = (row[0] or "").strip()
        asset_name = (row[1] or "").strip()
        if not asset_code or not asset_name:
            continue
        for index, metric_name_zh in enumerate(headers[2:], start=2):
            metric_value = row[index] if index < len(row) else ""
            records.append(
                {
                    "date": as_of_date,
                    "dataset_type": dataset_type,
                    "asset_code": asset_code,
                    "asset_name": asset_name,
                    "metric_name": METRIC_NAME_MAP[metric_name_zh],
                    "metric_value": metric_value,
                }
            )
    return records
