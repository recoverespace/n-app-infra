"""Initialise Metabase instance via HTTP API.

This script creates the first admin user and registers the primary data
warehouse as a source when the Metabase container runs for the first time.
If Metabase has already been configured it exits quietly.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


BASE_URL = _env("METABASE_BASE_URL", "http://metabase:3000").rstrip("/")
ADMIN_EMAIL = _env("METABASE_ADMIN_EMAIL")
ADMIN_PASSWORD = _env("METABASE_ADMIN_PASSWORD")
ADMIN_FIRST = _env("METABASE_ADMIN_FIRST_NAME", "Admin")
ADMIN_LAST = _env("METABASE_ADMIN_LAST_NAME", "User")
SITE_NAME = _env("METABASE_SITE_NAME", "Recovered")
DB_ENGINE = _env("METABASE_DATA_DB_ENGINE", "postgres")
DB_NAME = _env("METABASE_DATA_DB_NAME", "metabase")
DB_HOST = _env("METABASE_DATA_DB_HOST", "postgres")
DB_PORT = int(_env("METABASE_DATA_DB_PORT", "5432"))
DB_USER = _env("METABASE_DATA_DB_USER", "postgres")
DB_PASS = _env("METABASE_DATA_DB_PASSWORD", "postgres")
DB_SSL = _env("METABASE_DATA_DB_SSL", "false").lower() == "true"


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    for attempt in range(10):
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                content = response.read()
                if not content:
                    return {}
                return json.loads(content.decode("utf-8"))
        except urllib.error.URLError as exc:
            if attempt == 9:
                raise
            time.sleep(3)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Unable to parse response from {url}: {exc}") from exc

    raise RuntimeError(f"Failed to call {url}")


def main() -> int:
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("Metabase init skipped: admin email/password not provided", file=sys.stderr)
        return 0

    if len(ADMIN_PASSWORD) < 8:
        print("Metabase init aborted: admin password must be at least 8 characters", file=sys.stderr)
        return 1

    try:
        properties = _request("GET", "/api/session/properties")
    except Exception as exc:  # pragma: no cover - startup guard
        print(f"Failed to query Metabase properties: {exc}", file=sys.stderr)
        return 1

    token = properties.get("setup-token")
    is_setup = properties.get("is-setup", False)

    if is_setup or not token:
        print("Metabase already configured; skipping init")
        return 0

    payload = {
        "token": token,
        "user": {
            "first_name": ADMIN_FIRST,
            "last_name": ADMIN_LAST,
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "password_confirm": ADMIN_PASSWORD,
        },
        "prefs": {
            "site_name": SITE_NAME,
            "site_locale": "en",
            "allow_tracking": False,
        },
        "database": {
            "engine": DB_ENGINE,
            "name": "Recovered Database",
            "details": {
                "host": DB_HOST,
                "port": DB_PORT,
                "dbname": DB_NAME,
                "user": DB_USER,
                "password": DB_PASS,
                "ssl": DB_SSL,
            },
        },
    }

    try:
        _request("POST", "/api/setup", payload)
    except Exception as exc:  # pragma: no cover - startup guard
        print(f"Metabase setup failed: {exc}", file=sys.stderr)
        return 1

    print("Metabase initial setup completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
