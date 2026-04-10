"""
pipeline.p2_combinaison
=======================
Étape 2 — Construction de l'``EspaceCombinaisonTenseur``.

Assemble les charges caractéristiques (p1) avec les coefficients EC0 pour former
les sollicitations de calcul dans l'espace tenseur ``(n_L, n_C, n_M)``.

La charge linéique de calcul pour chaque combinaison et chaque matériau est :
    q_d[l, c, m] = γ_G × (g_pp[m] + g)
                 + γ_G2 × g2
                 + γ_Q1 × q_princ
                 + γ_Q_accomp × q_accomp

où q_princ et q_accomp dépendent de ``type_charge_principale`` de la combinaison.

Les moments et efforts tranchants sont calculés en bi-appui simple (formules
valables pour toutes les pièces modélisées) :
    M_d = q_d × L² / 8   (n_L, n_C, n_M)
    V_d = q_d × L / 2    (n_L, n_C, n_M)

Pour la double flexion, les composantes M_y et M_z sont calculées depuis
les composantes de charge q_y et q_z via ``TypePoutreVect.decomposer_charges()``.
"""

from __future__ import annotations

from importlib.resources import files

import numpy as np
import pandas as pd

from ..ec5.proprietes import (
    calculer_k_crit_LM,
    calculer_kdef_arr,
    calculer_resistances_CM,
    calculer_kmod_CM,
)
from ..modeles.combinaison import CombinaisonEC0Vect
from ..modeles.config_calcul import ConfigCalculVect
from ..modeles.config_materiau import ConfigMatériauVect
from ..protocoles.type_poutre import TypePoutreVect
from .espace import EspaceCombinaisonTenseur


def _sc(v: float | list[float] | int | list[int]) -> float:
    """Retourne la valeur scalaire ou le premier élément d'une liste."""
    return float(v[0] if isinstance(v, list) else v)


def _charger_limites_fleche(usage: str) -> dict[str, float | None]:
    """Lit les limites de flèche ELS depuis le CSV normatif."""
    chemin: str = str(files("abac_charpente_vectoriser.donnees").joinpath("limites_fleche_ec5.csv"))
    df: pd.DataFrame = pd.read_csv(chemin, sep=";", comment="#")
    df = df.set_index("usage")
    if usage not in df.index:
        raise ValueError(
            f"Usage '{usage}' non trouvé dans limites_fleche_ec5.csv. "
            f"Valeurs disponibles : {list(df.index)}"
        )
    row: pd.Series = df.loc[usage]
    w2: float | None = float(row["w_2"]) if float(row["w_2"]) > 0 else None
    return {
        "w_inst": float(row["w_inst"]),
        "w_fin": float(row["w_fin"]),
        "w_2": w2,
    }


