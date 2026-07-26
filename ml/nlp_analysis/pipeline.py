"""
The main pipeline: scrape -> classify -> save -> aggregate.
This is what runs every poll cycle.
"""

from datetime import datetime, timedelta, timezone

from scraper import scrape_all_sources, get_article_content
from model import classify
from extract import build_alert
from db import article_exists, save_raw_article, save_alert, get_recent_alerts, upsert_storm_metrics


def update_storm_metrics():
    """Aggregates alerts from the last 6 hours into one summary row per storm."""

    since = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
    alerts = get_recent_alerts(since)

    if not alerts:
        print("No new alerts to aggregate.")
        return

    groups = {}

    for alert in alerts:
        storm = alert.get("storm_name") or "UNNAMED"
        country = alert.get("country", "")
        event_id = f"{storm.upper().replace(' ', '_')}_{country}"

        if event_id not in groups:
            groups[event_id] = {
                "storm_name": storm,
                "country": country,
                "scores": [],
                "provinces": set(),
                "alert_levels": [],
                "article_count": 0
            }

        groups[event_id]["scores"].append(float(alert["score"] or 0))
        groups[event_id]["alert_levels"].append(alert.get("alert_level", "none"))
        groups[event_id]["article_count"] += 1

        for p in (alert.get("provinces") or []):
            groups[event_id]["provinces"].add(p)
        for n in (alert.get("neighbors") or []):
            groups[event_id]["provinces"].add(n)

    level_rank = {"none": 0, "watch": 1, "advisory": 2, "warning": 3}

    for event_id, data in groups.items():
        scores = data["scores"]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        top_level = max(data["alert_levels"], key=lambda l: level_rank.get(l, 0))

        row = {
            "event_id": event_id,
            "storm_name": data["storm_name"],
            "article_count": data["article_count"],
            "avg_score": round(avg_score, 4),
            "max_score": round(max_score, 4),
            "alert_level": top_level,
            "provinces": list(data["provinces"]),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        upsert_storm_metrics(row)
        print(f"storm_metrics updated: {event_id} | max={max_score:.3f} | {top_level} | {data['article_count']} articles")


def process_articles() -> int:

    print("Starting scrape...")
    all_articles = scrape_all_sources()
    print("Collected:", len(all_articles))

    if not all_articles:
        print("No candidate articles found this run.")
        return 0

    saved_count = 0

    for article in all_articles:

        try:
            if article_exists(article["url"]):
                continue

            print("Downloading:", article["title"])
            article["content"] = get_article_content(article["url"])

            if not article["content"]:
                continue

            text = article["title"] + "\n" + article["content"]
            prediction = classify(text)
            print(prediction)

            if prediction["label"] == "other":
                continue

            save_raw_article(article)
            alert = build_alert(article, prediction)
            save_alert(alert)
            saved_count += 1

            print("Saved:", alert["hazard"], round(alert["score"], 3))

        except Exception as e:
            print("Failed article:", article.get("title", "UNKNOWN"))
            print(e)

    print(f"Done. Saved {saved_count} new alert(s) out of {len(all_articles)} candidate(s).")

    update_storm_metrics()
    return saved_count
