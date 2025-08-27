import os
from typing import Any, Dict, List

import httpx


API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")


async def api_get(path: str) -> List[Dict[str, Any]]:
    url = f"{API_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def api_get_one(path: str) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


