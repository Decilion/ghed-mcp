"""Read and query the GHED workbook."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook

CORE_COLUMNS = {"location", "code", "region", "income", "year"}
DEFAULT_PROFILE_INDICATORS = [
    "che_gdp",
    "che_pc_usd",
    "gghed_che",
    "oops_che",
    "ext_che",
    "gghed_gdp",
    "gghed_gge",
]


@dataclass(frozen=True)
class Indicator:
    indicator_code: str
    indicator_name: str | None
    long_code: str | None
    category_1: str | None
    category_2: str | None
    unit: str | None
    currency: str | None
    measurement_method: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "indicator_code": self.indicator_code,
            "indicator_name": self.indicator_name,
            "long_code": self.long_code,
            "category_1": self.category_1,
            "category_2": self.category_2,
            "unit": self.unit,
            "currency": self.currency,
            "measurement_method": self.measurement_method,
        }


def _clean(value: Any) -> Any:
    if value == "-":
        return None
    return value


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


class GHEDStore:
    """Small query layer over the public GHED XLSX workbook."""

    def __init__(self, workbook_path: str | Path):
        self.path = Path(workbook_path)
        self._header: list[str] | None = None
        self._indicators: dict[str, Indicator] | None = None
        self._countries: dict[str, dict[str, Any]] | None = None
        self._version: list[str] | None = None

    def _workbook(self):
        return load_workbook(self.path, read_only=True, data_only=True)

    def data_header(self) -> list[str]:
        if self._header is None:
            wb = self._workbook()
            try:
                self._header = [str(v) for v in next(wb["Data"].iter_rows(values_only=True))]
            finally:
                wb.close()
        return self._header

    def indicators(self) -> list[dict[str, Any]]:
        if self._indicators is None:
            wb = self._workbook()
            out: dict[str, Indicator] = {}
            try:
                rows = wb["Codebook"].iter_rows(values_only=True)
                next(rows)
                for row in rows:
                    code = row[0]
                    if not code or code in CORE_COLUMNS:
                        continue
                    ind = Indicator(
                        indicator_code=str(code),
                        indicator_name=_clean(row[1]),
                        long_code=_clean(row[2]),
                        category_1=_clean(row[3]),
                        category_2=_clean(row[4]),
                        unit=_clean(row[5]),
                        currency=_clean(row[6]),
                        measurement_method=_clean(row[7]),
                    )
                    out[ind.indicator_code] = ind
            finally:
                wb.close()
            self._indicators = out
        return [v.to_dict() for v in self._indicators.values()]

    def indicator_map(self) -> dict[str, Indicator]:
        if self._indicators is None:
            self.indicators()
        assert self._indicators is not None
        return self._indicators

    def get_indicator(self, indicator_code: str) -> dict[str, Any] | None:
        ind = self.indicator_map().get(indicator_code)
        return ind.to_dict() if ind else None

    def search_indicators(self, query: str, top: int = 50) -> list[dict[str, Any]]:
        needle = query.lower().strip()
        if not needle:
            return []
        matches = []
        for item in self.indicators():
            haystack = " ".join(
                str(item.get(k) or "")
                for k in (
                    "indicator_code",
                    "indicator_name",
                    "long_code",
                    "category_1",
                    "category_2",
                    "unit",
                    "currency",
                )
            ).lower()
            if needle in haystack:
                matches.append(item)
                if len(matches) >= top:
                    break
        return matches

    def countries(self) -> list[dict[str, Any]]:
        if self._countries is None:
            wb = self._workbook()
            out: dict[str, dict[str, Any]] = {}
            try:
                rows = wb["Data"].iter_rows(values_only=True)
                next(rows)
                for row in rows:
                    code = row[1]
                    if not code or code in out:
                        continue
                    out[str(code)] = {
                        "country_code": str(code),
                        "country_name": row[0],
                        "region": row[2],
                        "income": row[3],
                    }
            finally:
                wb.close()
            self._countries = out
        return list(self._countries.values())

    def country_map(self) -> dict[str, dict[str, Any]]:
        if self._countries is None:
            self.countries()
        assert self._countries is not None
        return self._countries

    def find_countries(self, query: str) -> list[dict[str, Any]]:
        needle = query.lower().strip()
        return [
            row for row in self.countries()
            if needle in row["country_code"].lower()
            or needle in str(row["country_name"]).lower()
        ]

    def resolve_country(self, country: str) -> str:
        value = country.strip()
        upper = value.upper()
        countries = self.country_map()
        if upper in countries:
            return upper
        matches = [
            code for code, row in countries.items()
            if value.lower() in str(row["country_name"]).lower()
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(countries[c]["country_name"] for c in matches[:5])
            more = "..." if len(matches) > 5 else ""
            raise ValueError(
                f"Ambiguous country '{country}': {len(matches)} matches "
                f"({names}{more}). Pass an ISO3 code."
            )
        raise ValueError(f"Could not resolve country '{country}'. Pass an ISO3 code.")

    def version(self) -> dict[str, Any]:
        if self._version is None:
            wb = self._workbook()
            try:
                self._version = [
                    str(row[0]) for row in wb["Version"].iter_rows(values_only=True)
                    if row and row[0]
                ]
            finally:
                wb.close()
        return {"lines": list(self._version)}

    def indicator_data(
        self,
        indicator_code: str,
        *,
        countries: Iterable[str] | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
        latest_only: bool = False,
        top: int = 1000,
    ) -> list[dict[str, Any]]:
        header = self.data_header()
        if indicator_code not in header:
            raise ValueError(f"Unknown GHED indicator '{indicator_code}'.")
        ind_idx = header.index(indicator_code)
        indicator = self.indicator_map().get(indicator_code)

        wanted = None
        if countries:
            wanted = {self.resolve_country(c) for c in countries}

        rows_out: list[dict[str, Any]] = []
        wb = self._workbook()
        try:
            rows = wb["Data"].iter_rows(values_only=True)
            next(rows)
            for row in rows:
                country_code = row[1]
                if wanted is not None and country_code not in wanted:
                    continue
                year = _as_int(row[4])
                if year_start is not None and (year is None or year < year_start):
                    continue
                if year_end is not None and (year is None or year > year_end):
                    continue
                value = row[ind_idx] if ind_idx < len(row) else None
                if value is None:
                    continue
                rows_out.append({
                    "indicator_code": indicator_code,
                    "indicator_name": indicator.indicator_name if indicator else None,
                    "country_code": country_code,
                    "country_name": row[0],
                    "region": row[2],
                    "income": row[3],
                    "year": year,
                    "value": value,
                    "unit": indicator.unit if indicator else None,
                    "currency": indicator.currency if indicator else None,
                    "category_1": indicator.category_1 if indicator else None,
                    "category_2": indicator.category_2 if indicator else None,
                })
        finally:
            wb.close()

        rows_out.sort(key=lambda r: (r["country_code"], -(r["year"] or 0)))
        if latest_only:
            latest: dict[str, dict[str, Any]] = {}
            for row in rows_out:
                current = latest.get(row["country_code"])
                if current is None or (row["year"] or -1) > (current["year"] or -1):
                    latest[row["country_code"]] = row
            rows_out = sorted(latest.values(), key=lambda r: r["country_code"])
        return rows_out[:top]

    def country_profile(
        self,
        country: str,
        *,
        year: int | None = None,
        indicator_codes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        code = self.resolve_country(country)
        codes = indicator_codes or DEFAULT_PROFILE_INDICATORS
        header = self.data_header()
        missing = [indicator_code for indicator_code in codes if indicator_code not in header]
        if missing:
            raise ValueError(f"Unknown GHED indicator(s): {', '.join(missing)}")

        indices = {indicator_code: header.index(indicator_code) for indicator_code in codes}
        indicators = self.indicator_map()
        countries = self.country_map()
        latest: dict[str, dict[str, Any]] = {}

        wb = self._workbook()
        try:
            rows = wb["Data"].iter_rows(values_only=True)
            next(rows)
            for row in rows:
                if row[1] != code:
                    continue
                row_year = _as_int(row[4])
                if year is not None and (row_year is None or row_year > year):
                    continue
                for indicator_code, idx in indices.items():
                    value = row[idx] if idx < len(row) else None
                    if value is None:
                        continue
                    current = latest.get(indicator_code)
                    if current is None or (row_year or -1) > (current["year"] or -1):
                        indicator = indicators.get(indicator_code)
                        latest[indicator_code] = {
                            "indicator_code": indicator_code,
                            "indicator_name": (
                                indicator.indicator_name if indicator else None
                            ),
                            "country_code": code,
                            "country_name": countries[code]["country_name"],
                            "region": row[2],
                            "income": row[3],
                            "year": row_year,
                            "value": value,
                            "unit": indicator.unit if indicator else None,
                            "currency": indicator.currency if indicator else None,
                            "category_1": indicator.category_1 if indicator else None,
                            "category_2": indicator.category_2 if indicator else None,
                        }
        finally:
            wb.close()

        results = []
        for indicator_code in codes:
            if indicator_code in latest:
                results.append(latest[indicator_code])
            else:
                indicator = self.get_indicator(indicator_code) or {}
                results.append({
                    "indicator_code": indicator_code,
                    "indicator_name": indicator.get("indicator_name"),
                    "country_code": code,
                    "country_name": countries[code]["country_name"],
                    "year": None,
                    "value": None,
                })
        return results

    def country_metadata(
        self,
        *,
        country: str | None = None,
        indicator_code: str | None = None,
        top: int = 20,
    ) -> list[dict[str, Any]]:
        resolved = self.resolve_country(country) if country else None
        wb = self._workbook()
        out = []
        try:
            rows = wb["Metadata"].iter_rows(values_only=True)
            next(rows)
            for row in rows:
                if resolved and row[1] != resolved:
                    continue
                if indicator_code and row[4] != indicator_code:
                    continue
                out.append({
                    "country_name": row[0],
                    "country_code": row[1],
                    "region": row[2],
                    "income": row[3],
                    "indicator_code": row[4],
                    "long_code": row[5],
                    "indicator_name": row[6],
                    "sources": row[7],
                    "comments": row[8],
                    "data_type": row[9],
                    "methods_of_estimation": row[10],
                    "country_footnote": row[11],
                })
                if len(out) >= top:
                    break
        finally:
            wb.close()
        return out


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    fields = [
        "indicator_code",
        "indicator_name",
        "country_code",
        "country_name",
        "region",
        "income",
        "year",
        "value",
        "unit",
        "currency",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
