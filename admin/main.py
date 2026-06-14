"""Admin Panel — FastAPI application entry point (sync mode)"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from admin.config import ADMIN_IDS, CORS_ORIGINS, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, STATIC_DIR
from admin.database import SessionFactory, dispose_engine, init_models
from admin.models.admin_user import AdminUser
from admin.routers import auth, balance, broadcasts, dashboard, logs, orders, settings as settings_router, users, ws
from admin.services.auth_service import hash_password

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown"""
    # Startup
    logger.info("Starting admin panel...")
    init_models()  # sync
    _ensure_default_admin()
    logger.info("Admin panel startup complete")
    yield
    # Shutdown
    dispose_engine()
    logger.info("Admin panel shutdown complete")


def _ensure_default_admin():
    """Create default admin user if none exists"""
    db = SessionFactory()
    try:
        from sqlalchemy import select
        result = db.execute(select(AdminUser).limit(1))
        existing = result.scalar_one_or_none()
        if not existing:
            admin = AdminUser(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="superadmin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info(f"Default admin created: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")

        # Ensure admins from ADMIN_IDS env exist
        for tid in ADMIN_IDS:
            result = db.execute(
                select(AdminUser).where(AdminUser.telegram_id == tid)
            )
            admin = result.scalar_one_or_none()
            if not admin:
                admin = AdminUser(
                    telegram_id=tid,
                    username=f"admin_{tid}",
                    password_hash=hash_password(f"admin_{tid}"),
                    role="admin",
                    is_active=True,
                )
                db.add(admin)
                db.commit()
                logger.info(f"Admin created from ADMIN_IDS: telegram_id={tid}")
            elif not admin.telegram_id:
                admin.telegram_id = tid
                db.commit()
    finally:
        db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="StarPayUz Admin Panel",
        description="Professional admin panel for StarPayUz Telegram bot",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include ALL API routers FIRST
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(users.router)
    app.include_router(balance.router)
    app.include_router(broadcasts.router)
    app.include_router(settings_router.router)
    app.include_router(logs.router)
    app.include_router(orders.router)
    app.include_router(ws.router)

    # Health check
    @app.get("/health")
    def health():
        return {"ok": True, "service": "StarPayUz Admin Panel", "version": "1.0.0"}

    # SPA catch-all: serve index.html for all non-API routes
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Serve SPA: static files directly, otherwise index.html for client-side routing"""
        # Skip API paths (FastAPI handles them via routers above)
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        # Check if the path is a real static file (css, js, images, etc.)
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise serve index.html for SPA client-side routing
        index_html = STATIC_DIR / "index.html"
        if index_html.exists():
            return FileResponse(str(index_html))
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    return app


app = create_app()


def main():
    """Run the admin panel server"""
    import uvicorn

    host = os.environ.get("ADMIN_HOST", "0.0.0.0")
    port = int(os.environ.get("ADMIN_PORT", "8000"))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()

    uvicorn.run(
        "admin.main:app",
        host=host,
        port=port,
        reload=False,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
