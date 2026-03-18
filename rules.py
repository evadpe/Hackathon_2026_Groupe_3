"""
Règles métier pour la vérification inter-documents — StepAhead Industries.
Chaque fonction prend des lignes ou documents et retourne une liste d'alertes.
"""

from typing import List, Tuple, Optional
from models import (
    BonCommande, Devis, Facture, Document,
    LigneDocument, Alerte, NiveauAlerte, CategorieArticle,
)

TOLERANCE_CUIR = 0.05  # 5% de tolérance pour le cuir (matière naturelle non uniforme)


# ─────────────────────────────────────────────────────────────────────────────
# Matching des lignes entre deux documents par référence article
# ─────────────────────────────────────────────────────────────────────────────

def matcher_lignes(
    bc: BonCommande,
    facture: Facture,
) -> List[Tuple[Optional[LigneDocument], Optional[LigneDocument]]]:
    """
    Associe les lignes BC ↔ Facture par référence.
    Retourne des paires (ligne_bc, ligne_facture).
    Si une ligne n'a pas de correspondance, l'autre est None.
    """
    pairs: List[Tuple[Optional[LigneDocument], Optional[LigneDocument]]] = []
    facture_dict = {l.reference: l for l in facture.lignes}

    for ligne_bc in bc.lignes:
        ligne_fac = facture_dict.pop(ligne_bc.reference, None)
        pairs.append((ligne_bc, ligne_fac))

    # Lignes facturées sans correspondance dans le BC
    for ligne_fac in facture_dict.values():
        pairs.append((None, ligne_fac))

    return pairs


# ─────────────────────────────────────────────────────────────────────────────
# Vérification des prix
# ─────────────────────────────────────────────────────────────────────────────

def verifier_prix(bc: LigneDocument, fac: LigneDocument) -> List[Alerte]:
    """Compare le prix unitaire. Applicable uniquement si les unités sont identiques."""
    alertes = []

    if bc.unite.lower() != fac.unite.lower():
        # Prix non comparable directement si unités différentes -> vérifier montant_ht
        return verifier_montant_ht(bc, fac)

    if abs(bc.prix_unitaire - fac.prix_unitaire) > 0.001:
        ecart_montant = (fac.prix_unitaire - bc.prix_unitaire) * fac.quantite
        ecart_pct = ((fac.prix_unitaire - bc.prix_unitaire) / bc.prix_unitaire) * 100
        alertes.append(Alerte(
            niveau=NiveauAlerte.ERREUR,
            categorie="PRIX",
            reference_ligne=bc.reference,
            message=f"Prix unitaire modifié par rapport au bon de commande",
            valeur_attendue=f"{bc.prix_unitaire:.2f} EUR/{bc.unite}",
            valeur_recue=f"{fac.prix_unitaire:.2f} EUR/{fac.unite}",
            ecart=f"{ecart_pct:+.1f}%  ->  {ecart_montant:+.2f} EUR sur le total HT",
        ))
    return alertes


def verifier_montant_ht(bc: LigneDocument, fac: LigneDocument) -> List[Alerte]:
    """Compare le montant HT total de la ligne (utile quand les unités diffèrent)."""
    alertes = []
    if abs(bc.montant_ht - fac.montant_ht) > 0.02:
        alertes.append(Alerte(
            niveau=NiveauAlerte.ERREUR,
            categorie="PRIX",
            reference_ligne=bc.reference,
            message="Montant HT de la ligne différent malgré une conversion d'unités",
            valeur_attendue=f"{bc.montant_ht:.2f} EUR",
            valeur_recue=f"{fac.montant_ht:.2f} EUR",
            ecart=f"{fac.montant_ht - bc.montant_ht:+.2f} EUR",
        ))
    return alertes


# ─────────────────────────────────────────────────────────────────────────────
# Vérification des quantités (avec tolérances selon la catégorie)
# ─────────────────────────────────────────────────────────────────────────────

