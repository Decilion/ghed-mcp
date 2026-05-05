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

ADDITIVE_RELATIONSHIPS: dict[str, list[dict[str, Any]]] = {
    "che": [
        {
            "relationship_id": "che_by_financing_scheme",
            "description": "CHE decomposed by SHA financing schemes.",
            "children": ["hf1", "hf2", "hf3", "hf4", "hfnec"],
            "basis": "Codebook measurement method for CHE; equivalent to sha11.HF direct children.",
        },
        {
            "relationship_id": "che_by_domestic_external_source",
            "description": "CHE decomposed into domestic government, domestic private, and external health expenditure.",
            "children": ["gghed", "pvtd", "ext"],
            "basis": "Derived from FS source groupings: GGHE-D + PVT-D + EXT.",
        },
    ],
    "gghed": [
        {
            "relationship_id": "gghed_by_revenue",
            "description": "Domestic general government health expenditure by revenue components.",
            "children": ["fs1", "fs3"],
            "basis": "Codebook measurement method: FS.1 + FS.3.",
        }
    ],
    "pvtd": [
        {
            "relationship_id": "pvtd_by_revenue",
            "description": "Domestic private health expenditure by revenue components.",
            "children": ["fs4", "fs5", "fs6", "fsnec"],
            "basis": "Codebook measurement method: FS.4 + FS.5 + FS.6 + FS.nec.",
        }
    ],
    "ext": [
        {
            "relationship_id": "ext_by_revenue",
            "description": "External health expenditure by revenue components.",
            "children": ["fs2", "fs7"],
            "basis": "Codebook measurement method: FS.2 + FS.7.",
        }
    ],
}

RESEARCH_USE_CASES: dict[str, dict[str, Any]] = {
    "health_financing_transition": {
        "description": (
            "Study how the level and composition of health spending changes with "
            "income, time, or reform: government, OOP, prepaid private, and external."
        ),
        "recommended_codes": [
            "che_pc_usd",
            "che_gdp",
            "gghed_che",
            "oops_che",
            "vpp_che",
            "ext_che",
        ],
        "typical_questions": [
            "How did the financing mix change from 2000 to 2024?",
            "Which countries rely more on OOP or external funding than peers?",
            "Did government spending rise as countries became richer?",
        ],
        "cautions": [
            "Latest values may differ by country and variable.",
            "Use constant or PPP per-capita series for cross-country level comparisons.",
        ],
    },
    "financial_protection_oop": {
        "description": (
            "Use OOP indicators as macro health-financing context for UHC and "
            "financial protection research."
        ),
        "recommended_codes": [
            "oops_che",
            "oops_pc_usd",
            "oops_ppp_pc",
            "oop_pc_usd",
        ],
        "typical_questions": [
            "Which countries have persistently high OOP shares?",
            "Did OOP decline after government spending increased?",
            "How does OOP spending compare with catastrophic expenditure survey results?",
        ],
        "cautions": [
            "GHED OOP is national accounts spending, not household catastrophic expenditure.",
            "Pair with household survey or SDG 3.8.2 data for direct financial-protection outcomes.",
        ],
    },
    "government_priority": {
        "description": (
            "Analyze government health spending effort and priority in the public budget."
        ),
        "recommended_codes": [
            "gghed",
            "gghed_che",
            "gghed_gdp",
            "gghed_gge",
            "gghed_pc_usd",
            "gghed_ppp_pc",
        ],
        "typical_questions": [
            "What share of total health spending is government funded?",
            "How much fiscal priority does health receive in the government budget?",
            "Did government health spending grow faster than GDP or general government expenditure?",
        ],
        "cautions": [
            "GGHE-D includes domestic general government sources; inspect metadata for estimated/documented status.",
            "Do not confuse share of CHE with share of GDP or share of GGE.",
        ],
    },
    "donor_dependence": {
        "description": "Assess external funding dependence and its change over time.",
        "recommended_codes": [
            "ext",
            "ext_che",
            "ext_gdp",
            "ext_pc_usd",
            "ext_ppp_pc",
        ],
        "typical_questions": [
            "Which countries are most dependent on external health funding?",
            "Has external funding declined after income growth?",
            "How volatile is external funding over time?",
        ],
        "cautions": [
            "External current health expenditure can exclude capital aid depending on reporting.",
            "Inspect sources/methods for donor-heavy countries.",
        ],
    },
    "private_and_voluntary_insurance": {
        "description": "Study private, voluntary, and prepaid financing arrangements.",
        "recommended_codes": [
            "pvtd_che",
            "vpp_che",
            "vhi_che",
            "chi_pvt_che",
        ],
        "typical_questions": [
            "Is voluntary insurance growing in LMICs?",
            "Does private prepayment substitute for OOP spending?",
            "Which countries have non-trivial voluntary/private insurance shares?",
        ],
        "cautions": [
            "Voluntary health insurance can be sparse and difficult to compare.",
            "Interpret insurance roles with country policy context.",
        ],
    },
    "services_providers_sha": {
        "description": (
            "Use detailed SHA series for spending by health care function, provider, "
            "financing scheme, source, disease/condition, or cross-tab."
        ),
        "recommended_categories": [
            "HEALTH CARE FUNCTIONS",
            "HEALTH CARE PROVIDERS",
            "FINANCING SCHEMES",
            "HEALTH CARE FUNCTIONS BY SOURCE",
            "DISEASES AND CONDITIONS",
            "DISEASES AND CONDITIONS BY SOURCE",
        ],
        "typical_questions": [
            "How much is spent on inpatient versus outpatient care?",
            "Which provider types account for spending?",
            "How are functions funded by public, private, or external sources?",
        ],
        "cautions": [
            "Detailed SHA categories are less complete than headline indicators.",
            "Run data availability checks before cross-country comparisons.",
        ],
    },
    "primary_health_care": {
        "description": "Analyze PHC spending levels and shares.",
        "recommended_codes": [
            "phc",
            "phc_che",
            "phc_pc_usd",
            "phc_ppp_pc",
        ],
        "typical_questions": [
            "What share of CHE is primary health care?",
            "Which countries report PHC spending consistently?",
            "How has PHC spending changed since 2016?",
        ],
        "cautions": [
            "PHC reporting can be partial; use metadata and missingness summaries.",
        ],
    },
}

