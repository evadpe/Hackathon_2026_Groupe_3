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

# Chemin Poppler : sur Linux/Mac, Poppler est dans le PATH système (rien à faire).
# Sur Windows, définir la variable d'env POPPLER_PATH.
# Exemple Windows : set POPPLER_PATH=C:\poppler\Library\bin
POPPLER_PATH = os.getenv("POPPLER_PATH") or None


def image_to_ocr_dict(image_path: str) -> dict | None:
    """
    Lance l'OCR directement sur une image (PNG, JPG, JPEG).
    Retourne None si l'extraction échoue.
    """
    try:
        import extraction
        return extraction.process_document_extraction(image_path)
    except Exception as e:
        print(f"[OCR] Erreur lors du traitement image : {e}")
        return None


def pdf_to_ocr_dict(pdf_path: str) -> dict | None:
    """
    Convertit un PDF en dict OCR structuré (format extraction.py).
    Retourne None si l'extraction échoue.
    """
    tmp_path = None
    try:
        from pdf2image import convert_from_path
        import extraction  # initialise ocr_reader au premier import

        kwargs = {}
        if POPPLER_PATH:
            kwargs["poppler_path"] = POPPLER_PATH

        # 300 dpi au lieu des 72 dpi par défaut : améliore considérablement l'OCR sur les docs dégradés
        pages = convert_from_path(pdf_path, dpi=300, **kwargs)
        if not pages:
            return None

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        # Qualité 95 pour éviter les artefacts JPEG qui perturbent l'OCR
        pages[0].save(tmp_path, "JPEG", quality=95)
        return extraction.process_document_extraction(tmp_path)

    except Exception as e:
        print(f"[OCR] Erreur lors du traitement PDF : {e}")
        return None

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
