"""
AI-ForenSight Backend API Entry Point.

FastAPI web server providing API endpoints for UFDR forensic analysis and database operations.
Reuses existing PostgreSQL connection module (backend/database/connection.py).
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

try:
    from .database.connection import get_connection
except ImportError:
    from database.connection import get_connection

try:
    from .database.initialize_schema import initialize_schema
except ImportError:
    from database.initialize_schema import initialize_schema

try:
    from .routes.cases import router as cases_router
except ImportError:
    from routes.cases import router as cases_router

try:
    from .routes.devices import router as devices_router
except ImportError:
    from routes.devices import router as devices_router

try:
    from .routes.contacts import router as contacts_router
except ImportError:
    from routes.contacts import router as contacts_router

try:
    from .routes.messages import router as messages_router
except ImportError:
    from routes.messages import router as messages_router

try:
    from .routes.calls import router as calls_router
except ImportError:
    from routes.calls import router as calls_router

try:
    from .routes.media import router as media_router
except ImportError:
    from routes.media import router as media_router

try:
    from .routes.ocr_results import router as ocr_results_router
except ImportError:
    from routes.ocr_results import router as ocr_results_router

try:
    from .routes.transcriptions import router as transcriptions_router
except ImportError:
    from routes.transcriptions import router as transcriptions_router

try:
    from .routes.image_analysis import router as image_analysis_router
except ImportError:
    from routes.image_analysis import router as image_analysis_router

try:
    from .routes.image_tags import router as image_tags_router
except ImportError:
    from routes.image_tags import router as image_tags_router

try:
    from .routes.upload import router as upload_router
except ImportError:
    from routes.upload import router as upload_router

try:
    from .routes.audit_logs import router as audit_logs_router
except ImportError:
    from routes.audit_logs import router as audit_logs_router


app = FastAPI(
    title="AI-ForenSight Forensic API",
    description="Backend API for forensic analysis and UFDR case data",
    version="1.0.0",
)

# allow_credentials=True cannot be combined with a wildcard origin (browsers
# reject it) -- the frontend's mock auth never sends cookies/credentialed
# requests anyway, so there's nothing that actually needs allow_credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _ensure_schema() -> None:
    """Create the UFDR tables/indexes if they don't exist yet (idempotent:
    every statement is CREATE TABLE/INDEX IF NOT EXISTS), so a fresh
    database doesn't need a separate manual setup step before first use."""
    initialize_schema()


app.include_router(cases_router)
app.include_router(devices_router)
app.include_router(contacts_router)
app.include_router(messages_router)
app.include_router(calls_router)
app.include_router(media_router)
app.include_router(ocr_results_router)
app.include_router(transcriptions_router)
app.include_router(image_analysis_router)
app.include_router(image_tags_router)
app.include_router(upload_router)
app.include_router(audit_logs_router)


@app.get("/api/health")
def health_check():
    """Verify API status and PostgreSQL database connectivity."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                db_version = cursor.fetchone()[0]
        return {
            "status": "healthy",
            "api_status": "API is running",
            "database_status": "PostgreSQL connection is successful",
            "database_version": db_version,
        }
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "unhealthy",
                "api_status": "API is running",
                "database_status": f"PostgreSQL connection failed: {str(err)}",
            },
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
