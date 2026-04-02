"""TypePoutre : Sommier — portée lourde, charges réparties + concentrées.

Notation EC5 française (Principe IX).
"""
from __future__ import annotations

import numpy as np

from sapeg_regen_stock.modeles import ConfigMatériau
from abac_charpente.modeles.combinaison import CombinaisonEC0
from abac_charpente.modeles.config_calcul import ConfigCalcul
from abac_charpente.ec5.types_poutre.base import TypePoutre
from abac_charpente.ec5.types_poutre.panne import (
    _charge_principale, _charge_accomp_2, _charge_accomp_3,
)


class Sommier(TypePoutre):
    """Sommier (poutre principale) — charges verticales horizontales, mono-axe.

    Traité comme une poutre à charge uniformément répartie (simplifié).
    Pente nulle, pas de double flexion.
    """

    def charges_lineaires(
        self,
        config: ConfigCalcul,
        materiau: ConfigMatériau,
        longueurs_m: np.ndarray,
        combi: CombinaisonEC0,
    ) -> dict[str, np.ndarray]:
        """Charges linéaires pour sommier (kN/m)."""
        entraxe_m = float(config.entraxe_m if isinstance(config.entraxe_m, (int, float)) else config.entraxe_m[0])
        g_k_kNm2 = float(config.g_k_kNm2 if isinstance(config.g_k_kNm2, (int, float)) else config.g_k_kNm2[0])
        q_k_kNm2 = float(config.q_k_kNm2 if isinstance(config.q_k_kNm2, (int, float)) else config.q_k_kNm2[0])
        s_k_kNm2 = float(config.s_k_kNm2 if isinstance(config.s_k_kNm2, (int, float)) else config.s_k_kNm2[0])
        w_k_kNm2 = float(config.w_k_kNm2 if isinstance(config.w_k_kNm2, (int, float)) else config.w_k_kNm2[0])

        q_G_kNm = g_k_kNm2 * entraxe_m + materiau.poids_propre_kNm
        q_Q_kNm = q_k_kNm2 * entraxe_m
        q_S_kNm = s_k_kNm2 * entraxe_m
        q_W_kNm = w_k_kNm2 * entraxe_m

        q_d_kNm = (
            combi.gamma_G * q_G_kNm
            + combi.gamma_Q1 * _charge_principale(combi, q_Q_kNm, q_S_kNm, q_W_kNm)
            + combi.psi_0_Q2 * _charge_accomp_2(combi, q_Q_kNm, q_S_kNm, q_W_kNm)
            + combi.psi_0_Q3 * _charge_accomp_3(combi, q_Q_kNm, q_S_kNm, q_W_kNm)
        )

        n = len(longueurs_m)
        q_d_arr = np.full(n, q_d_kNm)
        M_d_kNm = q_d_arr * longueurs_m ** 2 / 8.0
        V_d_kN = q_d_arr * longueurs_m / 2.0

        return {
            "q_G_kNm": np.full(n, q_G_kNm),
            "q_Q_kNm": np.full(n, q_Q_kNm),
            "q_S_kNm": np.full(n, q_S_kNm),
            "q_W_kNm": np.full(n, q_W_kNm),
            "q_d_kNm": q_d_arr,
            "M_d_kNm": M_d_kNm,
            "V_d_kN": V_d_kN,
        }

    def decomposer(
        self,
        charges_kNm: np.ndarray,
        pente_rad: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Sommier : pas de décomposition — tout en axe fort."""
        return charges_kNm.copy(), np.zeros_like(charges_kNm)
