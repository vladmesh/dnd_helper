# ruff: noqa: I001
import os

from dnd_helper_api.logging_config import configure_logging
from dnd_helper_api.routers.monsters import router as monsters_router
from dnd_helper_api.routers.spells import router as spells_router
from dnd_helper_api.routers.users import router as users_router
from dnd_helper_api.routers.i18n import router as i18n_router
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from sqlmodel import Session
import uuid
from pathlib import Path
from dnd_helper_api.db import get_session
from shared_models.admin_job import AdminJob
from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqladmin import Admin, ModelView
from sqladmin import BaseView, expose
from dnd_helper_api.db import engine
from typing import Optional
from shared_models import Monster, Spell, User, UiTranslation, EnumTranslation
from shared_models.monster_translation import MonsterTranslation
from shared_models.spell_translation import SpellTranslation
from shared_models.enums import Language, CasterClass, SpellSchool
from dnd_helper_api.routers.monsters.derived import _compute_monster_derived_fields, _slugify as _monster_slugify
from dnd_helper_api.routers.spells.derived import _compute_spell_derived_fields
from starlette.middleware.base import BaseHTTPMiddleware
import time
import traceback
import logging
import threading
from contextvars import ContextVar
from typing import Any
from datetime import datetime, date, time as dt_time
from uuid import UUID
import zipfile
import tarfile
import io
import json as _json
import gzip as _gzip
import base64
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
            value = getattr(obj, col.name)
            if isinstance(value, (datetime, date, dt_time)):
                data[col.name] = value.isoformat()
            elif isinstance(value, UUID):
                data[col.name] = str(value)
            else:
                data[col.name] = value
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
        if isinstance(obj, SQLModel) and getattr(obj, "__table__", None) is not None and not isinstance(obj, AdminAudit):
            _add_audit("create", obj, None, _serialize_instance(obj))
    for obj in session.dirty:
        if session.is_modified(obj, include_collections=False):
            if isinstance(obj, SQLModel) and getattr(obj, "__table__", None) is not None and not isinstance(obj, AdminAudit):
                _add_audit("update", obj, None, _serialize_instance(obj))
    for obj in session.deleted:
        if isinstance(obj, SQLModel) and getattr(obj, "__table__", None) is not None and not isinstance(obj, AdminAudit):
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

    class AdminAuditAdmin(ReadOnlyModelView, model=AdminAudit):
        name = "Admin Audit"
        column_list = [
            AdminAudit.id,
            AdminAudit.created_at,
            AdminAudit.table_name,
            AdminAudit.row_pk,
            AdminAudit.operation,
            AdminAudit.actor,
            AdminAudit.path,
            AdminAudit.client_ip,
        ]
        column_default_sort = [(AdminAudit.created_at, False)]
        form_excluded_columns = [AdminAudit.before_data, AdminAudit.after_data, AdminAudit.updated_at]
        column_searchable_list = [
            AdminAudit.table_name,
            AdminAudit.row_pk,
            AdminAudit.operation,
            AdminAudit.actor,
            AdminAudit.path,
            AdminAudit.client_ip,
        ]
        column_sortable_list = [
            AdminAudit.id,
            AdminAudit.created_at,
            AdminAudit.table_name,
            AdminAudit.row_pk,
            AdminAudit.operation,
            AdminAudit.actor,
        ]

    class AdminJobAdmin(ReadOnlyModelView, model=AdminJob):
        name = "Admin Jobs"
        column_list = [
            AdminJob.id,
            AdminJob.created_at,
            AdminJob.job_type,
            AdminJob.status,
            AdminJob.file_path,
            AdminJob.launched_by,
        ]
        column_default_sort = [(AdminJob.created_at, False)]
        form_excluded_columns = [
            AdminJob.updated_at,
            AdminJob.started_at,
            AdminJob.finished_at,
            AdminJob.args,
            AdminJob.counters,
            AdminJob.error,
        ]
        column_searchable_list = [AdminJob.job_type, AdminJob.status, AdminJob.file_path, AdminJob.launched_by]
        column_sortable_list = [AdminJob.id, AdminJob.created_at, AdminJob.job_type, AdminJob.status]

    class AdminUploadView(BaseView):
        name = "Upload"

        @expose("/upload", methods=["GET"])  # type: ignore[misc]
        async def page(self, request: Request):  # type: ignore[override]
            html = """
            <!DOCTYPE html>
            <html lang=\"en\">
            <head>
              <meta charset=\"UTF-8\" />
              <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
              <title>Admin Upload</title>
              <style>
                body { font-family: sans-serif; padding: 16px; }
                fieldset { margin-bottom: 20px; }
                legend { font-weight: bold; }
                label { display: block; margin: 8px 0; }
                .row { margin: 16px 0; }
                .ok { color: #0a0; }
                .err { color: #a00; }
              </style>
            </head>
            <body>
              <h1>Admin Uploads</h1>

              <fieldset>
                <legend>Monsters</legend>
                <form action=\"/admin-api/upload\" method=\"post\" enctype=\"multipart/form-data\">
                  <input type=\"hidden\" name=\"job_type\" value=\"monsters_import\" />
                  <label>File (.json): <input type=\"file\" name=\"file\" accept=\"application/json\" required /></label>
                  <label><input type=\"checkbox\" name=\"dry_run\" value=\"true\" /> Dry run</label>
                  <button type=\"submit\">Upload Monsters</button>
                </form>
                <div id=\"monsters_result\"></div>
              </fieldset>

              <fieldset>
                <legend>Spells</legend>
                <form action=\"/admin-api/upload\" method=\"post\" enctype=\"multipart/form-data\">
                  <input type=\"hidden\" name=\"job_type\" value=\"spells_import\" />
                  <label>File (.json): <input type=\"file\" name=\"file\" accept=\"application/json\" required /></label>
                  <label><input type=\"checkbox\" name=\"dry_run\" value=\"true\" /> Dry run</label>
                  <button type=\"submit\">Upload Spells</button>
                </form>
                <div id=\"spells_result\"></div>
              </fieldset>

              <fieldset>
                <legend>Enums</legend>
                <form action=\"/admin-api/upload\" method=\"post\" enctype=\"multipart/form-data\">
                  <input type=\"hidden\" name=\"job_type\" value=\"enums_import\" />
                  <label>File (.json): <input type=\"file\" name=\"file\" accept=\"application/json\" required /></label>
                  <label><input type=\"checkbox\" name=\"dry_run\" value=\"true\" /> Dry run</label>
                  <button type=\"submit\">Upload Enums</button>
                </form>
                <div id=\"enums_result\"></div>
              </fieldset>

              <fieldset>
                <legend>UI Translations (i18n)</legend>
                <form action=\"/admin-api/upload\" method=\"post\" enctype=\"multipart/form-data\">
                  <input type=\"hidden\" name=\"job_type\" value=\"ui_translations_import\" />
                  <label>File (.json): <input type=\"file\" name=\"file\" accept=\"application/json\" required /></label>        
                  <label><input type=\"checkbox\" name=\"dry_run\" value=\"true\" /> Dry run</label>
                  <button type=\"submit\">Upload UI Translations</button>
                </form>
                <div id=\"ui_result\"></div>
              </fieldset>
            </body>
            </html>
            """
            return HTMLResponse(content=html)

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
    admin.add_view(AdminAuditAdmin)
    admin.add_view(AdminJobAdmin)
    admin.add_view(AdminUploadView)

    # --- Iteration 4: upload endpoint (store only) ---
    upload_router = APIRouter()

    @upload_router.post("/admin-api/upload")
    async def admin_upload(
        request: Request,
        file: UploadFile = File(...),
        job_type: str = Form("monsters_import"),
        dry_run: bool = Form(False),
        session: Session = Depends(get_session),
    ) -> dict:
        try:
            _admin_token_auth(request.headers.get("Authorization"))
            # Enforce non-empty file for all job types
            if not file or not (getattr(file, "filename", None) or "").strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File is required")
            upload_dir = os.getenv("ADMIN_UPLOAD_DIR", "/data/admin_uploads")
            Path(upload_dir).mkdir(parents=True, exist_ok=True)
            # Save to disk in chunks
            filename = f"{uuid.uuid4()}_{file.filename}"
            dest_path = os.path.join(upload_dir, filename)
            with open(dest_path, "wb") as out:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            # Create DB job row
            job = AdminJob(
                job_type=job_type,
                args={"dry_run": dry_run},
                file_path=dest_path,
                status="queued",
                counters={},
                launched_by=request.headers.get("Authorization"),
            )
            session.add(job)
            try:
                session.commit()
            except Exception:
                logging.getLogger(__name__).exception("Failed to create AdminJob")
                raise
            return {"id": str(job.id), "status": job.status}
        except HTTPException as exc:  # pass through expected HTTP errors
            raise exc
        except Exception as exc:
            logging.getLogger(__name__).exception("Admin upload failed")
            raise HTTPException(status_code=500, detail=str(exc))

    app.include_router(upload_router)

    # --- Universal bundle ingest endpoints ---
    ingest_router = APIRouter()

    @ingest_router.post("/admin-api/ingest/bundle")
    async def admin_ingest_bundle(
        request: Request,
        file: UploadFile = File(...),
        dry_run: bool = Form(False),
        session: Session = Depends(get_session),
    ) -> dict:
        try:
            _admin_token_auth(request.headers.get("Authorization"))
            if not file or not (getattr(file, "filename", None) or "").strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File is required")
            upload_dir = os.getenv("ADMIN_UPLOAD_DIR", "/data/admin_uploads")
            Path(upload_dir).mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4()}_{file.filename}"
            dest_path = os.path.join(upload_dir, filename)
            with open(dest_path, "wb") as out:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            job = AdminJob(
                job_type="bundle_ingest",
                args={"dry_run": dry_run},
                file_path=dest_path,
                status="queued",
                counters={},
                launched_by=request.headers.get("Authorization"),
            )
            session.add(job)
            session.commit()
            return {"id": str(job.id), "status": job.status}
        except HTTPException as exc:
            raise exc
        except Exception as exc:
            logging.getLogger(__name__).exception("Admin bundle ingest enqueue failed")
            raise HTTPException(status_code=500, detail=str(exc))

    @ingest_router.get("/admin-api/ingest/jobs/{job_id}")
    async def admin_ingest_job_status(job_id: UUID, session: Session = Depends(get_session)) -> dict:
        job = session.get(AdminJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "file_path": job.file_path,
            "counters": job.counters or {},
            "error": job.error,
            "args": job.args or {},
        }

    # Sync run endpoint was removed (temporary testing aid)

    app.include_router(ingest_router)

