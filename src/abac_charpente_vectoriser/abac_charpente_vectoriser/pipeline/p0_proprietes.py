"""
pipeline.p0_proprietes
======================
Étape 0 — Extraction des vecteurs de propriétés matériau.

Transforme la liste de ``ConfigMatériauVect`` en vecteurs numpy ``(n_M,)``
directement utilisables dans les étapes suivantes du pipeline.

Cette étape ne dépend ni des combinaisons ni des longueurs. Elle est appelée
une seule fois par configuration de calcul.
"""

from __future__ import annotations

import numpy as np

from ..modeles.config_materiau import ConfigMatériauVect


def extraire_vecteurs_materiaux(
    materiaux: list[ConfigMatériauVect],
) -> dict[str, np.ndarray]:
    """Extrait les propriétés matériau en vecteurs numpy ``(n_M,)``.

    Parameters
    ----------
    materiaux:
        Liste des configurations matériau filtrées et ordonnées.

    Returns
    -------
    dict[str, np.ndarray]
        Dictionnaire de vecteurs ``(n_M,)`` :
        - ``A_eff_cis_cm2``  : section efficace cisaillement [cm²]
        - ``W_y_cm3``        : module résistant axe fort [cm³]
        - ``W_z_cm3``        : module résistant axe faible [cm³]
        - ``I_y_cm4``        : moment quadratique axe fort [cm⁴]
        - ``I_z_cm4``        : moment quadratique axe faible [cm⁴]
        - ``E_mean_MPa``     : module élasticité moyen [MPa]
        - ``rho_k_kgm3``     : masse volumique caractéristique [kg/m³]
        - ``A_cm2``          : aire totale [cm²]
    """
    return {
        "A_eff_cis_cm2": np.array([m.A_eff_cisaillement_cm2 for m in materiaux], dtype=float),
        "W_y_cm3": np.array([m.W_y_cm3 for m in materiaux], dtype=float),
        "W_z_cm3": np.array([m.W_z_cm3 for m in materiaux], dtype=float),
        "I_y_cm4": np.array([m.I_y_cm4 for m in materiaux], dtype=float),
        "I_z_cm4": np.array([m.I_z_cm4 for m in materiaux], dtype=float),
        "E_mean_MPa": np.array([m.E_0_mean_MPa for m in materiaux], dtype=float),
        "rho_k_kgm3": np.array([m.rho_k_kgm3 for m in materiaux], dtype=float),
        "A_cm2": np.array([m.A_cm2 for m in materiaux], dtype=float),
    }
