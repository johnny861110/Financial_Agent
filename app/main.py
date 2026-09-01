"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core import get_settings
from app.api import financials_router, agent_router, data_router
from app.data.factory import get_data_provider
from app.data.providers import FinancialDataContractError, FinancialDataProviderUnavailable

# Initialize settings
settings = get_settings()
cors_origins = [origin.strip() for origin in settings.api_cors_origins.split(",") if origin.strip()]

# Create FastAPI app
app = FastAPI(
    title="Financial Report Agent",
    description="AI-powered financial analysis API for professional fund managers",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(financials_router)
app.include_router(agent_router)
app.include_router(data_router)


# A provider fault is an upstream problem, not a bug in the requested route, so
# it is translated once here rather than in every handler that touches data.
# Without this a FinancialReports outage surfaces as a bare 500.
@app.exception_handler(FinancialDataProviderUnavailable)
async def _provider_unavailable_handler(_request, exc: FinancialDataProviderUnavailable):
    return JSONResponse(
        status_code=503,
        content={"error": "data_source_unavailable", "message": str(exc)},
    )


@app.exception_handler(FinancialDataContractError)
async def _provider_contract_handler(_request, exc: FinancialDataContractError):
    return JSONResponse(
        status_code=502,
        content={"error": "data_source_contract", "message": str(exc)},
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Financial Report Agent API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "financial-agent",
        "version": "2.0.0",
    }


@app.get("/health/live")
async def liveness_check():
    """Report whether the application process can serve requests."""
    return {"status": "healthy", "service": "financial-agent"}


@app.get("/health/ready")
async def readiness_check():
    """Report whether the configured financial data provider is reachable."""
    try:
        stocks = await run_in_threadpool(get_data_provider().list_all_stocks)
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "financial-agent",
                "data_provider": settings.data_provider,
                "detail": str(exc),
            },
        )
    return {
        "status": "ready",
        "service": "financial-agent",
        "data_provider": settings.data_provider,
        "available_stocks": len(stocks),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
