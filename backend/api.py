"""
Point d'entree principal de l'API.
Fait le lien entre le frontend Next.js, le moteur OCR, le verificateur de documents,
la base de donnees SQLite et le stockage MinIO.
"""

import json
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, upsert_document, get_by_status, get_by_id, update_status, update_anomalies
from models import BonCommande, Devis, Facture
from ocr_engine import pdf_to_ocr_dict, image_to_ocr_dict
from run_ocr_test import adapter_ocr
from storage import init_storage, upload_file, upload_json
from verifier import VerificateurDocuments

# Correspondance entre les types OCR et les types internes
OCR_TYPE_MAP = {
    "Facture":         "facture",
    "Bon de Commande": "bon_commande",
    "Devis":           "devis",
}

# Correspondance entre les types internes et les types attendus par le frontend
TYPE_TO_FRONTEND = {
    "facture":      "invoice",
    "bon_commande": "purchase_order",
    "devis":        "quote",
}

# Correspondance entre les niveaux d'alerte Python et les severites JSON
NIVEAU_TO_SEVERITY = {
    "ERREUR":        "error",
    "AVERTISSEMENT": "warning",
    "INFO":          "warning",
}
FRONTEND_ORIGINS = ["http://localhost:3000", "http://localhost:3001"]
ORCHESTRATION_STALE_HOURS = int(os.getenv("ORCHESTRATION_STALE_HOURS", "12"))
SEVERITY_PRIORITY = {"error": 2, "warning": 1, "ok": 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au demarrage : on cree la table SQLite et les buckets MinIO si necessaire
    init_db()
    try:
        init_storage()
        print("[Storage] Buckets MinIO prets (bronze / silver / gold)")
    except Exception as e:
        print(f"[Storage] MinIO non disponible : {e}")
    yield


app = FastAPI(
    title="StepAhead Industries - API Conformite",
    version="2.0.0",
    lifespan=lifespan,
)

# On autorise les requetes depuis le frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _detecter_type(raw: dict) -> str:
    """Lit le champ metadata.type du JSON OCR et retourne le type interne correspondant."""
    type_ocr = raw.get("metadata", {}).get("type", "")
    return OCR_TYPE_MAP.get(type_ocr, "inconnu")


def _ocr_to_extracted_data(raw: dict, type_frontend: str) -> dict:
    """Transforme le JSON brut de l'OCR en un objet plat lisible par le frontend."""
    doc_info   = raw.get("doc_info", {})
    vendor     = raw.get("vendor", {})
    financials = raw.get("financials", {})

    data = {
        "numero":      doc_info.get("number", "INCONNU"),
        "date":        doc_info.get("date", ""),
        "fournisseur": vendor.get("name", ""),
        "siret":       vendor.get("siret", ""),
        "total_ht":    financials.get("total_ht", 0.0),
        "tva_taux":    financials.get("tva_rate", "20%"),
        "tva_montant": financials.get("tva_amount", 0.0),
        "total_ttc":   financials.get("total_ttc", 0.0),
    }

    # Champs supplementaires selon le type de document
    if type_frontend == "invoice":
        data["echeance"] = doc_info.get("due_date", "")
    elif type_frontend == "quote":
        data["validite"] = doc_info.get("due_date", "")

    return data


def _extraction_illisible(extracted_data: dict) -> bool:
    """Retourne True si l'OCR n'a rien extrait d'utile (tout est inconnu ou zéro)."""
    return (
        extracted_data.get("numero", "INCONNU") in ("INCONNU", "Inconnu", "")
        and extracted_data.get("fournisseur", "") in ("Inconnu", "")
        and extracted_data.get("total_ttc", 0.0) == 0.0
    )


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None

    normalized = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _document_age_hours(upload_date: str | None) -> float | None:
    parsed = _parse_iso_datetime(upload_date)
    if not parsed:
        return None
    return round((datetime.now(timezone.utc) - parsed).total_seconds() / 3600, 2)


def _document_severity(anomalies: list[dict]) -> str:
    if any(anomaly.get("severity") == "error" for anomaly in anomalies):
        return "error"
    if any(anomaly.get("severity") == "warning" for anomaly in anomalies):
        return "warning"
    return "ok"


def _make_admin_doc(doc_id, filename, type_frontend, extracted_data, anomalies, file_url) -> dict:
    """Construit le dictionnaire standard AdminDocument attendu par le frontend."""
    return {
        "id":            doc_id,
        "filename":      filename,
        "fileUrl":       file_url,
        "type":          type_frontend,
        "status":        "silver",
        "uploadDate":    datetime.now().isoformat(),
        "extractedData": extracted_data,
        "anomalies":     anomalies,
    }


def _serialize_document_for_orchestration(document: dict) -> dict:
    anomalies = document.get("anomalies", [])
    severity = _document_severity(anomalies)
    age_hours = _document_age_hours(document.get("uploadDate"))

    return {
        "id": document.get("id"),
        "filename": document.get("filename"),
        "type": document.get("type"),
        "status": document.get("status"),
        "uploadDate": document.get("uploadDate"),
        "fileUrl": document.get("fileUrl"),
        "anomalyCount": len(anomalies),
        "severity": severity,
        "ageHours": age_hours,
        "hasBlockingAnomalies": severity == "error",
        "requiresReview": severity != "ok",
    }


def _build_documents_summary(documents: list[dict]) -> dict:
    counts_by_status = {}
    counts_by_type = {}
    counts_by_severity = {}
    pending_with_blocking_anomalies = 0
    documents_requiring_review = 0
    stale_pending_documents = 0
    oldest_pending_hours = 0.0

    for document in documents:
        status = document.get("status", "unknown")
        doc_type = document.get("type", "unknown")
        severity = _document_severity(document.get("anomalies", []))
        age_hours = _document_age_hours(document.get("uploadDate"))

        counts_by_status[status] = counts_by_status.get(status, 0) + 1
        counts_by_type[doc_type] = counts_by_type.get(doc_type, 0) + 1
        counts_by_severity[severity] = counts_by_severity.get(severity, 0) + 1

        if severity != "ok":
            documents_requiring_review += 1

        if status == "silver":
            if severity == "error":
                pending_with_blocking_anomalies += 1
            if age_hours is not None:
                oldest_pending_hours = max(oldest_pending_hours, age_hours)
                if age_hours >= ORCHESTRATION_STALE_HOURS:
                    stale_pending_documents += 1

    return {
        "totalDocuments": len(documents),
        "countsByStatus": counts_by_status,
        "countsByType": counts_by_type,
        "countsBySeverity": counts_by_severity,
        "documentsRequiringReview": documents_requiring_review,
        "pendingWithBlockingAnomalies": pending_with_blocking_anomalies,
        "oldestPendingHours": oldest_pending_hours,
        "stalePendingDocuments": stale_pending_documents,
    }


def _build_review_queue(documents: list[dict]) -> list[dict]:
    queue = [_serialize_document_for_orchestration(document) for document in documents]
    queue.sort(
        key=lambda document: (
            SEVERITY_PRIORITY.get(document["severity"], 0),
            document["ageHours"] or 0,
            document["filename"] or "",
        ),
        reverse=True,
    )
    return queue


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_stale_documents(documents: list[dict]) -> list[dict]:
    stale_documents = []

    for document in documents:
        serialized = _serialize_document_for_orchestration(document)
        age_hours = serialized.get("ageHours")
        if age_hours is None or age_hours < ORCHESTRATION_STALE_HOURS:
            continue
        stale_documents.append(serialized)

    stale_documents.sort(
        key=lambda document: (
            document["ageHours"] or 0,
            SEVERITY_PRIORITY.get(document["severity"], 0),
            document["filename"] or "",
        ),
        reverse=True,
    )
    return stale_documents


def _build_publication_summary(documents: list[dict]) -> dict:
    counts_by_type = {}
    total_amount_ttc = 0.0
    published_documents = []

    for document in documents:
        doc_type = document.get("type", "unknown")
        extracted_data = document.get("extractedData", {})
        total_ttc = _safe_float(extracted_data.get("total_ttc"))

        counts_by_type[doc_type] = counts_by_type.get(doc_type, 0) + 1
        total_amount_ttc += total_ttc
        published_documents.append(
            {
                "id": document.get("id"),
                "filename": document.get("filename"),
                "type": doc_type,
                "status": document.get("status"),
                "uploadDate": document.get("uploadDate"),
                "fileUrl": document.get("fileUrl"),
                "totalTtc": round(total_ttc, 2),
            }
        )

    published_documents.sort(
        key=lambda document: (
            document["type"] or "",
            document["filename"] or "",
        )
    )
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "documentCount": len(documents),
        "countsByType": counts_by_type,
        "totalAmountTtc": round(total_amount_ttc, 2),
        "documents": published_documents,
    }


