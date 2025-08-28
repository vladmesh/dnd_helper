import os
import logging
from typing import Any, Dict, List

import httpx


API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
logger = logging.getLogger(__name__)


async def api_get(path: str) -> List[Dict[str, Any]]:
    url = f"{API_BASE_URL}{path}"
    logger.info("API GET", extra={"url": url})
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        logger.info("API GET response", extra={"url": url, "status_code": resp.status_code})
        resp.raise_for_status()
        return resp.json()


async def api_get_one(path: str) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    logger.info("API GET ONE", extra={"url": url})
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        logger.info("API GET ONE response", extra={"url": url, "status_code": resp.status_code})
        resp.raise_for_status()
        return resp.json()


