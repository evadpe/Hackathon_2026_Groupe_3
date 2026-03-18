"""
Modèles de données pour la vérification inter-documents — StepAhead Industries.
Ces modèles correspondent au JSON produit par l'OCR des autres membres du groupe.
"""

from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class CategorieArticle(str, Enum):
    CUIR_TEXTILE    = "cuir_textile"       # Facturé au m² ou au mètre linéaire (tolérance 5%)
    SEMELLES_TALONS = "semelles_talons"    # Facturé à la paire / unité (pointure obligatoire)
    FOURNITURES     = "fournitures"        # Lacets, œillets, colles, fils (quantités strictes)


class NiveauAlerte(str, Enum):
    ERREUR          = "ERREUR"         # Bloque la validation, doit être traité
    AVERTISSEMENT   = "AVERTISSEMENT"  # À vérifier manuellement
    INFO            = "INFO"           # Information, pas bloquant


class Fournisseur(BaseModel):
    nom:   str
    siret: Optional[str] = None


class ConversionUnite(BaseModel):
    """Règle de conversion d'unité intégrée dans le JSON (ex: 1 rouleau = 500 mètres)."""
    unite_equivalente: str    # Unité cible (ex: "metre")
    facteur:           float  # 1 unité source = facteur × unité cible


class LigneDocument(BaseModel):
    reference:     str
    description:   str
    categorie:     CategorieArticle
    quantite:      float
    unite:         str
    pointure:      Optional[int]             = None   # Requis pour semelles_talons
    couleur:       Optional[str]             = None
    prix_unitaire: float
    montant_ht:    float
    conversion:    Optional[ConversionUnite] = None   # Règle de conversion si unités diff.


class Document(BaseModel):
    numero:        str
    date:          str
    fournisseur:   Fournisseur
    lignes:        List[LigneDocument]
    frais_port:    float = 0.0
    franco_de_port: bool = False
    total_ht:      float
    tva_taux:      float = 20.0
    tva_montant:   float
    total_ttc:     float


class BonCommande(Document):
    pass


class Devis(Document):
    pass


class Facture(Document):
    pass


class Alerte(BaseModel):
    niveau:           NiveauAlerte
    categorie:        str                   # PRIX, QUANTITE, POINTURE, COULEUR, UNITE, FRAIS_PORT, TOTAL, DESCRIPTION
    reference_ligne:  Optional[str] = None  # Référence article concerné
    message:          str
    valeur_attendue:  Optional[str] = None
    valeur_recue:     Optional[str] = None
    ecart:            Optional[str] = None


class RapportVerification(BaseModel):
    date_verification:    str
    numero_bon_commande:  str
    numero_devis:         Optional[str] = None
    numero_facture:       str
    statut:               str              # CONFORME | A_VERIFIER | NON_CONFORME
    alertes:              List[Alerte] = []
    nb_erreurs:           int = 0
    nb_avertissements:    int = 0
    nb_infos:             int = 0
    analyse_semantique:   Optional[str] = None  # Résumé de l'analyse Claude AI
