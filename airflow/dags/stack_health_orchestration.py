import pendulum
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException

from common.project_api import (
    BACKEND_API_URL,
    FRONTEND_URL,
    MINIO_HEALTHCHECK_URL,
    backend_get,
    build_report_metadata,
    iso_utc_now,
    probe_http_service,
    write_report,
)


DAG_ID = "stack_health_orchestration"


@dag(
    dag_id=DAG_ID,
    schedule="*/10 * * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["stepahead", "platform", "health"],
    doc_md="""
    Monitors the full platform by checking backend, frontend and MinIO,
    then enriches the report with orchestration metrics exposed by the backend.
    """,
)
def stack_health_orchestration():
    @task
    def probe_backend_service():
        return probe_http_service("backend", f"{BACKEND_API_URL}/health")

    @task
    def probe_frontend_service():
        return probe_http_service("frontend", FRONTEND_URL)

    @task
    def probe_minio_service():
        return probe_http_service("minio", MINIO_HEALTHCHECK_URL)

    @task
    def fetch_orchestration_overview(backend_probe: dict):
        if not backend_probe["ok"]:
            return {
                "available": False,
                "error": "Backend health endpoint is unavailable.",
            }

        return {
            "available": True,
            "data": backend_get("/orchestration/overview"),
        }

    @task
    def build_stack_report(
        backend_probe: dict,
        frontend_probe: dict,
        minio_probe: dict,
        overview: dict,
    ):
        services = [backend_probe, frontend_probe, minio_probe]
        unhealthy_services = [
            service["service"] for service in services if not service["ok"]
        ]
        overall_status = "healthy" if not unhealthy_services else "degraded"

        payload = {
            "metadata": build_report_metadata("stack_health", DAG_ID),
            "summary": {
                "generatedAt": iso_utc_now(),
                "overallStatus": overall_status,
                "monitoredServices": len(services),
                "unhealthyServices": unhealthy_services,
                "orchestrationOverviewAvailable": overview.get("available", False),
            },
            "services": {
                "backend": backend_probe,
                "frontend": frontend_probe,
                "minio": minio_probe,
            },
            "orchestrationOverview": overview.get("data"),
            "errors": [overview["error"]] if not overview.get("available") else [],
        }
        report_path = write_report("stack_health", payload)
        return {
            "reportPath": report_path,
            "overallStatus": overall_status,
            "unhealthyServices": unhealthy_services,
        }

    @task
    def assert_stack_health(report_result: dict):
        if report_result["overallStatus"] != "healthy":
            raise AirflowException(
                "Platform healthcheck failed for services: "
                + ", ".join(report_result["unhealthyServices"])
            )
        return report_result["reportPath"]

    backend_probe = probe_backend_service()
    frontend_probe = probe_frontend_service()
    minio_probe = probe_minio_service()
    overview = fetch_orchestration_overview(backend_probe)
    assert_stack_health(
        build_stack_report(
            backend_probe,
            frontend_probe,
            minio_probe,
            overview,
        )
    )


stack_health_orchestration()
