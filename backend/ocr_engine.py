"""
ocr_engine.py — Wrapper OCR pour l'API FastAPI.

Utilise extraction.py (à la racine du projet) pour traiter les PDFs.
Configurer la variable d'environnement POPPLER_PATH si Poppler n'est
pas dans le PATH système (Windows notamment).
"""
import os
import sys
import tempfile
from pathlib import Path

# Ajouter la racine du projet au path pour importer extraction.py
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Chemin Poppler (Windows) : définir via variable d'environnement
# Exemple : set POPPLER_PATH=C:\poppler\Library\bin
POPPLER_PATH = os.getenv("POPPLER_PATH")  # None sur Linux/Docker (Poppler dans le PATH système)


def _run_ocr_on_pdf_path(pdf_path: str) -> dict | None:
    """
    Convertit un PDF en dict OCR structuré (format extraction.py).
    Retourne None si l'extraction échoue.
    """
    tmp_image_path = None
    try:
        from pdf2image import convert_from_path
        import extraction  # initialise ocr_reader au premier import

        kwargs = {}
        if POPPLER_PATH:
            kwargs["poppler_path"] = POPPLER_PATH

        pages = convert_from_path(pdf_path, **kwargs)
        if not pages:
            return None

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_image_path = tmp.name

        pages[0].save(tmp_image_path, "JPEG")
        return extraction.process_document_extraction(tmp_image_path)

    except Exception as e:
        print(f"[OCR] Erreur lors du traitement PDF : {e}")
        return None

    finally:
        if tmp_image_path and os.path.exists(tmp_image_path):
            os.remove(tmp_image_path)


def pdf_to_ocr_dict(pdf_path: str) -> dict | None:
    return _run_ocr_on_pdf_path(pdf_path)


def pdf_bytes_to_ocr_dict(pdf_bytes: bytes) -> dict | None:
    tmp_pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            tmp_pdf.write(pdf_bytes)
            tmp_pdf_path = tmp_pdf.name

        return _run_ocr_on_pdf_path(tmp_pdf_path)
    except Exception as e:
        print(f"[OCR] Erreur lors de la préparation du PDF : {e}")
        return None
    finally:
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)
