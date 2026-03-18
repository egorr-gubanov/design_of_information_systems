from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import init_db
from routers_segments import router as segments_router
from routers_traffic import router as traffic_router
from routers_alerts import router as alerts_router
from routers_metrics import router as metrics_router
from seed_data import ensure_seeded


BASE_DIR = Path(__file__).parent

app = FastAPI(title="CityPulse Traffic Module")


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    ensure_seeded()


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


app.include_router(segments_router)
app.include_router(traffic_router)
app.include_router(alerts_router)
app.include_router(metrics_router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

