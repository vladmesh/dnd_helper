from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, Dict, List


def run_curl(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def curl_get_json(base_url: str, path: str) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    result = run_curl(["curl", "-sS", url])
    if result.returncode != 0:
        print(f"GET {url} failed: {result.stderr}", file=sys.stderr)
        raise SystemExit(result.returncode)
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        print(f"GET {url} invalid JSON: {exc}\nBody: {result.stdout}", file=sys.stderr)
        raise SystemExit(1) from exc


def curl_post_json(base_url: str, path: str, payload: Dict[str, Any]) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload, ensure_ascii=False)
    result = run_curl([
        "curl",
        "-sS",
        "-H",
        "Content-Type: application/json",
        "-X",
        "POST",
        "-d",
        data,
        url,
    ])
    if result.returncode != 0:
        print(f"POST {url} failed: {result.stderr}", file=sys.stderr)
        raise SystemExit(result.returncode)
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        print(f"POST {url} invalid JSON: {exc}\nBody: {result.stdout}", file=sys.stderr)
        raise SystemExit(1) from exc


