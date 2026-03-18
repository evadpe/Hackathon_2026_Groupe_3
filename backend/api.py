"""
API FastAPI — Pont entre le backend de vérification et le frontend Next.js.

Cette version introduit une vraie couche de stockage pour supporter :
- mode local : `backend/data_lake/...`
- mode HDFS  : `HDFS_BASE_PATH/...`

Organisation logique :
- bronze/raw            : fichiers source uploadés
- silver/extracted      : données OCR/extractées en attente
- gold/validated        : données validées/corrigées
- metadata/documents    : catalogues et métadonnées des documents
"""

import json
import mimetypes
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from airflow_client import is_airflow_enabled
from models import BonCommande, Devis, Facture
from ocr_engine import pdf_bytes_to_ocr_dict
from pipeline_service import DocumentPipelineService
from run_ocr_test import adapter_ocr
from storage import get_storage
from verifier import VerificateurDocuments

app = FastAPI(title="StepAhead Industries — API Conformité", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = get_storage()
pipeline_service = DocumentPipelineService(storage)
documents_db: Dict[str, dict] = {}

OCR_TYPE_MAP = {
    "Facture": "facture",
    "Bon de Commande": "bon_commande",
    "Devis": "devis",
}

TYPE_TO_FRONTEND = {
    "facture": "invoice",
    "bon_commande": "purchase_order",
    "devis": "quote",
}

NIVEAU_TO_SEVERITY = {
    "ERREUR": "error",
    "AVERTISSEMENT": "warning",
    "INFO": "warning",
}


def _detecter_type(raw: dict) -> str:
    type_ocr = raw.get("metadata", {}).get("type", "")
    return OCR_TYPE_MAP.get(type_ocr, "inconnu")


def _ocr_to_extracted_data(raw: dict, type_frontend: str) -> dict:
    doc_info = raw.get("doc_info", {})
    vendor = raw.get("vendor", {})
    financials = raw.get("financials", {})

    data = {
        "numero": doc_info.get("number", "INCONNU"),
        "date": doc_info.get("date", ""),
        "fournisseur": vendor.get("name", ""),
        "siret": vendor.get("siret", ""),
        "total_ht": financials.get("total_ht", 0.0),
        "tva_taux": financials.get("tva_rate", "20%"),
        "tva_montant": financials.get("tva_amount", 0.0),
        "total_ttc": financials.get("total_ttc", 0.0),
    }

    if type_frontend == "invoice":
        data["echeance"] = doc_info.get("due_date", "")
    elif type_frontend == "quote":
        data["validite"] = doc_info.get("due_date", "")

    return data


def _metadata_path(doc_id: str) -> str:
    return f"metadata/documents/{doc_id}.json"


def _silver_path(doc_id: str) -> str:
    return f"silver/extracted/{doc_id}.json"


def _gold_path(doc_id: str) -> str:
    return f"gold/validated/{doc_id}.json"


def _raw_upload_path(session_id: str, file_key: str) -> str:
    return f"bronze/raw/{session_id}/{file_key}"


def _make_file_url(storage_path: str) -> str:
    return f"/files/{storage_path}"


def _cache_and_save_document(document: dict) -> dict:
    documents_db[document["id"]] = document
    storage.write_json(_metadata_path(document["id"]), document)
    return document


def _require_internal_token(request: Request) -> None:
    expected_token = os.getenv("INTERNAL_API_TOKEN", "").strip()
    if not expected_token:
        return

    provided_token = request.headers.get("X-Internal-Token", "").strip()
    if provided_token != expected_token:
        raise HTTPException(status_code=401, detail="Acces interne non autorise.")


def _persist_silver_document(doc_id: str, raw_ocr: dict, source_path: str) -> str:
    silver_payload = {
        "documentId": doc_id,
        "storedAt": datetime.utcnow().isoformat(),
        "sourcePath": source_path,
        "ocr": raw_ocr,
    }
    return storage.write_json(_silver_path(doc_id), silver_payload)


def _persist_gold_document(doc_id: str, document: dict) -> str:
    gold_payload = {
        "documentId": doc_id,
        "validatedAt": datetime.utcnow().isoformat(),
        "document": document,
    }
    return storage.write_json(_gold_path(doc_id), gold_payload)


def _load_document(doc_id: str) -> dict | None:
    if doc_id in documents_db:
        return documents_db[doc_id]

    metadata_path = _metadata_path(doc_id)
    if not storage.exists(metadata_path):
        return None

    document = storage.read_json(metadata_path)
    documents_db[doc_id] = document
    return document


def _list_documents(status: str | None = None) -> list[dict]:
    documents = []
    for path in storage.list_files("metadata/documents", suffix=".json"):
        try:
            document = storage.read_json(path)
        except Exception as exc:
            print(f"[Storage] Impossible de lire {path}: {exc}")
            continue

        documents_db[document["id"]] = document
        if status is None or document.get("status") == status:
            documents.append(document)

    return sorted(documents, key=lambda doc: doc.get("uploadDate", ""), reverse=True)


def _make_admin_doc(
    doc_id: str,
    filename: str,
    type_frontend: str,
    extracted_data: dict,
    anomalies: list,
    file_url: str,
    raw_path: str,
    silver_path: str | None = None,
    gold_path: str | None = None,
) -> dict:
    return {
        "id": doc_id,
        "filename": filename,
        "fileUrl": file_url,
        "type": type_frontend,
        "status": "silver",
        "uploadDate": datetime.utcnow().isoformat(),
        "extractedData": extracted_data,
        "anomalies": anomalies,
        "storage": {
            "backend": storage.kind,
            "rawPath": raw_path,
            "silverPath": silver_path,
            "goldPath": gold_path,
            "metadataPath": _metadata_path(doc_id),
        },
    }


@app.get("/files/{storage_path:path}")
async def get_stored_file(storage_path: str):
    normalized_path = storage_path.strip("/")
    if not storage.exists(normalized_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable.")

    media_type = mimetypes.guess_type(normalized_path)[0] or "application/octet-stream"
    filename = Path(normalized_path).name
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return Response(content=storage.read_bytes(normalized_path), media_type=media_type, headers=headers)


@app.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    session_id = uuid.uuid4().hex[:8]
    stored_files: List[dict[str, str]] = []

    for upload in files:
        suffix = Path(upload.filename or "file").suffix.lower()
        file_key = f"{uuid.uuid4().hex[:12]}{suffix}"
        content = await upload.read()

        raw_path = storage.write_bytes(_raw_upload_path(session_id, file_key), content)
        filename = upload.filename or file_key
        stored_files.append({"filename": filename, "raw_path": raw_path})

    if is_airflow_enabled():
        pipeline_service.create_pending_session(session_id, stored_files)
        return pipeline_service.build_bronze_placeholders(session_id, stored_files)

    return pipeline_service.process_session_upload(session_id, stored_files)


@app.get("/documents/pending")
async def get_pending_documents():
    return _list_documents(status="silver")


@app.post("/documents/{doc_id}/validate")
@app.put("/documents/{doc_id}/validate")
async def validate_document(doc_id: str, payload: dict[str, Any]):
    document = _load_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' introuvable.")

    corrected_data = payload.get("extractedData", payload)
    document["status"] = "gold"
    document["extractedData"] = corrected_data
    document["anomalies"] = []
    document["validatedAt"] = datetime.utcnow().isoformat()

    gold_storage_path = _persist_gold_document(doc_id, document)
    document["storage"]["goldPath"] = gold_storage_path
    _cache_and_save_document(document)

    return {
        "message": "Document validé et passé en zone Gold.",
        "id": doc_id,
        "document": document,
    }


@app.get("/documents/gold")
async def get_gold_documents():
    return _list_documents(status="gold")


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    document = _load_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' introuvable.")
    return document


@app.get("/internal/pipelines/pending-sessions")
async def get_pending_sessions(request: Request):
    _require_internal_token(request)
    return pipeline_service.list_sessions(status="pending")


@app.post("/internal/pipelines/claim-session")
async def claim_pending_session(payload: dict[str, Any], request: Request):
    _require_internal_token(request)
    session_id = payload.get("sessionId") or payload.get("session_id")
    dag_run_id = payload.get("dagRunId") or payload.get("dag_run_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="sessionId manquant.")

    session_state = pipeline_service.load_session_state(session_id)
    if session_state is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' introuvable.")

    claimed_session = pipeline_service.claim_session(session_id, dag_run_id=dag_run_id)
    return {
        "claimed": claimed_session is not None and claimed_session.get("status") == "processing",
        "session": claimed_session or session_state,
    }


@app.post("/internal/pipelines/process-session")
async def process_pending_session(payload: dict[str, Any], request: Request):
    _require_internal_token(request)
    session_id = payload.get("sessionId") or payload.get("session_id")
    stored_files = payload.get("files") or []
    dag_run_id = payload.get("dagRunId") or payload.get("dag_run_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="sessionId manquant.")
    if not isinstance(stored_files, list) or not stored_files:
        raise HTTPException(status_code=400, detail="files manquant.")

    try:
        documents = pipeline_service.process_session_upload(session_id, stored_files)
        pipeline_service.complete_session(session_id, documents, dag_run_id=dag_run_id)
        return documents
    except Exception as exc:
        pipeline_service.fail_session(session_id, str(exc), dag_run_id=dag_run_id)
        raise HTTPException(
            status_code=500,
            detail=f"Echec du traitement de la session '{session_id}'.",
        ) from exc


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.1.0", "storageBackend": storage.kind}