def _build_business_metrics(pending_documents: list[dict], gold_documents: list[dict]) -> dict:
    pending_amount_ttc = 0.0
    gold_amount_ttc = 0.0
    documents_with_errors = 0
    documents_with_warnings = 0

    for document in pending_documents + gold_documents:
        severity = _document_severity(document.get("anomalies", []))
        if severity == "error":
            documents_with_errors += 1
        elif severity == "warning":
            documents_with_warnings += 1

    for document in pending_documents:
        pending_amount_ttc += _safe_float(document.get("extractedData", {}).get("total_ttc"))

    for document in gold_documents:
        gold_amount_ttc += _safe_float(document.get("extractedData", {}).get("total_ttc"))

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "staleThresholdHours": ORCHESTRATION_STALE_HOURS,
        "operational": {
            "pendingDocuments": len(pending_documents),
            "goldDocuments": len(gold_documents),
            "stalePendingDocuments": len(_build_stale_documents(pending_documents)),
            "documentsWithErrors": documents_with_errors,
            "documentsWithWarnings": documents_with_warnings,
        },
        "financial": {
            "pendingAmountTtc": round(pending_amount_ttc, 2),
            "goldAmountTtc": round(gold_amount_ttc, 2),
            "totalCertifiedAmountTtc": round(gold_amount_ttc, 2),
        },
        "queues": {
            "reviewQueuePreview": _build_review_queue(pending_documents)[:10],
            "publishedPreview": _build_publication_summary(gold_documents)["documents"][:10],
        },
    }


