"""Financial source-data status and refresh endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.data.factory import get_data_provider
from app.data.models import SnapshotRecord
from app.data.providers import FinancialDataContractError, FinancialDataProviderUnavailable
from app.data.readiness import DataReadinessService


router = APIRouter(prefix="/api/data", tags=["data"])


def _service() -> DataReadinessService:
    return DataReadinessService(get_data_provider())


@router.get("/capabilities")
async def get_data_capabilities():
    try:
        return await run_in_threadpool(get_data_provider().get_capabilities)
    except FinancialDataProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FinancialDataContractError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{stock_code}/{period}/record", response_model=SnapshotRecord)
async def get_data_record(stock_code: str, period: str):
    try:
        record = await run_in_threadpool(get_data_provider().load_record, stock_code, period)
    except FinancialDataProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FinancialDataContractError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Financial record was not found")
    status_code = 202 if record.status == "processing" else 200
    return JSONResponse(status_code=status_code, content=record.model_dump(mode="json"))


@router.get("/{stock_code}/{period}/status")
async def get_data_status(stock_code: str, period: str):
    readiness = await run_in_threadpool(_service().check, stock_code, period)
    status_code = 202 if readiness.status == "processing" else 200
    return JSONResponse(status_code=status_code, content=readiness.model_dump(mode="json"))


@router.post("/{stock_code}/{period}/refresh")
async def refresh_data(stock_code: str, period: str):
    try:
        result = await run_in_threadpool(_service().request_refresh, stock_code, period)
    except FinancialDataProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FinancialDataContractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse(status_code=202, content=result)


@router.get("/jobs/{job_id}")
async def get_data_job(job_id: str):
    try:
        return await run_in_threadpool(_service().get_job, job_id)
    except FinancialDataProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FinancialDataContractError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
