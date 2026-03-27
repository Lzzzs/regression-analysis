"""FastAPI entrypoint (with graceful fallback if fastapi not installed)."""

from __future__ import annotations

from apps.shared.contracts import ContractError
from portfolio_lab.errors import SnapshotError, ValidationError

from .job_store import JobStore
from .orchestration import AutoJobOrchestrator, map_auto_job_error
from .snapshot_service import build_snapshot_service
from .service import JobService

store = JobStore()
service = JobService(store)
snapshot_service = build_snapshot_service()
auto_job_orchestrator = AutoJobOrchestrator(service, snapshot_service)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Portfolio Lab API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/jobs")
    def create_job(payload: dict) -> dict:
        try:
            return service.create_job(payload)
        except ContractError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/jobs/auto")
    def create_job_auto(payload: dict) -> dict:
        try:
            return auto_job_orchestrator.create_job_auto(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(map_auto_job_error(exc)))

    @app.post("/snapshots/from-providers")
    def create_snapshot_from_providers(payload: dict) -> dict:
        try:
            return snapshot_service.create_snapshot_from_providers(payload)
        except (ValidationError, SnapshotError, ContractError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/jobs")
    def list_jobs(status: str | None = None, limit: int = 50, offset: int = 0, q: str | None = None) -> dict:
        return service.list_jobs(status=status, limit=limit, offset=offset, q=q)

    @app.get("/jobs/dead-letter")
    def dead_letter_jobs(limit: int = 50, offset: int = 0, q: str | None = None) -> dict:
        return service.dead_letter_jobs(limit=limit, offset=offset, q=q)

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        try:
            return service.job_status(job_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/jobs/{job_id}/result")
    def get_job_result(job_id: str) -> dict:
        try:
            return service.job_result(job_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ContractError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    @app.post("/jobs/{job_id}/requeue")
    def requeue_job(job_id: str) -> dict:
        try:
            return service.requeue_job(job_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ContractError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

except ImportError:
    app = None
