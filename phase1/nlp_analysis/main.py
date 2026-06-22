"""
Entry point for continuous polling.

Run with:
    python main.py

Run detached so it survives closing the terminal:
    nohup python main.py > scraper.log 2>&1 &      (macOS/Linux)
    Start-Process python -ArgumentList "main.py"   (Windows PowerShell)

For auto-restart on crash/reboot, wrap this in a systemd service or
Windows Task Scheduler entry (see README.md).
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv

from pipeline import process_articles

load_dotenv()

INTERVAL_HOURS = float(os.getenv("POLL_INTERVAL_HOURS", "6"))


def run_continuous(interval_hours: float = INTERVAL_HOURS):
    interval_seconds = interval_hours * 3600
    print(f"Polling every {interval_hours} hours. Ctrl+C to stop.")

    while True:
        start = datetime.now()
        print(f"\n=== Poll started: {start.isoformat()} ===")

        try:
            process_articles()
        except Exception as e:
            print("Poll failed:", e)

        print(f"=== Poll finished: {datetime.now().isoformat()} ===")
        print(f"Sleeping for {interval_hours} hours...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_continuous()
