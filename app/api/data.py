"""Financial source-data status and refresh endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.data.factory import get_data_provider
from app.data.providers import FinancialDataContractError, FinancialDataProviderUnavailable
from app.data.readiness import DataReadinessService
from app.data.readiness import DataReadiness
from app.models.api_models import (
    DataCapabilitiesResponse,
    DataRecordResponse,
    PeriodDiscoveryResponse,
    ProviderOperationResponse,
    StockDiscoveryResponse,
)


router = APIRouter(prefix="/api/data", tags=["data"])


def _service() -> DataReadinessService:
    return DataReadinessService(get_data_provider())


@router.get("/capabilities", response_model=DataCapabilitiesResponse)
async def get_data_capabilities():
    try:
        return await run_in_threadpool(get_data_provider().get_capabilities)
    except FinancialDataProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FinancialDataContractError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# Discovery routes. The provider has always been able to enumerate stocks and
# periods; without them over HTTP the UI can only offer free-text inputs, which
# is how an unusable period reaches the provider in the first place.
# Declared before the parameterized routes so the literal segments win.
@router.get("/stocks", response_model=StockDiscoveryResponse)
async def list_stocks():
    """List every stock the configured provider can serve."""
    stocks = await run_in_threadpool(get_data_provider().list_all_stocks)
    return {"stocks": stocks}


@router.get("/{stock_code}/periods", response_model=PeriodDiscoveryResponse)
async def list_periods(stock_code: str):
    """List the periods available for one stock, newest first."""
    periods = await run_in_threadpool(get_data_provider().list_available_periods, stock_code)
    return {"stock_code": stock_code, "periods": sorted(periods, reverse=True)}


@router.get("/{stock_code}/{period}/record", response_model=DataRecordResponse)
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


@router.get("/{stock_code}/{period}/status", response_model=DataReadiness)
async def get_data_status(stock_code: str, period: str):
    readiness = await run_in_threadpool(_service().check, stock_code, period)
    status_code = 202 if readiness.status == "processing" else 200
    return JSONResponse(status_code=status_code, content=readiness.model_dump(mode="json"))


@router.post("/{stock_code}/{period}/refresh", response_model=ProviderOperationResponse)
async def refresh_data(stock_code: str, period: str):
    try:
        result = await run_in_threadpool(_service().request_refresh, stock_code, period)
    except FinancialDataProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FinancialDataContractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse(status_code=202, content=result)


@router.get("/jobs/{job_id}", response_model=ProviderOperationResponse)
async def get_data_job(job_id: str):
    try:
        return await run_in_threadpool(_service().get_job, job_id)
    except FinancialDataProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FinancialDataContractError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
