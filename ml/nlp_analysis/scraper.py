"""
Manual HTML scraping — no RSS. scrape_source() pulls links off a listing
page; get_article_content() downloads the full article text for a single URL.
"""

import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from newspaper import Article, Config

from config import WEATHER_SOURCES, keep_article

ARTICLE_CONFIG = Config()
ARTICLE_CONFIG.browser_user_agent = "Mozilla/5.0"
ARTICLE_CONFIG.request_timeout = 15


def scrape_source(source: dict) -> list[dict]:
    """Scrape one source's listing page(s) for candidate article links."""

    articles = []
    urls = source.get("urls") or [source["url"]]

    for search_url in urls:

        try:
            response = requests.get(
                search_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20
            )

            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a"):

                href = a.get("href")
                title = a.get_text(strip=True)

                if not href:
                    continue

                if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                    continue

                if len(title) < 10:
                    continue

                absolute_url = urljoin(search_url, href)

                articles.append({
                    "title": title,
                    "url": absolute_url,
                    "source": source["name"],
                    "country": source["country"]
                })

            time.sleep(1)  # be polite between requests

        except Exception as e:
            print(f"[scrape_source] {source['name']}: {e}")

    return articles


def scrape_all_sources() -> list[dict]:
    """Scrape every configured source, filter, and de-duplicate by URL."""

    all_articles = []
    seen_urls = set()

    for source in WEATHER_SOURCES:

        try:
            scraped = scrape_source(source)
            kept = []

            for article in scraped:

                if not keep_article(article["title"], article["url"]):
                    continue

                if article["url"] in seen_urls:
                    continue

                seen_urls.add(article["url"])
                kept.append(article)

            all_articles.extend(kept)
            print(f"{source['name']}: {len(kept)} kept / {len(scraped)} scraped")

        except Exception as e:
            print(f"Failed {source['name']}: {e}")

    return all_articles


def get_article_content(url: str) -> str | None:
    """Download and extract the full body text of a single article."""

    try:
        article = Article(url, config=ARTICLE_CONFIG)
        article.download()
        article.parse()

        text = article.text.strip()

        if len(text) < 200:
            return None  # likely a paywall stub or failed parse

        return text

    except Exception as e:
        print(f"Could not extract content from {url}: {e}")
        return None
