
Documentation API : Système de Traitement OCR (SaaS)
Cette API gère le cycle de vie des documents comptables, de l'upload brut à la certification des données.


# Liste des Endpoints à Implémenter. 


## Collecte & Analyse (Transition Bronze -> Silver)

Endpoint : POST /api/documents/upload

Description : Reçoit un ou plusieurs fichiers, les stocke localement (Bronze), lance l'OCR, et renvoie les données extraites (Silver).

Input : multipart/form-data (Files)

Output : List[DocumentSchema]

Logique Service : Appeler ocr_service.extract_data(file) pour chaque fichier.



## Gestion du Flux (Silver Zone)

Endpoint : GET /api/documents/pending

Description : Récupère tous les documents ayant le statut silver pour affichage dans la sidebar de conformité.

Output : List[DocumentSchema]


## Récupérer un document unique

Méthode : GET

Route : /api/documents/{doc_id}

Réponse : L'objet AdminDocument complet.

Utilité : Permet d'ouvrir un document directement via son ID (ex: lien direct depuis un email ou un log).

## Certification des Données (Transition Silver -> Gold)

Endpoint : PUT /api/documents/{doc_id}/validate

Description : Reçoit les corrections de l'utilisateur, met à jour l'objet en base et change le statut en gold.

Input : { "extractedData": { ... } }

Output : DocumentSchema (Status updated)



## Consultation Métier (Gold Zone / CRM)

Endpoint : GET /api/documents/gold

Description : Récupère les données certifiées pour le Dashboard. Doit supporter la recherche et le filtrage.

Query Params : search (string), type (string).

Output : List[DocumentSchema]


## Rejeter un document

Méthode : PATCH (ou POST)

Route : /api/documents/{doc_id}/reject

Body (optionnel) : { "reason": "string" } (ex: "Image illisible", "Document non conforme")