import json
import logging
import os
from datetime import datetime, timedelta
from urllib import error, request

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.sensors.python import PythonSensor

logger = logging.getLogger(__name__)

BACKEND_API_URL = Variable.get(
    "backend_api_url",
    default_var=os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000"),
)
BACKEND_INTERNAL_TOKEN = Variable.get(
    "backend_internal_token",
    default_var=os.getenv("INTERNAL_API_TOKEN", ""),
)


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if BACKEND_INTERNAL_TOKEN:
        headers["X-Internal-Token"] = BACKEND_INTERNAL_TOKEN
    return headers


def _get_json(url: str) -> list[dict]:
    req = request.Request(url=url, headers=_headers(), method="GET")
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    req = request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **_headers(),
        },
        method="POST",
    )
    with request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _pending_sessions_url() -> str:
    return f"{BACKEND_API_URL.rstrip('/')}/internal/pipelines/pending-sessions"


def _claim_session_url() -> str:
    return f"{BACKEND_API_URL.rstrip('/')}/internal/pipelines/claim-session"


def _process_session_url() -> str:
    return f"{BACKEND_API_URL.rstrip('/')}/internal/pipelines/process-session"


def _poke_wait_for_pending_session() -> bool:
    try:
        sessions = _get_json(_pending_sessions_url())
    except Exception as exc:
        logger.warning("Impossible de joindre le backend pour les sessions en attente: %s", exc)
        return False

    if sessions:
        logger.info("Sessions en attente detectees: %s", [item.get("sessionId") for item in sessions])
        return True
    return False


default_args = {
    "owner": "ocr-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    dag_id="document_ingestion_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=timedelta(minutes=1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["ocr", "hdfs", "documents", "airflow"],
)
def document_ingestion_pipeline():
    @task()
    def get_backend_access() -> dict:
        return {
            "base_url": BACKEND_API_URL,
            "secured": bool(BACKEND_INTERNAL_TOKEN),
        }

    @task()
    def list_pending_sessions(_: dict) -> list[dict]:
        sessions = _get_json(_pending_sessions_url())
        logger.info("Nombre de sessions en attente: %s", len(sessions))
        return sessions

    @task()
    def claim_session(session: dict) -> dict:
        from airflow.operators.python import get_current_context

        dag_run = get_current_context().get("dag_run")
        dag_run_id = dag_run.run_id if dag_run else None
        claimed = _post_json(
            _claim_session_url(),
            {
                "sessionId": session["sessionId"],
                "dagRunId": dag_run_id,
            },
        )
        logger.info("Claim session %s -> %s", session["sessionId"], claimed.get("claimed"))
        return claimed

    @task()
    def process_session(claim_result: dict) -> dict:
        from airflow.operators.python import get_current_context

        if not claim_result.get("claimed"):
            session = claim_result.get("session", {})
            return {
                "session_id": session.get("sessionId"),
                "documents_created": 0,
                "document_ids": [],
                "processed": False,
            }

        session = claim_result["session"]
        dag_run = get_current_context().get("dag_run")
        dag_run_id = dag_run.run_id if dag_run else None
        documents = _post_json(
            _process_session_url(),
            {
                "sessionId": session["sessionId"],
                "files": session["files"],
                "dagRunId": dag_run_id,
            },
        )
        logger.info(
            "Session %s traitee -> %s document(s)",
            session["sessionId"],
            len(documents),
        )
        return {
            "session_id": session["sessionId"],
            "documents_created": len(documents),
            "document_ids": [doc["id"] for doc in documents],
            "processed": True,
        }

    @task()
    def summarize(results: list[dict] | None = None) -> dict:
        results = results or []
        processed = [result for result in results if result.get("processed")]
        total_documents = sum(result.get("documents_created", 0) for result in processed)
        summary = {
            "sessions_processed": len(processed),
            "documents_created": total_documents,
            "session_ids": [result.get("session_id") for result in processed],
        }
        logger.info("Resume pipeline: %s", summary)
        return summary

    start = EmptyOperator(task_id="start")

    wait_for_pending_session = PythonSensor(
        task_id="wait_for_pending_session",
        python_callable=_poke_wait_for_pending_session,
        poke_interval=30,
        timeout=60 * 60,
        mode="poke",
    )

    access = get_backend_access()
    sessions = list_pending_sessions(access)
    claimed_sessions = claim_session.expand(session=sessions)
    processed_sessions = process_session.expand(claim_result=claimed_sessions)
    summary = summarize(processed_sessions)

    end = EmptyOperator(task_id="end")

    start >> wait_for_pending_session >> access >> sessions
    sessions >> claimed_sessions >> processed_sessions >> summary >> end


document_ingestion_pipeline()
