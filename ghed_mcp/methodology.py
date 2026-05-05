"""Methodology guidance and curated GHED indicator topics."""
from __future__ import annotations

from typing import Any

METHODOLOGY_SUMMARY: dict[str, Any] = {
    "source_of_truth": (
        "The MCP uses the Documentation Centre 'GHED all data' workbook as the "
        "source of truth. The workbook contains Data, Codebook, Metadata, and "
        "Version sheets."
    ),
    "framework": (
        "GHED follows the System of Health Accounts 2011 (SHA 2011). The data "
        "cover health expenditure by financing arrangements, revenues, health "
        "care functions, providers, diseases and conditions, capital, primary "
        "health care, and selected age/COVID reporting items."
    ),
    "variable_classes": {
        "INDICATORS": (
            "Headline/derived indicators intended for common analysis, such as "
            "current health expenditure as a share of GDP, per-capita spending, "
            "government spending shares, out-of-pocket shares, external funding, "
            "capital spending, and PHC-related shares."
        ),
        "HEALTH EXPENDITURE DATA": (
            "Detailed SHA accounting series. These include raw or derived health "
            "expenditure series by financing scheme, revenue, function, provider, "
            "disease/condition, source combinations, age, capital, PHC, and COVID "
            "special reporting."
        ),
        "MACRO DATA": (
            "Macro denominators and conversion series used to calculate health "
            "expenditure indicators, such as GDP, population, exchange rates, and "
            "price index variables."
        ),
    },
    "analysis_cautions": [
        "Prefer category_1='INDICATORS' for ordinary policy questions unless the user explicitly asks for detailed SHA classifications.",
        "Use Metadata rows for country/variable source notes, data type, and estimation method before making strong claims.",
        "When latest values come from different years across countries, say so explicitly.",
        "Data for recent years can be preliminary; inspect the Version sheet and Metadata notes.",
        "Current NCU, constant NCU, current USD, constant USD, PPP, per-capita, %CHE, %GDP, and %GGE variants are not interchangeable.",
    ],
}

CATEGORY_GUIDE: dict[str, str] = {
    "AGGREGATES": "Broad spending totals and shares: CHE, CHE/GDP, CHE per capita, domestic/external components.",
    "FINANCING SOURCES": "Revenue/source perspective, including government, private, external, OOP, and voluntary spending shares.",
    "FINANCING SCHEMES": "Health financing arrangement perspective, such as government schemes, insurance, OOP, and rest-of-world schemes.",
    "REVENUES": "Detailed revenues of health care financing schemes under SHA 2011 FS classifications.",
    "HEALTH CARE FUNCTIONS": "Spending by type of health care good/service under SHA 2011 HC classifications.",
    "HEALTH CARE FUNCTIONS BY SOURCE": "Health care functions crossed with funding source or financing dimensions.",
    "HEALTH CARE PROVIDERS": "Spending by provider type under SHA 2011 HP classifications.",
    "DISEASES AND CONDITIONS": "Spending by disease or condition groups.",
    "DISEASES AND CONDITIONS BY SOURCE": "Disease/condition spending crossed with funding source or financing dimensions.",
    "CAPITAL INVESTMENTS": "Capital formation and investment in health care assets.",
    "PRIMARY HEALTH CARE": "Primary health care expenditure and related shares.",
    "AGE": "Under-five or age-focused health expenditure variables.",
    "COVID-19": "COVID-19 spending indicators.",
    "COVID-19 SPECIAL REPORTING ITEMS": "Detailed COVID-19 special reporting series.",
    "MACRO": "Macro denominators such as GDP and population.",
    "EXCHANGE RATES": "Exchange rate variables used for currency conversion.",
    "PRICE INDEX": "Deflator or price index variables used for constant-price series.",
    "POPULATION": "Population variables used for per-capita calculations.",
}

TOPICS: dict[str, dict[str, Any]] = {
    "core_spending": {
        "description": "Core health spending level and scale indicators.",
        "indicator_codes": [
            "che_gdp",
            "che_pc_usd",
            "che_ppp_pc",
            "che",
            "che_usd",
            "che_usd2023",
        ],
    },
    "government_spending": {
        "description": "Domestic general government health spending level and priority indicators.",
        "indicator_codes": [
            "gghed",
            "gghed_che",
            "gghed_gdp",
            "gghed_gge",
            "gghed_pc_usd",
            "gghed_ppp_pc",
        ],
    },
    "out_of_pocket": {
        "description": "Household out-of-pocket payment level and burden indicators.",
        "indicator_codes": [
            "oops",
            "oops_che",
            "oops_pc_usd",
            "oops_ppp_pc",
        ],
    },
    "external_aid": {
        "description": "External funding for health and external funding shares.",
        "indicator_codes": [
            "ext",
            "ext_che",
            "ext_gdp",
            "ext_pc_usd",
            "ext_ppp_pc",
        ],
    },
    "private_spending": {
        "description": "Domestic private spending and voluntary payment indicators.",
        "indicator_codes": [
            "pvtd",
            "pvtd_che",
            "pvtd_pc_usd",
            "vpp_che",
        ],
    },
    "capital": {
        "description": "Capital health expenditure and investment indicators.",
        "indicator_codes": [
            "hk",
            "hk_gdp",
            "hk_pc_usd",
            "hk_ppp_pc",
        ],
    },
    "primary_health_care": {
        "description": "Primary health care expenditure indicators.",
        "indicator_codes": [
            "phc",
            "phc_che",
            "phc_pc_usd",
            "phc_ppp_pc",
        ],
    },
    "macro_context": {
        "description": "Macro denominators and conversion variables for interpretation.",
        "indicator_codes": [
            "gdp",
            "pop",
            "ex_usd",
            "ppp",
        ],
    },
}


def methodology_summary() -> dict[str, Any]:
    return {
        "summary": METHODOLOGY_SUMMARY,
        "category_guide": CATEGORY_GUIDE,
        "topics": TOPICS,
    }


def topic_index() -> dict[str, Any]:
    return {"topics": TOPICS}
