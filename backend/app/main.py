from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.routers import admin, auth, imports, members, meta, public, referrals, sources, surveys

app = FastAPI(
    title=settings.APP_NAME,
    description="ViewBox Panel System — member panel, source attribution, referrals, eligibility and operations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, public.router, members.router, sources.router, surveys.router,
               surveys.admin_router, referrals.router, imports.router, admin.router, meta.router):
    app.include_router(router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["system"])
def health() -> dict:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        database = "connected"
    except Exception as exc:
        database = f"unavailable: {type(exc).__name__}"
    return {"status": "ok", "database": database, "environment": settings.ENVIRONMENT}
