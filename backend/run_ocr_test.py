"""
Adaptateur OCR → vérification inter-documents.

Convertit les JSON produits par l'OCR (format Ilham) vers le format
attendu par les modèles Pydantic, puis lance la vérification pour chaque
dossier client trouvé dans resultats_json/.
"""

import sys
import os
import json
from pathlib import Path

if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from models import BonCommande, Devis, Facture
from verifier import VerificateurDocuments
from report import afficher_rapport, exporter_rapport_json


# Correspondance entre le type retourné par l'OCR et le type interne utilisé dans le code
TYPE_MAP = {
    "Facture":        "facture",
    "Bon de Commande": "bon_commande",
    "Devis":          "devis",
}

# Catégorie appliquée par défaut si l'OCR ne précise pas le type de matériau
CATEGORIE_PAR_DEFAUT = "fournitures"

MOTS_CLES_CATEGORIE = {
    "cuir_textile":    ["cuir", "textile", "tissu", "toile", "daim", "nubuck", "respirant", "coton", "polyester"],
    "semelles_talons": ["semelle", "talon", "gomme", "caoutchouc"],
}


def deviner_categorie(description: str) -> str:
    desc = description.lower()
    for cat, mots in MOTS_CLES_CATEGORIE.items():
        if any(m in desc for m in mots):
            return cat
    return CATEGORIE_PAR_DEFAUT


def tva_str_to_float(tva_rate) -> float:
    """Convertit '20%' ou 20 ou 20.0 en float."""
    if isinstance(tva_rate, str):
        return float(tva_rate.replace("%", "").strip())
    return float(tva_rate)


def adapter_ocr(data: dict) -> dict:
    """Transforme un dict OCR en dict compatible avec les modèles Document."""
    doc_info  = data.get("doc_info", {})
    vendor    = data.get("vendor", {})
    financials = data.get("financials", {})
    raw_lines = data.get("line_items", [])

    lignes = []
    for i, item in enumerate(raw_lines):
        desc = item.get("description", f"Article {i+1}")
        lignes.append({
            "reference":     item.get("reference", f"REF-{i+1:03d}"),
            "description":   desc,
            "categorie":     item.get("categorie", deviner_categorie(desc)),
            "quantite":      item.get("qty", item.get("quantite", 0)),
            "unite":         item.get("unit", item.get("unite", "unite")),
            "pointure":      item.get("pointure"),
            "couleur":       item.get("couleur"),
            "prix_unitaire": item.get("pu_ht", item.get("prix_unitaire", 0.0)),
            "montant_ht":    item.get("total_ht", item.get("montant_ht", 0.0)),
        })

    tva_taux = tva_str_to_float(financials.get("tva_rate", financials.get("tva_taux", 20.0)))
    # Si le taux est 0 mais qu'il y a un montant TVA, on recalcule
    total_ht = financials.get("total_ht", 0.0)
    tva_montant = financials.get("tva_amount", financials.get("tva_montant", 0.0))
    total_ttc   = financials.get("total_ttc", 0.0)

    if tva_taux == 0.0 and total_ht > 0 and total_ttc > 0 and total_ttc != total_ht:
        tva_montant = round(total_ttc - total_ht, 2)
        tva_taux    = round(tva_montant / total_ht * 100, 1) if total_ht else 20.0

    return {
        "numero":      doc_info.get("number", "INCONNU"),
        "date":        doc_info.get("date", ""),
        "fournisseur": {
            "nom":   vendor.get("name", "Fournisseur inconnu"),
            "siret": vendor.get("siret"),
        },
        "lignes":       lignes,
        "frais_port":   data.get("frais_port", 0.0),
        "franco_de_port": data.get("franco_de_port", False),
        "total_ht":     total_ht,
        "tva_taux":     tva_taux,
        "tva_montant":  tva_montant,
        "total_ttc":    total_ttc,
    }


def charger_et_adapter(chemin: Path) -> dict:
    with open(chemin, encoding="utf-8") as f:
        raw = json.load(f)
    return adapter_ocr(raw)


def detecter_type(chemin: Path) -> str:
    """Retourne 'facture', 'bon_commande' ou 'devis' selon le contenu du fichier."""
    with open(chemin, encoding="utf-8") as f:
        raw = json.load(f)
    type_ocr = raw.get("metadata", {}).get("type", "")
    return TYPE_MAP.get(type_ocr, "inconnu")


def traiter_dossier(dossier: Path, export_dir: Path | None = None):
    print(f"\n{'='*60}")
    print(f"  Dossier : {dossier.name}")
    print(f"{'='*60}")

    # Classifier les fichiers JSON du dossier
    docs = {"facture": None, "bon_commande": None, "devis": None}
    for fpath in sorted(dossier.glob("*.json")):
        t = detecter_type(fpath)
        if t in docs:
            docs[t] = fpath
            print(f"  [{t.upper()}] {fpath.name}")
        else:
            print(f"  [?] {fpath.name} — type non reconnu, ignoré")

    if docs["bon_commande"] is None or docs["facture"] is None:
        print("  ERREUR : bon de commande ou facture manquant, dossier ignoré.")
        return

    # Charger et adapter
    data_bc  = charger_et_adapter(docs["bon_commande"])
    data_fac = charger_et_adapter(docs["facture"])

    bon_commande = BonCommande.model_validate(data_bc)
    facture      = Facture.model_validate(data_fac)

    devis = None
    if docs["devis"]:
        data_devis = charger_et_adapter(docs["devis"])
        devis = Devis.model_validate(data_devis)

    print(f"\n  BC    : {bon_commande.numero}")
    print(f"  Devis : {devis.numero if devis else 'N/A'}")
    print(f"  Fac   : {facture.numero}")
    print("\n  Lancement de la vérification...\n")

    verificateur = VerificateurDocuments()
    rapport = verificateur.verifier(bon_commande, facture, devis)
    afficher_rapport(rapport)

    if export_dir:
        export_dir.mkdir(parents=True, exist_ok=True)
        nom_fichier = export_dir / f"rapport_{dossier.name.replace(' ', '_')}.json"
        with open(nom_fichier, "w", encoding="utf-8") as f:
            f.write(exporter_rapport_json(rapport))
        print(f"\n  Rapport exporté -> {nom_fichier}")

    return rapport


def main():
    resultats_dir = Path(__file__).parent / "resultats_json"
    export_dir    = Path(__file__).parent / "rapports_ocr"

    if not resultats_dir.exists():
        print(f"Dossier introuvable : {resultats_dir}")
        sys.exit(1)

    dossiers = sorted([d for d in resultats_dir.iterdir() if d.is_dir()])
    if not dossiers:
        print("Aucun sous-dossier trouvé dans resultats_json/")
        sys.exit(1)

    print(f"Trouvé {len(dossiers)} dossier(s) client(s) à traiter.")

    rapports = []
    for dossier in dossiers:
        r = traiter_dossier(dossier, export_dir=export_dir)
        if r:
            rapports.append(r)

    # Résumé global
    print(f"\n{'='*60}")
    print("  RÉSUMÉ GLOBAL")
    print(f"{'='*60}")
    for r in rapports:
        statut_icon = "OK" if r.statut == "CONFORME" else ("!!" if r.statut == "A_VERIFIER" else "XX")
        print(f"  [{statut_icon}] BC {r.numero_bon_commande} / FAC {r.numero_facture} → {r.statut}"
              f"  ({r.nb_erreurs} err, {r.nb_avertissements} avert)")

    non_conformes = [r for r in rapports if r.statut == "NON_CONFORME"]
    sys.exit(1 if non_conformes else 0)


if __name__ == "__main__":
    main()
