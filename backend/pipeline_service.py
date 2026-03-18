import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from models import BonCommande, Devis, Facture
from ocr_engine import pdf_bytes_to_ocr_dict
from run_ocr_test import adapter_ocr
from storage import StorageBackend
from verifier import VerificateurDocuments

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


class DocumentPipelineService:
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.documents_db: Dict[str, dict] = {}

    def detecter_type(self, raw: dict) -> str:
        type_ocr = raw.get("metadata", {}).get("type", "")
        return OCR_TYPE_MAP.get(type_ocr, "inconnu")

    def ocr_to_extracted_data(self, raw: dict, type_frontend: str) -> dict:
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

    def metadata_path(self, doc_id: str) -> str:
        return f"metadata/documents/{doc_id}.json"

    def session_metadata_path(self, session_id: str) -> str:
        return f"metadata/sessions/{session_id}.json"

    def silver_path(self, doc_id: str) -> str:
        return f"silver/extracted/{doc_id}.json"

    def gold_path(self, doc_id: str) -> str:
        return f"gold/validated/{doc_id}.json"

    def raw_upload_path(self, session_id: str, file_key: str) -> str:
        return f"bronze/raw/{session_id}/{file_key}"

    def make_file_url(self, storage_path: str) -> str:
        return f"/files/{storage_path}"

    def cache_and_save_document(self, document: dict) -> dict:
        self.documents_db[document["id"]] = document
        self.storage.write_json(self.metadata_path(document["id"]), document)
        return document

    def save_session_state(self, session_state: dict) -> dict:
        self.storage.write_json(
            self.session_metadata_path(session_state["sessionId"]),
            session_state,
        )
        return session_state

    def load_session_state(self, session_id: str) -> dict | None:
        metadata_path = self.session_metadata_path(session_id)
        if not self.storage.exists(metadata_path):
            return None
        return self.storage.read_json(metadata_path)

    def list_sessions(self, status: str | None = None) -> list[dict]:
        sessions = []
        for path in self.storage.list_files("metadata/sessions", suffix=".json"):
            try:
                session_state = self.storage.read_json(path)
            except Exception as exc:
                print(f"[Storage] Impossible de lire {path}: {exc}")
                continue

            if status is None or session_state.get("status") == status:
                sessions.append(session_state)

        return sorted(
            sessions,
            key=lambda session: session.get("createdAt", ""),
            reverse=True,
        )

    def create_pending_session(
        self,
        session_id: str,
        stored_files: List[dict[str, str]],
        dag_run_id: str | None = None,
    ) -> dict:
        existing = self.load_session_state(session_id)
        if existing is not None:
            return existing

        session_state = {
            "sessionId": session_id,
            "status": "pending",
            "createdAt": datetime.utcnow().isoformat(),
            "files": stored_files,
            "dagRunId": dag_run_id,
            "processedDocumentIds": [],
        }
        return self.save_session_state(session_state)

    def claim_session(
        self,
        session_id: str,
        dag_run_id: str | None = None,
        processor: str = "airflow",
    ) -> dict | None:
        session_state = self.load_session_state(session_id)
        if session_state is None or session_state.get("status") != "pending":
            return session_state

        session_state["status"] = "processing"
        session_state["claimedAt"] = datetime.utcnow().isoformat()
        session_state["processor"] = processor
        if dag_run_id:
            session_state["dagRunId"] = dag_run_id
        return self.save_session_state(session_state)

    def complete_session(
        self,
        session_id: str,
        documents: List[dict],
        dag_run_id: str | None = None,
    ) -> dict:
        session_state = self.load_session_state(session_id) or {
            "sessionId": session_id,
            "createdAt": datetime.utcnow().isoformat(),
            "files": [],
        }
        session_state["status"] = "completed"
        session_state["completedAt"] = datetime.utcnow().isoformat()
        session_state["documentsCreated"] = len(documents)
        session_state["processedDocumentIds"] = [doc["id"] for doc in documents]
        session_state["lastError"] = None
        if dag_run_id:
            session_state["dagRunId"] = dag_run_id
        return self.save_session_state(session_state)

    def fail_session(
        self,
        session_id: str,
        error_message: str,
        dag_run_id: str | None = None,
    ) -> dict:
        session_state = self.load_session_state(session_id) or {
            "sessionId": session_id,
            "createdAt": datetime.utcnow().isoformat(),
            "files": [],
        }
        session_state["status"] = "failed"
        session_state["failedAt"] = datetime.utcnow().isoformat()
        session_state["lastError"] = error_message
        if dag_run_id:
            session_state["dagRunId"] = dag_run_id
        return self.save_session_state(session_state)

    def persist_silver_document(self, doc_id: str, raw_ocr: dict, source_path: str) -> str:
        silver_payload = {
            "documentId": doc_id,
            "storedAt": datetime.utcnow().isoformat(),
            "sourcePath": source_path,
            "ocr": raw_ocr,
        }
        return self.storage.write_json(self.silver_path(doc_id), silver_payload)

    def persist_gold_document(self, doc_id: str, document: dict) -> str:
        gold_payload = {
            "documentId": doc_id,
            "validatedAt": datetime.utcnow().isoformat(),
            "document": document,
        }
        return self.storage.write_json(self.gold_path(doc_id), gold_payload)

    def load_document(self, doc_id: str) -> dict | None:
        if doc_id in self.documents_db:
            return self.documents_db[doc_id]

        metadata_path = self.metadata_path(doc_id)
        if not self.storage.exists(metadata_path):
            return None

        document = self.storage.read_json(metadata_path)
        self.documents_db[doc_id] = document
        return document

    def list_documents(self, status: str | None = None) -> list[dict]:
        documents = []
        for path in self.storage.list_files("metadata/documents", suffix=".json"):
            try:
                document = self.storage.read_json(path)
            except Exception as exc:
                print(f"[Storage] Impossible de lire {path}: {exc}")
                continue

            self.documents_db[document["id"]] = document
            if status is None or document.get("status") == status:
                documents.append(document)

        return sorted(documents, key=lambda doc: doc.get("uploadDate", ""), reverse=True)

    def make_admin_doc(
        self,
        doc_id: str,
        filename: str,
        type_frontend: str,
        extracted_data: dict,
        anomalies: list,
        file_url: str,
        raw_path: str,
        status: str = "silver",
        silver_path: str | None = None,
        gold_path: str | None = None,
        orchestration: dict[str, Any] | None = None,
    ) -> dict:
        return {
            "id": doc_id,
            "filename": filename,
            "fileUrl": file_url,
            "type": type_frontend,
            "status": status,
            "uploadDate": datetime.utcnow().isoformat(),
            "extractedData": extracted_data,
            "anomalies": anomalies,
            "storage": {
                "backend": self.storage.kind,
                "rawPath": raw_path,
                "silverPath": silver_path,
                "goldPath": gold_path,
                "metadataPath": self.metadata_path(doc_id),
            },
            "orchestration": orchestration or {"mode": "sync"},
        }

    def build_bronze_placeholders(
        self,
        session_id: str,
        stored_files: List[dict[str, str]],
        dag_run_id: str | None = None,
    ) -> list[dict]:
        placeholders = []
        for index, item in enumerate(stored_files, start=1):
            doc_id = f"BRONZE-{session_id}-{index:02d}"
            placeholder = self.make_admin_doc(
                doc_id=doc_id,
                filename=item["filename"],
                type_frontend="invoice",
                extracted_data={
                    "note": "Traitement OCR orchestre par Airflow en cours.",
                    "session_id": session_id,
                },
                anomalies=[{
                    "field": "pipeline",
                    "message": "Document en attente de traitement par Airflow.",
                    "severity": "warning",
                }],
                file_url=self.make_file_url(item["raw_path"]),
                raw_path=item["raw_path"],
                status="bronze",
                orchestration={
                    "mode": "airflow",
                    "sessionId": session_id,
                    "dagRunId": dag_run_id,
                },
            )
            self.cache_and_save_document(placeholder)
            placeholders.append(placeholder)
        return placeholders

    def process_session_upload(self, session_id: str, stored_files: List[dict[str, str]]) -> List[dict]:
        docs_by_type: Dict[str, dict] = {}
        created_docs: List[dict] = []

        for stored_file in stored_files:
            filename = stored_file["filename"]
            raw_path = stored_file["raw_path"]
            suffix = Path(filename).suffix.lower()
            content = self.storage.read_bytes(raw_path)
            file_url = self.make_file_url(raw_path)

            if suffix == ".json":
                try:
                    raw_ocr = json.loads(content)
                except json.JSONDecodeError:
                    continue

                type_interne = self.detecter_type(raw_ocr)
                if type_interne == "inconnu":
                    continue

                docs_by_type[type_interne] = {
                    "raw_ocr": raw_ocr,
                    "filename": filename,
                    "file_url": file_url,
                    "raw_path": raw_path,
                }
                continue

            if suffix != ".pdf":
                continue

            raw_ocr = pdf_bytes_to_ocr_dict(content)
            if raw_ocr is None:
                doc_id = f"PDF-{session_id}-{uuid.uuid4().hex[:4]}"
                admin_doc = self.make_admin_doc(
                    doc_id=doc_id,
                    filename=filename,
                    type_frontend="invoice",
                    extracted_data={"note": "Extraction OCR échouée", "fichier": filename},
                    anomalies=[{
                        "field": "ocr",
                        "message": "L'OCR n'a pas pu extraire les données du PDF.",
                        "severity": "error",
                    }],
                    file_url=file_url,
                    raw_path=raw_path,
                )
                self.cache_and_save_document(admin_doc)
                created_docs.append(admin_doc)
                continue

            type_interne = self.detecter_type(raw_ocr)
            if type_interne != "inconnu":
                docs_by_type[type_interne] = {
                    "raw_ocr": raw_ocr,
                    "filename": filename,
                    "file_url": file_url,
                    "raw_path": raw_path,
                }
                continue

            doc_id = f"PDF-{session_id}-{uuid.uuid4().hex[:4]}"
            persisted_silver_path = self.persist_silver_document(doc_id, raw_ocr, raw_path)
            admin_doc = self.make_admin_doc(
                doc_id=doc_id,
                filename=filename,
                type_frontend="invoice",
                extracted_data=self.ocr_to_extracted_data(raw_ocr, "invoice"),
                anomalies=[{
                    "field": "type",
                    "message": "Type de document non reconnu (Facture / Bon de Commande / Devis attendu).",
                    "severity": "warning",
                }],
                file_url=file_url,
                raw_path=raw_path,
                silver_path=persisted_silver_path,
            )
            self.cache_and_save_document(admin_doc)
            created_docs.append(admin_doc)

        for type_interne, payload in docs_by_type.items():
            raw_ocr = payload["raw_ocr"]
            type_frontend = TYPE_TO_FRONTEND[type_interne]
            doc_id = f"{type_interne.upper()}-{session_id}"
            persisted_silver_path = self.persist_silver_document(doc_id, raw_ocr, payload["raw_path"])

            admin_doc = self.make_admin_doc(
                doc_id=doc_id,
                filename=payload["filename"],
                type_frontend=type_frontend,
                extracted_data=self.ocr_to_extracted_data(raw_ocr, type_frontend),
                anomalies=[],
                file_url=payload["file_url"],
                raw_path=payload["raw_path"],
                silver_path=persisted_silver_path,
            )
            self.cache_and_save_document(admin_doc)
            created_docs.append(admin_doc)

        if "bon_commande" in docs_by_type and "facture" in docs_by_type:
            try:
                bon_commande = BonCommande.model_validate(adapter_ocr(docs_by_type["bon_commande"]["raw_ocr"]))
                facture = Facture.model_validate(adapter_ocr(docs_by_type["facture"]["raw_ocr"]))
                devis = None
                if "devis" in docs_by_type:
                    devis = Devis.model_validate(adapter_ocr(docs_by_type["devis"]["raw_ocr"]))

                rapport = VerificateurDocuments().verifier(bon_commande, facture, devis)
                fac_doc_id = f"FACTURE-{session_id}"

                anomalies = [
                    {
                        "field": alerte.reference_ligne or alerte.categorie,
                        "message": alerte.message,
                        "severity": NIVEAU_TO_SEVERITY.get(alerte.niveau.value, "warning"),
                    }
                    for alerte in rapport.alertes
                ]

                facture_doc = self.load_document(fac_doc_id)
                if facture_doc is not None:
                    facture_doc["anomalies"] = anomalies
                    self.cache_and_save_document(facture_doc)
                    for doc in created_docs:
                        if doc["id"] == fac_doc_id:
                            doc["anomalies"] = anomalies
                            break
            except Exception as exc:
                print(f"[Verification] Erreur : {exc}")

        return created_docs
