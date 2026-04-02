"""Entité RésultatPortée — toutes les colonnes EF-014.

Notation française EC5 (Principe IX). Entité dataclass (Principe X).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RésultatPortée:
    """Résultat complet pour un quadruplet (produit × config × longueur × combinaison).

    Contient toutes les colonnes définies dans EF-014 et contracts/csv-output-schema.md.
    Les champs optionnels (None) sont exclus selon le type de poutre / options activées.
    """
    # -----------------------------------------------------------------------
    # Identification
    # -----------------------------------------------------------------------
    horodatage_iso: str
    id_produit: str
    id_config_materiau: str
    id_config_calcul: str
    type_poutre: str
    usage: str
    second_oeuvre: bool
    double_flexion: bool
    entraxe_antideversement_mm: float
    longueur_m: float
    longueur_projetee_m: float | None  # None si ≠ Chevron
    id_combinaison: str
    type_combinaison: str

    # -----------------------------------------------------------------------
    # Section
    # -----------------------------------------------------------------------
    b_mm: float
    h_mm: float
    classe_resistance: str
    L_max_m: float

    # -----------------------------------------------------------------------
    # Propriétés mécaniques
    # -----------------------------------------------------------------------
    A_cm2: float
    I_cm4: float
    W_cm3: float
    I_z_cm4: float | None  # None si double_flexion=False
    W_z_cm3: float | None  # None si double_flexion=False
    poids_propre_kNm: float

    # -----------------------------------------------------------------------
    # Résistances de calcul
    # -----------------------------------------------------------------------
    f_m_k_MPa: float
    f_v_k_MPa: float
    k_mod: float
    gamma_M: float
    f_m_d_MPa: float
    f_v_d_MPa: float

    # -----------------------------------------------------------------------
    # Charges linéaires (kN/m)
    # -----------------------------------------------------------------------
    q_G_kNm: float
    q_Q_kNm: float
    q_S_kNm: float
    q_W_kNm: float

    # -----------------------------------------------------------------------
    # Combinaison EC0
    # -----------------------------------------------------------------------
    gamma_G: float
    charge_principale: str
    gamma_Q1: float
    psi_0_Q2: float
    psi_0_Q3: float
    q_combinee_kNm: float

    # -----------------------------------------------------------------------
    # Efforts internes
    # -----------------------------------------------------------------------
    M_max_kNm: float
    V_max_kN: float
    M_z_kNm: float | None  # None si double_flexion=False

    # -----------------------------------------------------------------------
    # ELU — vérifications
    # -----------------------------------------------------------------------
    sigma_m_MPa: float
    taux_flexion_ELU: float
    tau_MPa: float
    taux_cisaillement_ELU: float
    f_c90_k_MPa: float
    f_c90_d_MPa: float
    sigma_c90_MPa: float
    k_c90: float
    longueur_appui_mm: float
    taux_cible_appui: float
    longueur_appui_min_mm: float
    taux_appui_ELU: float
    k_crit: float
    L_deversement_m: float | None   # None si double_flexion=False
    taux_deversement_ELU: float
    sigma_m_y_MPa: float | None     # None si double_flexion=False
    sigma_m_z_MPa: float | None     # None si double_flexion=False
    k_m: float | None               # None si double_flexion=False
    taux_biaxial_1_ELU: float | None  # None si double_flexion=False
    taux_biaxial_2_ELU: float | None  # None si double_flexion=False

    # -----------------------------------------------------------------------
    # ELS — flèches
    # -----------------------------------------------------------------------
    w_inst_mm: float
    limite_inst_mm: float
    taux_ELS_inst: float
    w_creep_mm: float
    w_fin_mm: float
    limite_fin_mm: float
    taux_ELS_fin: float
    w_2_mm: float | None        # None si second_oeuvre=False
    limite_2_mm: float | None   # None si second_oeuvre=False
    taux_ELS_2: float | None    # None si second_oeuvre=False
    # Double flexion ELS
    w_y_inst_mm: float | None   # None si double_flexion=False
    w_z_inst_mm: float | None   # None si double_flexion=False
    w_res_inst_mm: float | None # None si double_flexion=False
    w_y_fin_mm: float | None    # None si double_flexion=False
    w_z_fin_mm: float | None    # None si double_flexion=False
    w_res_fin_mm: float | None  # None si double_flexion=False
    # Chevron uniquement
    w_vert_inst_mm: float | None  # None si ≠ Chevron
    w_vert_fin_mm: float | None   # None si ≠ Chevron

    # -----------------------------------------------------------------------
    # Résultat synthétique
    # -----------------------------------------------------------------------
    taux_determinant: float
    verification_determinante: str
    clause_EC5: str
    statut: str          # 'admis' | 'refusé' | 'rejeté_usage'
    marge_securite: float
