"""Render alert templates by (severity, hazard, language).

DEMO STUB: templates are seeded JSON. The proposal's full system would also
include a multilingual NLP layer for bidirectional comprehension of citizen
reports — out of scope here.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jinja2 import Template

from ..config import FIXTURES_DIR
from ..models import HazardType, Severity


@lru_cache(maxsize=1)
def _load_templates() -> dict:
    path: Path = FIXTURES_DIR / "alert_templates.json"
    return json.loads(path.read_text(encoding="utf-8"))["templates"]


SUPPORTED_LANGUAGES = ("en", "fil", "vi", "th")


def render_alert(
    *,
    hazard_type: HazardType,
    severity: Severity,
    language: str,
    municipality: str,
    storm_name: str,
    category: int,
    eta_hours: float,
) -> tuple[str, str]:
    """Return (title, body) localized to `language`. Falls back to English."""
    templates = _load_templates()
    hazard_block = templates.get(hazard_type.value) or templates["typhoon"]
    severity_block = hazard_block.get(severity.value) or hazard_block["advisory"]
    pack = severity_block.get(language) or severity_block["en"]

    ctx = {
        "municipality": municipality,
        "storm_name": storm_name,
        "category": category,
        "eta_hours": int(round(eta_hours)),
    }
    title = Template(pack["title"]).render(**ctx)
    body = Template(pack["body"]).render(**ctx)
    return title, body
