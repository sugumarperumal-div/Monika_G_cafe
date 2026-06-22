import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.models.database import create_tables
from backend.routers.auth import router as auth_router
from backend.routers.menu import router as menu_router
from backend.routers.orders import router as orders_router
from backend.routers.other import (
    tables_router, reservations_router, inventory_router,
    employees_router, feedback_router, reports_router
)

# ── Create FastAPI app ────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Full-stack cafe management system API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ─────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ─────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── API Routers ───────────────────────────────
for router in [
    auth_router, menu_router, orders_router,
    tables_router, reservations_router, inventory_router,
    employees_router, feedback_router, reports_router,
]:
    app.include_router(router, prefix="/api")

# ── Serve frontend SPA ────────────────────────
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    index = os.path.join("frontend", "templates", "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "Monika G Cafe API is running. Visit /api/docs"}


# ── Startup ───────────────────────────────────
@app.on_event("startup")
async def startup():
    create_tables()
    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"   API docs → http://localhost:8000/api/docs")