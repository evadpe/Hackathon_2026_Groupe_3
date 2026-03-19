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
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import httpx
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, upsert_document, get_by_status, get_by_id, update_status, update_anomalies
from models import BonCommande, Devis, Facture
from ocr_engine import pdf_to_ocr_dict
from run_ocr_test import adapter_ocr
from storage import init_storage, upload_file, upload_json, public_url
from verifier import VerificateurDocuments

# URL du webhook n8n qui declenche le workflow apres chaque upload
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/document-uploaded")

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
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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


async def _notifier_n8n(docs: list):
    """Previent n8n qu'un upload vient de se terminer pour declencher le workflow."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(N8N_WEBHOOK_URL, json={"documents": docs})
    except Exception as e:
        print(f"[n8n] Webhook non joignable : {e}")


@app.post("/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Recoit un ou plusieurs fichiers PDF ou JSON depuis le frontend.

    Pour chaque fichier :
      - On le stocke dans le bucket bronze (fichier brut)
      - Si c'est un PDF, on lance l'OCR pour en extraire les donnees
      - Si c'est un JSON OCR deja traite, on l'utilise directement

    Si on recoit a la fois un bon de commande et une facture, on lance
    la verification inter-documents pour detecter les anomalies.

    A la fin, on notifie n8n pour qu'il traite les nouveaux documents.
    """
    session_id    = uuid.uuid4().hex[:8]
    docs_by_type: Dict[str, dict] = {}
    file_urls:    Dict[str, str]  = {}
    created_docs: List[dict]      = []

    for upload in files:
        suffix   = Path(upload.filename or "file").suffix.lower()
        file_key = f"{session_id}_{uuid.uuid4().hex[:6]}{suffix}"
        content  = await upload.read()

        # On envoie le fichier brut dans le bucket bronze du data lake
        try:
            content_type = "application/pdf" if suffix == ".pdf" else "application/json"
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
                type_interne = _detecter_type(raw_ocr)
                if type_interne != "inconnu":
                    docs_by_type[type_interne] = raw_ocr
                    file_urls[type_interne]    = file_url
                else:
                    # L'OCR a fonctionne mais le type de document n'est pas reconnu
                    doc_id    = f"PDF-{session_id}-{uuid.uuid4().hex[:4]}"
                    admin_doc = _make_admin_doc(
                        doc_id, upload.filename or file_key, "invoice",
                        _ocr_to_extracted_data(raw_ocr, "invoice"),
                        [{"field": "type", "message": "Type non reconnu.", "severity": "warning"}],
                        file_url,
                    )
                    upsert_document(admin_doc)
                    created_docs.append(admin_doc)
            else:
                # L'OCR a completement echoue (image trop floue, format non supporte...)
                doc_id    = f"PDF-{session_id}-{uuid.uuid4().hex[:4]}"
                admin_doc = _make_admin_doc(
                    doc_id, upload.filename or file_key, "invoice",
                    {"note": "Extraction OCR echouee", "fichier": upload.filename},
                    [{"field": "ocr", "message": "L'OCR n'a pas pu extraire les donnees du PDF.", "severity": "error"}],
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

    # On previent n8n en arriere-plan pour ne pas bloquer la reponse au frontend
    if created_docs and background_tasks:
        background_tasks.add_task(_notifier_n8n, created_docs)

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


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
