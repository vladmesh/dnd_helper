# ruff: noqa: I001
import os

from dnd_helper_api.logging_config import configure_logging
from dnd_helper_api.routers.monsters import router as monsters_router
from dnd_helper_api.routers.spells import router as spells_router
from dnd_helper_api.routers.users import router as users_router
from dnd_helper_api.routers.i18n import router as i18n_router
from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqladmin import Admin, ModelView
from dnd_helper_api.db import engine
from typing import Optional
from shared_models import Monster, Spell, User, UiTranslation
from starlette.middleware.base import BaseHTTPMiddleware
import time
import traceback
import logging
from contextvars import ContextVar
from typing import Any
from sqlalchemy import event
from sqlalchemy.orm import Session as SASession
from sqlmodel import SQLModel
from shared_models.admin_audit import AdminAudit

configure_logging(
    service_name=os.getenv("LOG_SERVICE_NAME", "api"),
)

app = FastAPI(title="DnD Helper API")


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        try:
            response = await call_next(request)
            # Log 5xx responses too (even if handled downstream)
            if 500 <= response.status_code < 600:
                duration_ms = int((time.perf_counter() - start) * 1000)
                logging.getLogger(__name__).error(
                    "HTTP 5xx response",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "client": request.client.host if request.client else None,
                        "duration_ms": duration_ms,
                    },
                )
            return response
        except Exception as exc:  # noqa: BLE001 - we want to log all unhandled exceptions
            duration_ms = int((time.perf_counter() - start) * 1000)
            tb_str = traceback.format_exc()
            logging.getLogger(__name__).error(
                "Unhandled exception during request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client": request.client.host if request.client else None,
                    "duration_ms": duration_ms,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "traceback": tb_str,
                },
            )
            raise


app.add_middleware(ErrorLoggingMiddleware)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


app.include_router(users_router)
app.include_router(monsters_router)
app.include_router(spells_router)
app.include_router(i18n_router)


# --- SQLAdmin (Iteration 1): gated by ADMIN_ENABLED and protected by simple Bearer token ---
def _admin_token_auth(authorization: Optional[str] = None) -> None:
    required = os.getenv("ADMIN_TOKEN")
    if not required:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1]
    if token != required:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


class ReadOnlyModelView(ModelView):
    can_create = False
    can_edit = False
    can_delete = False


# Context vars to carry admin request metadata to DB event hooks
_admin_active: ContextVar[bool] = ContextVar("admin_active", default=False)
_admin_actor: ContextVar[Optional[str]] = ContextVar("admin_actor", default=None)
_admin_path: ContextVar[Optional[str]] = ContextVar("admin_path", default=None)
_admin_client_ip: ContextVar[Optional[str]] = ContextVar("admin_client_ip", default=None)


def _serialize_instance(obj: Any) -> dict:
    try:
        data = {}
        for col in obj.__table__.columns:  # type: ignore[attr-defined]
            data[col.name] = getattr(obj, col.name)
        return data
    except Exception:
        return {}


@event.listens_for(SASession, "after_flush")
def _admin_after_flush(session: SASession, flush_context) -> None:  # type: ignore[override]
    if not _admin_active.get():
        return
    actor = _admin_actor.get()
    path = _admin_path.get()
    client_ip = _admin_client_ip.get()

    def _add_audit(op: str, obj: Any, before: dict | None, after: dict | None) -> None:
        try:
            table_name = obj.__table__.name  # type: ignore[attr-defined]
            pk = None
            for col in obj.__table__.primary_key.columns:  # type: ignore[attr-defined]
                pk = getattr(obj, col.name)
                break
            audit = AdminAudit(
                table_name=table_name,
                row_pk=str(pk) if pk is not None else "",
                operation=op,
                before_data=before,
                after_data=after,
                actor=actor,
                path=path,
                client_ip=client_ip,
            )
            session.add(audit)
        except Exception:
            # Never break main transaction on audit failure
            logging.getLogger(__name__).exception("Failed to enqueue admin audit record")

    for obj in session.new:
        if isinstance(obj, SQLModel) and getattr(obj, "__table__", None) is not None:
            _add_audit("create", obj, None, _serialize_instance(obj))
    for obj in session.dirty:
        if session.is_modified(obj, include_collections=False):
            if isinstance(obj, SQLModel) and getattr(obj, "__table__", None) is not None:
                _add_audit("update", obj, None, _serialize_instance(obj))
    for obj in session.deleted:
        if isinstance(obj, SQLModel) and getattr(obj, "__table__", None) is not None:
            _add_audit("delete", obj, _serialize_instance(obj), None)


if os.getenv("ADMIN_ENABLED", "false").lower() in {"1", "true", "yes"}:
    admin = Admin(app=app, engine=engine)

    class MonsterAdmin(ReadOnlyModelView, model=Monster):
        name = "Monsters"

    class SpellAdmin(ReadOnlyModelView, model=Spell):
        name = "Spells"

    class UserAdmin(ReadOnlyModelView, model=User):
        name = "Users"

    class UiTranslationAdmin(ModelView, model=UiTranslation):
        name = "UI Translations"
        can_create = True
        can_edit = True
        can_delete = False
        column_list = [UiTranslation.namespace, UiTranslation.key, UiTranslation.lang, UiTranslation.text]
        column_default_sort = [(UiTranslation.namespace, True), (UiTranslation.key, True), (UiTranslation.lang, True)]
        form_excluded_columns = [UiTranslation.id]

    # Protect admin endpoints via dependency on token auth using FastAPI route middleware
    # sqladmin registers under /admin by default. We'll attach a simple dependency via middleware.
    @app.middleware("http")
    async def admin_auth_middleware(request: Request, call_next):  # type: ignore[override]
        if request.url.path.startswith("/admin"):
            _admin_token_auth(request.headers.get("Authorization"))
            # Stash context for audit hooks
            _admin_active.set(True)
            _admin_actor.set(request.headers.get("Authorization"))
            _admin_path.set(request.url.path)
            _admin_client_ip.set(request.client.host if request.client else None)
            try:
                response = await call_next(request)
            finally:
                # Reset to defaults to avoid leaking context across requests
                _admin_active.set(False)
                _admin_actor.set(None)
                _admin_path.set(None)
                _admin_client_ip.set(None)
            return response
        return await call_next(request)

    admin.add_view(MonsterAdmin)
    admin.add_view(SpellAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(UiTranslationAdmin)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dnd_helper_api.main:app", host="0.0.0.0", port=8000, log_config=None)
