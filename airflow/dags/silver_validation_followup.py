from datetime import datetime, timedelta, timezone

import pendulum
from airflow.decorators import dag, task

from common.project_api import backend_get, write_report


def _parse_iso_date(raw_value: str) -> datetime:
    normalized = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@dag(
    dag_id="silver_validation_followup",
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
    def fetch_pending_documents():
        return backend_get("/documents/pending")

    @task
    def detect_stale_documents(pending_documents: list[dict]):
        now_utc = datetime.now(timezone.utc)
        stale_threshold = timedelta(hours=12)
        stale_documents = []

        for document in pending_documents:
            upload_date = document.get("uploadDate")
            if not upload_date:
                continue

            age = now_utc - _parse_iso_date(upload_date)
            if age >= stale_threshold:
                stale_documents.append(
                    {
                        "id": document.get("id"),
                        "filename": document.get("filename"),
                        "type": document.get("type"),
                        "status": document.get("status"),
                        "ageHours": round(age.total_seconds() / 3600, 2),
                        "anomalyCount": len(document.get("anomalies", [])),
                    }
                )

        return stale_documents

    @task
    def generate_followup_report(stale_documents: list[dict]):
        payload = {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "staleThresholdHours": 12,
            "staleCount": len(stale_documents),
            "documents": stale_documents,
        }
        return write_report("silver_followup", payload)

    pending_documents = fetch_pending_documents()
    stale_documents = detect_stale_documents(pending_documents)
    generate_followup_report(stale_documents)


silver_validation_followup()
