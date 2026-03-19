import pendulum
from airflow.decorators import dag, task

from common.project_api import (
    build_report_metadata,
    iso_utc_now,
    backend_get,
    require_backend_healthy,
    write_report,
)


DAG_ID = "gold_publication_orchestration"


@dag(
    dag_id=DAG_ID,
    schedule="0 7 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["stepahead", "gold", "crm"],
    doc_md="""
    Builds a daily manifest of validated gold documents ready for downstream
    CRM or ERP integrations.
    """,
)
def gold_publication_orchestration():
    @task
    def check_backend_health():
        return require_backend_healthy()

    @task
    def fetch_publication_summary(_: dict):
        return backend_get("/orchestration/publication-summary")

    @task
    def build_gold_manifest(health_status: dict, publication_summary: dict):
        payload = {
            "metadata": build_report_metadata("gold_manifest", DAG_ID),
            "backend": health_status,
            "summary": {
                "generatedAt": iso_utc_now(),
                "documentCount": publication_summary.get("documentCount", 0),
                "countsByType": publication_summary.get("countsByType", {}),
                "totalAmountTtc": publication_summary.get("totalAmountTtc", 0),
            },
            "documents": publication_summary.get("documents", []),
        }
        return write_report("gold_manifest", payload)

    health_status = check_backend_health()
    publication_summary = fetch_publication_summary(health_status)
    build_gold_manifest(health_status, publication_summary)


gold_publication_orchestration()
