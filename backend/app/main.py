"""
FastAPI Main Application
Airtel Fraud Detection System
"""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .config import APP_TITLE, APP_VERSION, API_PREFIX
from .services.db import init_db
from .api.v1 import upload, process, download, delete, statements, status, ui, parallel_import

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Fraud detection system for Airtel statements with duplicate detection and balance verification"
)

# CORS middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Setup Jinja2 templates
templates_path = Path(__file__).parent / "templates"
templates_path.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_path))

# Include API routers
app.include_router(upload.router, prefix=API_PREFIX, tags=["Upload"])
app.include_router(process.router, prefix=API_PREFIX, tags=["Process"])
app.include_router(download.router, prefix=API_PREFIX, tags=["Download"])
app.include_router(delete.router, prefix=API_PREFIX, tags=["Delete"])
app.include_router(statements.router, prefix=API_PREFIX, tags=["Statements"])
app.include_router(status.router, prefix=API_PREFIX, tags=["Status"])
app.include_router(ui.router, prefix=API_PREFIX, tags=["UI"])
app.include_router(parallel_import.router, prefix=API_PREFIX, tags=["Parallel Import"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION}")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve main dashboard page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    favicon_path = Path(__file__).parent / "static" / "favicon.ico"
    return FileResponse(favicon_path, media_type="image/x-icon")


@app.get("/health")
async def health():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "app": APP_TITLE, "version": APP_VERSION}


@app.get("/api/health")
async def api_health():
    """Health check endpoint"""
    return {"status": "healthy", "app": APP_TITLE, "version": APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
