"""
Static configuration: which sites to scrape, and the keyword filter that
decides whether a scraped link is worth downloading. No RSS — manual
HTML scraping only, per your original design.
"""

WEATHER_SOURCES = [

    # PHILIPPINES

    {
        "name": "PAGASA",
        "country": "PH",
        "url": "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin"
    },

    {
        "name": "PAGASA Flood",
        "country": "PH",
        "url": "https://www.pagasa.dost.gov.ph/flood-forecasting-and-warning"
    },

    {
        "name": "PNA Weather",
        "country": "PH",
        "url": "https://www.pna.gov.ph/articles/search?q=weather"
    },

    {
        "name": "Rappler Climate",
        "country": "PH",
        "url": "https://www.rappler.com/?q=weather#gsc.tab=0&gsc.q=weather&gsc.page=1"
    },

    {
        "name": "Manila Bulletin Environment",
        "country": "PH",
        "url": "https://mb.com.ph/search?query=Philippine%20Weather&limit=12&page=2"
    },

    # VIETNAM

    {
        "name": "VNExpress Environment",
        "country": "VN",
        "urls": ["https://e.vnexpress.net/search/q/rain", "https://e.vnexpress.net/search/q/typhoon"]
    },

    {
        "name": "Vietnam News Environment",
        "country": "VN",
        "urls": ["https://vietnamnews.vn/search.html?s=rain", "https://vietnamnews.vn/search.html?s=typhoon"]
    },

    # THAILAND

    {
        "name": "Bangkok Post Environment",
        "country": "TH",
        "urls": ["https://search.bangkokpost.com/search/result?category=all&q=weather",
                 "https://search.bangkokpost.com/search/result?q=flood&category=all"]
    },

    {
        "name": "Thai PBS Environment",
        "country": "TH",
        "urls": ["https://www.thaipbs.or.th/search/%E0%B8%9E%E0%B8%B2%E0%B8%A2%E0%B8%B8",
                 "https://www.thaipbs.or.th/search/%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%97%E0%B9%88%E0%B8%A7%E0%B8%A1",
                 "https://www.thaipbs.or.th/search/%E0%B9%84%E0%B8%95%E0%B9%89%E0%B8%9D%E0%B8%B8%E0%B9%88%E0%B8%99"]
    }
]

WEATHER_TITLE_TERMS = [
    "typhoon", "storm", "cyclone", "tropical depression",
    "flood", "flooding",
    "rain", "rainfall",
    "weather",
    "el niño", "la niña",
    "bagyo", "amihan",
    "bão", "lụt",
    "พายุ", "น้ำท่วม", "ไต้ฝุ่น"
]

NOISE_TERMS = [
    "about", "contact", "privacy", "policy", "advertise",
    "login", "register", "subscription", "newsletter",
    "weather outlook", "general weather", "climate monitoring",
    "daily weather forecast"
]


def keep_article(title: str, url: str) -> bool:
    """Returns True only if the title looks like a real hazard-related article."""

    title = title.lower()

    if not any(term.lower() in title for term in WEATHER_TITLE_TERMS):
        return False

    if any(term in title for term in NOISE_TERMS):
        return False

    return True
