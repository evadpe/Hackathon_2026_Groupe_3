FROM python:3.11-slim

# Poppler pour lire les PDFs, libs système pour OpenCV
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# On installe d'abord les dépendances (mise en cache Docker)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pré-télécharge le modèle EasyOCR français au moment du build
# (évite une attente de ~500 Mo au premier démarrage)
RUN python -c "import easyocr; easyocr.Reader(['fr'])"

# Copie le backend et extraction.py (utilisé par ocr_engine via sys.path)
COPY backend/ ./backend/
COPY extraction.py .

WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
