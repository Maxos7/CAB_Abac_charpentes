"""
ec1.neige
=========
Calcul de la charge de neige linéique sur une poutre — EN 1991-1-3.

Le coefficient de forme μ₁ est interpolé depuis ``donnees/ec1_mu1_neige.csv``
(aucune valeur normative hardcodée dans le code).

La charge de neige sur le sol ``s_k`` est fournie dans la config (en kN/m²,
sur projection horizontale). Le coefficient d'exposition c_e et le coefficient
thermique c_t sont pris à 1.0 (AN France, valeur par défaut).
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

import numpy as np
import pandas as pd


@lru_cache(maxsize=1)
def _charger_mu1_table() -> tuple[np.ndarray, np.ndarray]:
    """Charge les points d'interpolation μ₁ depuis le CSV normatif.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (pentes_deg, mu1_values) — vecteurs pour ``np.interp``.
    """
    chemin: str = str(files("abac_charpente_vectoriser.donnees").joinpath("ec1_mu1_neige.csv"))
    df: pd.DataFrame = pd.read_csv(chemin, sep=";", comment="#")
    return df["pente_deg"].to_numpy(float), df["mu1"].to_numpy(float)


def mu1(pente_deg_arr: np.ndarray) -> np.ndarray:
    """Coefficient de forme μ₁ pour la neige — EN 1991-1-3 §5.3.2 Figure 5.1.

    Interpolation linéaire entre les points de la table normative.
    La valeur est clampée à 0 pour les pentes > 60°.

    Parameters
    ----------
    pente_deg_arr:
        Tableau numpy de pentes en degrés.

    Returns
    -------
    np.ndarray
        Coefficients μ₁ de même forme que ``pente_deg_arr``.
    """
    xp: np.ndarray
    fp: np.ndarray
    xp, fp = _charger_mu1_table()
    return np.interp(pente_deg_arr, xp, fp).clip(0.0)


def charge_neige_kNm(
    s_k_kNm2: float,
    pente_deg: float,
    entraxe_m: float,
    c_e: float = 1.0,
    c_t: float = 1.0,
) -> float:
    """Charge linéique caractéristique de neige sur une poutre — EN 1991-1-3 §5.2.

    s_d = μ₁ × c_e × c_t × s_k   [kN/m²]
    q_s_kNm = s_d × entraxe_m    [kN/m linéaire]

    Parameters
    ----------
    s_k_kNm2:
        Charge de neige caractéristique sur le sol en kN/m² (projection horizontale).
    pente_deg:
        Pente du rampant en degrés.
    entraxe_m:
        Entraxe entre poutres en mètres.
    c_e:
        Coefficient d'exposition (défaut 1.0 — AN France).
    c_t:
        Coefficient thermique (défaut 1.0 — AN France).

    Returns
    -------
    float
        Charge linéique caractéristique de neige en kN/m.
    """
    mu_1: float = float(mu1(np.array([pente_deg]))[0])
    s_d_kNm2: float = mu_1 * c_e * c_t * s_k_kNm2
    return s_d_kNm2 * entraxe_m
