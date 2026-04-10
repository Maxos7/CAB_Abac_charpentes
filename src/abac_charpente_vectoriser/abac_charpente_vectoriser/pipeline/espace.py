"""
pipeline.espace
===============
Dataclass central ``EspaceCombinaisonTenseur`` — étape intermédiaire du pipeline.

Cet espace est construit par ``p2_combinaison.py`` après assemblage des charges
pondérées et des propriétés de calcul. Il est consommé par ``p3_elu.py`` et
``p4_els.py`` sans distinction du type de poutre (polymorphisme respecté).

Convention d'axes des tableaux numpy :
    Axe 0 : longueurs  n_L
    Axe 1 : combinaisons EC0  n_C
    Axe 2 : matériaux  n_M

Les tableaux (n_C, n_M) sont des matrices "combinaison × matériau" destinées
à être broadcastées contre l'axe longueur via ``[:, np.newaxis, :]`` ou
``[np.newaxis, :, :]`` selon le contexte.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..modeles.combinaison import CombinaisonEC0Vect
from ..modeles.config_calcul import ConfigCalculVect
from ..modeles.config_materiau import ConfigMatériauVect


@dataclass
class EspaceCombinaisonTenseur:
    """Espace tenseur après assemblage charges + propriétés EC5.

    Produit par ``p2_combinaison.py``, consommé par ``p3_elu`` et ``p4_els``.
    Toutes les valeurs sont en unités SI du pipeline (kN, m, kNm, MPa, cm).

    Parameters
    ----------
    longueurs_m:
        Vecteur de portées en mètres ``(n_L,)``.
    combinaisons:
        Liste des combinaisons EC0 ``(n_C,)``.
    materiaux:
        Liste des configurations matériau ``(n_M,)``.
    config:
        Configuration de calcul (scalaires après développement du produit cartésien).
    type_poutre:
        Instance du type de poutre (polymorphisme — décomposition des charges).

    Sollicitations de calcul — tenseurs ``(n_L, n_C, n_M)``
    ──────────────────────────────────────────────────────
    M_d_kNm:
        Moment fléchissant maximal de calcul en kN·m (bi-appui : qL²/8).
    V_d_kN:
        Effort tranchant maximal de calcul en kN (bi-appui : qL/2).
    q_d_kNm:
        Charge linéique de calcul totale en kN/m.
    M_y_kNm:
        Moment fléchissant axe fort y (double flexion) — None si inactif.
    M_z_kNm:
        Moment fléchissant axe faible z (double flexion) — None si inactif.
    N_d_kN:
        Effort normal de calcul en kN — None si non applicable.

    Charges pour ELS fluage
    ───────────────────────
    q_G_kNm:
        Charge permanente G pondérée quasi-permanente ``(n_L, n_C, n_M)`` (pour k_def).
    q_G2_kNm:
        Charge permanente fragile G2 en kN/m (scalaire — non pondérée pour fluage).

    Géométrie inclinée
    ──────────────────
    longueur_projetee_m:
        Portée horizontale projetée ``(n_L,)`` — None sauf pour Chevron.
    pente_rad:
        Pente en radians — None si non applicable.

    Propriétés EC5 — format ``(n_C, n_M)``
    ───────────────────────────────────────
    k_mod_CM:
        Facteur de modification k_mod (EC5 Table 3.1).
    f_m_d_CM, f_v_d_CM, f_c90_d_CM, f_t0_d_CM, f_c0_d_CM:
        Résistances de calcul en MPa.

    Propriétés EC5 — format ``(n_M,)``
    ────────────────────────────────────
    k_def_arr:
        Facteur de fluage k_def (EC5 Table 3.2).
    k_crit_LM:
        Facteur de déversement k_crit ``(n_L, n_M)`` (EC5 §6.3.3).
    A_eff_cis_cm2_arr:
        Section efficace pour le cisaillement en cm² (EC5 §6.1.7).
    W_y_cm3_arr:
        Module résistant axe fort en cm³.
    W_z_cm3_arr:
        Module résistant axe faible en cm³.
    I_y_cm4_arr:
        Moment quadratique axe fort en cm⁴.
    I_z_cm4_arr:
        Moment quadratique axe faible en cm⁴ (double flexion ELS).
    E_mean_MPa_arr:
        Module d'élasticité moyen en MPa (ELS flèche).

    Limites ELS — scalaires
    ────────────────────────
    limite_fleche_inst:
        Limite L/x pour la flèche instantanée.
    limite_fleche_fin:
        Limite L/x pour la flèche finale.
    limite_fleche_2:
        Limite L/x pour la flèche second-œuvre (None si ``second_oeuvre=False``).

    Paramètres de vérification à l'appui
    ──────────────────────────────────────
    longueur_appui_mm:
        Longueur d'appui en mm (scalaire).
    k_c90:
        Facteur k_c90 pour la vérification à l'appui (EC5 §6.1.5).
    """

    # Méta-données
    longueurs_m: np.ndarray
    combinaisons: list[CombinaisonEC0Vect]
    materiaux: list[ConfigMatériauVect]
    config: ConfigCalculVect

    # Sollicitations de calcul (n_L, n_C, n_M)
    M_d_kNm: np.ndarray
    V_d_kN: np.ndarray
    q_d_kNm: np.ndarray
    M_y_kNm: np.ndarray | None
    M_z_kNm: np.ndarray | None
    N_d_kN: np.ndarray | None

    # Charges pour fluage ELS
    q_G_kNm: np.ndarray   # (n_L, n_C, n_M) — charge permanente G quasi-permanente
    q_G2_kNm: float        # scalaire — charge G2 non amplifiée (pour k_def)

    # Géométrie inclinée
    longueur_projetee_m: np.ndarray | None
    pente_rad: float | None

    # Propriétés EC5 (n_C, n_M)
    k_mod_CM: np.ndarray
    f_m_d_CM: np.ndarray
    f_v_d_CM: np.ndarray
    f_c90_d_CM: np.ndarray
    f_t0_d_CM: np.ndarray
    f_c0_d_CM: np.ndarray

    # Propriétés EC5 (n_M,)
    k_def_arr: np.ndarray
    k_crit_LM: np.ndarray  # (n_L, n_M)
    A_eff_cis_cm2_arr: np.ndarray
    W_y_cm3_arr: np.ndarray
    W_z_cm3_arr: np.ndarray
    I_y_cm4_arr: np.ndarray
    I_z_cm4_arr: np.ndarray
    E_mean_MPa_arr: np.ndarray

    # Limites ELS
    limite_fleche_inst: float
    limite_fleche_fin: float
    limite_fleche_2: float | None

    # Paramètres vérification appui
    longueur_appui_mm: float
    k_c90: float
