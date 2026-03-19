"""
Couche d'acces a la base de donnees SQLite.

Remplace le dictionnaire en memoire utilise initialement.
Les donnees sont persistees sur disque et survivent aux redemarrages du backend.
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "documents.db"


def _get_conn() -> sqlite3.Connection:
    """Ouvre une connexion SQLite et configure le retour en dictionnaire."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cree la table documents au premier demarrage si elle n'existe pas."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id             TEXT PRIMARY KEY,
                filename       TEXT NOT NULL,
                file_url       TEXT,
                type           TEXT,
                status         TEXT DEFAULT 'silver',
                upload_date    TEXT,
                extracted_data TEXT DEFAULT '{}',
                anomalies      TEXT DEFAULT '[]'
            )
        """)
        conn.commit()


def upsert_document(doc: dict):
    """Insere un nouveau document ou remplace l'existant si l'id est deja present."""
    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO documents
              (id, filename, file_url, type, status, upload_date, extracted_data, anomalies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc["id"],
            doc["filename"],
            doc["fileUrl"],
            doc["type"],
            doc["status"],
            doc["uploadDate"],
            json.dumps(doc.get("extractedData", {})),
            json.dumps(doc.get("anomalies", [])),
        ))
        conn.commit()


def get_by_status(status: str) -> list:
    """Retourne tous les documents ayant le statut demande (silver, gold, rejected...)."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE status = ?", (status,)
        ).fetchall()
    return [_to_dict(r) for r in rows]


def get_by_id(doc_id: str) -> dict | None:
    """Retourne un document par son identifiant, ou None s'il n'existe pas."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return _to_dict(row) if row else None


def update_status(doc_id: str, status: str, extracted_data: dict = None, anomalies: list = None):
    """
    Met a jour le statut d'un document.
    Si des donnees extraites sont fournies, on les met a jour en meme temps.
    """
    with _get_conn() as conn:
        if extracted_data is not None:
            conn.execute(
                "UPDATE documents SET status=?, extracted_data=?, anomalies=? WHERE id=?",
                (status, json.dumps(extracted_data), json.dumps(anomalies or []), doc_id),
            )
        else:
            conn.execute("UPDATE documents SET status=? WHERE id=?", (status, doc_id))
        conn.commit()


def update_anomalies(doc_id: str, anomalies: list):
    """Met a jour uniquement la liste des anomalies d'un document, sans toucher au reste."""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE documents SET anomalies=? WHERE id=?",
            (json.dumps(anomalies), doc_id),
        )
        conn.commit()


def _to_dict(row: sqlite3.Row) -> dict:
    """Convertit une ligne SQLite en dictionnaire compatible avec le format AdminDocument."""
    return {
        "id":            row["id"],
        "filename":      row["filename"],
        "fileUrl":       row["file_url"],
        "type":          row["type"],
        "status":        row["status"],
        "uploadDate":    row["upload_date"],
        "extractedData": json.loads(row["extracted_data"]),
        "anomalies":     json.loads(row["anomalies"]),
    }