def construire_espace(
    longueurs_m: np.ndarray,
    combinaisons: list[CombinaisonEC0Vect],
    materiaux: list[ConfigMatériauVect],
    config: ConfigCalculVect,
    type_poutre: TypePoutreVect,
    charges_k: dict[str, float | np.ndarray],
) -> EspaceCombinaisonTenseur:
    """Construit l'``EspaceCombinaisonTenseur`` depuis les charges caractéristiques.

    Parameters
    ----------
    longueurs_m:
        Vecteur de portées ``(n_L,)``.
    combinaisons:
        Liste des combinaisons EC0.
    materiaux:
        Liste des configurations matériau.
    config:
        Configuration de calcul (scalaires).
    type_poutre:
        Instance du type de poutre.
    charges_k:
        Charges caractéristiques issues de ``p1_charges.calculer_charges_caracteristiques``.

    Returns
    -------
    EspaceCombinaisonTenseur
        Espace tenseur complet prêt pour les vérifications ELU/ELS.
    """
    n_L: int = len(longueurs_m)
    n_C: int = len(combinaisons)
    n_M: int = len(materiaux)

    # Scalaires depuis charges_k
    g_pp_kNm: np.ndarray = charges_k["g_pp_kNm"]  # type: ignore[assignment]
    g_kNm: float = charges_k["g_kNm"]              # type: ignore[assignment]
    g2_kNm: float = charges_k["g2_kNm"]            # type: ignore[assignment]
    q_kNm: float = charges_k["q_kNm"]              # type: ignore[assignment]
    s_kNm: float = charges_k["s_kNm"]              # type: ignore[assignment]
    w_kNm: float = charges_k["w_kNm"]              # type: ignore[assignment]

    classe_service: int = int(_sc(config.classe_service))

    # ── Propriétés EC5 ───────────────────────────────────────────────────────────
    k_mod_CM: np.ndarray = calculer_kmod_CM(combinaisons, materiaux, classe_service)
    k_def_arr: np.ndarray = calculer_kdef_arr(materiaux, classe_service)
    resistances: dict[str, np.ndarray] = calculer_resistances_CM(combinaisons, materiaux, classe_service)

    l_dev_m: np.ndarray = type_poutre.longueur_deversement_m(longueurs_m)
    k_crit_LM: np.ndarray = calculer_k_crit_LM(longueurs_m, materiaux, l_dev_m)

    # ── Tenseur des charges de calcul (n_L, n_C, n_M) ───────────────────────────
    # Shapes pour broadcast :
    #   longueurs : (n_L, 1, 1)
    #   combinaisons : (1, n_C, 1)
    #   matériaux : (1, 1, n_M)

    L_L11: np.ndarray = longueurs_m[:, np.newaxis, np.newaxis]   # (n_L, 1, 1)

    gamma_G: np.ndarray = np.array([c.gamma_G for c in combinaisons], dtype=float)
    gamma_G2: np.ndarray = np.array([c.gamma_G2 for c in combinaisons], dtype=float)
    gamma_Q1: np.ndarray = np.array([c.gamma_Q1 for c in combinaisons], dtype=float)
    gamma_Qa: np.ndarray = np.array([c.gamma_Q_accomp for c in combinaisons], dtype=float)

    q_princ_C: np.ndarray = np.array(
        [_charge_principale(c.type_charge_principale, q_kNm, s_kNm, w_kNm)
         for c in combinaisons],
        dtype=float,
    )
    q_accomp_C: np.ndarray = np.array(
        [_charge_accompagnement(c.type_charge_principale, q_kNm, s_kNm, w_kNm)
         for c in combinaisons],
        dtype=float,
    )

    g_pp_11M: np.ndarray = g_pp_kNm[np.newaxis, np.newaxis, :]   # (1, 1, n_M)

    gamma_G_1C1: np.ndarray  = gamma_G[np.newaxis, :, np.newaxis]
    gamma_G2_1C1: np.ndarray = gamma_G2[np.newaxis, :, np.newaxis]
    gamma_Q1_1C1: np.ndarray = gamma_Q1[np.newaxis, :, np.newaxis]
    gamma_Qa_1C1: np.ndarray = gamma_Qa[np.newaxis, :, np.newaxis]
    q_princ_1C1: np.ndarray  = q_princ_C[np.newaxis, :, np.newaxis]
    q_accomp_1C1: np.ndarray = q_accomp_C[np.newaxis, :, np.newaxis]

    q_d_LCM: np.ndarray = (
        gamma_G_1C1 * (g_pp_11M + g_kNm)
        + gamma_G2_1C1 * g2_kNm
        + gamma_Q1_1C1 * q_princ_1C1
        + gamma_Qa_1C1 * q_accomp_1C1
    )
    q_d_LCM = np.broadcast_to(q_d_LCM, (n_L, n_C, n_M)).copy()

    q_y_LCM: np.ndarray
    q_z_LCM: np.ndarray
    q_y_LCM, q_z_LCM = type_poutre.decomposer_charges(q_d_LCM)

    L2_L11: np.ndarray = longueurs_m[:, np.newaxis, np.newaxis] ** 2
    M_d_LCM: np.ndarray = q_d_LCM * L2_L11 / 8.0
    V_d_LCM: np.ndarray = q_d_LCM * L_L11 / 2.0

    M_y_LCM: np.ndarray | None = None
    M_z_LCM: np.ndarray | None = None
    if type_poutre.double_flexion_active:
        M_y_LCM = q_y_LCM * L2_L11 / 8.0
        M_z_LCM = q_z_LCM * L2_L11 / 8.0

    N_d_LCM: np.ndarray | None = type_poutre.effort_normal_kN(longueurs_m, n_C, n_M)

    # ── Charge permanente quasi-permanente pour ELS fluage ───────────────────────
    q_G_qperm_LCM: np.ndarray = (g_pp_kNm[np.newaxis, np.newaxis, :] + g_kNm) * np.ones((n_L, 1, n_M))

    # ── Limites ELS ──────────────────────────────────────────────────────────────
    limites: dict[str, float | None] = _charger_limites_fleche(config.usage)
    lim_inst: float = config.limite_fleche_inst or limites["w_inst"]   # type: ignore[assignment]
    lim_fin: float = config.limite_fleche_fin or limites["w_fin"]      # type: ignore[assignment]
    lim_2: float | None = config.limite_fleche_2 or (limites["w_2"] if config.second_oeuvre else None)

    # ── Propriétés de section en vecteurs ────────────────────────────────────────
    A_eff_arr: np.ndarray = np.array([m.A_eff_cisaillement_cm2 for m in materiaux], dtype=float)
    W_y_arr: np.ndarray   = np.array([m.W_y_cm3 for m in materiaux], dtype=float)
    W_z_arr: np.ndarray   = np.array([m.W_z_cm3 for m in materiaux], dtype=float)
    I_y_arr: np.ndarray   = np.array([m.I_y_cm4 for m in materiaux], dtype=float)
    I_z_arr: np.ndarray   = np.array([m.I_z_cm4 for m in materiaux], dtype=float)
    E_arr: np.ndarray     = np.array([m.E_0_mean_MPa for m in materiaux], dtype=float)

    pente_rad: float | None = None
    if hasattr(type_poutre, "_pente_rad"):
        pente_rad = type_poutre._pente_rad  # type: ignore[attr-defined]

    return EspaceCombinaisonTenseur(
        longueurs_m=longueurs_m,
        combinaisons=combinaisons,
        materiaux=materiaux,
        config=config,
        M_d_kNm=M_d_LCM,
        V_d_kN=V_d_LCM,
        q_d_kNm=q_d_LCM,
        M_y_kNm=M_y_LCM,
        M_z_kNm=M_z_LCM,
        N_d_kN=N_d_LCM,
        q_G_kNm=q_G_qperm_LCM,
        q_G2_kNm=float(g2_kNm),
        longueur_projetee_m=type_poutre.longueur_projetee_m(longueurs_m),
        pente_rad=pente_rad,
        k_mod_CM=k_mod_CM,
        f_m_d_CM=resistances["f_m_d_CM"],
        f_v_d_CM=resistances["f_v_d_CM"],
        f_c90_d_CM=resistances["f_c90_d_CM"],
        f_t0_d_CM=resistances["f_t0_d_CM"],
        f_c0_d_CM=resistances["f_c0_d_CM"],
        k_def_arr=k_def_arr,
        k_crit_LM=k_crit_LM,
        A_eff_cis_cm2_arr=A_eff_arr,
        W_y_cm3_arr=W_y_arr,
        W_z_cm3_arr=W_z_arr,
        I_y_cm4_arr=I_y_arr,
        I_z_cm4_arr=I_z_arr,
        E_mean_MPa_arr=E_arr,
        limite_fleche_inst=float(lim_inst),
        limite_fleche_fin=float(lim_fin),
        limite_fleche_2=float(lim_2) if lim_2 is not None else None,
        longueur_appui_mm=float(_sc(config.longueur_appui_mm)),
        k_c90=float(_sc(config.k_c90)),
    )


def _charge_principale(type_ch: str, q: float, s: float, w: float) -> float:
    """Retourne la charge caractéristique de la charge variable principale."""
    mapping: dict[str, float] = {"Q": q, "S": s, "W": w}
    return mapping[type_ch]


def _charge_accompagnement(type_ch_princ: str, q: float, s: float, w: float) -> float:
    """Retourne la somme des charges variables d'accompagnement (hors principale)."""
    toutes: dict[str, float] = {"Q": q, "S": s, "W": w}
    return sum(v for k, v in toutes.items() if k != type_ch_princ)
