"""
modeles.type_section
====================
Énumération des types de sections transversales supportés.
"""

from enum import Enum


class TypeSection(str, Enum):
    """Forme de la section transversale d'une pièce de bois."""

    RECTANGULAIRE = "rectangulaire"
    """Section pleine rectangulaire (b × h). Cas le plus courant."""

    RONDE = "rond"
    """Section pleine circulaire (diamètre d). Propriétés calculées depuis d_mm.
    Pas de déversement (k_crit = 1.0 — section doublement symétrique).
    b_mm = h_mm = d_mm pour les vérifications d'appui."""

    PERSONNALISEE = "personnalisee"
    """Section quelconque — propriétés A, I, W lues depuis le CSV.
    Fallback sur formules rectangulaires si une colonne est absente."""
