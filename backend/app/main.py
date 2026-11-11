"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import events, runs, system
from app.config import APP_VERSION, Settings, get_settings
from app.logsetup import configure_logging, get_logger
from app.services import Services, build_services


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    settings = settings or (services.settings if services else get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.aps_log_level, settings.secret_values())
        svc = services or build_services(settings)
        await svc.db.init()
        await svc.runs.recover()
        app.state.services = svc
        get_logger("app").info("app.started", version=APP_VERSION, data_dir=str(settings.aps_data_dir),
                               workhorse=svc.router.has("workhorse"), escalation=svc.router.has("escalation"),
                               sandbox=svc.executor is not None)
        try:
            yield
        finally:
            await svc.aclose()

    app = FastAPI(title="Agentic Advent of Code Solver", version=APP_VERSION, lifespan=lifespan,
                  openapi_url="/api/openapi.json", docs_url="/api/docs")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST", "DELETE"],
                       allow_headers=["Content-Type", "Last-Event-ID"])
    for r in (system.router, runs.router, events.router):
        app.include_router(r, prefix="/api")
    return app


app = None


def get_app() -> FastAPI:  # uvicorn factory: `uvicorn app.main:get_app --factory`
    return create_app()
