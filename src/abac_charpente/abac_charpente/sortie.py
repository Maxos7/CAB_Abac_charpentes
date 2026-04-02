"""Écriture du CSV de sortie (append-only) — EF-014, EF-015.

Format : UTF-8, séparateur `;`, mode append, en-têtes si fichier vide/absent.
Ordre des colonnes conforme à contracts/csv-output-schema.md v1.2.0.
Erreur code 4 si écriture impossible.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from abac_charpente.modeles.resultat_portee import RésultatPortée


# Ordre des colonnes selon contracts/csv-output-schema.md v1.2.0
COLONNES_SORTIE: list[str] = [
    # Identification
    "horodatage_iso",
    "id_produit",
    "id_config_materiau",
    "id_config_calcul",
    "type_poutre",
    "usage",
    "second_oeuvre",
    "double_flexion",
    "entraxe_antideversement_mm",
    "longueur_m",
    "longueur_projetee_m",
    "id_combinaison",
    "type_combinaison",
    # Section
    "b_mm",
    "h_mm",
    "classe_resistance",
    "L_max_m",
    # Propriétés mécaniques
    "A_cm2",
    "I_cm4",
    "W_cm3",
    "I_z_cm4",
    "W_z_cm3",
    "poids_propre_kNm",
    # Résistances
    "f_m_k_MPa",
    "f_v_k_MPa",
    "k_mod",
    "gamma_M",
    "f_m_d_MPa",
    "f_v_d_MPa",
    # Charges
    "q_G_kNm",
    "q_Q_kNm",
    "q_S_kNm",
    "q_W_kNm",
    # EC0
    "gamma_G",
    "charge_principale",
    "gamma_Q1",
    "psi_0_Q2",
    "psi_0_Q3",
    "q_combinee_kNm",
    # Efforts internes
    "M_max_kNm",
    "V_max_kN",
    "M_z_kNm",
    # ELU
    "sigma_m_MPa",
    "taux_flexion_ELU",
    "tau_MPa",
    "taux_cisaillement_ELU",
    "f_c90_k_MPa",
    "f_c90_d_MPa",
    "sigma_c90_MPa",
    "k_c90",
    "longueur_appui_mm",
    "taux_cible_appui",
    "longueur_appui_min_mm",
    "taux_appui_ELU",
    "k_crit",
    "L_deversement_m",
    "taux_deversement_ELU",
    "sigma_m_y_MPa",
    "sigma_m_z_MPa",
    "k_m",
    "taux_biaxial_1_ELU",
    "taux_biaxial_2_ELU",
    # ELS
    "w_inst_mm",
    "limite_inst_mm",
    "taux_ELS_inst",
    "w_creep_mm",
    "w_fin_mm",
    "limite_fin_mm",
    "taux_ELS_fin",
    "w_2_mm",
    "limite_2_mm",
    "taux_ELS_2",
    "w_y_inst_mm",
    "w_z_inst_mm",
    "w_res_inst_mm",
    "w_y_fin_mm",
    "w_z_fin_mm",
    "w_res_fin_mm",
    "w_vert_inst_mm",
    "w_vert_fin_mm",
    # Résultat
    "taux_determinant",
    "verification_determinante",
    "clause_EC5",
    "statut",
    "marge_securite",
]


def _résultat_vers_dict(r: RésultatPortée) -> dict[str, Any]:
    """Convertit un RésultatPortée en dict pour pandas."""
    return {col: getattr(r, col, None) for col in COLONNES_SORTIE}


def ecrire_sortie(resultats: list[RésultatPortée], chemin: Path) -> None:
    """Écrit les résultats dans le CSV de sortie (mode append).

    Paramètres :
        resultats : liste de RésultatPortée
        chemin    : chemin du fichier CSV de sortie

    Lève SystemExit(4) si l'écriture est impossible.
    """
    if not resultats:
        logger.warning("Aucun résultat à écrire.")
        return

    # Création du répertoire si nécessaire
    chemin = Path(chemin)
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Impossible de créer le répertoire {chemin.parent} : {e}")
        sys.exit(4)

    fichier_existant = chemin.exists() and chemin.stat().st_size > 0
    lignes = [_résultat_vers_dict(r) for r in resultats]
    df = pd.DataFrame(lignes, columns=COLONNES_SORTIE)

    # Format numérique
    float_cols_6 = [c for c in COLONNES_SORTIE if "taux" in c]
    float_cols_3 = [c for c in COLONNES_SORTIE if c.endswith("_m") or c == "longueur_m"]
    float_cols_2 = [c for c in COLONNES_SORTIE if c.endswith("_mm")]

    for col in float_cols_6:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.6f}" if x is not None else "")

    for col in float_cols_3:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.3f}" if x is not None else "")

    for col in float_cols_2:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.2f}" if x is not None else "")

    try:
        df.to_csv(
            chemin,
            sep=";",
            encoding="utf-8",
            index=False,
            mode="a",
            header=not fichier_existant,
        )
        logger.info(f"{len(resultats)} lignes écrites dans {chemin}")
    except Exception as e:
        logger.error(f"Impossible d'écrire dans {chemin} : {e}")
        sys.exit(4)