@app.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Recoit un ou plusieurs fichiers PDF ou JSON depuis le frontend.

    Pour chaque fichier :
      - On le stocke dans le bucket bronze (fichier brut)
      - Si c'est un PDF, on lance l'OCR pour en extraire les donnees
      - Si c'est un JSON OCR deja traite, on l'utilise directement

    Si on recoit a la fois un bon de commande et une facture, on lance
    la verification inter-documents pour detecter les anomalies.

    A la fin, les documents sont mis a disposition des DAGs Airflow via les
    endpoints d'orchestration exposes par ce backend.
    """
    session_id    = uuid.uuid4().hex[:8]
    docs_by_type: Dict[str, dict] = {}
    file_urls:    Dict[str, str]  = {}
    created_docs: List[dict]      = []

    for upload in files:
        suffix   = Path(upload.filename or "file").suffix.lower()
        file_key = f"{session_id}_{uuid.uuid4().hex[:6]}{suffix}"
        content  = await upload.read()

        IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

        # On envoie le fichier brut dans le bucket bronze du data lake
        try:
            if suffix == ".pdf":
                content_type = "application/pdf"
            elif suffix in IMAGE_SUFFIXES:
                content_type = f"image/{suffix.lstrip('.')}"
            else:
                content_type = "application/json"
            file_url = upload_file("bronze", file_key, content, content_type)
        except Exception:
            # Si MinIO est indisponible, on garde une URL locale de secours
            file_url = f"/files/{file_key}"

        if suffix == ".json":
            # Fichier JSON : c'est deja un resultat OCR, on le parse directement
            try:
                raw_ocr = json.loads(content)
            except json.JSONDecodeError:
                continue

            type_interne = _detecter_type(raw_ocr)
            if type_interne == "inconnu":
                continue

            docs_by_type[type_interne] = raw_ocr
            file_urls[type_interne]    = file_url

        elif suffix == ".pdf":
            # Fichier PDF : on doit passer par l'OCR pour extraire le texte.
            # EasyOCR a besoin d'un vrai fichier sur le disque, donc on passe
            # par un fichier temporaire qu'on supprime apres.
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                raw_ocr = pdf_to_ocr_dict(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

            if raw_ocr is not None:
                type_interne   = _detecter_type(raw_ocr)
                extracted_data = _ocr_to_extracted_data(raw_ocr, TYPE_TO_FRONTEND.get(type_interne, "invoice"))
                if type_interne != "inconnu" and not _extraction_illisible(extracted_data):
                    docs_by_type[type_interne] = raw_ocr
                    file_urls[type_interne]    = file_url
                else:
                    # OCR a tourné mais n'a rien extrait d'utile : document illisible
                    doc_id    = f"PDF-{session_id}-{uuid.uuid4().hex[:4]}"
                    admin_doc = _make_admin_doc(
                        doc_id, upload.filename or file_key, "invoice",
                        {"note": "Document illisible"},
                        [{"field": "ocr", "message": "Le document est illisible ou pixellise. Veuillez fournir un fichier de meilleure qualite.", "severity": "error"}],
                        file_url,
                    )
                    upsert_document(admin_doc)
                    created_docs.append(admin_doc)
            else:
                # L'OCR a completement echoue
                doc_id    = f"PDF-{session_id}-{uuid.uuid4().hex[:4]}"
                admin_doc = _make_admin_doc(
                    doc_id, upload.filename or file_key, "invoice",
                    {"note": "Document illisible"},
                    [{"field": "ocr", "message": "Le document est illisible ou pixellise. Veuillez fournir un fichier de meilleure qualite.", "severity": "error"}],
                    file_url,
                )
                upsert_document(admin_doc)
                created_docs.append(admin_doc)

        elif suffix in IMAGE_SUFFIXES:
            # Fichier image (PNG, JPG...) : on lance l'OCR directement sans conversion PDF
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                raw_ocr = image_to_ocr_dict(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

            if raw_ocr is not None:
                type_interne   = _detecter_type(raw_ocr)
                extracted_data = _ocr_to_extracted_data(raw_ocr, TYPE_TO_FRONTEND.get(type_interne, "invoice"))
                if type_interne != "inconnu" and not _extraction_illisible(extracted_data):
                    docs_by_type[type_interne] = raw_ocr
                    file_urls[type_interne]    = file_url
                else:
                    doc_id    = f"IMG-{session_id}-{uuid.uuid4().hex[:4]}"
                    admin_doc = _make_admin_doc(
                        doc_id, upload.filename or file_key, "invoice",
                        {"note": "Document illisible"},
                        [{"field": "ocr", "message": "Le document est illisible ou pixellise. Veuillez fournir un fichier de meilleure qualite.", "severity": "error"}],
                        file_url,
                    )
                    upsert_document(admin_doc)
                    created_docs.append(admin_doc)
            else:
                doc_id    = f"IMG-{session_id}-{uuid.uuid4().hex[:4]}"
                admin_doc = _make_admin_doc(
                    doc_id, upload.filename or file_key, "invoice",
                    {"note": "Extraction OCR echouee", "fichier": upload.filename},
                    [{"field": "ocr", "message": "L'OCR n'a pas pu extraire les donnees de l'image.", "severity": "error"}],
                    file_url,
                )
                upsert_document(admin_doc)
                created_docs.append(admin_doc)

    # Pour chaque type de document reconnu, on cree un AdminDocument et on le persiste
    for type_interne, raw_ocr in docs_by_type.items():
        type_frontend  = TYPE_TO_FRONTEND[type_interne]
        doc_id         = f"{type_interne.upper()}-{session_id}"
        extracted_data = _ocr_to_extracted_data(raw_ocr, type_frontend)

        admin_doc = _make_admin_doc(
            doc_id, f"{type_interne}.json", type_frontend,
            extracted_data, [], file_urls.get(type_interne, ""),
        )

        # On archive aussi le JSON extrait dans le bucket silver
        try:
            upload_json("silver", f"{doc_id}.json", extracted_data)
        except Exception:
            pass

        upsert_document(admin_doc)
        created_docs.append(admin_doc)

    # Si on a un bon de commande ET une facture, on verifie leur coherence
    if "bon_commande" in docs_by_type and "facture" in docs_by_type:
        try:
            bon_commande = BonCommande.model_validate(adapter_ocr(docs_by_type["bon_commande"]))
            facture      = Facture.model_validate(adapter_ocr(docs_by_type["facture"]))
            devis        = None
            if "devis" in docs_by_type:
                devis = Devis.model_validate(adapter_ocr(docs_by_type["devis"]))

            rapport = VerificateurDocuments().verifier(bon_commande, facture, devis)

            fac_doc_id = f"FACTURE-{session_id}"
            anomalies  = [
                {
                    "field":    a.reference_ligne or a.categorie,
                    "message":  a.message,
                    "severity": NIVEAU_TO_SEVERITY.get(a.niveau.value, "warning"),
                }
                for a in rapport.alertes
            ]

            # On attache les anomalies detectees a la facture
            update_anomalies(fac_doc_id, anomalies)
            for doc in created_docs:
                if doc["id"] == fac_doc_id:
                    doc["anomalies"] = anomalies
                    break

        except Exception as exc:
            print(f"[Verification] Erreur : {exc}")

    return created_docs


@app.get("/documents/pending")
async def get_pending_documents():
    """Retourne les documents en zone Silver, c'est-a-dire en attente de validation par un operateur."""
    return get_by_status("silver")


