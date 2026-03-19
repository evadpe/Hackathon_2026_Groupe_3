"""
Gestion du stockage de fichiers avec MinIO.

Le data lake est organise en trois zones qui correspondent aux etapes de traitement :
  bronze : fichiers bruts tels qu'ils ont ete uploades (PDFs, JSONs)
  silver : donnees extraites par l'OCR, en attente de validation
  gold   : donnees validees par un operateur, pret pour l'espace metier
"""
import io
import json
import os

from minio import Minio

MINIO_ENDPOINT   = os.getenv("MINIO_ENDPOINT",   "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

BUCKETS = ["bronze", "silver", "gold"]

# Cette politique S3 permet a n'importe qui de lire les fichiers,
# ce qui est necessaire pour afficher les PDFs dans le navigateur.
_PUBLIC_POLICY = """{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": ["*"]},
    "Action": ["s3:GetObject"],
    "Resource": ["arn:aws:s3:::{bucket}/*"]
  }]
}"""


def init_storage():
    """Cree les trois buckets au demarrage s'ils n'existent pas encore."""
    for bucket in BUCKETS:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        client.set_bucket_policy(bucket, _PUBLIC_POLICY.format(bucket=bucket))


def upload_file(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Envoie des donnees brutes dans un bucket et retourne l'URL publique du fichier."""
    client.put_object(bucket, object_name, io.BytesIO(data), len(data), content_type=content_type)
    return f"{MINIO_PUBLIC_URL}/{bucket}/{object_name}"


def upload_json(bucket: str, object_name: str, data: dict) -> str:
    """Convertit un dictionnaire en JSON et l'envoie dans un bucket."""
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return upload_file(bucket, object_name, raw, content_type="application/json")


def public_url(bucket: str, object_name: str) -> str:
    """Retourne l'URL publique d'un fichier sans l'uploader."""
    return f"{MINIO_PUBLIC_URL}/{bucket}/{object_name}"
