from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import services
from app.config import APP_VERSION
from app.preflight import run_checks
from app.services import Services

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}


@router.get("/config")
async def config(svc: Services = Depends(services)) -> dict:
    return svc.settings.public_summary()


class VerifyRequest(BaseModel):
    checks: list[Literal["storage", "aoc", "workhorse", "escalation", "sandbox"]] | None = None
    year: int = 2024


@router.post("/connections/verify")
async def verify(body: VerifyRequest, svc: Services = Depends(services)) -> dict:
    results = await run_checks(svc, body.checks, body.year)
    overall = "fail" if any(r.status == "fail" for r in results) else "pass"
    return {"overall": overall, "checks": [r.dict() for r in results]}
