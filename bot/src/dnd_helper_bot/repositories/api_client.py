import logging
import os
from typing import Any, Dict, List, Optional

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
logger = logging.getLogger(__name__)


async def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    url = f"{API_BASE_URL}{path}"
    logger.info("API GET", extra={"url": url})
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params or {})
        logger.info("API GET response", extra={"url": url, "status_code": resp.status_code})
        resp.raise_for_status()
        return resp.json()


async def api_get_one(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    logger.info("API GET ONE", extra={"url": url})
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params or {})
        logger.info("API GET ONE response", extra={"url": url, "status_code": resp.status_code})
        resp.raise_for_status()
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


