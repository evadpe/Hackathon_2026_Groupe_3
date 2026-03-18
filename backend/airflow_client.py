import base64
import json
import os
from urllib import error, request


class AirflowTriggerError(RuntimeError):
    pass


def is_airflow_enabled() -> bool:
    return os.getenv("PIPELINE_ORCHESTRATOR", "sync").strip().lower() == "airflow"


def _build_headers() -> dict[str, str]:
    username = os.getenv("AIRFLOW_USERNAME", "airflow")
    password = os.getenv("AIRFLOW_PASSWORD", "airflow")
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def trigger_document_pipeline(session_id: str, stored_files: list[dict[str, str]]) -> str:
    base_url = os.getenv("AIRFLOW_API_URL", "http://airflow-webserver:8080")
    dag_id = os.getenv("AIRFLOW_DAG_ID", "document_ingestion_pipeline")
    url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns"

    dag_run_id = f"session-{session_id}"
    payload = json.dumps(
        {
            "dag_run_id": dag_run_id,
            "conf": {
                "session_id": session_id,
                "files": stored_files,
            },
        }
    ).encode("utf-8")

    req = request.Request(url=url, data=payload, headers=_build_headers(), method="POST")
    try:
        with request.urlopen(req, timeout=15) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise AirflowTriggerError(
            f"Echec du declenchement Airflow ({exc.code}): {details}"
        ) from exc
    except error.URLError as exc:
        raise AirflowTriggerError(f"Airflow indisponible: {exc.reason}") from exc

    return response_payload.get("dag_run_id", dag_run_id)
