import os
from datetime import datetime, timedelta, timezone

import pendulum
from airflow.decorators import dag, task

from common.project_api import (
    build_report_metadata,
    iso_utc_now,
    backend_get,
    require_backend_healthy,
    write_report,
)


DAG_ID = "silver_validation_followup"
STALE_THRESHOLD_HOURS = int(os.getenv("AIRFLOW_SILVER_STALE_HOURS", "12"))


def _parse_iso_date(raw_value: str) -> datetime:
    normalized = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@dag(
    dag_id=DAG_ID,
    schedule="0 * * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["stepahead", "silver", "validation"],
    doc_md="""
    Detects documents that remain too long in the silver zone and prepares a
    follow-up report for operators.
    """,
)
def silver_validation_followup():
    @task
    def check_backend_health():
        return require_backend_healthy()

    @task
    def fetch_stale_documents(_: dict):
        return backend_get("/orchestration/stale-documents")

    @task
    def detect_stale_documents(stale_documents_payload: dict):
        if stale_documents_payload.get("documents") is not None:
            return {
                "documents": stale_documents_payload.get("documents", []),
                "summary": {
                    "staleCount": stale_documents_payload.get("staleCount", 0),
                    "staleThresholdHours": stale_documents_payload.get(
                        "staleThresholdHours",
                        STALE_THRESHOLD_HOURS,
                    ),
                    "staleByType": {},
                    "staleWithBlockingAnomalies": 0,
                    "documentsMissingUploadDate": 0,
                },
            }

        now_utc = datetime.now(timezone.utc)
        stale_threshold = timedelta(hours=STALE_THRESHOLD_HOURS)
        stale_documents = []
        stale_by_type = {}
        stale_with_blocking_anomalies = 0
        stale_with_missing_dates = 0

        for document in pending_documents:
            upload_date = document.get("uploadDate")
            if not upload_date:
                stale_with_missing_dates += 1
                continue

            age = now_utc - _parse_iso_date(upload_date)
            if age >= stale_threshold:
                doc_type = document.get("type", "unknown")
                anomaly_count = len(document.get("anomalies", []))
                has_blocking_anomaly = any(
                    anomaly.get("severity") == "error"
                    for anomaly in document.get("anomalies", [])
                )

                stale_documents.append(
                    {
                        "id": document.get("id"),
                        "filename": document.get("filename"),
                        "type": doc_type,
                        "status": document.get("status"),
                        "ageHours": round(age.total_seconds() / 3600, 2),
                        "anomalyCount": anomaly_count,
                        "hasBlockingAnomaly": has_blocking_anomaly,
                    }
                )
                stale_by_type[doc_type] = stale_by_type.get(doc_type, 0) + 1
                if has_blocking_anomaly:
                    stale_with_blocking_anomalies += 1

        stale_documents.sort(
            key=lambda document: document["ageHours"],
            reverse=True,
        )
        result = {
            "documents": stale_documents,
            "summary": {
                "staleCount": len(stale_documents),
                "staleThresholdHours": STALE_THRESHOLD_HOURS,
                "staleByType": stale_by_type,
                "staleWithBlockingAnomalies": stale_with_blocking_anomalies,
                "documentsMissingUploadDate": stale_with_missing_dates,
            },
        }
        return result

    @task
    def generate_followup_report(health_status: dict, stale_analysis: dict):
        stale_by_type = {}
        stale_with_blocking_anomalies = 0
        for document in stale_analysis["documents"]:
            doc_type = document.get("type", "unknown")
            stale_by_type[doc_type] = stale_by_type.get(doc_type, 0) + 1
            if document.get("hasBlockingAnomalies"):
                stale_with_blocking_anomalies += 1

        payload = {
            "metadata": build_report_metadata(
                "silver_followup",
                DAG_ID,
                {"staleThresholdHours": STALE_THRESHOLD_HOURS},
            ),
            "backend": health_status,
            "summary": {
                "generatedAt": iso_utc_now(),
                **stale_analysis["summary"],
                "staleByType": stale_by_type,
                "staleWithBlockingAnomalies": stale_with_blocking_anomalies,
            },
            "documents": stale_analysis["documents"],
        }
        return write_report("silver_followup", payload)

    health_status = check_backend_health()
    stale_documents_payload = fetch_stale_documents(health_status)
    stale_analysis = detect_stale_documents(stale_documents_payload)
    generate_followup_report(health_status, stale_analysis)


silver_validation_followup()
