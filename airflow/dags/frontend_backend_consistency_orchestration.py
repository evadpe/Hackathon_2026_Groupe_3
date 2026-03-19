import pendulum
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException

from common.project_api import (
    BACKEND_API_URL,
    FRONTEND_URL,
    backend_get,
    build_report_metadata,
    iso_utc_now,
    probe_http_service,
    write_report,
)


DAG_ID = "frontend_backend_consistency_orchestration"


@dag(
    dag_id=DAG_ID,
    schedule="*/30 * * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["stepahead", "frontend", "backend", "consistency"],
    doc_md="""
    Validates that the frontend-facing backend queues remain reachable and
    internally consistent for operational users.
    """,
)
def frontend_backend_consistency_orchestration():
    @task
    def probe_backend_service():
        return probe_http_service("backend", f"{BACKEND_API_URL}/health")

    @task
    def probe_frontend_service():
        return probe_http_service("frontend", FRONTEND_URL)

    @task
    def fetch_operational_data(backend_probe: dict):
        if not backend_probe["ok"]:
            return {
                "available": False,
                "error": "Backend health endpoint is unavailable.",
            }

        pending_documents = backend_get("/documents/pending")
        gold_documents = backend_get("/documents/gold")
        overview = backend_get("/orchestration/overview")
        review_queue = backend_get("/orchestration/review-queue")

        return {
            "available": True,
            "pendingDocuments": pending_documents,
            "goldDocuments": gold_documents,
            "overview": overview,
            "reviewQueue": review_queue,
        }

    @task
    def build_consistency_report(
        backend_probe: dict,
        frontend_probe: dict,
        operational_data: dict,
    ):
        issues = []
        checks = {}

        if not backend_probe["ok"]:
            issues.append("backend_unreachable")
        if not frontend_probe["ok"]:
            issues.append("frontend_unreachable")

        if operational_data.get("available"):
            pending_documents = operational_data["pendingDocuments"]
            gold_documents = operational_data["goldDocuments"]
            overview = operational_data["overview"]
            review_queue = operational_data["reviewQueue"]

            overview_queues = overview.get("queues", {})
            overview_status_counts = overview.get("summary", {}).get(
                "countsByStatus",
                {},
            )

            checks = {
                "pendingCountMatchesOverviewQueue": (
                    len(pending_documents) == overview_queues.get("silver", 0)
                ),
                "pendingCountMatchesOverviewSummary": (
                    len(pending_documents)
                    == overview_status_counts.get("silver", 0)
                ),
                "goldCountMatchesOverviewQueue": (
                    len(gold_documents) == overview_queues.get("gold", 0)
                ),
                "goldCountMatchesOverviewSummary": (
                    len(gold_documents) == overview_status_counts.get("gold", 0)
                ),
                "reviewQueueMatchesPending": (
                    review_queue.get("queueSize", 0) == len(pending_documents)
                ),
            }

            if not checks["pendingCountMatchesOverviewQueue"]:
                issues.append("silver_queue_mismatch")
            if not checks["pendingCountMatchesOverviewSummary"]:
                issues.append("silver_summary_mismatch")
            if not checks["goldCountMatchesOverviewQueue"]:
                issues.append("gold_queue_mismatch")
            if not checks["goldCountMatchesOverviewSummary"]:
                issues.append("gold_summary_mismatch")
            if not checks["reviewQueueMatchesPending"]:
                issues.append("review_queue_mismatch")
        else:
            checks = {
                "pendingCountMatchesOverviewQueue": False,
                "pendingCountMatchesOverviewSummary": False,
                "goldCountMatchesOverviewQueue": False,
                "goldCountMatchesOverviewSummary": False,
                "reviewQueueMatchesPending": False,
            }
            issues.append("backend_operational_data_unavailable")

        payload = {
            "metadata": build_report_metadata(
                "frontend_backend_consistency",
                DAG_ID,
            ),
            "summary": {
                "generatedAt": iso_utc_now(),
                "frontendAvailable": frontend_probe["ok"],
                "backendAvailable": backend_probe["ok"],
                "operationalDataAvailable": operational_data.get(
                    "available",
                    False,
                ),
                "consistencyStatus": "consistent" if not issues else "inconsistent",
                "issueCount": len(issues),
            },
            "checks": checks,
            "frontend": frontend_probe,
            "backend": backend_probe,
            "issueCodes": issues,
            "operationalData": (
                {
                    "queueSizes": operational_data["overview"].get("queues", {}),
                    "reviewQueuePreview": operational_data["reviewQueue"].get(
                        "documents",
                        [],
                    )[:10],
                    "pendingPreview": operational_data["pendingDocuments"][:10],
                    "goldPreview": operational_data["goldDocuments"][:10],
                }
                if operational_data.get("available")
                else {"error": operational_data.get("error")}
            ),
        }
        report_path = write_report("frontend_backend_consistency", payload)
        return {"reportPath": report_path, "issues": issues}

    @task
    def assert_consistency(result: dict):
        if result["issues"]:
            raise AirflowException(
                "Frontend/backend consistency checks failed: "
                + ", ".join(result["issues"])
            )
        return result["reportPath"]

    backend_probe = probe_backend_service()
    frontend_probe = probe_frontend_service()
    operational_data = fetch_operational_data(backend_probe)
    assert_consistency(
        build_consistency_report(
            backend_probe,
            frontend_probe,
            operational_data,
        )
    )


frontend_backend_consistency_orchestration()