_USE_CASE_KEYWORDS: dict[str, set[str]] = {
    "health_financing_transition": {
        "transition", "financing mix", "composition", "economic development",
        "income", "prepaid", "mix", "sources", "resource mobilization",
        "health financing", "financing transition", "spending transition",
    },
    "financial_protection_oop": {
        "oop", "out-of-pocket", "out of pocket", "financial protection",
        "catastrophic", "impoverishing", "household", "direct payment",
        "user fee", "copayment", "co-payment", "financial hardship",
    },
    "government_priority": {
        "government", "public", "fiscal", "priority", "budget", "gghe",
        "gghed", "domestic general government", "public spending",
        "public expenditure", "fiscal space", "government budget",
        "general government expenditure",
    },
    "donor_dependence": {
        "external", "donor", "aid", "development assistance", "dah",
        "foreign", "oda", "donor dependence", "external resources",
        "aid dependence",
    },
    "private_and_voluntary_insurance": {
        "private", "voluntary", "insurance", "vhi", "prepayment",
        "compulsory private", "private insurance", "voluntary health insurance",
        "prepaid private",
    },
    "services_providers_sha": {
        "function", "provider", "service", "disease", "condition", "scheme",
        "revenue", "sha", "classification", "inpatient", "outpatient",
        "hospital", "ambulatory", "breakdown", "decomposition", "hierarchy",
    },
    "primary_health_care": {
        "primary health care", "phc", "primary care", "first contact",
        "basic care",
    },
}

_INDICATOR_ALIASES: dict[str, list[str]] = {
    "che_gdp": ["health spending share of GDP", "health expenditure percent GDP"],
    "che_pc_usd": ["health spending per capita", "current health expenditure per capita"],
    "che_ppp_pc": ["PPP health spending per capita", "comparable per capita health spending"],
    "gghed_gge": ["fiscal priority", "health share of government budget"],
    "gghed_gdp": ["public health spending share of GDP"],
    "gghed_che": ["government share of health spending", "public share of health spending"],
    "oops_che": ["out-of-pocket burden", "OOP share", "household payment share"],
    "oops_pc_usd": ["OOP per capita", "out-of-pocket spending per person"],
    "ext_che": ["donor dependence", "external share of health spending"],
    "ext_gdp": ["external health funding share of GDP"],
    "pvtd_che": ["private domestic share of health spending"],
    "vpp_che": ["voluntary prepaid share", "voluntary prepayment"],
    "phc_che": ["primary health care share", "PHC share of CHE"],
}


def research_use_cases() -> dict[str, Any]:
    return {"use_cases": RESEARCH_USE_CASES}


def suggest_use_cases(question: str) -> dict[str, Any]:
    q = question.lower()
    scores = []
    for use_case, keywords in _USE_CASE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in q)
        if score:
            scores.append((score, use_case))
    scores.sort(reverse=True)
    if not scores:
        scores = [(1, "core_spending")]

    suggestions = []
    for _, use_case in scores[:3]:
        payload = RESEARCH_USE_CASES.get(use_case)
        if payload:
            suggestions.append({"use_case": use_case, **payload})
        elif use_case in TOPICS:
            topic = TOPICS[use_case]
            suggestions.append({
                "use_case": use_case,
                "description": topic["description"],
                "recommended_codes": topic["indicator_codes"],
                "typical_questions": [],
                "cautions": [],
            })
    matched_aliases = []
    for code, aliases in _INDICATOR_ALIASES.items():
        hits = [alias for alias in aliases if alias.lower() in q]
        if hits:
            matched_aliases.append({
                "indicator_code": code,
                "matched_aliases": hits,
            })
    return {
        "question": question,
        "suggestions": suggestions,
        "matched_indicator_aliases": matched_aliases,
        "general_cautions": METHODOLOGY_SUMMARY["analysis_cautions"],
    }


def methodology_summary() -> dict[str, Any]:
    return {
        "summary": METHODOLOGY_SUMMARY,
        "category_guide": CATEGORY_GUIDE,
        "topics": TOPICS,
        "research_use_cases": RESEARCH_USE_CASES,
        "additive_relationships": ADDITIVE_RELATIONSHIPS,
    }


def topic_index() -> dict[str, Any]:
    return {"topics": TOPICS}
