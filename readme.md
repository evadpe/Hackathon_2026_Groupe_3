# StepAhead Industries - Plateforme d'Analyse Documentaire IA

Bienvenue sur le dépôt du projet **Hackathon 2026 - Groupe 3**. Cette application est une solution complète d'automatisation et de vérification documentaire B2B (Moteur de conformité). Elle permet d'extraire, de vérifier et de valider automatiquement les bons de commande, factures et devis grâce à l'Intelligence Artificielle.

## Fonctionnalités Principales

- **Extraction OCR Intelligente** : Traitement automatique des factures, bons de commande et devis (format PDF ou Image) grâce à `EasyOCR`.
- **Rapprochement Tripartite** : Vérification métier automatique croisant les données du Bon de Commande, du Devis et de la Facture (prix, quantités, TVA, frais de port).
- **Analyse Sémantique IA** : Utilisation de **Claude AI** pour déceler les incohérences subtiles (ex: "Chaise bleue" commandée mais "Siège azur" facturé).
- **Architecture Data Lake (Médaillon)** :
  - **Bronze** : Stockage des documents bruts (MinIO / Local).
  - **Silver** : Données extraites en attente de validation humaine via l'interface UI.
  - **Gold** : Données certifiées et conformes, prêtes pour l'intégration CRM.
- **Interface Utilisateur Moderne** : Dashboard interactif développé en Next.js avec retours visuels instantanés (Toast notifications) et espace métier (CRM).
- **Automatisation n8n** : Webhook intégré pour déclencher des workflows post-validation.
- **Orchestration Airflow** : DAGs planifiés pour superviser les flux bronze -> silver -> gold et préparer les exports métier.

---

## Architecture du Projet

Le projet est divisé en plusieurs briques conteneurisées via **Docker** :

### 1. Backend (Python / FastAPI) `[Port 8000]`
- **FastAPI** : API RESTful robuste et asynchrone.
- **EasyOCR / Poppler / OpenCV** : Moteur d'extraction de texte.
- **Pydantic** : Validation stricte des modèles de données.
- **SQLite / MinIO (Simulé)** : Stockage des métadonnées et des fichiers physiques.

### 2. Frontend (Next.js / React) `[Port 3000]`
- **Next.js (App Router)** : Framework React pour le rendu UI.
- **Tailwind CSS** : Design system moderne et responsive.
- **Lucide React & Sonner** : Iconographie premium et notifications push (Toasts).
- **Axios & React Dropzone** : Gestion des APIs et de l'upload de fichiers en Drag & Drop.

### 3. Orchestration (n8n / Airflow) `[Ports 5678 / 8080]`
- **n8n** : Orchestration événementielle déclenchée après l'upload.
- **Airflow** : Orchestration planifiée des DAGs de suivi Silver et de publication Gold.

---

## Prérequis

Pour exécuter le projet, vous aurez besoin de :
- [Docker](https://www.docker.com/) et [Docker Compose](https://docs.docker.com/compose/) (Recommandé)
- **Si exécution locale (sans Docker)** :
  - Python 3.11+
  - Node.js 18+
  - [Poppler](https://poppler.freedesktop.org/) (Nécessaire pour la conversion PDF → Image)

---

## Installation & Démarrage (Docker - Recommandé)

C'est la méthode la plus simple, Docker s'occupe de toutes les dépendances systèmes (comme Poppler ou OpenCV).

1. **Cloner le dépôt** :
   ```bash
   git clone <url-du-repo>
   cd Hackathon_2026_Groupe_3
   ```

2. **Lancer les conteneurs** :
   ```bash
   docker compose up --build -d
   ```

3. **Accéder à l'application** :
   - Interface UI (Frontend) : [http://localhost:3000](http://localhost:3000)
   - Swagger API (Backend) : [http://localhost:8000/docs](http://localhost:8000/docs)
   - n8n : [http://localhost:5678](http://localhost:5678)
   - Airflow : [http://localhost:8080](http://localhost:8080)

---

## Exécution Locale (Mode Développement)

Si vous souhaitez modifier le code et voir les changements en direct :

### 1. Lancer le Backend (Python)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt

# Sur Windows, n'oubliez pas de configurer POPPLER_PATH dans vos variables d'environnement.

uvicorn api:app --reload --port 8000
```

### 2. Lancer le Frontend (Next.js)
Dans un nouveau terminal :
```bash
cd frontend-platform
npm install
npm run dev
```

---

## Structure du Répertoire

```text
Hackathon_2026_Groupe_3/
├── backend/                   # Serveur FastAPI et logique métier IA
│   ├── analyzer.py            # Analyse sémantique 
│   ├── api.py                 # Points d'entrée (Endpoints) REST
│   ├── Dockerfile             # Recette de construction de l'image Backend
│   ├── extraction.py          # Script principal de l'extraction EasyOCR
│   ├── models.py              # Schémas de données Pydantic (Facture, Devis...)
│   ├── ocr_engine.py          # Wrapper liant l'API aux scripts OCR
│   ├── requirements.txt       # Dépendances Python (opencv-python-headless, fastapi...)
│   └── verifier.py            # Logique de rapprochement tripartite
├── airflow/                   # Image Airflow, DAGs et documentation associée
│   ├── Dockerfile             # Recette de construction de l'image Airflow
│   ├── dags/                  # DAGs d'orchestration bronze / silver / gold
│   └── README.md              # Documentation d'orchestration
├── docker-compose.yml         # Orchestration des services
├── frontend-platform/         # Application web Next.js
│   ├── Dockerfile             # Recette de construction de l'image Frontend
│   ├── package.json           # Dépendances Node.js
│   ├── src/
│   │   ├── app/               # Pages (Home, /conformite, /crm)
│   │   ├── components/        # Composants UI (UploadZone, ValidationForm, Toasts)
│   │   ├── lib/               # Utilitaires (Axios, Tailwind, parsers)
│   │   └── services/          # Appels API vers le backend (docService.ts)
└── readme.md                  # Ce fichier !
```

---

## Workflow d'Utilisation

1. **Dashboard** : Visualisez les KPI en temps réel (documents totaux, en attente, validés).
2. **Centre de Conformité (`/conformite`)** : 
   - Déposez vos PDF ou Images.
   - L'IA extrait les données, analyse la sémantique et fait le rapprochement.
   - Si des incohérences sont détectées, elles sont signalées en rouge/orange.
3. **Validation Humaine** : L'opérateur corrige les erreurs éventuelles et valide le document (Passage Silver -> Gold).
4. **Espace Métier CRM (`/crm`)** : Seuls les documents certifiés "Gold" apparaissent, prêts à être envoyés en comptabilité ou intégrés à un ERP.
5. **Supervision Airflow** : Les DAGs surveillent les documents en attente, génèrent des rapports de suivi et préparent les manifestes d'export.
