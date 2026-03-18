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
    Effectue le rapprochement tripartite : Bon de Commande ↔ Devis ↔ Facture.
    Le Devis est optionnel (si absent, la vérification des frais de port est ignorée).
    """

    def verifier(
        self,
        bon_commande: BonCommande,
        facture: Facture,
        devis: Optional[Devis] = None,
    ) -> RapportVerification:

        toutes_alertes: list[Alerte] = []

        # ── 1. Cohérence interne des totaux ──────────────────────────────────
        toutes_alertes.extend(verifier_totaux(facture, "facture"))
        if devis:
            toutes_alertes.extend(verifier_totaux(devis, "devis"))

        # ── 2. Matching et vérifications ligne par ligne ──────────────────────
        pairs = matcher_lignes(bon_commande, facture)

        for bc_ligne, fac_ligne in pairs:

            # Ligne facturée qui n'existe pas dans le BC
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

            # Ligne commandée non présente dans la facture
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

            # Vérifications métier sur la paire de lignes
            toutes_alertes.extend(verifier_prix(bc_ligne, fac_ligne))
            toutes_alertes.extend(verifier_quantite(bc_ligne, fac_ligne))
            toutes_alertes.extend(verifier_pointure(bc_ligne, fac_ligne))

        # ── 3. Frais de port (requiert le devis) ─────────────────────────────
        if devis:
            toutes_alertes.extend(verifier_frais_port(devis, facture))

        # ── 4. Analyse sémantique intelligente (Claude AI) ───────────────────
        alertes_ia, resume_ia = analyser_coherence_semantique(
            bon_commande.lignes, facture.lignes
        )
        toutes_alertes.extend(alertes_ia)

        # ── 5. Calcul du statut global ────────────────────────────────────────
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
