"""
chargeur.depuis_dict
====================
Création d'un ``ConfigMatériauVect`` depuis un dictionnaire de propriétés.

Utilisé pour les sections personnalisées (non-rectangulaires) ou pour les
tests unitaires où les propriétés sont définies manuellement.

Pour les sections rectangulaires provenant d'un CSV stock, préférer ``depuis_csv.py``.
"""

from __future__ import annotations

from ..modeles.config_materiau import ConfigMatériauVect


def depuis_dict(donnees: dict) -> ConfigMatériauVect:
    """Crée un ``ConfigMatériauVect`` depuis un dictionnaire de propriétés.

    Tous les champs de ``ConfigMatériauVect`` doivent être présents dans
    ``donnees``. Les champs ``b_mm`` et ``h_mm`` peuvent être ``None`` pour
    les sections personnalisées.

    Parameters
    ----------
    donnees:
        Dictionnaire de propriétés. Doit contenir exactement les champs
        de ``ConfigMatériauVect`` (voir sa docstring pour la liste complète).

    Returns
    -------
    ConfigMatériauVect
        Instance créée depuis le dictionnaire.

    Raises
    ------
    TypeError
        Si des champs obligatoires sont manquants.

    Examples
    --------
    Section personnalisée (poutre I en bois lamellé) :

    >>> mat = depuis_dict({
    ...     "id_config_materiau": "GL28h_IPE200_custom",
    ...     "classe_resistance": "GL28h",
    ...     "famille": "bois_lamelle_colle",
    ...     "b_mm": None,
    ...     "h_mm": None,
    ...     "A_cm2": 28.5,
    ...     "I_y_cm4": 1943.0,
    ...     "I_z_cm4": 142.0,
    ...     "W_y_cm3": 194.3,
    ...     "W_z_cm3": 28.4,
    ...     "A_eff_cisaillement_cm2": 19.1,
    ...     "f_m_k_MPa": 28.0,
    ...     "f_v_k_MPa": 3.2,
    ...     "f_c90_k_MPa": 2.5,
    ...     "f_t0_k_MPa": 19.5,
    ...     "f_c0_k_MPa": 26.5,
    ...     "E_0_mean_MPa": 12600,
    ...     "E_0_05_MPa": 10200,
    ...     "rho_k_kgm3": 380,
    ... })
    """
    return ConfigMatériauVect(**donnees)
