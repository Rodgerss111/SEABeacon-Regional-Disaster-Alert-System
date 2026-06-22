"""
Pulls storm name and province mentions out of article text, and assembles
the final alert dict ready to insert into Supabase.
"""

import re
from db import PROVINCES, get_neighbors


def extract_storm_name(text: str) -> str | None:
    patterns = [
        r"Typhoon\s+([A-Z][a-zA-Z]+)",
        r"Tropical Storm\s+([A-Z][a-zA-Z]+)",
        r"Tropical Depression\s+([A-Z][a-zA-Z]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)

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
