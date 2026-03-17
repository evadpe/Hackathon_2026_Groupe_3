# Format d'annotation

## Objectif

Chaque document généré possède une annotation JSON associée.
Cette annotation stocke :
- le type de document
- le fournisseur concerné
- les champs extraits attendus
- le scénario appliqué
- les anomalies attendues
- la qualité visuelle du document

---

## Annotation document

Exemple :

```json
{
  "document_id": "supplier_001_invoice_001",
  "supplier_id": "supplier_001",
  "document_type": "invoice",
  "scenario": "normal_pdf_clean",
  "is_authentic": true,
  "is_coherent": true,
  "fields": {
    "invoice_number": "FAC-2026-001",
    "issue_date": "2026-03-17",
    "company_name": "Cuir Excellence SAS",
    "siren": "123456789",
    "siret": "12345678900012",
    "product_name": "Cuir noir pleine fleur",
    "quantity": 120,
    "unit": "m²",
    "unit_price": 18.50,
    "amount_ht": 2220.00,
    "amount_tva": 444.00,
    "amount_ttc": 2664.00
  },
  "quality": {
    "blur": false,
    "rotation": 0,
    "noise": false,
    "contrast": "normal",
    "scan_type": "pdf"
  },
  "expected_flags": []
}