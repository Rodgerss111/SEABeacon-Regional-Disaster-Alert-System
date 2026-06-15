from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .bot.dispatcher import get_dispatcher
from .bot.telegram_bot import lifespan_start, lifespan_stop
from .db import init_db
from .routes import alerts, events, scenarios, signals, subscriptions
from .services.scenario_clock import get_runner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("seabeacon")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Seed on first boot (idempotent).
    try:
        from .seed import seed_all
        seed_all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("seed step skipped: %s", exc)

    bot_app = await lifespan_start()
    dispatcher = get_dispatcher()
    runner = get_runner()
    runner.attach_sender(dispatcher.send)

    yield

    runner_active = list(runner.runs.keys())
    for slug in runner_active:
        await runner.stop(slug)
    await lifespan_stop()


app = FastAPI(
    title="SEABeacon API",
    version="0.1.0",
    description="Cross-border disaster early-warning demo for ASEAN.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scenarios.router)
app.include_router(alerts.router)
app.include_router(signals.router)
app.include_router(subscriptions.router)
app.include_router(events.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "seabeacon"}
