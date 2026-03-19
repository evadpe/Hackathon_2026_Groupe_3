import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from airflow.exceptions import AirflowException


LOGGER = logging.getLogger(__name__)
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://backend:8000").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://frontend:3000").rstrip("/")
MINIO_HEALTHCHECK_URL = os.getenv(
    "MINIO_HEALTHCHECK_URL",
    "http://minio:9000/minio/health/live",
)
REPORTS_DIR = Path(os.getenv("AIRFLOW_REPORTS_DIR", "/opt/airflow/logs/reports"))
REQUEST_TIMEOUT = int(os.getenv("AIRFLOW_REQUEST_TIMEOUT_SECONDS", "30"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def fetch_json(url: str) -> dict | list:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise AirflowException(
            f"Unable to reach JSON endpoint '{url}': {exc}"
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise AirflowException(
            f"Endpoint '{url}' did not return valid JSON."
        ) from exc


def backend_get(path: str) -> dict | list:
    return fetch_json(f"{BACKEND_API_URL}{path}")


def backend_get_many(paths: dict[str, str]) -> dict[str, dict | list]:
    return {
        alias: backend_get(path)
        for alias, path in paths.items()
    }


def probe_http_service(
    service_name: str,
    url: str,
    expected_status: int = 200,
    allow_redirects: bool = True,
) -> dict[str, Any]:
    started_at = time.monotonic()

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=allow_redirects,
        )
        latency_ms = round((time.monotonic() - started_at) * 1000, 2)
    except requests.RequestException as exc:
        return {
            "service": service_name,
            "url": url,
            "ok": False,
            "statusCode": None,
            "latencyMs": round((time.monotonic() - started_at) * 1000, 2),
            "error": str(exc),
        }

    response_preview = response.text.strip().replace("\n", " ")[:160]
    return {
        "service": service_name,
        "url": url,
        "ok": response.status_code == expected_status,
        "statusCode": response.status_code,
        "latencyMs": latency_ms,
        "responsePreview": response_preview,
    }


def require_http_service(
    service_name: str,
    url: str,
    expected_status: int = 200,
    allow_redirects: bool = True,
) -> dict[str, Any]:
    probe = probe_http_service(
        service_name,
        url,
        expected_status=expected_status,
        allow_redirects=allow_redirects,
    )
    if not probe["ok"]:
        raise AirflowException(
            f"Service '{service_name}' is unhealthy: {probe}"
        )
    LOGGER.info("%s healthcheck succeeded: %s", service_name, probe)
    return probe


def require_backend_healthy() -> dict[str, Any]:
    health = backend_get("/health")
    status = str(health.get("status", "")).lower()
    if status != "ok":
        raise AirflowException(
            f"Backend healthcheck returned an unexpected status: {health}"
        )

    LOGGER.info("Backend healthcheck succeeded: %s", health)
    return health


def require_frontend_healthy() -> dict[str, Any]:
    return require_http_service("frontend", FRONTEND_URL)


def require_minio_healthy() -> dict[str, Any]:
    return require_http_service("minio", MINIO_HEALTHCHECK_URL)


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def sanitize_report_prefix(prefix: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", prefix).strip("_")
    return normalized or "report"


def build_report_metadata(report_name: str, source_dag: str, extra: dict | None = None) -> dict:
    metadata = {
        "reportName": report_name,
        "sourceDag": source_dag,
        "generatedAt": iso_utc_now(),
        "backendApiUrl": BACKEND_API_URL,
    }
    if extra:
        metadata.update(extra)
    return metadata


def write_report(prefix: str, payload: dict) -> str:
    ensure_reports_dir()
    timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    output_path = REPORTS_DIR / f"{sanitize_report_prefix(prefix)}_{timestamp}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    LOGGER.info("Report written to %s", output_path)
    return str(output_path)
