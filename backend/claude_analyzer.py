"""
Analyse sémantique des descriptions sans LLM.
Détecte les incohérences de couleur et de matière par règles et similarité de texte.
"""

from difflib import SequenceMatcher
from typing import List, Tuple
from models import LigneDocument, Alerte, NiveauAlerte

# Palettes de couleurs : si deux couleurs sont dans le même groupe, elles sont considérées identiques
GROUPES_COULEURS = [
    {"noir", "black", "ebene", "ebène", "anthracite", "charbon"},
    {"blanc", "white", "ivoire", "creme", "crème", "ecru", "écru", "nacre"},
    {"marron", "brun", "caramel", "chocolat", "cognac", "tabac", "noisette", "havane"},
    {"rouge", "bordeaux", "grenat", "vermillon", "carmin", "cramoisi"},
    {"bleu", "marine", "bleu marine", "navy", "cobalt", "azur", "indigo", "bleu nuit"},
    {"vert", "kaki", "olive", "sauge", "emeraude", "émeraude", "bouteille"},
    {"beige", "sable", "taupe", "nude", "naturel"},
    {"gris", "argent", "silver", "perle", "acier"},
    {"or", "gold", "dore", "doré", "bronze", "laiton"},
    {"jaune", "ocre", "moutarde", "citron"},
    {"rose", "fuchsia", "corail", "saumon", "poudre"},
    {"violet", "lilas", "prune", "aubergine", "parme", "mauve"},
    {"orange", "rouille", "terre cuite", "brique"},
]


def _normaliser(texte: str) -> str:
    """Passe le texte en minuscules et retire les accents pour comparer sans se tromper."""
    if not texte:
        return ""
    t = texte.lower().strip()
    remplacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ù": "u", "û": "u", "ü": "u",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ç": "c",
    }
    for accent, sans in remplacements.items():
        t = t.replace(accent, sans)
    return t


def _groupe_couleur(couleur: str) -> int | None:
    """Trouve dans quelle palette se trouve une couleur (retourne None si inconnue)."""
    c = _normaliser(couleur)
    for i, groupe in enumerate(GROUPES_COULEURS):
        for membre in groupe:
            if _normaliser(membre) in c or c in _normaliser(membre):
                return i
    return None


def _couleurs_compatibles(c1: str, c2: str) -> bool:
    """Retourne True si les deux couleurs sont de la même famille (ex: 'marine' et 'navy')."""
    if _normaliser(c1) == _normaliser(c2):
        return True
    g1 = _groupe_couleur(c1)
    g2 = _groupe_couleur(c2)
    if g1 is None or g2 is None:
        # Couleur inconnue : on compare les chaînes directement
        return _normaliser(c1) in _normaliser(c2) or _normaliser(c2) in _normaliser(c1)
    return g1 == g2


def _similarite(a: str, b: str) -> float:
    """Mesure à quel point deux textes se ressemblent, de 0 (rien en commun) à 1 (identiques)."""
    return SequenceMatcher(None, _normaliser(a), _normaliser(b)).ratio()


# Matières dont un remplacement serait une fraude grave (ex: cuir vrai → simili)
MATIERES_CRITIQUES = [
    {"cuir", "leather"},
    {"cuir synthetique", "simili", "synthetique", "pu", "polyurethane"},
    {"gomme", "caoutchouc", "rubber"},
    {"thermoplastique", "tpu", "eva"},
    {"textile", "tissu", "toile", "nylon", "polyester"},
    {"daim", "nubuck", "velours"},
    {"liege", "liège"},
]


def _detecter_matiere(description: str) -> int | None:
    """Cherche quelle matière critique est mentionnée dans une description de produit."""
    d = _normaliser(description)
    for i, groupe in enumerate(MATIERES_CRITIQUES):
        for mot in groupe:
            if _normaliser(mot) in d:
                return i
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Fonction principale
# ─────────────────────────────────────────────────────────────────────────────

def analyser_coherence_semantique(
    lignes_bc: List[LigneDocument],
    lignes_facture: List[LigneDocument],
) -> Tuple[List[Alerte], str]:
    """
    Compare ligne par ligne le bon de commande et la facture sur 3 points :
    1. La couleur est-elle la même famille ?
    2. La matière a-t-elle été substituée (ex: cuir → simili) ?
    3. Les descriptions se ressemblent-elles globalement (score > 40%) ?

    Retourne : (liste d'alertes, résumé textuel)
    """
    facture_dict = {l.reference: l for l in lignes_facture}
    alertes: List[Alerte] = []
    nb_ok = 0
    details = []

    for ligne_bc in lignes_bc:
        ligne_fac = facture_dict.get(ligne_bc.reference)
        if not ligne_fac:
            continue

        ref = ligne_bc.reference

        # Vérifie que la couleur facturée est dans la même famille que celle commandée
        if ligne_bc.couleur and ligne_fac.couleur:
            if not _couleurs_compatibles(ligne_bc.couleur, ligne_fac.couleur):
                alertes.append(Alerte(
                    niveau=NiveauAlerte.ERREUR,
                    categorie="DESCRIPTION",
                    reference_ligne=ref,
                    message=(
                        f"Couleur incorrecte sur la facture : "
                        f"'{ligne_bc.couleur}' commande, '{ligne_fac.couleur}' facture"
                    ),
                    valeur_attendue=ligne_bc.couleur,
                    valeur_recue=ligne_fac.couleur,
                    ecart="Couleurs de familles differentes",
                ))
                details.append(f"{ref}: couleur NOK ({ligne_bc.couleur} != {ligne_fac.couleur})")
            else:
                nb_ok += 1

        # Détecte si on a remplacé une matière critique par une autre (fraude potentielle)
        mat_bc  = _detecter_matiere(ligne_bc.description)
        mat_fac = _detecter_matiere(ligne_fac.description)
        if mat_bc is not None and mat_fac is not None and mat_bc != mat_fac:
            alertes.append(Alerte(
                niveau=NiveauAlerte.ERREUR,
                categorie="DESCRIPTION",
                reference_ligne=ref,
                message="Matiere differente entre commande et facture",
                valeur_attendue=ligne_bc.description[:60],
                valeur_recue=ligne_fac.description[:60],
                ecart="Substitution de matiere critique detectee",
            ))
            details.append(f"{ref}: matiere NOK")

        # Si aucune matière connue détectée, compare les descriptions textuellement
        elif mat_bc is None and mat_fac is None:
            score = _similarite(ligne_bc.description, ligne_fac.description)
            if score < 0.40:
                alertes.append(Alerte(
                    niveau=NiveauAlerte.AVERTISSEMENT,
                    categorie="DESCRIPTION",
                    reference_ligne=ref,
                    message="Descriptions très différentes entre commande et facture",
                    valeur_attendue=ligne_bc.description[:60],
                    valeur_recue=ligne_fac.description[:60],
                    ecart=f"Similarite : {score*100:.0f}%",
                ))
                details.append(f"{ref}: description differente ({score*100:.0f}%)")
            else:
                nb_ok += 1

    # Résumé lisible pour l'opérateur
    if not alertes:
        resume = (
            f"Analyse semantique OK : {nb_ok} ligne(s) verifiee(s), "
            "aucune incoherence de couleur ou de matiere detectee."
        )
    else:
        resume = (
            f"Analyse semantique : {len(alertes)} incoherence(s) detectee(s). "
            + " | ".join(details)
        )

    return alertes, resume
