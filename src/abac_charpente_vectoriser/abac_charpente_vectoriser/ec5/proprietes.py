"""
ec5.proprietes
==============
Calcul vectorisé des propriétés de calcul EC5 sur l'espace combinaison-matériau.

Toutes les tables normatives (kmod, kdef, gamma_M) sont lues depuis ``donnees/*.csv``.
Les résultats sont des tableaux numpy de forme ``(n_C, n_M)`` ou ``(n_M,)``
compatibles avec le broadcast tenseur ``(n_L, n_C, n_M)``.

Référence : EN 1995-1-1 §2.4.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

import numpy as np
import pandas as pd

from ..modeles.combinaison import CombinaisonEC0Vect
from ..modeles.config_materiau import ConfigMatériauVect


@lru_cache(maxsize=1)
def _charger_kmod() -> pd.DataFrame:
    """Charge la table k_mod depuis le CSV normatif (EC5 Table 3.1)."""
    chemin = files("abac_charpente_vectoriser.donnees").joinpath("kmod.csv")
    return pd.read_csv(str(chemin), sep=";", comment="#")


@lru_cache(maxsize=1)
def _charger_kdef() -> pd.DataFrame:
    """Charge la table k_def depuis le CSV normatif (EC5 Table 3.2)."""
    chemin = files("abac_charpente_vectoriser.donnees").joinpath("kdef.csv")
    return pd.read_csv(str(chemin), sep=";", comment="#")


@lru_cache(maxsize=1)
def _charger_gamma_m() -> pd.DataFrame:
    """Charge la table γ_M depuis le CSV normatif (AN France)."""
    chemin = files("abac_charpente_vectoriser.donnees").joinpath("gamma_m.csv")
    return pd.read_csv(str(chemin), sep=";", comment="#")


@lru_cache(maxsize=1)
def _charger_params_ec5() -> dict[str, float]:
    """Charge les paramètres EC5 (k_cr, k_m, seuils k_crit) depuis le CSV normatif."""
    chemin = files("abac_charpente_vectoriser.donnees").joinpath("params_ec5.csv")
    df = pd.read_csv(str(chemin), sep=";", comment="#")
    return dict(zip(df["parametre"], df["valeur"].astype(float)))


def calculer_kmod_CM(
    combinaisons: list[CombinaisonEC0Vect],
    materiaux: list[ConfigMatériauVect],
    classe_service: int,
) -> np.ndarray:
    """Calcule la matrice k_mod de forme ``(n_C, n_M)`` — EC5 §2.4.3, Table 3.1.

    Parameters
    ----------
    combinaisons:
        Liste des combinaisons EC0 (axe n_C).
    materiaux:
        Liste des configurations matériau (axe n_M).
    classe_service:
        Classe de service (1, 2 ou 3).

    Returns
    -------
    np.ndarray
        Tableau ``(n_C, n_M)`` des facteurs k_mod.
    """
    df_kmod = _charger_kmod()
    n_C = len(combinaisons)
    n_M = len(materiaux)
    k_mod_CM = np.empty((n_C, n_M), dtype=float)

    for j, mat in enumerate(materiaux):
        famille = mat.famille
        for i, comb in enumerate(combinaisons):
            masque = (
                (df_kmod["famille"] == famille)
                & (df_kmod["classe_service"] == classe_service)
                & (df_kmod["duree_charge"] == comb.duree_charge)
            )
            lignes = df_kmod[masque]
            if lignes.empty:
                raise ValueError(
                    f"k_mod non trouvé : famille={famille}, "
                    f"classe_service={classe_service}, "
                    f"duree_charge={comb.duree_charge}"
                )
            k_mod_CM[i, j] = float(lignes["k_mod"].iloc[0])

    return k_mod_CM


def calculer_kdef_arr(
    materiaux: list[ConfigMatériauVect],
    classe_service: int,
) -> np.ndarray:
    """Calcule le vecteur k_def de forme ``(n_M,)`` — EC5 Table 3.2.

    Parameters
    ----------
    materiaux:
        Liste des configurations matériau (axe n_M).
    classe_service:
        Classe de service (1, 2 ou 3).

    Returns
    -------
    np.ndarray
        Vecteur ``(n_M,)`` des facteurs k_def.
    """
    df_kdef = _charger_kdef()
    n_M = len(materiaux)
    k_def_arr = np.empty(n_M, dtype=float)

    for j, mat in enumerate(materiaux):
        masque = (
            (df_kdef["famille"] == mat.famille)
            & (df_kdef["classe_service"] == classe_service)
        )
        lignes = df_kdef[masque]
        if lignes.empty:
            raise ValueError(
                f"k_def non trouvé : famille={mat.famille}, classe_service={classe_service}"
            )
        k_def_arr[j] = float(lignes["k_def"].iloc[0])

    return k_def_arr


def calculer_gamma_m_arr(materiaux: list[ConfigMatériauVect]) -> np.ndarray:
    """Calcule le vecteur γ_M de forme ``(n_M,)`` — AN France.

    Parameters
    ----------
    materiaux:
        Liste des configurations matériau (axe n_M).

    Returns
    -------
    np.ndarray
        Vecteur ``(n_M,)`` des coefficients partiels γ_M.
    """
    df_gm = _charger_gamma_m()
    table = dict(zip(df_gm["famille"], df_gm["gamma_M"].astype(float)))
    return np.array([table[mat.famille] for mat in materiaux], dtype=float)


def calculer_resistances_CM(
    combinaisons: list[CombinaisonEC0Vect],
    materiaux: list[ConfigMatériauVect],
    classe_service: int,
) -> dict[str, np.ndarray]:
    """Calcule les résistances de calcul pour toutes les combinaisons et matériaux.

    Formule EC5 §2.4.3 : ``f_d = k_mod × f_k / γ_M``

    Parameters
    ----------
    combinaisons:
        Liste des combinaisons EC0 (axe n_C).
    materiaux:
        Liste des configurations matériau (axe n_M).
    classe_service:
        Classe de service (1, 2 ou 3).

    Returns
    -------
    dict[str, np.ndarray]
        Dictionnaire de tableaux ``(n_C, n_M)`` :
        - ``"f_m_d_CM"``    : résistance en flexion
        - ``"f_v_d_CM"``    : résistance en cisaillement
        - ``"f_c90_d_CM"``  : résistance en compression ⊥ au fil
        - ``"f_t0_d_CM"``   : résistance en traction // au fil
        - ``"f_c0_d_CM"``   : résistance en compression // au fil
    """
    k_mod_CM = calculer_kmod_CM(combinaisons, materiaux, classe_service)  # (n_C, n_M)
    gamma_m_arr = calculer_gamma_m_arr(materiaux)                          # (n_M,)

    # Résistances caractéristiques — vecteur (n_M,)
    f_m_k = np.array([m.f_m_k_MPa for m in materiaux], dtype=float)
    f_v_k = np.array([m.f_v_k_MPa for m in materiaux], dtype=float)
    f_c90_k = np.array([m.f_c90_k_MPa for m in materiaux], dtype=float)
    f_t0_k = np.array([m.f_t0_k_MPa for m in materiaux], dtype=float)
    f_c0_k = np.array([m.f_c0_k_MPa for m in materiaux], dtype=float)

    # Broadcast (n_C, n_M) / (n_M,) → (n_C, n_M)
    facteur_CM = k_mod_CM / gamma_m_arr[np.newaxis, :]

    return {
        "f_m_d_CM": facteur_CM * f_m_k,
        "f_v_d_CM": facteur_CM * f_v_k,
        "f_c90_d_CM": facteur_CM * f_c90_k,
        "f_t0_d_CM": facteur_CM * f_t0_k,
        "f_c0_d_CM": facteur_CM * f_c0_k,
    }


def calculer_k_crit_LM(
    longueurs_m: np.ndarray,
    materiaux: list[ConfigMatériauVect],
    longueur_deversement_m: np.ndarray,
) -> np.ndarray:
    """Calcule le facteur de déversement k_crit de forme ``(n_L, n_M)`` — EC5 §6.3.3.

    k_crit prend en compte le flambement latéral (déversement) des poutres fléchies.
    Le calcul est vectorisé sur les longueurs et les matériaux.

    Parameters
    ----------
    longueurs_m:
        Vecteur de longueurs en mètres ``(n_L,)``.
    materiaux:
        Liste des configurations matériau ``(n_M,)``.
    longueur_deversement_m:
        Longueur de déversement effective ``(n_L,)`` (peut différer de la portée).

    Returns
    -------
    np.ndarray
        Tableau ``(n_L, n_M)`` des facteurs k_crit.
    """
    params = _charger_params_ec5()
    lam_0 = params["lambda_rel_m_0"]  # 0.75
    lam_1 = params["lambda_rel_m_1"]  # 1.40

    # Propriétés matériaux — vecteurs (n_M,)
    E_0_05 = np.array([m.E_0_05_MPa for m in materiaux], dtype=float)
    f_m_k = np.array([m.f_m_k_MPa for m in materiaux], dtype=float)
    I_z = np.array([m.I_z_cm4 * 1e4 for m in materiaux], dtype=float)   # cm⁴ → mm⁴
    W_y = np.array([m.W_y_cm3 * 1e3 for m in materiaux], dtype=float)   # cm³ → mm³
    # G_0_05 ≈ E_0_05 / 16 (approximation EN 338 §3.3)
    G_0_05 = E_0_05 / 16.0

    # Moment critique M_crit — formule simplifiée poutres bi-appuyées (EC5 §6.3.3(3))
    # M_crit = π / l_ef × sqrt(E_0_05 × I_z × G_0_05 × I_tor)
    # Pour section rectangulaire : I_tor ≈ b³h/3 — ici simplifié via EI × GI
    # Formule EC5 Eq. (6.32) : σ_m_crit = π × sqrt(E_0_05 × I_z × G_0_05 × I_tor) / (l_ef × W_y)
    # Approximation conservatrice : σ_m_crit = 0.78 × b² × E_0_05 / (h × l_ef)
    # (valable pour section rectangulaire — EC5 §6.3.3 Note)
    b = np.array([m.b_mm if m.b_mm is not None else 0.0 for m in materiaux], dtype=float)
    h = np.array([m.h_mm if m.h_mm is not None else 0.0 for m in materiaux], dtype=float)

    # l_ef : (n_L,) → broadcast (n_L, 1) × (n_M,) → (n_L, n_M)
    l_ef_mm = longueur_deversement_m[:, np.newaxis] * 1000.0  # m → mm, shape (n_L, 1)

    # σ_m_crit [MPa] — formule EC5 §6.3.3(3) pour section rectangulaire
    sigma_m_crit = 0.78 * b[np.newaxis, :]**2 * E_0_05[np.newaxis, :] / (h[np.newaxis, :] * l_ef_mm)

    # λ_rel,m [-] — Eq. (6.30)
    lambda_rel_m = np.sqrt(f_m_k[np.newaxis, :] / sigma_m_crit)

    # k_crit selon EC5 §6.3.3(4) Eq. (6.28)
    k_crit = np.where(
        lambda_rel_m <= lam_0,
        1.0,
        np.where(
            lambda_rel_m <= lam_1,
            1.56 - 0.75 * lambda_rel_m,
            1.0 / lambda_rel_m**2,
        ),
    )

    return k_crit.clip(0.0, 1.0)
