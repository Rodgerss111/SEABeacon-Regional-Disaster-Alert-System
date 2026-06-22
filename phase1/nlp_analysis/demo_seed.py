"""
One-time script for your demo: clears demo_table, then inserts verified
historical Sept-Oct 2022 storm articles (Typhoon Noru/Karding/Sonca across
PH, VN, TH) run through your ACTUAL model and extraction functions, using
the corrected id2label mapping.

Run with:
    python demo_seed.py
"""

from model import classify
from extract import extract_provinces
from db import clear_demo_table, insert_demo_row

DEMO_ARTICLES = [
    # PHILIPPINES
    {
        "title": "Super Typhoon Noru intensifies rapidly before Luzon landfall",
        "content": "Tropical cyclone Noru, locally named Karding, underwent one of the fastest rapid intensifications ever recorded in the Pacific basin on September 25, 2022, reaching super typhoon strength with sustained winds of 195 km/h before striking the Polillo Islands and making landfall in Quezon and Aurora provinces. PAGASA raised the highest wind signal, Tropical Cyclone Wind Signal No. 5, over the affected areas.",
        "url": "https://reliefweb.int/report/philippines/philippines-super-typhoon-noru-karding-flash-update-no1-25-september-2022-8-pm-local-time",
        "source": "ReliefWeb/OCHA",
        "country": "PH",
        "storm_name": "Karding",
        "published_at": "2022-09-25"
    },
    {
        "title": "Typhoon Karding leaves over 700,000 people affected across Luzon",
        "content": "Days after Super Typhoon Karding made landfall, government reports showed more than 714,200 people affected across six regions of Luzon, with eight casualties and over 20,600 houses damaged. The hardest-hit provinces were Aurora, Quezon, and Nueva Ecija, where agricultural losses reached roughly 1.97 billion pesos.",
        "url": "https://reliefweb.int/report/philippines/philippines-super-typhoon-noru-karding-flash-update-no3-29-september-2022-7-pm-local-time",
        "source": "ReliefWeb/OCHA",
        "country": "PH",
        "storm_name": "Karding",
        "published_at": "2022-09-29"
    },
    {
        "title": "Flash floods and landslides reported as Karding crosses Sierra Madre",
        "content": "As Typhoon Karding traversed the Sierra Madre mountain range, torrential rains caused flooding in Bulacan and Rizal provinces, contributing to the displacement of residents even as the storm weakened on its way out of the Philippine Area of Responsibility. Five rescuers died in a flash flood while conducting operations in San Miguel, Bulacan.",
        "url": "https://reliefweb.int/report/philippines/philippines-super-typhoon-noru-karding-consolidated-rapid-assessment-report-30-september-2022",
        "source": "ReliefWeb",
        "country": "PH",
        "storm_name": "Karding",
        "published_at": "2022-09-30"
    },

    # VIETNAM
    {
        "title": "Vietnam evacuates hundreds of thousands as Typhoon Noru nears central coast",
        "content": "Vietnamese authorities mobilized over 260,000 soldiers and shut down ten airports as Typhoon Noru approached the central coast on September 27, 2022, with forecasters warning it could be the strongest typhoon to hit the country in two decades. Curfews were imposed in Da Nang and several other localities ahead of landfall.",
        "url": "https://www.cnn.com/2022/09/27/asia/vietnam-typhoon-noru-da-nang-intl-hnk/index.html",
        "source": "CNN",
        "country": "VN",
        "storm_name": "Noru",
        "published_at": "2022-09-27"
    },
    {
        "title": "Typhoon Noru makes landfall near Da Nang, knocking out power for 550,000 households",
        "content": "Typhoon Noru struck the coast between Da Nang and Quang Nam early on September 28, 2022, with gusts up to 117 km/h, cutting power to more than 550,000 households. Streets flooded in the historic town of Hoi An and strong winds downed trees and damaged roofs across the central region.",
        "url": "https://www.aljazeera.com/news/2022/9/28/vietnam-warns-of-floods-as-it-downgrades-typhoon-noru",
        "source": "Al Jazeera",
        "country": "VN",
        "storm_name": "Noru",
        "published_at": "2022-09-28"
    },
    {
        "title": "Central Vietnam floods worsen after Storm Sonca adds to Noru's aftermath",
        "content": "A second storm, Sonca, made landfall in Da Nang and Quang Nam on October 15, 2022, compounding flood damage left by Noru weeks earlier. Successive storm surges since late September left over 436,000 people affected and 19 dead, with floodwaters in Hue and Da Nang reaching depths of up to 1.5 meters.",
        "url": "https://reliefweb.int/disaster/fl-2022-000336-vnm",
        "source": "ReliefWeb",
        "country": "VN",
        "storm_name": "Sonca",
        "published_at": "2022-10-15"
    },

    # THAILAND
    {
        "title": "Tropical Storm Noru remnants trigger flooding across Thailand's northeast",
        "content": "Heavy rain from the remnants of Tropical Storm Noru caused floods and strong winds in Sisaket province in late September 2022, killing three people. Rivers continued rising afterward, with authorities issuing warnings for communities along the Chao Phraya and Pa Sak river basins by early October.",
        "url": "https://floodlist.com/asia/thailand-floods-october-2022#sisaket",
        "source": "FloodList",
        "country": "TH",
        "storm_name": "Noru",
        "published_at": "2022-10-02"
    },
    {
        "title": "Chao Phraya River flooding threatens Bangkok suburbs as water levels rise",
        "content": "Bangkok recorded 100.5 mm of rainfall in 24 hours on October 3, 2022, prompting the Bangkok Metropolitan Administration to urge employees to work from home. Officials warned that floodwaters arriving from the north combined with heavy rain could bring serious flooding to the city between October 5 and 7.",
        "url": "https://floodlist.com/asia/thailand-floods-october-2022#bangkok",
        "source": "FloodList",
        "country": "TH",
        "storm_name": "Noru",
        "published_at": "2022-10-03"
    },
    {
        "title": "Floods affect 25 provinces in Thailand as monsoon rains persist",
        "content": "By October 11, 2022, flooding had spread across 25 provinces in Thailand, affecting roughly 156,240 households, according to the Department of Disaster Prevention and Mitigation. Ubon Ratchathani province was especially hard-hit after the Mun River overflowed, forcing more than 13,000 people into shelters.",
        "url": "https://reliefweb.int/report/thailand/thailand-monsoon-flood-2022-operational-update-appeal-no-mdrth002",
        "source": "ReliefWeb/IFRC",
        "country": "TH",
        "storm_name": "Noru",
        "published_at": "2022-10-11"
    },
]


def seed():
    clear_demo_table()

    for item in DEMO_ARTICLES:
        text = item["title"] + "\n" + item["content"]
        prediction = classify(text)
        provinces = extract_provinces(item["content"])

        row = {
            "title": item["title"],
            "content": item["content"],
            "url": item["url"],
            "source": item["source"],
            "country": item["country"],
            "hazard": prediction["label"],
            "score": round(prediction["confidence"], 4),
            "storm_name": item["storm_name"],
            "provinces": provinces,
            "published_at": item["published_at"]
        }

        try:
            insert_demo_row(row)
            print(f"Inserted: {item['title']} | {row['hazard']} {row['score']}")
        except Exception as e:
            print(f"Failed: {item['title']} | {e}")


if __name__ == "__main__":
    seed()
