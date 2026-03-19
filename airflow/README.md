# Airflow orchestration

Ce dossier contient l'architecture d'orchestration Airflow du projet de
conformite documentaire.

## Objectif

Airflow complete l'orchestration evenementielle de `n8n` avec des traitements
planifies sur le cycle de vie des documents du data lake medaillon :

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

## Arborescence

```text
airflow/
├── Dockerfile
├── README.md
├── requirements.txt
└── dags/
    ├── bronze_to_silver_orchestration.py
    ├── gold_publication_orchestration.py
    ├── silver_validation_followup.py
    └── common/
        ├── __init__.py
        └── project_api.py
```

## Variables principales

- `BACKEND_API_URL` : URL interne du backend FastAPI depuis Airflow
- `AIRFLOW_REPORTS_DIR` : dossier ou sont stockes les rapports JSON generes
  par les DAGs, par defaut `/opt/airflow/logs/reports`

## Demarrage

Une fois la stack Docker lancee, Airflow est disponible sur
[http://localhost:8080](http://localhost:8080).

Identifiants fixes :

- utilisateur : `admin`
- mot de passe : `admin`
