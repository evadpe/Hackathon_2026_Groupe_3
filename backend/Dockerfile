FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PYTHONDONTWRITEBYTECODE=1

# Poppler pour lire les PDFs.
# OpenCV tourne ici en mode headless, donc pas besoin des libs graphiques.
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# On installe d'abord les dépendances (mise en cache Docker)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefer-binary \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    torch torchvision \
    && pip install --no-cache-dir --prefer-binary -r requirements.txt

# Optionnel : pré-télécharge le modèle EasyOCR au build.
# Désactivé par défaut pour alléger le build Docker.
ARG PRELOAD_EASYOCR_MODEL=0
RUN if [ "$PRELOAD_EASYOCR_MODEL" = "1" ]; then python -c "import easyocr; easyocr.Reader(['fr'], gpu=False)"; fi

# Copie le backend et extraction.py (utilisé par ocr_engine via sys.path)
COPY backend/ ./backend/
COPY extraction.py .

WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
