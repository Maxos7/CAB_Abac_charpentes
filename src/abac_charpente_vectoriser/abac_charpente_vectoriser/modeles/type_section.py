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

    PERSONNALISEE = "personnalisee"
    """Section quelconque — propriétés A, I, W passées directement dans ConfigMatériauVect."""
