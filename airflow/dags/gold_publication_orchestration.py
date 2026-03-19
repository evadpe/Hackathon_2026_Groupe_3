from datetime import datetime, timezone

import pendulum
from airflow.decorators import dag, task

from common.project_api import backend_get, write_report


@dag(
    dag_id="gold_publication_orchestration",
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
    def fetch_gold_documents():
        return backend_get("/documents/gold")

    @task
    def build_gold_manifest(gold_documents: list[dict]):
        payload = {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "documentCount": len(gold_documents),
            "documents": [
                {
                    "id": document.get("id"),
                    "filename": document.get("filename"),
                    "type": document.get("type"),
                    "fileUrl": document.get("fileUrl"),
                    "validatedAt": document.get("uploadDate"),
                }
                for document in gold_documents
            ],
        }
        return write_report("gold_manifest", payload)

    build_gold_manifest(fetch_gold_documents())


gold_publication_orchestration()
