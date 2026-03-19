# Airflow orchestration

Ce dossier contient l'architecture d'orchestration Airflow du projet de
conformite documentaire.

## Objectif

Airflow est l'orchestrateur principal de la stack. Il pilote a la fois :

- les controles de disponibilite de la plateforme `frontend + backend + MinIO`
- les traitements planifies autour du cycle de vie des documents
- les rapports de pilotage pour les equipes metier et les operateurs

Les DAGs couvrent maintenant l'ensemble du cycle de vie documentaire et la
supervision globale de la plateforme :

- `bronze_to_silver_orchestration`
  - verifie la disponibilite du backend
  - interroge les documents en attente de validation
  - genere un snapshot de pilotage pour la zone silver
- `silver_validation_followup`
  - detecte les documents bloques trop longtemps en zone silver
  - produit un rapport de suivi pour les operateurs
- `gold_publication_orchestration`
  - recupere les documents valides dans la zone gold
  - construit un manifeste quotidien pour les integrations CRM / ERP
- `stack_health_orchestration`
  - verifie la disponibilite du backend, du frontend et de MinIO
  - consolide une vue d'ensemble de l'etat de la plateforme
- `frontend_backend_consistency_orchestration`
  - controle la coherence entre les files backend exposees au frontend
  - verifie que les compteurs et les apercus de donnees restent alignes
- `document_processing_orchestration`
  - consolide la review queue, les documents bloques et les compteurs
  - prepare un rapport d'exploitation pour l'orchestration documentaire
- `business_reporting_orchestration`
  - centralise les indicateurs metier et financiers du flux documentaire
  - produit un rapport quotidien pour le pilotage business

## Arborescence

```text
airflow/
├── Dockerfile
├── README.md
├── requirements.txt
└── dags/
    ├── bronze_to_silver_orchestration.py
    ├── business_reporting_orchestration.py
    ├── document_processing_orchestration.py
    ├── frontend_backend_consistency_orchestration.py
    ├── gold_publication_orchestration.py
    ├── silver_validation_followup.py
    ├── stack_health_orchestration.py
    └── common/
        ├── __init__.py
        └── project_api.py
```

## Variables principales

- `BACKEND_API_URL` : URL interne du backend FastAPI depuis Airflow
- `FRONTEND_URL` : URL interne du frontend Next.js verifiee par les DAGs de
  supervision
- `MINIO_HEALTHCHECK_URL` : endpoint de healthcheck MinIO verifie par Airflow
- `AIRFLOW_REPORTS_DIR` : dossier ou sont stockes les rapports JSON generes
  par les DAGs, par defaut `/opt/airflow/logs/reports`
- `AIRFLOW_SILVER_STALE_HOURS` : seuil d'alerte pour considerer un document
  silver comme bloque, par defaut `12`
- `AIRFLOW_REQUEST_TIMEOUT_SECONDS` : timeout des appels HTTP vers le backend,
  par defaut `30`

## Schedules

- `bronze_to_silver_orchestration` : toutes les 15 minutes
- `document_processing_orchestration` : toutes les 20 minutes
- `stack_health_orchestration` : toutes les 10 minutes
- `frontend_backend_consistency_orchestration` : toutes les 30 minutes
- `silver_validation_followup` : toutes les heures
- `gold_publication_orchestration` : tous les jours a 07:00 UTC
- `business_reporting_orchestration` : tous les jours a 07:30 UTC

## Rapports generes

Chaque DAG produit un rapport JSON horodate dans `AIRFLOW_REPORTS_DIR` :

- `silver_snapshot_*.json`
  - etat du backend
  - volume de documents en attente
  - repartition par type et statut
  - anciennete des dossiers et echantillon des plus anciens
- `silver_followup_*.json`
  - liste des documents silver depassant le SLA
  - repartition par type
  - compteur de documents avec anomalies bloquantes
- `gold_manifest_*.json`
  - manifeste quotidien des documents gold
  - repartition par type pour les integrations aval
- `stack_health_*.json`
  - etat du backend, du frontend et de MinIO
  - synthese de disponibilite de la plateforme
  - copie du resume d'orchestration expose par le backend
- `frontend_backend_consistency_*.json`
  - controles de coherence entre files silver/gold et compteurs agreges
  - apercu des documents exposes au frontend
- `document_processing_*.json`
  - vue operationnelle de la file de revue et des documents bloques
  - synthese des compteurs documentaires de l'orchestration
- `business_reporting_*.json`
  - indicateurs metier et financiers du flux
  - synthese des publications gold et des documents en attente

## Endpoints backend pour Airflow

Le backend expose des endpoints dedies a l'orchestration, en plus des endpoints
fonctionnels utilises par le frontend :

- `/orchestration/overview`
- `/orchestration/review-queue`
- `/orchestration/stale-documents`
- `/orchestration/publication-summary`
- `/orchestration/business-metrics`

## Architecture

```text
Frontend Next.js -> Backend FastAPI -> SQLite + MinIO
                         ^
                         |
                      Airflow
```

Airflow ne remplace pas l'interface utilisateur du frontend. Il orchestre les
traitements batch, les controles de sante, les rapports et la supervision des
files que le frontend consomme. Les DAGs s'appuient prioritairement sur les
endpoints `/orchestration/*` du backend pour eviter de dependre uniquement des
routes pensees pour l'interface utilisateur.

## Demarrage

Une fois la stack Docker lancee, Airflow est disponible sur
[http://localhost:8080](http://localhost:8080).

Identifiants fixes :

- utilisateur : `admin`
- mot de passe : `admin`
