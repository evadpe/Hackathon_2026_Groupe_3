"""
Moteur principal de vérification inter-documents (rapprochement tripartite).
Orchestre les règles métier et l'analyse sémantique Claude.
"""

from datetime import datetime
from typing import Optional

from models import (
    BonCommande, Devis, Facture,
    Alerte, NiveauAlerte, RapportVerification,
)
from rules import (
    matcher_lignes,
    verifier_prix,
    verifier_quantite,
    verifier_pointure,
    verifier_frais_port,
    verifier_totaux,
)
from claude_analyzer import analyser_coherence_semantique


class VerificateurDocuments:
    """
    Compare les trois documents entre eux : Bon de Commande ↔ Devis ↔ Facture.
    Le Devis est optionnel — s'il manque, on ignore juste la vérification des frais de port.
    """

    def verifier(
        self,
        bon_commande: BonCommande,
        facture: Facture,
        devis: Optional[Devis] = None,
    ) -> RapportVerification:

        toutes_alertes: list[Alerte] = []

        # Étape 1 : les totaux du document sont-ils cohérents en interne (HT + TVA = TTC) ?
        toutes_alertes.extend(verifier_totaux(facture, "facture"))
        if devis:
            toutes_alertes.extend(verifier_totaux(devis, "devis"))

        # Étape 2 : on associe chaque ligne du BC à sa ligne correspondante dans la facture
        pairs = matcher_lignes(bon_commande, facture)

        for bc_ligne, fac_ligne in pairs:

            # Une ligne est facturée mais n'a jamais été commandée → suspect
            if bc_ligne is None:
                toutes_alertes.append(Alerte(
                    niveau=NiveauAlerte.ERREUR,
                    categorie="LIGNE_INCONNUE",
                    reference_ligne=fac_ligne.reference,
                    message="Ligne facturée absente du bon de commande",
                    valeur_attendue="Absent du BC",
                    valeur_recue=f"{fac_ligne.description}  ({fac_ligne.quantite} {fac_ligne.unite})",
                ))
                continue

            # Une ligne a été commandée mais n'apparaît pas sur la facture → livraison partielle ?
            if fac_ligne is None:
                toutes_alertes.append(Alerte(
                    niveau=NiveauAlerte.AVERTISSEMENT,
                    categorie="LIGNE_MANQUANTE",
                    reference_ligne=bc_ligne.reference,
                    message="Ligne commandée absente de la facture (livraison partielle ?)",
                    valeur_attendue=bc_ligne.description,
                    valeur_recue="Absent de la facture",
                ))
                continue

            # Pour chaque paire BC ↔ Facture : vérifie prix, quantité et pointure
            toutes_alertes.extend(verifier_prix(bc_ligne, fac_ligne))
            toutes_alertes.extend(verifier_quantite(bc_ligne, fac_ligne))
            toutes_alertes.extend(verifier_pointure(bc_ligne, fac_ligne))

        # Étape 3 : les frais de port correspondent-ils au devis ?
        if devis:
            toutes_alertes.extend(verifier_frais_port(devis, facture))

        # Étape 4 : analyse sémantique — couleurs, matières, similarité des descriptions
        alertes_ia, resume_ia = analyser_coherence_semantique(
            bon_commande.lignes, facture.lignes
        )
        toutes_alertes.extend(alertes_ia)

        # Étape 5 : verdict final selon le nombre et la gravité des alertes
        nb_erreurs       = sum(1 for a in toutes_alertes if a.niveau == NiveauAlerte.ERREUR)
        nb_avertissements = sum(1 for a in toutes_alertes if a.niveau == NiveauAlerte.AVERTISSEMENT)
        nb_infos         = sum(1 for a in toutes_alertes if a.niveau == NiveauAlerte.INFO)

        if nb_erreurs > 0:
            statut = "NON_CONFORME"
        elif nb_avertissements > 0:
            statut = "A_VERIFIER"
        else:
            statut = "CONFORME"

        return RapportVerification(
            date_verification=datetime.now().isoformat(),
            numero_bon_commande=bon_commande.numero,
            numero_devis=devis.numero if devis else None,
            numero_facture=facture.numero,
            statut=statut,
            alertes=toutes_alertes,
            nb_erreurs=nb_erreurs,
            nb_avertissements=nb_avertissements,
            nb_infos=nb_infos,
            analyse_semantique=resume_ia,
        )
