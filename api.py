"""
API FastAPI — Pont entre le backend de vérification et le frontend Next.js.

Endpoints attendus par le frontend (src/services/docService.ts) :
  POST /documents/upload          → Upload + vérification → AdminDocument[]
  GET  /documents/pending         → Liste des docs en zone Silver
  POST /documents/{id}/validate   → Valider et passer en zone Gold
  GET  /documents/gold            → Liste des docs validés (zone Gold)

Lancer avec :
  uvicorn api:app --reload --port 8000
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models import BonCommande, Devis, Facture
from run_ocr_test import adapter_ocr
from verifier import VerificateurDocuments

# ─── App & CORS ──────────────────────────────────────────────────────────────

app = FastAPI(title="StepAhead Industries — API Conformité", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Stockage fichiers uploadés ───────────────────────────────────────────────

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/files", StaticFiles(directory=str(UPLOAD_DIR)), name="files")

# ─── Base de données en mémoire ───────────────────────────────────────────────
# En prod : remplacer par PostgreSQL / SQLite

documents_db: Dict[str, dict] = {}

# ─── Mappings ─────────────────────────────────────────────────────────────────

OCR_TYPE_MAP = {
    "Facture":         "facture",
    "Bon de Commande": "bon_commande",
    "Devis":           "devis",
}

TYPE_TO_FRONTEND = {
    "facture":      "invoice",
    "bon_commande": "purchase_order",
    "devis":        "quote",
}

NIVEAU_TO_SEVERITY = {
    "ERREUR":        "error",
    "AVERTISSEMENT": "warning",
    "INFO":          "warning",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _detecter_type(raw: dict) -> str:
    """Retourne le type interne ('facture', 'bon_commande', 'devis') depuis un dict OCR."""
    type_ocr = raw.get("metadata", {}).get("type", "")
    return OCR_TYPE_MAP.get(type_ocr, "inconnu")


def _ocr_to_extracted_data(raw: dict, type_frontend: str) -> dict:
    """Aplatit le JSON OCR en extractedData lisible par le frontend."""
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

    if type_frontend == "invoice":
        data["echeance"] = doc_info.get("due_date", "")
    elif type_frontend == "quote":
        data["validite"] = doc_info.get("due_date", "")

    return data


def _make_admin_doc(
    doc_id: str,
    filename: str,
    type_frontend: str,
    extracted_data: dict,
    anomalies: list,
    file_url: str,
) -> dict:
    return {
        "id":           doc_id,
        "filename":     filename,
        "fileUrl":      file_url,
        "type":         type_frontend,
        "status":       "silver",
        "uploadDate":   datetime.now().isoformat(),
        "extractedData": extracted_data,
        "anomalies":    anomalies,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Reçoit N fichiers JSON (output OCR) ou PDF.
    - JSON : traitement immédiat via adapter_ocr + vérification inter-documents.
    - PDF  : stockage + stub (intégration OCR à brancher ici).
    Retourne la liste des AdminDocument créés.
    """
    session_id = uuid.uuid4().hex[:8]
    docs_by_type: Dict[str, dict] = {}       # type_interne → raw OCR dict
    saved_filenames: Dict[str, str] = {}     # type_interne → nom de fichier sauvegardé
    created_docs: List[dict] = []

    for upload in files:
        suffix   = Path(upload.filename or "file").suffix.lower()
        file_key = f"{session_id}_{uuid.uuid4().hex[:6]}{suffix}"
        dest     = UPLOAD_DIR / file_key
        content  = await upload.read()

        with open(dest, "wb") as f:
            f.write(content)

        file_url = f"/files/{file_key}"

        # ── Fichier JSON (output OCR) ────────────────────────────────────────
        if suffix == ".json":
            try:
                raw_ocr = json.loads(content)
            except json.JSONDecodeError:
                continue

            type_interne = _detecter_type(raw_ocr)
            if type_interne == "inconnu":
                continue

            docs_by_type[type_interne]    = raw_ocr
            saved_filenames[type_interne] = file_url

        # ── Fichier PDF (OCR non intégré : stub) ─────────────────────────────
        elif suffix == ".pdf":
            doc_id = f"PDF-{session_id}-{uuid.uuid4().hex[:4]}"
            admin_doc = _make_admin_doc(
                doc_id      = doc_id,
                filename    = upload.filename or file_key,
                type_frontend = "invoice",
                extracted_data = {"note": "OCR en attente", "fichier": upload.filename},
                anomalies   = [],
                file_url    = file_url,
            )
            documents_db[doc_id] = admin_doc
            created_docs.append(admin_doc)

    # ── Créer un AdminDocument par fichier JSON reçu ─────────────────────────
    for type_interne, raw_ocr in docs_by_type.items():
        type_frontend = TYPE_TO_FRONTEND[type_interne]
        doc_id        = f"{type_interne.upper()}-{session_id}"
        filename      = saved_filenames.get(type_interne, f"{type_interne}.json")

        admin_doc = _make_admin_doc(
            doc_id        = doc_id,
            filename      = Path(filename).name,
            type_frontend = type_frontend,
            extracted_data = _ocr_to_extracted_data(raw_ocr, type_frontend),
            anomalies     = [],
            file_url      = filename,
        )
        documents_db[doc_id] = admin_doc
        created_docs.append(admin_doc)

    # ── Vérification inter-documents (requiert BC + Facture au minimum) ───────
    if "bon_commande" in docs_by_type and "facture" in docs_by_type:
        try:
            bon_commande = BonCommande.model_validate(
                adapter_ocr(docs_by_type["bon_commande"])
            )
            facture = Facture.model_validate(
                adapter_ocr(docs_by_type["facture"])
            )
            devis = None
            if "devis" in docs_by_type:
                devis = Devis.model_validate(adapter_ocr(docs_by_type["devis"]))

            rapport = VerificateurDocuments().verifier(bon_commande, facture, devis)

            # Attacher les anomalies à la facture (doc_id = "FACTURE-<session_id>")
            fac_doc_id = f"FACTURE-{session_id}"

            anomalies = [
                {
                    "field":    alerte.reference_ligne or alerte.categorie,
                    "message":  alerte.message,
                    "severity": NIVEAU_TO_SEVERITY.get(alerte.niveau.value, "warning"),
                }
                for alerte in rapport.alertes
            ]

            if fac_doc_id in documents_db:
                documents_db[fac_doc_id]["anomalies"] = anomalies
                for doc in created_docs:
                    if doc["id"] == fac_doc_id:
                        doc["anomalies"] = anomalies
                        break

        except Exception as exc:
            print(f"[Vérification] Erreur : {exc}")

    return created_docs


@app.get("/documents/pending")
async def get_pending_documents():
    """Retourne tous les documents en zone Silver (en attente de validation)."""
    return [doc for doc in documents_db.values() if doc["status"] == "silver"]


@app.post("/documents/{doc_id}/validate")
async def validate_document(doc_id: str, corrected_data: dict):
    """
    Valide un document avec les données corrigées par l'opérateur.
    Passe le document en zone Gold.
    """
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' introuvable.")

    doc = documents_db[doc_id]
    doc["status"]        = "gold"
    doc["extractedData"] = corrected_data
    doc["anomalies"]     = []

    return {"message": "Document validé et passé en zone Gold.", "id": doc_id}


@app.get("/documents/gold")
async def get_gold_documents():
    """Retourne tous les documents validés (zone Gold)."""
    return [doc for doc in documents_db.values() if doc["status"] == "gold"]


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
