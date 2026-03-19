from datetime import datetime

import pendulum
from airflow.decorators import dag, task

from common.project_api import backend_get, write_report


@dag(
    dag_id="bronze_to_silver_orchestration",
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
        return backend_get("/health")

    @task
    def fetch_pending_documents():
        return backend_get("/documents/pending")

    @task
    def build_pending_snapshot(health_status: dict, pending_documents: list[dict]):
        counts_by_type = {}
        error_documents = 0

        for document in pending_documents:
            doc_type = document.get("type", "unknown")
            counts_by_type[doc_type] = counts_by_type.get(doc_type, 0) + 1
            if any(
                anomaly.get("severity") == "error"
                for anomaly in document.get("anomalies", [])
            ):
                error_documents += 1

        payload = {
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "backend": health_status,
            "pendingCount": len(pending_documents),
            "countsByType": counts_by_type,
            "documentsWithBlockingAnomalies": error_documents,
        }
        return write_report("silver_snapshot", payload)

    health_status = check_backend_health()
    pending_documents = fetch_pending_documents()
    build_pending_snapshot(health_status, pending_documents)


bronze_to_silver_orchestration()
