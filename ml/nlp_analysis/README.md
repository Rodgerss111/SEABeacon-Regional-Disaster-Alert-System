# Weather Risk Monitoring Pipeline (VS Code version)

Your Colab notebook split into proper files. Same logic, fixed label
mapping, no Drive mount needed, designed to run continuously on your machine.

```
weather_pipeline/
├── .env.example       copy to .env and fill in your real credentials
├── requirements.txt
├── config.py          WEATHER_SOURCES, keyword filters, keep_article()
├── scraper.py         scrape_source, scrape_all_sources, get_article_content
├── model.py           loads XLM-R locally, classify(), corrected id2label
├── db.py              Supabase client + all table read/write helpers
├── extract.py         storm name / province extraction, build_alert()
├── pipeline.py        process_articles(), update_storm_metrics()
├── main.py            entry point — continuous polling loop
└── demo_seed.py       clears + re-seeds demo_table with Sept-Oct 2022 data
```

---

## Step 1 — Get the model files onto your computer

In Colab, your model currently lives on Google Drive as
`xlmr_weather_model.zip`. Download that zip from Drive to your computer,
then unzip it into this project:

```
weather_pipeline/
└── models/
    └── xlmr_weather_model/     ← unzipped contents go here
        ├── config.json
        ├── model.safetensors (or pytorch_model.bin)
        ├── tokenizer.json
        └── ...
```

## Step 2 — Set up the Python environment

```bash
cd weather_pipeline
python -m venv venv

# activate it:
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

## Step 3 — Add your real credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your actual Supabase URL/key (the ones you had
hardcoded in the notebook):

```
SUPABASE_URL=https://nwlzgvunbpshfbvqnxjs.supabase.co
SUPABASE_KEY=your-real-anon-key
MODEL_PATH=./models/xlmr_weather_model
POLL_INTERVAL_HOURS=6
```

## Step 4 — Bake the corrected label mapping into the model (one time)

```bash
python -c "from model import save_corrected_model; save_corrected_model()"
```

This permanently fixes `id2label`/`label2id` in your model files, so you
never have to manually patch the mapping again on future loads.

## Step 5 — Clear and re-seed demo_table for your demonstration

```bash
python demo_seed.py
```

This wipes `demo_table` and inserts the 9 verified Sept–Oct 2022 Typhoon
Noru/Karding/Sonca articles (PH, VN, TH), classified with the corrected model.
Check Supabase afterward — `hazard` should now correctly show `typhoon`/`flood`
instead of `other`.

## Step 6 — Test the live pipeline once

```bash
python -c "from pipeline import process_articles; process_articles()"
```

Watch the console output. Check `raw_articles`, `alerts`, and `storm_metrics`
in Supabase afterward to confirm real rows landed.

## Step 7 — Start continuous polling

```bash
python main.py
```

This loops forever, scraping + classifying + saving every
`POLL_INTERVAL_HOURS` (default 6), until you stop it.

### Keep it running after closing the terminal

**macOS/Linux:**
```bash
nohup python main.py > scraper.log 2>&1 &
```
Check progress anytime with `tail -f scraper.log`. Stop it with
`pkill -f main.py`.

**Windows (PowerShell):**
```powershell
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden
```

### Auto-restart on crash or machine reboot (optional, more robust)

**Linux — systemd service** (`/etc/systemd/system/weather-scraper.service`):
```ini
[Unit]
Description=Weather Risk Scraper
After=network.target

[Service]
WorkingDirectory=/path/to/weather_pipeline
ExecStart=/path/to/weather_pipeline/venv/bin/python main.py
Restart=always
User=your_username

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable weather-scraper
sudo systemctl start weather-scraper
sudo systemctl status weather-scraper   # check it's running
```

**Windows — Task Scheduler:** create a task that runs
`venv\Scripts\python.exe main.py` at startup, with "restart on failure" set
under the task's settings tab.

---

## Reminder: this only runs while your machine is on

True 24/7 uptime (even with your laptop closed) needs a small cloud VM
running the same systemd setup — this VS Code setup is the right way to
develop and test it first.