# --- Iteration 5: Minimal background worker (validate-only) ---
_worker_thread: Optional[threading.Thread] = None
_worker_stop = threading.Event()


def _process_job(session: SASession, job: AdminJob) -> None:
    try:
        job.status = "running"
        session.commit()
        counters: dict[str, int] = {"processed": 0, "created": 0, "updated": 0, "skipped": 0}
        payload: dict | None = None
        # Validate JSON structure and perform minimal import (legacy JSON uploads)
        if job.job_type in {"monsters_import", "spells_import", "enums_import", "ui_translations_import"}:
            with open(job.file_path or "", "rb") as f:  # type: ignore[arg-type]
                payload = _json.load(f)
        if job.job_type == "monsters_import":
            rows = (payload or {}).get("monsters") or []
            tr_rows = (payload or {}).get("monster_translations") or []
            # index translations by (slug, lang)
            tr_index: dict[tuple[str, str], dict] = {}
            for it in tr_rows if isinstance(tr_rows, list) else []:
                slug = str(it.get("monster_slug") or "").strip()
                lang = str(it.get("lang") or "").strip().lower()
                if slug and lang in {"ru", "en"}:
                    tr_index[(slug, lang)] = it
            for raw in rows if isinstance(rows, list) else []:
                counters["processed"] += 1
                try:
                    data = dict(raw)
                    # compute slug if missing
                    slug = str(data.get("slug") or "").strip()
                    if not slug:
                        base_name = str(data.get("name") or data.get("name_en") or "").strip()
                        slug = _monster_slugify(base_name) if base_name else ""
                        if slug:
                            data["slug"] = slug
                    if not slug:
                        counters["skipped"] += 1
                        continue
                    # filter to Monster fields only
                    # Backward-compat: map legacy 'abilities' -> 'ability_scores'
                    if "abilities" in data and "ability_scores" not in data:
                        data["ability_scores"] = data.pop("abilities")
                    allowed = set(Monster.model_fields.keys()) - {"id"}
                    filtered = {k: v for k, v in data.items() if k in allowed}
                    # create or update by slug
                    existing = session.query(Monster).filter(Monster.slug == slug).first()
                    if existing is None:
                        monster = Monster(**filtered)  # type: ignore[arg-type]
                        _compute_monster_derived_fields(monster)
                        session.add(monster)
                        session.commit()
                        session.refresh(monster)
                        counters["created"] += 1
                    else:
                        for k, v in filtered.items():
                            setattr(existing, k, v)
                        _compute_monster_derived_fields(existing)
                        session.add(existing)
                        session.commit()
                        monster = existing
                        counters["updated"] += 1
                    # upsert translations
                    for lang in ("ru", "en"):
                        tr = tr_index.get((slug, lang))
                        if not isinstance(tr, dict):
                            continue
                        l = Language(lang)
                        mt = (
                            session.query(MonsterTranslation)
                            .filter(MonsterTranslation.monster_id == monster.id, MonsterTranslation.lang == l)
                            .first()
                        )
                        # derive languages_text from raw row if present
                        languages_text: Optional[str] = None
                        try:
                            langs_val = raw.get("languages") if isinstance(raw, dict) else None
                            if isinstance(langs_val, list):
                                languages_text = ", ".join([str(x) for x in langs_val if x is not None]) or None
                            elif isinstance(langs_val, str):
                                languages_text = langs_val or None
                        except Exception:
                            languages_text = None
                        if mt is None:
                            mt = MonsterTranslation(
                                monster_id=monster.id,
                                lang=l,
                                name=(tr.get("name") or ""),
                                description=(tr.get("description") or ""),
                                traits=tr.get("traits"),
                                actions=tr.get("actions"),
                                reactions=tr.get("reactions"),
                                legendary_actions=tr.get("legendary_actions"),
                                spellcasting=tr.get("spellcasting"),
                                languages_text=languages_text,
                            )
                        else:
                            if tr.get("name"):
                                mt.name = tr.get("name")
                            if tr.get("description"):
                                mt.description = tr.get("description")
                            mt.traits = tr.get("traits")
                            mt.actions = tr.get("actions")
                            mt.reactions = tr.get("reactions")
                            mt.legendary_actions = tr.get("legendary_actions")
                            mt.spellcasting = tr.get("spellcasting")
                            if languages_text is not None:
                                mt.languages_text = languages_text
                        session.add(mt)
                        session.commit()
                except Exception:
                    counters["skipped"] += 1
                    logging.getLogger(__name__).exception("Failed to import a monster row")
        elif job.job_type == "spells_import":
            rows = (payload or {}).get("spells") or []
            tr_rows = (payload or {}).get("spell_translations") or []
            tr_index: dict[tuple[str, str], dict] = {}
            for it in tr_rows if isinstance(tr_rows, list) else []:
                slug = str(it.get("spell_slug") or "").strip()
                lang = str(it.get("lang") or "").strip().lower()
                if slug and lang in {"ru", "en"}:
                    tr_index[(slug, lang)] = it
            for raw in rows if isinstance(rows, list) else []:
                counters["processed"] += 1
                try:
                    data = dict(raw)
                    slug = str(data.get("slug") or "").strip()
                    if not slug:
                        base_name = str(data.get("name") or data.get("name_en") or "").strip()
                        slug = base_name.lower().replace(" ", "-") if base_name else ""
                        if slug:
                            data["slug"] = slug
                    if not slug:
                        counters["skipped"] += 1
                        continue
                    # Validate enums
                    school = data.get("school")
                    if school is not None:
                        SpellSchool(str(school))
                    classes_val = data.get("classes")
                    if classes_val is not None:
                        if not isinstance(classes_val, list):
                            classes_val = [classes_val]
                        for cls in classes_val:
                            CasterClass(str(cls))
                        data["classes"] = classes_val
                    allowed = set(Spell.model_fields.keys()) - {"id"}
                    filtered = {k: v for k, v in data.items() if k in allowed}
                    existing = session.query(Spell).filter(Spell.slug == slug).first()
                    if existing is None:
                        spell = Spell(**filtered)  # type: ignore[arg-type]
                        _compute_spell_derived_fields(spell)
                        session.add(spell)
                        session.commit()
                        session.refresh(spell)
                        counters["created"] += 1
                    else:
                        for k, v in filtered.items():
                            setattr(existing, k, v)
                        _compute_spell_derived_fields(existing)
                        session.add(existing)
                        session.commit()
                        spell = existing
                        counters["updated"] += 1
                    for lang in ("ru", "en"):
                        tr = tr_index.get((slug, lang))
                        if not isinstance(tr, dict):
                            continue
                        l = Language(lang)
                        st = (
                            session.query(SpellTranslation)
                            .filter(SpellTranslation.spell_id == spell.id, SpellTranslation.lang == l)
                            .first()
                        )
                        if st is None:
                            st = SpellTranslation(
                                spell_id=spell.id,
                                lang=l,
                                name=(tr.get("name") or ""),
                                description=(tr.get("description") or ""),
                            )
                        else:
                            if tr.get("name"):
                                st.name = tr.get("name")
                            if tr.get("description"):
                                st.description = tr.get("description")
                        session.add(st)
                        session.commit()
                except Exception:
                    counters["skipped"] += 1
                    logging.getLogger(__name__).exception("Failed to import a spell row")
        elif job.job_type == "enums_import":
            rows = (payload or {}).get("enum_translations") or []
            for r in rows if isinstance(rows, list) else []:
                counters["processed"] += 1
                try:
                    enum_type = str(r.get("enum_type") or "").strip()
                    enum_value = str(r.get("enum_value") or "").strip()
                    lang_raw = str(r.get("lang") or "").strip().lower()
                    label = r.get("label")
                    if not (enum_type and enum_value and lang_raw in {"ru", "en"} and isinstance(label, str)):
                        counters["skipped"] += 1
                        continue
                    lang = Language(lang_raw)
                    ex = (
                        session.query(EnumTranslation)
                        .filter(
                            EnumTranslation.enum_type == enum_type,
                            EnumTranslation.enum_value == enum_value,
                            EnumTranslation.lang == lang,
                        )
                        .first()
                    )
                    if ex is None:
                        ex = EnumTranslation(
                            enum_type=enum_type,
                            enum_value=enum_value,
                            lang=lang,
                            label=label,
                            description=r.get("description"),
                            synonyms=r.get("synonyms"),
                        )
                        session.add(ex)
                        session.commit()
                        counters["created"] += 1
                    else:
                        ex.label = label
                        ex.description = r.get("description")
                        ex.synonyms = r.get("synonyms")
                        session.add(ex)
                        session.commit()
                        counters["updated"] += 1
                except Exception:
                    counters["skipped"] += 1
                    logging.getLogger(__name__).exception("Failed to upsert enum translation")
        elif job.job_type == "ui_translations_import":
            rows = (payload or {}).get("ui_translations") or []
            for r in rows if isinstance(rows, list) else []:
                counters["processed"] += 1
                try:
                    ns = str(r.get("namespace") or "bot").strip() or "bot"
                    key = str(r.get("key") or "").strip()
                    lang_raw = str(r.get("lang") or "").strip().lower()
                    text = r.get("text")
                    if not (key and lang_raw in {"ru", "en"} and isinstance(text, str)):
                        counters["skipped"] += 1
                        continue
                    lang = Language(lang_raw)
                    ex = (
                        session.query(UiTranslation)
                        .filter(
                            UiTranslation.namespace == ns,
                            UiTranslation.key == key,
                            UiTranslation.lang == lang,
                        )
                        .first()
                    )
                    if ex is None:
                        ex = UiTranslation(namespace=ns, key=key, lang=lang, text=text)
                        session.add(ex)
                        session.commit()
                        counters["created"] += 1
                    else:
                        ex.text = text
                        session.add(ex)
                        session.commit()
                        counters["updated"] += 1
                except Exception:
                    counters["skipped"] += 1
                    logging.getLogger(__name__).exception("Failed to upsert UI translation")
        elif job.job_type == "bundle_ingest":
            # Process a universal bundle archive according to manifest.json
            # Supported archives: .zip, .tar.gz, .tgz. Files inside may be plain .jsonl or .jsonl.gz per manifest.
            def _open_bundle(path: str) -> tuple[str, Any, str]:
                p = path.lower()
                if p.endswith(".zip"):
                    return ("zip", zipfile.ZipFile(path, "r"), path)
                if p.endswith(".tar.gz") or p.endswith(".tgz"):
                    return ("tar", tarfile.open(path, mode="r:gz"), path)
                raise ValueError("Unsupported bundle format. Use .zip or .tar.gz")

            def _read_file_bytes(kind: str, arc: Any, member_path: str) -> bytes:
                if kind == "zip":
                    with arc.open(member_path) as f:  # type: ignore[attr-defined]
                        return f.read()
                else:
                    member = arc.getmember(member_path)  # type: ignore[attr-defined]
                    f = arc.extractfile(member)  # type: ignore[attr-defined]
                    if f is None:
                        raise FileNotFoundError(member_path)
                    try:
                        return f.read()
                    finally:
                        f.close()

            def _iter_ndjson(data: bytes, compression: str) -> Any:
                if compression == "gzip":
                    with _gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as gf:
                        for line in gf:
                            s = line.decode("utf-8").strip()
                            if not s:
                                continue
                            yield _json.loads(s)
                else:
                    for line in io.BytesIO(data).read().splitlines():
                        s = line.decode("utf-8").strip()
                        if not s:
                            continue
                        yield _json.loads(s)

            kind, arc, _arc_path = _open_bundle(job.file_path or "")
            try:
                # Read and validate manifest.json
                manifest_bytes = _read_file_bytes(kind, arc, "manifest.json")
                manifest = _json.loads(manifest_bytes.decode("utf-8"))
                files = manifest.get("files") or []
                if not isinstance(files, list) or not files:
                    raise ValueError("manifest.files must be a non-empty array")
                # Simple topological-ish ordering: process in given order
                # Runtime state to map UIDs to created DB ids for this run
                uid_to_monster_id: dict[str, int] = {}
                uid_to_spell_id: dict[str, int] = {}
                per_file_stats: list[dict[str, Any]] = []
                for fdesc in files:
                    fpath = str((fdesc.get("path") or "")).strip()
                    ftype = str((fdesc.get("type") or "")).strip()
                    flang = str((fdesc.get("lang") or "")).strip().lower() or None
                    compression = str((fdesc.get("compression") or "none")).strip().lower()
                    if not fpath or not ftype:
                        raise ValueError("Each file entry must include path and type")
                    data = _read_file_bytes(kind, arc, fpath)
                    processed = created = updated = unchanged = failed = 0
                    # Iterate NDJSON records
                    for rec in _iter_ndjson(data, compression):
                        processed += 1
                        try:
                            if ftype == "monsters":
                                # Upsert by slug; derive from provided slug/name; track uid mapping
                                raw = dict(rec)
                                uid = str(raw.get("uid") or "").strip()
                                slug = str(raw.get("slug") or "").strip()
                                if not slug:
                                    base_name = str(raw.get("name") or raw.get("name_en") or "").strip()
                                    slug = _monster_slugify(base_name) if base_name else ""
                                    if slug:
                                        raw["slug"] = slug
                                if not slug:
                                    failed += 1
                                    continue
                                # Backward-compat mapping
                                if "abilities" in raw and "ability_scores" not in raw:
                                    raw["ability_scores"] = raw.pop("abilities")
                                allowed = set(Monster.model_fields.keys()) - {"id"}
                                filtered = {k: v for k, v in raw.items() if k in allowed}
                                existing = session.query(Monster).filter(Monster.slug == slug).first()
                                if existing is None:
                                    monster = Monster(**filtered)  # type: ignore[arg-type]
                                    _compute_monster_derived_fields(monster)
                                    session.add(monster)
                                    session.commit()
                                    session.refresh(monster)
                                    created += 1
                                else:
                                    before = _serialize_instance(existing)
                                    for k, v in filtered.items():
                                        setattr(existing, k, v)
                                    _compute_monster_derived_fields(existing)
                                    session.add(existing)
                                    session.commit()
                                    monster = existing
                                    updated += 1 if _serialize_instance(existing) != before else 0
                                    unchanged += 1 if _serialize_instance(existing) == before else 0
                                if uid:
                                    uid_to_monster_id[uid] = monster.id  # type: ignore[assignment]
                            elif ftype == "monster_translations":
                                if not flang:
                                    raise ValueError("monster_translations requires lang in manifest entry")
                                raw = dict(rec)
                                uid = str(raw.get("uid") or "").strip()
                                if not uid or uid not in uid_to_monster_id:
                                    failed += 1
                                    continue
                                l = Language(flang)
                                mt = (
                                    session.query(MonsterTranslation)
                                    .filter(MonsterTranslation.monster_id == uid_to_monster_id[uid], MonsterTranslation.lang == l)
                                    .first()
                                )
                                if mt is None:
                                    mt = MonsterTranslation(
                                        monster_id=uid_to_monster_id[uid],
                                        lang=l,
                                        name=(raw.get("name") or ""),
                                        description=(raw.get("description") or ""),
                                        traits=raw.get("traits"),
                                        actions=raw.get("actions"),
                                        reactions=raw.get("reactions"),
                                        legendary_actions=raw.get("legendary_actions"),
                                        spellcasting=raw.get("spellcasting"),
                                        languages_text=raw.get("languages_text"),
                                    )
                                else:
                                    if raw.get("name"):
                                        mt.name = raw.get("name")
                                    if raw.get("description"):
                                        mt.description = raw.get("description")
                                    mt.traits = raw.get("traits")
                                    mt.actions = raw.get("actions")
                                    mt.reactions = raw.get("reactions")
                                    mt.legendary_actions = raw.get("legendary_actions")
                                    mt.spellcasting = raw.get("spellcasting")
                                    if raw.get("languages_text") is not None:
                                        mt.languages_text = raw.get("languages_text")
                                session.add(mt)
                                session.commit()
                                created += 1  # treat as created/updated uniformly for now
                            elif ftype == "spells":
                                raw = dict(rec)
                                uid = str(raw.get("uid") or "").strip()
                                slug = str(raw.get("slug") or "").strip()
                                if not slug:
                                    base_name = str(raw.get("name") or raw.get("name_en") or "").strip()
                                    slug = base_name.lower().replace(" ", "-") if base_name else ""
                                    if slug:
                                        raw["slug"] = slug
                                if not slug:
                                    failed += 1
                                    continue
                                school = raw.get("school")
                                if school is not None:
                                    SpellSchool(str(school))
                                classes_val = raw.get("classes")
                                if classes_val is not None:
                                    if not isinstance(classes_val, list):
                                        classes_val = [classes_val]
                                    for cls in classes_val:
                                        CasterClass(str(cls))
                                    raw["classes"] = classes_val
                                allowed = set(Spell.model_fields.keys()) - {"id"}
                                filtered = {k: v for k, v in raw.items() if k in allowed}
                                existing = session.query(Spell).filter(Spell.slug == slug).first()
                                if existing is None:
                                    spell = Spell(**filtered)  # type: ignore[arg-type]
                                    _compute_spell_derived_fields(spell)
                                    session.add(spell)
                                    session.commit()
                                    session.refresh(spell)
                                    created += 1
                                else:
                                    before = _serialize_instance(existing)
                                    for k, v in filtered.items():
                                        setattr(existing, k, v)
                                    _compute_spell_derived_fields(existing)
                                    session.add(existing)
                                    session.commit()
                                    spell = existing
                                    updated += 1 if _serialize_instance(existing) != before else 0
                                    unchanged += 1 if _serialize_instance(existing) == before else 0
                                if uid:
                                    uid_to_spell_id[uid] = spell.id  # type: ignore[assignment]
                            elif ftype == "spell_translations":
                                if not flang:
                                    raise ValueError("spell_translations requires lang in manifest entry")
                                raw = dict(rec)
                                uid = str(raw.get("uid") or "").strip()
                                if not uid or uid not in uid_to_spell_id:
                                    failed += 1
                                    continue
                                l = Language(flang)
                                st = (
                                    session.query(SpellTranslation)
                                    .filter(SpellTranslation.spell_id == uid_to_spell_id[uid], SpellTranslation.lang == l)
                                    .first()
                                )
                                if st is None:
                                    st = SpellTranslation(
                                        spell_id=uid_to_spell_id[uid],
                                        lang=l,
                                        name=(raw.get("name") or ""),
                                        description=(raw.get("description") or ""),
                                    )
                                else:
                                    if raw.get("name"):
                                        st.name = raw.get("name")
                                    if raw.get("description"):
                                        st.description = raw.get("description")
                                session.add(st)
                                session.commit()
                                created += 1
                            elif ftype == "enum_translations":
                                raw = dict(rec)
                                enum_type = str(raw.get("entity") or raw.get("enum_type") or "").strip()
                                enum_value = str(raw.get("code") or raw.get("enum_value") or "").strip()
                                lang_raw = str(raw.get("lang") or "").strip().lower()
                                label = raw.get("label") if raw.get("label") is not None else raw.get("text")
                                if not (enum_type and enum_value and lang_raw in {"ru", "en"} and isinstance(label, str)):
                                    failed += 1
                                    continue
                                lang = Language(lang_raw)
                                ex = (
                                    session.query(EnumTranslation)
                                    .filter(
                                        EnumTranslation.enum_type == enum_type,
                                        EnumTranslation.enum_value == enum_value,
                                        EnumTranslation.lang == lang,
                                    )
                                    .first()
                                )
                                if ex is None:
                                    ex = EnumTranslation(
                                        enum_type=enum_type,
                                        enum_value=enum_value,
                                        lang=lang,
                                        label=label,
                                        description=raw.get("description"),
                                        synonyms=raw.get("synonyms"),
                                    )
                                    session.add(ex)
                                    session.commit()
                                    created += 1
                                else:
                                    ex.label = label
                                    ex.description = raw.get("description")
                                    ex.synonyms = raw.get("synonyms")
                                    session.add(ex)
                                    session.commit()
                                    updated += 1
                            else:
                                raise ValueError(f"Unsupported file type: {ftype}")
                        except Exception:
                            failed += 1
                            logging.getLogger(__name__).exception("Failed to process record in %s", fpath)
                    per_file_stats.append({
                        "path": fpath,
                        "type": ftype,
                        "processed": processed,
                        "created": created,
                        "updated": updated,
                        "unchanged": unchanged,
                        "failed": failed,
                    })
                # Aggregate counters
                total = {"processed": 0, "created": 0, "updated": 0, "unchanged": 0, "failed": 0}
                for s in per_file_stats:
                    for k in total:
                        total[k] += int(s.get(k, 0))
                job.counters = {"files": per_file_stats, "summary": total}
            finally:
                try:
                    arc.close()
                except Exception:
                    pass
        else:
            raise ValueError(f"Unsupported job_type: {job.job_type}")

        job.counters = counters
        job.status = "succeeded"
        session.commit()
        logging.getLogger(__name__).info("Admin worker: job succeeded", extra={"job_id": str(job.id), "counters": counters})
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Admin worker: job failed")
        job.status = "failed"
        job.error = str(exc)
        session.commit()


