"""
All Supabase reads/writes live here. Credentials come from .env —
never hardcode them in source files you might commit or share.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------- raw_articles ----------

def article_exists(url: str) -> bool:
    result = (
        supabase.table("raw_articles")
        .select("id")
        .eq("url", url)
        .limit(1)
        .execute()
    )
    return len(result.data) > 0


def save_raw_article(article: dict):
    supabase.table("raw_articles").insert({
        "title": article["title"],
        "content": article["content"],
        "url": article["url"],
        "source": article["source"],
        "country": article["country"]
    }).execute()


# ---------- provinces / neighbors (loaded once, cached in memory) ----------

_province_result = supabase.table("provinces").select("*").execute()
PROVINCES = [p["province_name"] for p in _province_result.data]

PROVINCES_BY_COUNTRY: dict[str, list[str]] = {}
for p in _province_result.data:
    PROVINCES_BY_COUNTRY.setdefault(p["country"], []).append(p["province_name"])

_neighbor_result = supabase.table("province_neighbors").select("*").execute()
NEIGHBOR_MAP: dict[str, list[str]] = {}

for row in _neighbor_result.data:
    province = row["province_name"]
    neighbor = row["neighbor_name"]
    NEIGHBOR_MAP.setdefault(province, []).append(neighbor)


def get_neighbors(provinces: list[str]) -> list[str]:
    neighbors = []
    for province in provinces:
        neighbors.extend(NEIGHBOR_MAP.get(province, []))
    return list(set(neighbors))


# ---------- alerts ----------

def save_alert(alert: dict):
    supabase.table("alerts").insert(alert).execute()


# ---------- storm_metrics ----------

def upsert_storm_metrics(row: dict):
    supabase.table("storm_metrics").upsert(row, on_conflict="event_id").execute()


def get_recent_alerts(since_iso: str) -> list[dict]:
    result = (
        supabase.table("alerts")
        .select("*")
        .gte("created_at", since_iso)
        .execute()
    )
    return result.data


# ---------- demo_table ----------

def clear_demo_table():
    """Deletes ALL rows from demo_table. Use before re-seeding for a clean demo."""
    supabase.table("demo_table").delete().gte("id", 0).execute()
    print("demo_table cleared.")


def insert_demo_row(row: dict):
    supabase.table("demo_table").insert(row).execute()
