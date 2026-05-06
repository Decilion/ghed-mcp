"""Curated country groupings used across Decilion's MCP servers.

This module defines analytical country groupings beyond what WHO publishes
directly — World Bank geographic regions, UN Least Developed Countries,
and OECD membership. The same definitions live in `gho-mcp` so both
servers resolve "LAC", "SSA", "OECD", "LDC", etc. identically.

Membership lists change. Each constant carries a `LAST_VERIFIED` marker
and a source URL. Re-check annually.

Sources:
- World Bank country and lending groups (regions + income):
  https://datahelpdesk.worldbank.org/knowledgebase/articles/906519
- UN list of Least Developed Countries:
  https://www.un.org/development/desa/dpad/least-developed-country-category.html
- OECD member list:
  https://www.oecd.org/about/document/list-oecd-member-countries.htm
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

LAST_VERIFIED = "2026-05-06"
# 2026-05-06 verification notes:
# - WB regions match WB FY2026 classification (effective July 2025).
#   The big restructuring vs prior classifications: WB renamed the old
#   "Middle East & North Africa" region to "Middle East, North Africa,
#   Afghanistan and Pakistan" and moved AFG and PAK out of South Asia.
#   We keep the alias `MENA` for the new 23-economy WB region; SAS
#   drops to 6.
# - LDC list (44) cross-checked against UN DESA / Wikipedia. Reflects
#   Bhutan (graduated Dec 2023) and São Tomé and Príncipe (Dec 2024)
#   graduations. Bangladesh, Lao PDR, and Nepal are scheduled to
#   graduate Nov 2026; Solomon Islands Dec 2027. Re-check after each.
# - OECD list (38) cross-checked. Costa Rica (May 2021) is the most
#   recent confirmed member. Argentina, Brazil, Bulgaria, Croatia, Peru,
#   and Romania are in accession negotiations; verify completion before
#   moving them into OECD["members"].
# - LAC is the 33-sovereign-state convention; use LAC_TERRITORIES for
#   the WB 42-economy region (includes Aruba, Cayman Islands, Curaçao,
#   Puerto Rico, etc.).

# ---------------------------------------------------------------------------
# World Bank geographic regions (7)
# Codes are the short forms most commonly used in literature. Official WB
# 3-letter region codes (in parentheses) are kept as aliases.
# ---------------------------------------------------------------------------

WB_REGIONS: dict[str, dict[str, Any]] = {
    "EAP": {
        "name": "East Asia & Pacific (WB FY2026)",
        "wb_code": "EAS",
        "members": [
            "ASM", "AUS", "BRN", "KHM", "CHN", "FJI", "PYF", "GUM",
            "HKG", "IDN", "JPN", "KIR", "PRK", "KOR", "LAO", "MAC", "MYS",
            "MHL", "FSM", "MNG", "MMR", "NRU", "NCL", "NZL", "MNP",
            "PLW", "PNG", "PHL", "WSM", "SGP", "SLB", "TWN", "THA", "TLS",
            "TON", "TUV", "VUT", "VNM",
        ],
    },
    "ECA": {
        "name": "Europe & Central Asia",
        "wb_code": "ECS",
        "members": [
            "ALB", "AND", "ARM", "AUT", "AZE", "BLR", "BEL", "BIH", "BGR",
            "CHI", "HRV", "CYP", "CZE", "DNK", "EST", "FRO", "FIN", "FRA",
            "GEO", "DEU", "GIB", "GRC", "GRL", "HUN", "ISL", "IRL", "IMN",
            "ITA", "KAZ", "XKX", "KGZ", "LVA", "LIE", "LTU", "LUX", "MKD",
            "MDA", "MCO", "MNE", "NLD", "NOR", "POL", "PRT", "ROU", "RUS",
            "SMR", "SRB", "SVK", "SVN", "ESP", "SWE", "CHE", "TJK", "TUR",
            "TKM", "UKR", "GBR", "UZB",
        ],
    },
    "LAC": {
        # 33 sovereign Latin American and Caribbean states. This is the
        # PAHO / Decilion convention — territories and dependencies are
        # excluded. Use LAC_TERRITORIES for the WB-style 42-economy list.
        "name": "Latin America & Caribbean (33 sovereign states)",
        "wb_code": None,
        "members": [
            "ATG", "ARG", "BHS", "BRB", "BLZ", "BOL", "BRA", "CHL", "COL",
            "CRI", "CUB", "DMA", "DOM", "ECU", "SLV", "GRD", "GTM", "GUY",
            "HTI", "HND", "JAM", "MEX", "NIC", "PAN", "PRY", "PER", "KNA",
            "LCA", "VCT", "SUR", "TTO", "URY", "VEN",
        ],
    },
    "LAC_TERRITORIES": {
        # World Bank's Latin America & Caribbean region — the 33 sovereign
        # states plus 9 territories and dependencies (Aruba, Curaçao,
        # Cayman Islands, Puerto Rico, etc.). Use this when you need to
        # match World Bank tables exactly.
        "name": "Latin America & Caribbean (incl. territories, WB definition)",
        "wb_code": "LCN",
        "members": [
            "ATG", "ARG", "ABW", "BHS", "BRB", "BLZ", "BOL", "BRA", "VGB",
            "CYM", "CHL", "COL", "CRI", "CUB", "CUW", "DMA", "DOM", "ECU",
            "SLV", "GRD", "GTM", "GUY", "HTI", "HND", "JAM", "MEX", "NIC",
            "PAN", "PRY", "PER", "PRI", "KNA", "LCA", "MAF", "VCT", "SXM",
            "SUR", "TTO", "TCA", "URY", "VEN", "VIR",
        ],
    },
    "MENA": {
        # WB FY2026 renamed this region to "Middle East, North Africa,
        # Afghanistan and Pakistan" and moved AFG and PAK in from South
        # Asia (23 economies). We keep the `MENA` alias because that's
        # the name health-financing literature uses; the new "MENAAP"
        # naming hasn't widely propagated yet.
        "name": "Middle East, North Africa, Afghanistan and Pakistan (WB FY2026)",
        "wb_code": "MEA",
        "members": [
            "AFG", "DZA", "BHR", "DJI", "EGY", "IRN", "IRQ", "ISR", "JOR",
            "KWT", "LBN", "LBY", "MLT", "MAR", "OMN", "PAK", "PSE", "QAT",
            "SAU", "SYR", "TUN", "ARE", "YEM",
        ],
    },
    "MENA_EXCL_ISR_MLT": {
        # MENA without Israel and Malta — used in some health-financing
        # literature. With the WB FY2026 reclassification this group now
        # contains 21 economies (the 23-member MENA minus ISR and MLT,
        # but including the newly-added AFG and PAK). Users wanting an
        # Arab-states-only subset should additionally exclude AFG, PAK,
        # and IRN.
        "name": "Middle East, North Africa, AFG, PAK (excl. Israel and Malta)",
        "wb_code": None,
        "members": [
            "AFG", "DZA", "BHR", "DJI", "EGY", "IRN", "IRQ", "JOR", "KWT",
            "LBN", "LBY", "MAR", "OMN", "PAK", "PSE", "QAT", "SAU", "SYR",
            "TUN", "ARE", "YEM",
        ],
    },
    "NAR": {
        "name": "North America",
        "wb_code": "NAC",
        "members": ["BMU", "CAN", "USA"],
    },
    "SAS": {
        "name": "South Asia (WB FY2026)",
        "wb_code": "SAS",
        # WB FY2026 dropped AFG and PAK from this region; they are now
        # in MENA. Use the MENA group for analyses that need them.
        "members": ["BGD", "BTN", "IND", "MDV", "NPL", "LKA"],
    },
    "SSA": {
        "name": "Sub-Saharan Africa",
        "wb_code": "SSF",
        "members": [
            "AGO", "BEN", "BWA", "BFA", "BDI", "CPV", "CMR", "CAF", "TCD",
            "COM", "COD", "COG", "CIV", "GNQ", "ERI", "SWZ", "ETH", "GAB",
            "GMB", "GHA", "GIN", "GNB", "KEN", "LSO", "LBR", "MDG", "MWI",
            "MLI", "MRT", "MUS", "MOZ", "NAM", "NER", "NGA", "RWA", "STP",
            "SEN", "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN", "TZA", "TGO",
            "UGA", "ZMB", "ZWE",
        ],
    },
}

# ---------------------------------------------------------------------------
# UN Least Developed Countries (LDCs).
# Membership changes as countries graduate. List below reflects the post-
# December 2024 graduations (Bhutan graduated 2023-12, São Tomé and Príncipe
# graduated 2024-12). Bangladesh, Lao PDR, and Nepal are scheduled to
# graduate in 2026.
# ---------------------------------------------------------------------------

LDC: dict[str, Any] = {
    "name": "Least Developed Countries (UN)",
    "members": [
        "AFG", "AGO", "BGD", "BEN", "BFA", "BDI", "KHM", "CAF", "TCD",
        "COM", "COD", "DJI", "ERI", "ETH", "GMB", "GIN", "GNB", "HTI",
        "KIR", "LAO", "LSO", "LBR", "MDG", "MWI", "MLI", "MRT", "MOZ",
        "MMR", "NPL", "NER", "RWA", "SEN", "SLE", "SLB", "SOM", "SSD",
        "SDN", "TZA", "TLS", "TGO", "TUV", "UGA", "YEM", "ZMB",
    ],
}

# ---------------------------------------------------------------------------
# OECD member states.
# 38 members as of January 2026. Costa Rica is the most recent member
# (joined 2021-05). Croatia, Romania, and Bulgaria have begun accession
# processes; verify their status before treating them as members.
# ---------------------------------------------------------------------------

OECD: dict[str, Any] = {
    "name": "OECD member countries",
    "members": [
        "AUS", "AUT", "BEL", "CAN", "CHL", "COL", "CRI", "CZE", "DNK",
        "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "ISL", "IRL", "ISR",
        "ITA", "JPN", "KOR", "LVA", "LTU", "LUX", "MEX", "NLD", "NZL",
        "NOR", "POL", "PRT", "SVK", "SVN", "ESP", "SWE", "CHE", "TUR",
        "GBR", "USA",
    ],
}

# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

# Acceptable spellings → canonical key.
_GROUP_ALIASES: dict[str, str] = {
    # WB regions
    "EAP": "EAP", "EAS": "EAP", "EAST ASIA AND PACIFIC": "EAP",
    "EAST ASIA PACIFIC": "EAP",
    "ECA": "ECA", "ECS": "ECA", "EUROPE AND CENTRAL ASIA": "ECA",
    "LAC": "LAC", "LATIN AMERICA AND CARIBBEAN": "LAC",
    "LATIN AMERICA": "LAC", "LATIN AMERICA CARIBBEAN": "LAC",
    "LAC SOVEREIGN": "LAC", "LAC 33": "LAC",
    "LAC TERRITORIES": "LAC_TERRITORIES",
    "LAC INCL TERRITORIES": "LAC_TERRITORIES",
    "LAC INCLUDING TERRITORIES": "LAC_TERRITORIES",
    "LAC WB": "LAC_TERRITORIES",
    "LCN": "LAC_TERRITORIES",
    "MENA": "MENA", "MEA": "MENA",
    "MIDDLE EAST AND NORTH AFRICA": "MENA",
    "MIDDLE EAST NORTH AFRICA": "MENA",
    "MENA EXCL ISR MLT": "MENA_EXCL_ISR_MLT",
    "MENA EXCLUDING ISRAEL AND MALTA": "MENA_EXCL_ISR_MLT",
    "MENA EXCL ISRAEL MALTA": "MENA_EXCL_ISR_MLT",
    "NAR": "NAR", "NAC": "NAR", "NORTH AMERICA": "NAR",
    "SAS": "SAS", "SOUTH ASIA": "SAS",
    "SSA": "SSA", "SSF": "SSA", "SUB SAHARAN AFRICA": "SSA",
    "SUBSAHARAN AFRICA": "SSA",
    # LDC
    "LDC": "LDC", "LDCS": "LDC",
    "LEAST DEVELOPED COUNTRIES": "LDC",
    "LEAST DEVELOPED COUNTRY": "LDC",
    # OECD
    "OECD": "OECD", "OECD MEMBERS": "OECD",
    "OECD MEMBER COUNTRIES": "OECD",
    "OECD COUNTRIES": "OECD",
    "ORGANISATION FOR ECONOMIC COOPERATION AND DEVELOPMENT": "OECD",
    "ORGANIZATION FOR ECONOMIC COOPERATION AND DEVELOPMENT": "OECD",
}


def _norm_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip())
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[\s\-_/&,.]+", " ", ascii_value.upper()).strip()


def all_groups() -> dict[str, dict[str, Any]]:
    """Return every curated group keyed by canonical code."""
    out: dict[str, dict[str, Any]] = {}
    for code, payload in WB_REGIONS.items():
        out[code] = {
            "code": code,
            "name": payload["name"],
            "kind": "wb_region",
            "wb_code": payload["wb_code"],
            "members": list(payload["members"]),
            "member_count": len(payload["members"]),
            "source": "World Bank country and lending groups",
            "last_verified": LAST_VERIFIED,
        }
    out["LDC"] = {
        "code": "LDC",
        "name": LDC["name"],
        "kind": "un_designation",
        "members": list(LDC["members"]),
        "member_count": len(LDC["members"]),
        "source": "UN Committee for Development Policy",
        "last_verified": LAST_VERIFIED,
    }
    out["OECD"] = {
        "code": "OECD",
        "name": OECD["name"],
        "kind": "membership",
        "members": list(OECD["members"]),
        "member_count": len(OECD["members"]),
        "source": "OECD",
        "last_verified": LAST_VERIFIED,
    }
    return out


def resolve_country_group(value: str) -> dict[str, Any]:
    """Resolve a group name or alias to {code, name, members, ...}.

    Raises ValueError listing available groups when the value is unknown.
    """
    if not value or not str(value).strip():
        raise ValueError("Country group cannot be empty.")
    canonical = _GROUP_ALIASES.get(_norm_key(value))
    groups = all_groups()
    if canonical and canonical in groups:
        return groups[canonical]
    available = ", ".join(sorted(groups))
    raise ValueError(
        f"Unknown country group '{value}'. Available: {available}."
    )
