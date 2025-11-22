"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import get_settings
from app.api import financials_router, agent_router

# Initialize settings
settings = get_settings()

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
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(financials_router)
app.include_router(agent_router)


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


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
