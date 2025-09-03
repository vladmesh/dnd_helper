# ruff: noqa: I001
import os

from dnd_helper_api.logging_config import configure_logging
from dnd_helper_api.routers.monsters import router as monsters_router
from dnd_helper_api.routers.spells import router as spells_router
from dnd_helper_api.routers.users import router as users_router
from dnd_helper_api.routers.i18n import router as i18n_router
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import traceback
import logging

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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dnd_helper_api.main:app", host="0.0.0.0", port=8000, log_config=None)