@app.put("/documents/{doc_id}/validate")
async def validate_document(doc_id: str, corrected_data: dict):
    """
    L'operateur a verifie et corrige les donnees du document.
    On le passe en zone Gold et on archive le JSON final dans MinIO.
    """
    doc = get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' introuvable.")

    extracted = corrected_data.get("extractedData", corrected_data)
    update_status(doc_id, "gold", extracted_data=extracted, anomalies=[])

    # On archive les donnees validees dans le bucket gold du data lake
    try:
        upload_json("gold", f"{doc_id}.json", extracted)
    except Exception:
        pass

    return {"message": "Document valide et passe en zone Gold.", "id": doc_id}


@app.patch("/documents/{doc_id}/reject")
async def reject_document(doc_id: str, body: dict = {}):
    """L'operateur a rejete le document. On le marque comme rejete avec la raison eventuellement fournie."""
    doc = get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' introuvable.")

    update_status(doc_id, "rejected")
    return {"message": "Document rejete.", "id": doc_id, "reason": body.get("reason")}


@app.get("/documents/gold")
async def get_gold_documents():
    """Retourne les documents valides en zone Gold, visibles dans l'espace metier."""
    return get_by_status("gold")


@app.get("/orchestration/review-queue")
async def get_orchestration_review_queue():
    """Expose la file silver enrichie pour les rapports et controles Airflow."""
    pending_documents = get_by_status("silver")
    queue = _build_review_queue(pending_documents)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "staleThresholdHours": ORCHESTRATION_STALE_HOURS,
        "queueSize": len(queue),
        "documents": queue,
    }


