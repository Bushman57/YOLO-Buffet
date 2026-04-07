from fastapi import FastAPI

from app.routers import cameras, events, health, sites

app = FastAPI(
    title="Buffet MVP API",
    description="AI Buffet Analytics — events and classifications",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(sites.router)
app.include_router(cameras.router)
app.include_router(events.router)