def _worker_loop() -> None:
    poll_seconds = max(2, int(os.getenv("ADMIN_WORKER_POLL_SECONDS", "5")))
    logging.getLogger(__name__).info("Admin worker started", extra={"poll_seconds": poll_seconds})
    while not _worker_stop.is_set():
        try:
            with Session(engine) as session:
                job = (
                    session.query(AdminJob)  # type: ignore[attr-defined]
                    .filter(AdminJob.status == "queued")
                    .order_by(AdminJob.created_at)  # type: ignore[attr-defined]
                    .first()
                )
                if job is None:
                    pass
                else:
                    _process_job(session, job)
        except Exception:
            logging.getLogger(__name__).exception("Admin worker loop error")
        _worker_stop.wait(poll_seconds)
    logging.getLogger(__name__).info("Admin worker stopped")


@app.on_event("startup")
def _start_worker() -> None:
    if os.getenv("ADMIN_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return
    # Allow disabling background worker (useful in tests)
    if os.getenv("ADMIN_WORKER_DISABLE", "false").lower() in {"1", "true", "yes"}:
        return
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _worker_stop.clear()
    _worker_thread = threading.Thread(target=_worker_loop, name="admin-worker", daemon=True)
    _worker_thread.start()


@app.on_event("shutdown")
def _stop_worker() -> None:
    global _worker_thread
    _worker_stop.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5)
        _worker_thread = None

    # --- Admin UI: simple upload page with 4 sections posting via fetch() to /admin-api/upload ---
    @app.get("/admin/upload", response_class=HTMLResponse)
    async def admin_upload_form() -> HTMLResponse:  # type: ignore[override]
        html = """
        <!DOCTYPE html>
        <html lang=\"en\">
        <head>
          <meta charset=\"UTF-8\" />
          <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
          <title>Admin Upload</title>
          <style>
            body { font-family: sans-serif; padding: 16px; }
            fieldset { margin-bottom: 20px; }
            legend { font-weight: bold; }
            label { display: block; margin: 8px 0; }
            .row { margin: 16px 0; }
            .ok { color: #0a0; }
            .err { color: #a00; }
          </style>
        </head>
        <body>
          <h1>Admin Uploads</h1>
          <div class=\"row\">
            <label>Bearer token (required for API calls from browser):
              <input type=\"text\" id=\"token\" placeholder=\"dev\" style=\"width: 420px\" />
            </label>
            <small>The token is sent as Authorization: Bearer &lt;token&gt; to /admin-api/upload</small>
          </div>

          <fieldset>
            <legend>Monsters</legend>
            <label>File (.json): <input type=\"file\" id=\"monsters_file\" accept=\"application/json\" /></label>
            <label><input type=\"checkbox\" id=\"monsters_dry\" /> Dry run</label>
            <button onclick=\"upload('monsters_import','monsters_file','monsters_dry')\">Upload Monsters</button>
            <div id=\"monsters_result\"></div>
            <small>Repo file: seed_data_monsters.json</small>
          </fieldset>

          <fieldset>
            <legend>Spells</legend>
            <label>File (.json): <input type=\"file\" id=\"spells_file\" accept=\"application/json\" /></label>
            <label><input type=\"checkbox\" id=\"spells_dry\" /> Dry run</label>
            <button onclick=\"upload('spells_import','spells_file','spells_dry')\">Upload Spells</button>
            <div id=\"spells_result\"></div>
            <small>Repo file: seed_data_spells.json</small>
          </fieldset>

          <fieldset>
            <legend>Enums</legend>
            <label>File (.json): <input type=\"file\" id=\"enums_file\" accept=\"application/json\" /></label>
            <label><input type=\"checkbox\" id=\"enums_dry\" /> Dry run</label>
            <button onclick=\"upload('enums_import','enums_file','enums_dry')\">Upload Enums</button>
            <div id=\"enums_result\"></div>
            <small>Repo file: seed_data_enums.json</small>
          </fieldset>

          <fieldset>
            <legend>UI Translations (i18n)</legend>
            <label>File (.json): <input type=\"file\" id=\"ui_file\" accept=\"application/json\" /></label>
            <label><input type=\"checkbox\" id=\"ui_dry\" /> Dry run</label>
            <button onclick=\"upload('ui_translations_import','ui_file','ui_dry')\">Upload UI Translations</button>
            <div id=\"ui_result\"></div>
            <small>Note: current ops may use a hardcoded source; upload is optional.</small>
          </fieldset>

          <script>
          async function upload(jobType, fileInputId, dryId) {
            const token = document.getElementById('token').value.trim();
            const fileInput = document.getElementById(fileInputId);
            const dry = document.getElementById(dryId).checked;
            const resultEl = document.getElementById(jobType.split('_')[0] + '_result');
            resultEl.textContent = '';
            if (!token) { resultEl.innerHTML = '<span class="err">Token required</span>'; return; }
            if (!fileInput.files || fileInput.files.length === 0) { resultEl.innerHTML = '<span class="err">Select a file</span>'; return; }
            const form = new FormData();
            form.append('file', fileInput.files[0]);
            form.append('job_type', jobType);
            form.append('dry_run', dry ? 'true' : 'false');
            try {
              const resp = await fetch('/admin-api/upload', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
                body: form
              });
              const text = await resp.text();
              try { const data = JSON.parse(text); resultEl.innerHTML = '<span class="' + (resp.ok ? 'ok' : 'err') + '">' + JSON.stringify(data) + '</span>'; }
              catch { resultEl.innerHTML = '<span class="' + (resp.ok ? 'ok' : 'err') + '">' + text + '</span>'; }
            } catch (e) {
              resultEl.innerHTML = '<span class="err">' + (e?.message || e) + '</span>';
            }
          }
          </script>

        </body>
        </html>
        """
        return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dnd_helper_api.main:app", host="0.0.0.0", port=8000, log_config=None)
