# Architecture Data Lake HDFS

Cette version du backend peut stocker les documents directement dans un data lake logique organise en quatre zones :

- `bronze/raw` : fichiers source uploades (`pdf`, `json`)
- `silver/extracted` : resultats OCR/extraction en attente de validation
- `gold/validated` : donnees corrigees et validees par l'operateur
- `metadata/documents` : catalogue des documents, statut, chemins et dates

## Vue d'ensemble

```text
Frontend Next.js
    |
    v
FastAPI /documents/upload
    |
    +--> bronze/raw/<session>/<file>
    |
    +--> OCR / parsing
            |
            v
        silver/extracted/<doc_id>.json
            |
            v
FastAPI /documents/{id}/validate
    |
    v
gold/validated/<doc_id>.json
    |
    v
metadata/documents/<doc_id>.json
```

## Sur HDFS

Quand `STORAGE_BACKEND=hdfs`, les memes zones sont ecrites sous `HDFS_BASE_PATH`.

Exemple :

```text
/stepahead-lake/
  bronze/raw/8f12ab34/7fd91f42c3c1.pdf
  silver/extracted/FACTURE-8f12ab34.json
  gold/validated/FACTURE-8f12ab34.json
  metadata/documents/FACTURE-8f12ab34.json
```

## Variables d'environnement

- `STORAGE_BACKEND=local|hdfs`
- `DATA_LAKE_BASE_DIR=/app/backend/data_lake`
- `HDFS_URL=http://namenode:9870`
- `HDFS_USER=hdfs`
- `HDFS_BASE_PATH=/stepahead-lake`

## Conteneurs HDFS inclus

Le `docker-compose.yml` embarque maintenant :

- `namenode` : interface HDFS et WebHDFS
- `datanode` : stockage des blocs HDFS
- `backend` : connecte directement a `http://namenode:9870`

Ports exposes :

- `9870` : UI NameNode / WebHDFS
- `9000` : endpoint HDFS interne
- `9864` : UI DataNode
- `8000` : API backend
- `3000` : frontend

## Demarrage

Pour lancer toute l'architecture :

```bash
docker compose up --build
```

Le backend utilisera HDFS par defaut via :

```text
STORAGE_BACKEND=hdfs
HDFS_URL=http://namenode:9870
HDFS_USER=hdfs
HDFS_BASE_PATH=/stepahead-lake
```

## Verification

Une fois les conteneurs demarres :

- UI NameNode : [http://localhost:9870](http://localhost:9870)
- API backend : [http://localhost:8000/health](http://localhost:8000/health)

Le endpoint `/health` doit retourner un `storageBackend` egal a `hdfs`.

## Remarques d'architecture

- Le backend ne depend plus d'un dossier local `uploads` pour fonctionner.
- Les fichiers sont servis via `GET /files/{storage_path}` meme quand ils sont stockes dans HDFS.
- `silver` et `gold` ne sont plus seulement des statuts memoire : ils correspondent maintenant a de vraies zones persistantes.
- `metadata/documents` joue le role de catalogue minimal pour lister les documents et retrouver leurs chemins dans le lake.

## Ce que stocke chaque zone

- `bronze/raw` : binaire original, jamais modifie
- `silver/extracted` : OCR brut ou structure intermediaire
- `gold/validated` : version metier validee
- `metadata/documents` : id, type, statut, dates, anomalies, chemins `bronze/silver/gold`