@app.get("/orchestration/overview")
async def get_orchestration_overview():
    """Retourne une vue agregee de la stack documentaire pour Airflow."""
    pending_documents = get_by_status("silver")
    gold_documents = get_by_status("gold")
    rejected_documents = get_by_status("rejected")
    all_documents = pending_documents + gold_documents + rejected_documents
    review_queue = _build_review_queue(pending_documents)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "staleThresholdHours": ORCHESTRATION_STALE_HOURS,
        "service": {
            "backendStatus": "ok",
            "version": app.version,
        },
        "frontend": {
            "allowedOrigins": FRONTEND_ORIGINS,
        },
        "summary": _build_documents_summary(all_documents),
        "queues": {
            "silver": len(pending_documents),
            "gold": len(gold_documents),
            "rejected": len(rejected_documents),
        },
        "reviewQueuePreview": review_queue[:10],
    }


@app.get("/orchestration/stale-documents")
async def get_orchestration_stale_documents():
    """Retourne les documents silver depassant le seuil de stagnation."""
    pending_documents = get_by_status("silver")
    stale_documents = _build_stale_documents(pending_documents)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "staleThresholdHours": ORCHESTRATION_STALE_HOURS,
        "staleCount": len(stale_documents),
        "documents": stale_documents,
    }


@app.get("/orchestration/publication-summary")
async def get_orchestration_publication_summary():
    """Expose un resume exploitable par Airflow pour la publication gold."""
    gold_documents = get_by_status("gold")
    return _build_publication_summary(gold_documents)


@app.get("/orchestration/business-metrics")
async def get_orchestration_business_metrics():
    """Expose les indicateurs metier consolides pour les DAGs de reporting."""
    pending_documents = get_by_status("silver")
    gold_documents = get_by_status("gold")
    return _build_business_metrics(pending_documents, gold_documents)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
