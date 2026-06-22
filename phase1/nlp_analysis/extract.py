"""
Pulls storm name and province mentions out of article text, and assembles
the final alert dict ready to insert into Supabase.
"""

import re
from db import PROVINCES, get_neighbors


def extract_storm_name(text: str) -> str | None:
    patterns = [
        r"[Tt]yphoon\s+([A-Z][a-zA-Z]+)",
        r"[Ss]evere [Tt]ropical [Ss]torm\s+([A-Z][a-zA-Z]+)",
        r"[Tt]ropical [Ss]torm\s+([A-Z][a-zA-Z]+)",
        r"[Tt]ropical [Dd]epression\s+([A-Z][a-zA-Z]+)"
    ]

    # Common false positives even with correct capitalization handling
    blacklist = {"is", "was", "may", "will", "season", "outside",
                 "intensity", "near", "over", "still", "also", "now", "the"}

    for pattern in patterns:
        match = re.search(pattern, text)  # no re.I — capture group stays strictly uppercase-only
        if match:
            candidate = match.group(1)
            if candidate.lower() not in blacklist:
                return candidate

    return None


def extract_provinces(text: str) -> list[str]:
    found = []
    lower_text = text.lower()

    for province in PROVINCES:
        if province.lower() in lower_text:
            found.append(province)

    return list(set(found))


def get_alert_level(score: float) -> str:
    if score >= 0.80:
        return "warning"
    elif score >= 0.65:
        return "advisory"
    elif score >= 0.50:
        return "watch"
    return "none"


def build_alert(article: dict, prediction: dict) -> dict:
    storm = extract_storm_name(article["content"])
    provinces = extract_provinces(article["content"])
    neighbors = get_neighbors(provinces)

    score = prediction["confidence"]

    return {
        "article_url": article["url"],
        "article_title": article["title"],
        "source": article["source"],
        "country": article["country"],
        "storm_name": storm,
        "hazard": prediction["label"],
        "score": round(score, 4),
        "alert_level": get_alert_level(score),
        "provinces": provinces,
        "neighbors": neighbors  # matches your alerts table column name
    }
