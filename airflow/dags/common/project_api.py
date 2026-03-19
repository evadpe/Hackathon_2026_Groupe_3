import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests


BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://backend:8000")
REPORTS_DIR = Path(os.getenv("AIRFLOW_REPORTS_DIR", "/opt/airflow/logs/reports"))


def backend_get(path: str) -> dict | list:
    response = requests.get(f"{BACKEND_API_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def write_report(prefix: str, payload: dict) -> str:
    ensure_reports_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = REPORTS_DIR / f"{prefix}_{timestamp}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logging.info("Report written to %s", output_path)
    return str(output_path)
