# Spécification des documents générés

## Contexte métier

Les documents générés concernent une entreprise de fabrication de chaussures.
Les fournisseurs représentent des fournisseurs de matières premières et de composants :
- cuir
- textile
- semelles
- talons
- lacets
- œillets
- colle
- fil de couture

## Types de documents

1. Facture
2. Devis
3. Bon de commande

---

## 1. Facture

### Champs généraux
- document_id
- supplier_id
- invoice_number
- issue_date
- due_date
- company_name
- address
- postal_code
- city
- siren
- siret
- vat_number

### Champs métier
- product_name
- quantity
- unit
- unit_price
- amount_ht
- amount_tva
- amount_ttc
- currency

### Champs critiques
- supplier_id
- siren
- siret
- product_name
- quantity
- unit
- unit_price
- amount_ht
- amount_tva
- amount_ttc

---

## 2. Devis

### Champs généraux
- document_id
- supplier_id
- quote_number
- issue_date
- valid_until
- company_name
- address
- postal_code
- city
- siren
- siret
- vat_number

### Champs métier
- product_name
- quantity
- unit
- unit_price
- amount_ht
- amount_tva
- amount_ttc
- currency

### Champs critiques
- supplier_id
- siren
- siret
- product_name
- quantity
- unit
- unit_price
- amount_ht
- amount_ttc

---

## 3. Bon de commande

### Champs généraux
- document_id
- supplier_id
- purchase_order_number
- issue_date

### Champs acheteur / émetteur
- buyer_company_name
- buyer_address
- buyer_postal_code
- buyer_city
- buyer_siren
- buyer_siret
- buyer_vat_number

### Champs fournisseur
- supplier_company_name
- supplier_address
- supplier_postal_code
- supplier_city
- supplier_siren
- supplier_siret
- supplier_vat_number

### Champs métier
- product_name
- quantity
- unit
- expected_unit_price
- expected_amount_ht
- currency

### Champs critiques
- buyer_company_name
- supplier_company_name
- supplier_siren
- supplier_siret
- supplier_vat_number
- product_name
- quantity
- unit
- expected_unit_price