def verifier_quantite(bc: LigneDocument, fac: LigneDocument) -> List[Alerte]:
    alertes = []

    # Unités différentes : déléguer à la vérification de conversion
    if bc.unite.lower() != fac.unite.lower():
        alertes.extend(verifier_conversion_unites(bc, fac))
        return alertes

    if bc.quantite == 0:
        return alertes

    ecart_pct = (fac.quantite - bc.quantite) / bc.quantite

    if bc.categorie == CategorieArticle.CUIR_TEXTILE:
        # Tolérance de 5% (peaux naturelles non uniformes)
        if abs(ecart_pct) > TOLERANCE_CUIR:
            alertes.append(Alerte(
                niveau=NiveauAlerte.ERREUR,
                categorie="QUANTITE",
                reference_ligne=bc.reference,
                message=f"Écart de quantité cuir/textile hors tolérance (max 5%)",
                valeur_attendue=f"{bc.quantite} {bc.unite}",
                valeur_recue=f"{fac.quantite} {fac.unite}",
                ecart=f"{ecart_pct*100:+.1f}% (tolérance : ±5%)",
            ))
        elif abs(ecart_pct) > 0:
            alertes.append(Alerte(
                niveau=NiveauAlerte.INFO,
                categorie="QUANTITE",
                reference_ligne=bc.reference,
                message=f"Légère variation de quantité cuir/textile (dans la tolérance de 5%)",
                valeur_attendue=f"{bc.quantite} {bc.unite}",
                valeur_recue=f"{fac.quantite} {fac.unite}",
                ecart=f"{ecart_pct*100:+.1f}%",
            ))

    elif bc.categorie == CategorieArticle.FOURNITURES:
        # Zéro tolérance + détection d'erreur de zéro (ex: 1000 au lieu de 10 000)
        if fac.quantite != bc.quantite:
            ratio = max(fac.quantite, bc.quantite) / min(fac.quantite, bc.quantite) if min(fac.quantite, bc.quantite) != 0 else 0
            erreur_zero = ratio in (10.0, 100.0, 1000.0)
            msg = "Quantite fournitures incorrecte"
            if erreur_zero:
                msg += f" [!] POSSIBLE ERREUR DE ZERO (facteur x{ratio:.0f})"
            alertes.append(Alerte(
                niveau=NiveauAlerte.ERREUR,
                categorie="QUANTITE",
                reference_ligne=bc.reference,
                message=msg,
                valeur_attendue=f"{bc.quantite:.0f} {bc.unite}",
                valeur_recue=f"{fac.quantite:.0f} {fac.unite}",
                ecart=f"Facteur ×{ratio:.0f}" if erreur_zero else f"{fac.quantite - bc.quantite:+.0f}",
            ))

    else:
        # Semelles/talons : vérification stricte
        if fac.quantite != bc.quantite:
            alertes.append(Alerte(
                niveau=NiveauAlerte.ERREUR,
                categorie="QUANTITE",
                reference_ligne=bc.reference,
                message="Quantité semelles/talons incorrecte",
                valeur_attendue=f"{bc.quantite} {bc.unite}",
                valeur_recue=f"{fac.quantite} {fac.unite}",
                ecart=f"{fac.quantite - bc.quantite:+.0f}",
            ))

    return alertes


# ─────────────────────────────────────────────────────────────────────────────
# Vérification des pointures (semelles et talons uniquement)
# ─────────────────────────────────────────────────────────────────────────────

def verifier_pointure(bc: LigneDocument, fac: LigneDocument) -> List[Alerte]:
    alertes = []

    if bc.categorie != CategorieArticle.SEMELLES_TALONS:
        return alertes

    if bc.pointure is None:
        return alertes

    if fac.pointure is None:
        alertes.append(Alerte(
            niveau=NiveauAlerte.AVERTISSEMENT,
            categorie="POINTURE",
            reference_ligne=bc.reference,
            message="Pointure non renseignée sur la facture",
            valeur_attendue=f"Pointure {bc.pointure}",
            valeur_recue="Non renseignée",
        ))
    elif bc.pointure != fac.pointure:
        alertes.append(Alerte(
            niveau=NiveauAlerte.ERREUR,
            categorie="POINTURE",
            reference_ligne=bc.reference,
            message="Pointure incorrecte sur la facture",
            valeur_attendue=f"Pointure {bc.pointure}",
            valeur_recue=f"Pointure {fac.pointure}",
            ecart=f"Différence de {abs(fac.pointure - bc.pointure)} pointure(s)",
        ))

    return alertes


# ─────────────────────────────────────────────────────────────────────────────
# Vérification des conversions d'unités
# ─────────────────────────────────────────────────────────────────────────────

