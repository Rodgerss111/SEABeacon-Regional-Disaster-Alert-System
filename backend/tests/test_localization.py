from __future__ import annotations

from seabeacon.models import HazardType, Severity
from seabeacon.services.localization import render_alert, SUPPORTED_LANGUAGES


def test_renders_all_languages_and_severities():
    for lang in SUPPORTED_LANGUAGES:
        for severity in (Severity.advisory, Severity.warning, Severity.urgent):
            title, body = render_alert(
                hazard_type=HazardType.typhoon,
                severity=severity,
                language=lang,
                municipality="Sorsogon City",
                storm_name="Kammuri",
                category=4,
                eta_hours=12.0,
            )
            assert "Sorsogon City" in title or "Sorsogon City" in body
            assert "Kammuri" in body
            assert "{{" not in body and "{{" not in title


def test_falls_back_to_english_when_lang_unknown():
    title, body = render_alert(
        hazard_type=HazardType.typhoon,
        severity=Severity.warning,
        language="zz",
        municipality="Da Nang",
        storm_name="Kammuri",
        category=2,
        eta_hours=24.0,
    )
    assert "Da Nang" in body


def test_eta_hours_rounded_to_int_in_template():
    _, body = render_alert(
        hazard_type=HazardType.typhoon,
        severity=Severity.advisory,
        language="en",
        municipality="Manila",
        storm_name="Kammuri",
        category=3,
        eta_hours=11.6,
    )
    assert "12 hours" in body
