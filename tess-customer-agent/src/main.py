"""
TESS FastAPI Application
Main entry point for the TESS Customer Agent API
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.api.routes import router
from src.api.middleware import CorrelationIDMiddleware, LoggingMiddleware
from src.utils.logging import init_logging, get_logger
from src.agent.graph import get_tess_agent
from src.memory.postgres_manager import get_memory_manager

# Initialize logging
init_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting TESS application")

    settings = get_settings()
    logger.info(
        f"Environment: {settings.app_env}",
        host=settings.app_host,
        port=settings.app_port
    )

    # Initialize memory manager
    try:
        memory_manager = get_memory_manager()
        await memory_manager.initialize()
        logger.info("Memory manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize memory manager: {e}", exc_info=True)

    # Initialize agent (this will also initialize MCP client and tools)
    try:
        agent = await get_tess_agent()
        logger.info(
            "TESS agent initialized",
            tools=agent.get_available_tools()
        )
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)

    logger.info("TESS application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down TESS application")

    # Close memory manager
    try:
        memory_manager = get_memory_manager()
        await memory_manager.close()
        logger.info("Memory manager closed")
    except Exception as e:
        logger.error(f"Error closing memory manager: {e}")

    logger.info("TESS application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="TESS - Technical Expert Support System",
    description="AI-powered customer support agent with multi-tool capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(LoggingMiddleware)

# Include routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse({
        "service": "TESS - Technical Expert Support System",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    })


@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )
