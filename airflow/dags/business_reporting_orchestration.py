import pendulum
from airflow.decorators import dag, task

from common.project_api import (
    backend_get_many,
    build_report_metadata,
    iso_utc_now,
    require_backend_healthy,
    write_report,
)


DAG_ID = "business_reporting_orchestration"


@dag(
    dag_id=DAG_ID,
    schedule="30 7 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["stepahead", "business", "reporting"],
    doc_md="""
    Produces a daily business report based on the orchestration endpoints
    exposed by the backend for Airflow.
    """,
)
def business_reporting_orchestration():
    @task
    def check_backend_health():
        return require_backend_healthy()

    @task
    def fetch_reporting_data(_: dict):
        return backend_get_many(
            {
                "businessMetrics": "/orchestration/business-metrics",
                "publicationSummary": "/orchestration/publication-summary",
                "overview": "/orchestration/overview",
            }
        )

    @task
    def build_business_report(health_status: dict, reporting_data: dict):
        business_metrics = reporting_data["businessMetrics"]
        publication_summary = reporting_data["publicationSummary"]
        overview = reporting_data["overview"]

        payload = {
            "metadata": build_report_metadata("business_reporting", DAG_ID),
            "backend": health_status,
            "summary": {
                "generatedAt": iso_utc_now(),
                "pendingDocuments": business_metrics.get("operational", {}).get(
                    "pendingDocuments",
                    0,
                ),
                "goldDocuments": business_metrics.get("operational", {}).get(
                    "goldDocuments",
                    0,
                ),
                "stalePendingDocuments": business_metrics.get(
                    "operational",
                    {},
                ).get("stalePendingDocuments", 0),
                "documentsWithErrors": business_metrics.get("operational", {}).get(
                    "documentsWithErrors",
                    0,
                ),
                "documentsWithWarnings": business_metrics.get(
                    "operational",
                    {},
                ).get("documentsWithWarnings", 0),
                "goldAmountTtc": business_metrics.get("financial", {}).get(
                    "goldAmountTtc",
                    0,
                ),
                "publishedDocumentCount": publication_summary.get(
                    "documentCount",
                    0,
                ),
            },
            "financial": business_metrics.get("financial", {}),
            "queues": overview.get("queues", {}),
            "publication": publication_summary,
            "reviewQueuePreview": business_metrics.get("queues", {}).get(
                "reviewQueuePreview",
                [],
            ),
        }
        return write_report("business_reporting", payload)

    health_status = check_backend_health()
    reporting_data = fetch_reporting_data(health_status)
    build_business_report(health_status, reporting_data)


business_reporting_orchestration()
