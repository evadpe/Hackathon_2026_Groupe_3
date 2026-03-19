"""
Point d'entrée — Vérification inter-documents StepAhead Industries.

Utilisation :
    python main.py                              # Utilise les fichiers de démo dans data/
    python main.py bc.json devis.json fac.json  # Fichiers personnalisés
    python main.py bc.json devis.json fac.json --export rapport.json
"""

import sys
import os
import json
from pathlib import Path

# Active UTF-8 et ANSI dans le terminal Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from models import BonCommande, Devis, Facture
from verifier import VerificateurDocuments
from report import afficher_rapport, exporter_rapport_json

# Chemins par défaut vers les fichiers de démonstration
DATA_DIR = Path(__file__).parent / "data"
DEFAULT_BC     = DATA_DIR / "sample_bc.json"
DEFAULT_DEVIS  = DATA_DIR / "sample_devis.json"
DEFAULT_FACTURE = DATA_DIR / "sample_facture.json"


def charger_json(chemin: Path) -> dict:
    """Charge un fichier JSON en filtrant les clés de commentaire (_xxx)."""
    with open(chemin, encoding="utf-8") as f:
        data = json.load(f)
    # Supprimer les clés de commentaire ajoutées pour la démo
    return {k: v for k, v in data.items() if not k.startswith("_")}


def nettoyer_lignes(lignes: list[dict]) -> list[dict]:
    """Retire les clés de commentaire dans chaque ligne."""
    return [{k: v for k, v in ligne.items() if not k.startswith("_")} for ligne in lignes]


def main():
    args = sys.argv[1:]

    # Résolution des fichiers à partir des arguments de la ligne de commande
    export_fichier = None
    fichiers = []
    i = 0
    while i < len(args):
        if args[i] == "--export" and i + 1 < len(args):
            export_fichier = args[i + 1]
            i += 2
        else:
            fichiers.append(args[i])
            i += 1

    if len(fichiers) == 0:
        # Mode démo avec les fichiers de l'arborescence data/
        chemin_bc      = DEFAULT_BC
        chemin_devis   = DEFAULT_DEVIS
        chemin_facture = DEFAULT_FACTURE
        print("  >> Mode demo : utilisation des fichiers dans data/\n")
    elif len(fichiers) == 3:
        chemin_bc, chemin_devis, chemin_facture = [Path(f) for f in fichiers]
    elif len(fichiers) == 2:
        chemin_bc, chemin_facture = [Path(f) for f in fichiers]
        chemin_devis = None
    else:
        print("Usage : python main.py [bc.json devis.json facture.json] [--export rapport.json]")
        sys.exit(1)

    # Chargement et validation des trois documents
    print("Chargement des documents...")

    data_bc = charger_json(chemin_bc)
    data_bc["lignes"] = nettoyer_lignes(data_bc.get("lignes", []))
    bon_commande = BonCommande.model_validate(data_bc)

    devis = None
    if chemin_devis and Path(chemin_devis).exists():
        data_devis = charger_json(chemin_devis)
        data_devis["lignes"] = nettoyer_lignes(data_devis.get("lignes", []))
        devis = Devis.model_validate(data_devis)

    data_fac = charger_json(chemin_facture)
    data_fac["lignes"] = nettoyer_lignes(data_fac.get("lignes", []))
    facture = Facture.model_validate(data_fac)

    print(f"  [OK] Bon de commande : {bon_commande.numero}")
    print(f"  [OK] Devis           : {devis.numero if devis else 'N/A'}")
    print(f"  [OK] Facture         : {facture.numero}")
    print("\nLancement de la verification...\n")

    # Lancement de la vérification inter-documents
    verificateur = VerificateurDocuments()
    rapport = verificateur.verifier(bon_commande, facture, devis)

    # Affichage du rapport dans le terminal
    afficher_rapport(rapport)

    # Export JSON du rapport si le flag --export a été passé
    if export_fichier:
        with open(export_fichier, "w", encoding="utf-8") as f:
            f.write(exporter_rapport_json(rapport))
        print(f"Rapport exporte -> {export_fichier}")

    # Code de sortie : 0 si conforme, 1 si anomalies détectées
    sys.exit(0 if rapport.statut == "CONFORME" else 1)


if __name__ == "__main__":
    main()
