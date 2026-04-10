"""
chargeur.derivateur
===================
Calcul des propriétés de section à partir des dimensions b × h (section rectangulaire).

Les formules sont celles de la résistance des matériaux pour une section pleine
rectangulaire. La section efficace pour le cisaillement intègre le facteur k_cr
(EC5 §6.1.7) lu depuis ``donnees/params_ec5.csv``.

Toutes les grandeurs géométriques sont retournées dans les unités du pipeline
(cm², cm³, cm⁴) pour compatibilité avec ``ConfigMatériauVect``.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

import pandas as pd


@lru_cache(maxsize=1)
def _k_cr() -> float:
    """Lit le facteur k_cr depuis params_ec5.csv — EC5 §6.1.7(2)."""
    chemin: str = str(files("abac_charpente_vectoriser.donnees").joinpath("params_ec5.csv"))
    df: pd.DataFrame = pd.read_csv(chemin, sep=";", comment="#")
    return float(df.set_index("parametre").loc["k_cr", "valeur"])


def deriver_section_rect(b_mm: float, h_mm: float) -> dict[str, float]:
    """Calcule les propriétés d'une section rectangulaire pleine b × h.

    Convention : h est la hauteur selon l'axe fort y (flexion principale).
    b est la largeur selon l'axe faible z.

    Parameters
    ----------
    b_mm:
        Largeur de la section en mm.
    h_mm:
        Hauteur de la section en mm (axe fort).

    Returns
    -------
    dict[str, float]
        Dictionnaire avec les clés :
        - ``A_cm2``                  : aire en cm²
        - ``I_y_cm4``                : moment quadratique axe fort en cm⁴
        - ``I_z_cm4``                : moment quadratique axe faible en cm⁴
        - ``W_y_cm3``                : module résistant axe fort en cm³
        - ``W_z_cm3``                : module résistant axe faible en cm³
        - ``A_eff_cisaillement_cm2`` : section efficace cisaillement en cm² (× k_cr)
    """
    b_cm: float = b_mm / 10.0
    h_cm: float = h_mm / 10.0
    k_cr: float = _k_cr()

    A_cm2: float = b_cm * h_cm
    I_y_cm4: float = b_cm * h_cm**3 / 12.0
    I_z_cm4: float = h_cm * b_cm**3 / 12.0
    W_y_cm3: float = b_cm * h_cm**2 / 6.0
    W_z_cm3: float = h_cm * b_cm**2 / 6.0
    A_eff_cisaillement_cm2: float = A_cm2 * k_cr

    return {
        "A_cm2": A_cm2,
        "I_y_cm4": I_y_cm4,
        "I_z_cm4": I_z_cm4,
        "W_y_cm3": W_y_cm3,
        "W_z_cm3": W_z_cm3,
        "A_eff_cisaillement_cm2": A_eff_cisaillement_cm2,
    }