def verifier_conversion_unites(bc: LigneDocument, fac: LigneDocument) -> List[Alerte]:
    """
    Vérifie la cohérence quand les unités BC ≠ Facture.
    Utilise la règle de conversion définie dans le JSON du BC.
    Ex : BC commande 10 rouleaux (1 rouleau = 500 m), la facture doit indiquer 5000 m.
    """
    alertes = []

    if bc.conversion is None:
        alertes.append(Alerte(
            niveau=NiveauAlerte.AVERTISSEMENT,
            categorie="UNITE",
            reference_ligne=bc.reference,
            message="Unités différentes entre commande et facture, aucune règle de conversion définie dans le BC",
            valeur_attendue=f"{bc.quantite} {bc.unite}",
            valeur_recue=f"{fac.quantite} {fac.unite}",
        ))
        return alertes

    if fac.unite.lower() == bc.conversion.unite_equivalente.lower():
        quantite_attendue = bc.quantite * bc.conversion.facteur
        ecart = fac.quantite - quantite_attendue

        if abs(ecart) > 0.01:
            alertes.append(Alerte(
                niveau=NiveauAlerte.ERREUR,
                categorie="UNITE",
                reference_ligne=bc.reference,
                message="Conversion d'unités incohérente",
                valeur_attendue=(
                    f"{quantite_attendue:.1f} {fac.unite}  "
                    f"({bc.quantite} {bc.unite} × {bc.conversion.facteur:.0f})"
                ),
                valeur_recue=f"{fac.quantite} {fac.unite}",
                ecart=f"{ecart:+.1f} {fac.unite}",
            ))
        else:
            alertes.append(Alerte(
                niveau=NiveauAlerte.INFO,
                categorie="UNITE",
                reference_ligne=bc.reference,
                message=(
                    f"Unités différentes mais conversion cohérente : "
                    f"{bc.quantite} {bc.unite} = {fac.quantite} {fac.unite}"
                ),
                valeur_attendue=f"{bc.quantite} {bc.unite}",
                valeur_recue=f"{fac.quantite} {fac.unite}",
            ))
    else:
        alertes.append(Alerte(
            niveau=NiveauAlerte.AVERTISSEMENT,
            categorie="UNITE",
            reference_ligne=bc.reference,
            message="Unité de facturation inattendue (ni l'unité commandée, ni l'équivalent connu)",
            valeur_attendue=f"{bc.unite} ou {bc.conversion.unite_equivalente}",
            valeur_recue=fac.unite,
        ))

    return alertes


# ─────────────────────────────────────────────────────────────────────────────
# Vérification des frais de port (BC / Devis -> Facture)
# ─────────────────────────────────────────────────────────────────────────────

def verifier_frais_port(devis: Devis, facture: Facture) -> List[Alerte]:
    alertes = []

    if devis.franco_de_port and facture.frais_port > 0:
        alertes.append(Alerte(
            niveau=NiveauAlerte.ERREUR,
            categorie="FRAIS_PORT",
            message="Frais de port facturés alors que le devis stipule 'franco de port'",
            valeur_attendue="0.00 EUR (franco de port)",
            valeur_recue=f"{facture.frais_port:.2f} EUR",
            ecart=f"+{facture.frais_port:.2f} EUR non prévu",
        ))
    elif not devis.franco_de_port and devis.frais_port > 0:
        if abs(devis.frais_port - facture.frais_port) > 0.01:
            alertes.append(Alerte(
                niveau=NiveauAlerte.AVERTISSEMENT,
                categorie="FRAIS_PORT",
                message="Montant des frais de port différent du devis",
                valeur_attendue=f"{devis.frais_port:.2f} EUR",
                valeur_recue=f"{facture.frais_port:.2f} EUR",
                ecart=f"{facture.frais_port - devis.frais_port:+.2f} EUR",
            ))

    return alertes


# ─────────────────────────────────────────────────────────────────────────────
# Vérification de la cohérence interne des totaux d'un document
# ─────────────────────────────────────────────────────────────────────────────

def verifier_totaux(doc: Document, label: str) -> List[Alerte]:
    alertes = []

    # Total HT = Σ lignes + frais de port
    total_calcule = sum(l.montant_ht for l in doc.lignes) + doc.frais_port
    if abs(total_calcule - doc.total_ht) > 0.02:
        alertes.append(Alerte(
            niveau=NiveauAlerte.ERREUR,
            categorie="TOTAL",
            message=f"Total HT incohérent sur le {label}",
            valeur_attendue=f"{total_calcule:.2f} EUR (calculé)",
            valeur_recue=f"{doc.total_ht:.2f} EUR (déclaré)",
            ecart=f"{doc.total_ht - total_calcule:+.2f} EUR",
        ))

    # Total TTC = Total HT + TVA
    ttc_calcule = doc.total_ht + doc.tva_montant
    if abs(ttc_calcule - doc.total_ttc) > 0.02:
        alertes.append(Alerte(
            niveau=NiveauAlerte.ERREUR,
            categorie="TOTAL",
            message=f"Total TTC incohérent sur le {label}",
            valeur_attendue=f"{ttc_calcule:.2f} EUR (calculé)",
            valeur_recue=f"{doc.total_ttc:.2f} EUR (déclaré)",
            ecart=f"{doc.total_ttc - ttc_calcule:+.2f} EUR",
        ))

    return alertes
