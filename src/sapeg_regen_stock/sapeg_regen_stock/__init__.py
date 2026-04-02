"""API publique du paquet sapeg_regen_stock.

Exports principaux (T033) :
    run()                  : pipeline complet
    detecter_fichier_stock : détection auto du CSV stock le plus récent
    ConfigIngestion        : paramètres de lecture CSV
    ProduitValide          : produit ayant passé les validations
    ProduitExclu           : produit rejeté
    RegleFiltre            : union des types de règles de filtrage
    ConfigFiltre           : configuration d'un filtre nommé
    ConfigMatériau         : entité matériau dérivée

IMPORTANT : ce paquet n'importe PAS abac_charpente.ec5 / ec0 / ec1 / moteur / sortie
(Constitution IV — couplage faible).
"""
__version__ = "0.1.0"

from sapeg_regen_stock.pipeline import run
from sapeg_regen_stock.detecteur import detecter_fichier_stock
from sapeg_regen_stock.modeles import (
    ConfigIngestion,
    ProduitStock,
    ProduitValide,
    ProduitExclu,
    RegleFiltre,
    RegleEgal,
    ReglePlage,
    RegleListe,
    RegleNonNul,
    ConfigFiltre,
    ConfigMatériau,
)

__all__ = [
    "run",
    "detecter_fichier_stock",
    "ConfigIngestion",
    "ProduitStock",
    "ProduitValide",
    "ProduitExclu",
    "RegleFiltre",
    "RegleEgal",
    "ReglePlage",
    "RegleListe",
    "RegleNonNul",
    "ConfigFiltre",
    "ConfigMatériau",
]
