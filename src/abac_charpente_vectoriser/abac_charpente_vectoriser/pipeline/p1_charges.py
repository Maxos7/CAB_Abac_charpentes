"""
pipeline.p1_charges
===================
Étape 1 — Calcul des charges linéiques caractéristiques par matériau.

Transforme les charges surfaciques (kN/m²) en charges linéiques (kN/m) en
appliquant l'entraxe entre poutres et les coefficients EC1 (μ₁ pour la neige,
c_pe pour le vent).

Le poids propre de la pièce est calculé par matériau (variable selon A et ρ_k).
Les autres charges sont des scalaires (identiques pour tous les matériaux).

Résultat : dictionnaire de charges caractéristiques linéiques en kN/m.
La pondération EC0 est appliquée à l'étape suivante (p2_combinaison).
"""

from __future__ import annotations

import numpy as np

from ..ec1.neige import charge_neige_kNm
from ..ec1.vent import charge_vent_kNm
from ..modeles.config_calcul import ConfigCalculVect
from ..modeles.config_materiau import ConfigMatériauVect
from ..protocoles.type_poutre import TypePoutreVect


def calculer_charges_caracteristiques(
    config: ConfigCalculVect,
    materiaux: list[ConfigMatériauVect],
    type_poutre: TypePoutreVect,
) -> dict[str, float | np.ndarray]:
    """Calcule les charges caractéristiques linéiques par matériau.

    Les charges G et Q sont exprimées en kN/m par mètre de portée (rampant
    pour les pannes et chevrons, horizontal pour les solives/sommiers).
    Le poids propre est calculé pour chaque matériau (variable n_M).

    Parameters
    ----------
    config:
        Configuration de calcul (scalaires).
    materiaux:
        Liste des configurations matériau filtrées.
    type_poutre:
        Instance du type de poutre (pour le calcul du poids propre).

    Returns
    -------
    dict[str, float | np.ndarray]
        Dictionnaire de charges caractéristiques en kN/m :
        - ``g_pp_kNm``   : poids propre de la pièce ``(n_M,)``
        - ``g_kNm``      : charges permanentes G (hors poids propre) — scalaire
        - ``g2_kNm``     : charges permanentes fragiles G2 — scalaire
        - ``q_kNm``      : charges variables Q — scalaire
        - ``s_kNm``      : charges de neige S — scalaire
        - ``w_kNm``      : charges de vent W — scalaire
    """
    entraxe_m: float = _sc(config.entraxe_m)
    pente_deg: float = _sc(config.pente_deg)
    g_k: float = _sc(config.g_k_kNm2)
    g2_k: float = _sc(config.g2_k_kNm2)
    q_k: float = _sc(config.q_k_kNm2)
    s_k: float = _sc(config.s_k_kNm2)
    w_k: float = _sc(config.w_k_kNm2)

    g_pp_kNm: np.ndarray = type_poutre.poids_propre_kNm(materiaux)
    g_kNm: float = g_k * entraxe_m
    g2_kNm: float = g2_k * entraxe_m
    q_kNm: float = q_k * entraxe_m
    s_kNm: float = charge_neige_kNm(s_k, pente_deg, entraxe_m) if s_k > 0 else 0.0
    w_kNm: float = charge_vent_kNm(w_k, config.type_toiture_vent, entraxe_m) if w_k > 0 else 0.0

    return {
        "g_pp_kNm": g_pp_kNm,
        "g_kNm": g_kNm,
        "g2_kNm": g2_kNm,
        "q_kNm": q_kNm,
        "s_kNm": s_kNm,
        "w_kNm": w_kNm,
    }


def _sc(v: float | list[float] | int | list[int]) -> float:
    """Retourne la valeur scalaire ou le premier élément d'une liste."""
    return float(v[0] if isinstance(v, list) else v)
