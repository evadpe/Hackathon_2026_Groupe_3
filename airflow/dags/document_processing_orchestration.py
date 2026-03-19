import pendulum
from airflow.decorators import dag, task

from common.project_api import (
    backend_get_many,
    build_report_metadata,
    iso_utc_now,
    require_backend_healthy,
    write_report,
)


DAG_ID = "document_processing_orchestration"


@dag(
    dag_id=DAG_ID,
    schedule="*/20 * * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["stepahead", "documents", "operations"],
    doc_md="""
    Consolidates the operational document queues exposed by the backend and
    produces a report for Airflow-driven orchestration and follow-up.
    """,
)
def document_processing_orchestration():
    @task
    def check_backend_health():
        return require_backend_healthy()

    @task
    def fetch_orchestration_data(_: dict):
        return backend_get_many(
            {
                "overview": "/orchestration/overview",
                "reviewQueue": "/orchestration/review-queue",
                "staleDocuments": "/orchestration/stale-documents",
            }
        )

    @task
    def build_document_processing_report(health_status: dict, orchestration_data: dict):
        overview = orchestration_data["overview"]
        review_queue = orchestration_data["reviewQueue"]
        stale_documents = orchestration_data["staleDocuments"]

        payload = {
            "metadata": build_report_metadata(
                "document_processing",
                DAG_ID,
                {
                    "staleThresholdHours": stale_documents.get(
                        "staleThresholdHours",
                    ),
                },
            ),
            "backend": health_status,
            "summary": {
                "generatedAt": iso_utc_now(),
                "queueSizes": overview.get("queues", {}),
                "reviewQueueSize": review_queue.get("queueSize", 0),
                "staleDocuments": stale_documents.get("staleCount", 0),
                "documentsRequiringReview": overview.get("summary", {}).get(
                    "documentsRequiringReview",
                    0,
                ),
                "pendingWithBlockingAnomalies": overview.get("summary", {}).get(
                    "pendingWithBlockingAnomalies",
                    0,
                ),
            },
            "reviewQueuePreview": review_queue.get("documents", [])[:10],
            "staleDocumentsPreview": stale_documents.get("documents", [])[:10],
            "overview": overview,
        }
        return write_report("document_processing", payload)

    health_status = check_backend_health()
    orchestration_data = fetch_orchestration_data(health_status)
    build_document_processing_report(health_status, orchestration_data)


document_processing_orchestration()
