# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from app.config import get_settings
from app.dependencies.auth import get_current_user

# Routers
from app.routes import (
    auth as auth_routes,        # /api/token, /api/register
    otp as otp_routes,          # /api/otp/*
    users as users_routes,      # /api/users/*
    upload_visit_file,          # /api/upload/*
    whoami,                     # /api/whoami
    history,                    # /api/history/*
    upload_patient_file,       # /api/upload/patients
    export_billable_notes,  # /api/export/billable-notes
    import_hellonoteAPI_visits,  # /api/import-hellonote-visits
    # visits, invoices, etc. can be added later
)

# ---------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------
settings = get_settings()
app = FastAPI(
    title="Payroll Tool",
    # docs_url=None,        # disable Swagger UI in prod
    # redoc_url=None,       # disable ReDoc in prod
    # openapi_url=None      # disable OpenAPI schema in prod
)

# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------
# CORS settings
origins = (
    settings.ALLOWED_ORIGINS
    if isinstance(settings.ALLOWED_ORIGINS, list)
    else [o.strip() for o in str(settings.ALLOWED_ORIGINS).split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://visits.paradigmops.com", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Public routes (no auth required)
# ---------------------------------------------------------------------
app.include_router(auth_routes.router, prefix="/api", tags=["auth"])
app.include_router(otp_routes.router, prefix="/api", tags=["otp"])

@app.get("/healthz", tags=["health"])
async def healthz():
    """Simple health check endpoint for uptime monitoring."""
    return {"status": "ok"}

# ---------------------------------------------------------------------
# Protected routes (all require auth)
# ---------------------------------------------------------------------
protected = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])

protected.include_router(users_routes.router, tags=["users"])
protected.include_router(upload_visit_file.router, tags=["upload"])
protected.include_router(upload_patient_file.router, tags=["upload"])
protected.include_router(whoami.router, tags=["auth"])
protected.include_router(history.router, tags=["history"])
protected.include_router(export_billable_notes.router, tags=["export"])
protected.include_router(import_hellonoteAPI_visits.router, tags=["import"])
# protected.include_router(visits.router, tags=["visits"])
# protected.include_router(invoices.router, tags=["invoices"])

app.include_router(protected)
