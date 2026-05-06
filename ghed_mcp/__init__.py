"""MCP server for the WHO Global Health Expenditure Database (GHED).

Designed for health-financing researchers: comparative cross-country
panels, additive accounting decompositions (CHE = HF1+HF2+HF3+HF4+HFnec,
GGHE-D = FS1+FS3, etc.), and methodology-aware indicator selection across
the SHA 2011 framework. Wraps the public GHED all-data workbook from
https://apps.who.int/nha/database.
"""
from __future__ import annotations

from .server import main

__version__ = "0.5.1"
__all__ = ["main"]
