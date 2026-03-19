from datetime import datetime, timezone

import pendulum
from airflow.decorators import dag, task

from common.project_api import (
    build_report_metadata,
    iso_utc_now,
    backend_get,
    require_backend_healthy,
    write_report,
)


DAG_ID = "bronze_to_silver_orchestration"
STALE_THRESHOLD_HOURS = 12


def _parse_iso_date(raw_value: str) -> datetime | None:
    if not raw_value:
        return None

    normalized = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@dag(
    dag_id=DAG_ID,
    schedule="*/15 * * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["stepahead", "bronze", "silver"],
    doc_md="""
    Checks the ingestion pipeline and creates a snapshot of documents waiting
    for manual validation in the silver zone.
    """,
)
def bronze_to_silver_orchestration():
    @task
    def check_backend_health():
        return require_backend_healthy()

    @task
    def fetch_review_queue(_: dict):
        return backend_get("/orchestration/review-queue")

    @task
    def build_pending_snapshot(health_status: dict, review_queue_payload: dict):
        pending_documents = review_queue_payload.get("documents", [])
        counts_by_type = {}
        status_breakdown = {}
        total_anomalies = 0
        blocking_documents = 0
        warning_documents = 0
        now_utc = datetime.now(timezone.utc)
        oldest_pending_hours = 0.0
        stale_documents = 0
        documents_sample = []

        for document in pending_documents:
            doc_type = document.get("type", "unknown")
            doc_status = document.get("status", "unknown")
            counts_by_type[doc_type] = counts_by_type.get(doc_type, 0) + 1
            status_breakdown[doc_status] = status_breakdown.get(doc_status, 0) + 1

            total_anomalies += document.get("anomalyCount", 0)
            has_blocking_anomaly = document.get("hasBlockingAnomalies", False)
            has_warning_anomaly = (
                document.get("severity") == "warning" and not has_blocking_anomaly
            )

            if has_blocking_anomaly:
                blocking_documents += 1
            elif has_warning_anomaly:
                warning_documents += 1

            age_hours = document.get("ageHours")
            if age_hours is None:
                upload_date = _parse_iso_date(document.get("uploadDate"))
                if upload_date:
                    age_hours = round(
                        (now_utc - upload_date).total_seconds() / 3600,
                        2,
                    )
            if age_hours is not None:
                oldest_pending_hours = max(oldest_pending_hours, age_hours)
                if age_hours >= STALE_THRESHOLD_HOURS:
                    stale_documents += 1

            documents_sample.append(
                {
                    "id": document.get("id"),
                    "filename": document.get("filename"),
                    "type": doc_type,
                    "status": doc_status,
                    "ageHours": age_hours,
                    "anomalyCount": document.get("anomalyCount", 0),
                    "hasBlockingAnomaly": has_blocking_anomaly,
                }
            )

        documents_sample.sort(
            key=lambda document: document["ageHours"] or 0,
            reverse=True,
        )

        payload = {
            "metadata": build_report_metadata(
                "silver_snapshot",
                DAG_ID,
                {"staleThresholdHours": STALE_THRESHOLD_HOURS},
            ),
            "backend": health_status,
            "summary": {
                "generatedAt": iso_utc_now(),
                "pendingCount": review_queue_payload.get("queueSize", len(pending_documents)),
                "countsByType": counts_by_type,
                "countsByStatus": status_breakdown,
                "documentsWithBlockingAnomalies": blocking_documents,
                "documentsWithWarningsOnly": warning_documents,
                "totalAnomalies": total_anomalies,
                "oldestPendingHours": oldest_pending_hours,
                "staleDocuments": stale_documents,
            },
            "documentsSample": documents_sample[:10],
        }
        return write_report("silver_snapshot", payload)

    health_status = check_backend_health()
    review_queue_payload = fetch_review_queue(health_status)
    build_pending_snapshot(health_status, review_queue_payload)


bronze_to_silver_orchestration()
