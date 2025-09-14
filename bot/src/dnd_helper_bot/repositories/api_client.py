import logging
import os
from typing import Any, Dict, List, Optional

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
logger = logging.getLogger(__name__)


def _build_headers(params: Optional[Dict[str, Any]]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if params and isinstance(params.get("lang"), str):
        v = str(params["lang"]).strip().lower()
        if v in {"ru", "en"}:
            headers["Accept-Language"] = v
    return headers


async def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    url = f"{API_BASE_URL}{path}"
    logger.info("API GET", extra={"url": url})
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params or {}, headers=_build_headers(params))
        logger.info("API GET response", extra={"url": url, "status_code": resp.status_code})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Log response body to aid debugging (422 details, etc.)
            body_text = None
            try:
                body_text = resp.text
            except Exception:
                body_text = None
            logger.error(
                "API GET error",
                extra={
                    "url": url,
                    "status_code": resp.status_code,
                    "response_body": (body_text if body_text is not None else "<unavailable>"),
                },
            )
            raise exc
        return resp.json()


async def api_get_one(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    logger.info("API GET ONE", extra={"url": url})
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params or {}, headers=_build_headers(params))
        logger.info("API GET ONE response", extra={"url": url, "status_code": resp.status_code})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body_text = None
            try:
                body_text = resp.text
            except Exception:
                body_text = None
            logger.error(
                "API GET ONE error",
                extra={
                    "url": url,
                    "status_code": resp.status_code,
                    "response_body": (body_text if body_text is not None else "<unavailable>"),
                },
            )
            raise exc
        return resp.json()


async def api_post(path: str, json: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    logger.info("API POST", extra={"url": url})
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=json)
        logger.info("API POST response", extra={"url": url, "status_code": resp.status_code})
        resp.raise_for_status()
        return resp.json()


async def api_patch(path: str, json: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    logger.info("API PATCH", extra={"url": url})
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(url, json=json)
        logger.info("API PATCH response", extra={"url": url, "status_code": resp.status_code})
        resp.raise_for_status()
        return resp.json()


