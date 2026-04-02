"""TypePoutre : Chevron — membre incliné rampant (EF-025).

L = longueur rampante (pas horizontale).
Décomposition cos(α) / cos²(α) selon le type de charge.
Notation EC5 française (Principe IX).
"""
from __future__ import annotations

import math

import numpy as np
from loguru import logger

from sapeg_regen_stock.modeles import ConfigMatériau
from abac_charpente.modeles.combinaison import CombinaisonEC0
from abac_charpente.modeles.config_calcul import ConfigCalcul
from abac_charpente.ec5.types_poutre.base import TypePoutre


class Chevron(TypePoutre):
    """Chevron porteur — membre incliné rampant (EF-025).

    Spécificités par rapport à Panne :
    - L_min correspond à la longueur rampante
    - g_k en kN/m² rampant : q_G_perp = g_k × e × cos(α)
    - q_k, s_k en kN/m² horizontal : projetés par cos²(α)
    - w_k projeté par cos(α) uniquement
    - ELS : w_perp ≤ L_rampant / x (flèche perpendiculaire au rampant)
    - cas pente=0° → avertissement (chevron horizontal n'a pas de sens)
    - cas double_flexion=True → ignoré + avertissement
    """

    def charges_lineaires(
        self,
        config: ConfigCalcul,
        materiau: ConfigMatériau,
        longueurs_m: np.ndarray,
        combi: CombinaisonEC0,
    ) -> dict[str, np.ndarray]:
        """Charges linéaires pour chevron rampant (kN/m⊥ = perpendiculaire au rampant)."""
        from abac_charpente.ec1.neige import mu1

        # Double flexion ignorée pour Chevron
        if config.double_flexion:
            logger.warning(
                "Chevron : double_flexion=True ignoré — le chevron est toujours mono-axe."
            )

        pente_deg = float(config.pente_deg if isinstance(config.pente_deg, (int, float)) else config.pente_deg[0])
        if pente_deg == 0.0:
            logger.warning(
                "Chevron : pente=0° — un chevron horizontal n'a pas de sens physique. "
                "Les résultats peuvent être incorrects."
            )

        pente_rad = math.radians(pente_deg)
        cos_a = math.cos(pente_rad)
        cos2_a = cos_a ** 2

        entraxe_m = float(config.entraxe_m if isinstance(config.entraxe_m, (int, float)) else config.entraxe_m[0])
        g_k_kNm2 = float(config.g_k_kNm2 if isinstance(config.g_k_kNm2, (int, float)) else config.g_k_kNm2[0])
        q_k_kNm2 = float(config.q_k_kNm2 if isinstance(config.q_k_kNm2, (int, float)) else config.q_k_kNm2[0])
        s_k_kNm2 = float(config.s_k_kNm2 if isinstance(config.s_k_kNm2, (int, float)) else config.s_k_kNm2[0])
        w_k_kNm2 = float(config.w_k_kNm2 if isinstance(config.w_k_kNm2, (int, float)) else config.w_k_kNm2[0])

        # Charges perpendiculaires au rampant (kN/m rampant)
        # g_k en kN/m² rampant → cos(α)
        q_G_perp_kNm = g_k_kNm2 * entraxe_m * cos_a + materiau.poids_propre_kNm
        # q_k, s_k en kN/m² horizontal → cos²(α)
        q_Q_perp_kNm = q_k_kNm2 * entraxe_m * cos2_a
        _mu1 = float(mu1(np.array([pente_deg]))[0])
        q_S_perp_kNm = _mu1 * s_k_kNm2 * entraxe_m * cos2_a
        # w_k projeté par cos(α)
        q_W_perp_kNm = w_k_kNm2 * entraxe_m * cos_a

        # Combinaison EC0
        from abac_charpente.ec5.types_poutre.panne import (
            _charge_principale, _charge_accomp_2, _charge_accomp_3,
        )
        q_d_perp_kNm = (
            combi.gamma_G * q_G_perp_kNm
            + combi.gamma_Q1 * _charge_principale(combi, q_Q_perp_kNm, q_S_perp_kNm, q_W_perp_kNm)
            + combi.psi_0_Q2 * _charge_accomp_2(combi, q_Q_perp_kNm, q_S_perp_kNm, q_W_perp_kNm)
            + combi.psi_0_Q3 * _charge_accomp_3(combi, q_Q_perp_kNm, q_S_perp_kNm, q_W_perp_kNm)
        )

        n = len(longueurs_m)
        q_d_arr = np.full(n, q_d_perp_kNm)
        # L = longueur rampante (entrée directe)
        M_d_kNm = q_d_arr * longueurs_m ** 2 / 8.0
        V_d_kN = q_d_arr * longueurs_m / 2.0

        return {
            "q_G_kNm": np.full(n, q_G_perp_kNm),
            "q_Q_kNm": np.full(n, q_Q_perp_kNm),
            "q_S_kNm": np.full(n, q_S_perp_kNm),
            "q_W_kNm": np.full(n, q_W_perp_kNm),
            "q_d_kNm": q_d_arr,
            "M_d_kNm": M_d_kNm,
            "V_d_kN": V_d_kN,
            # Longueur projetée (horizontale) pour information CSV
            "longueur_projetee_m": longueurs_m * cos_a,
            # Composante verticale de la flèche (informatif)
            "pente_rad": np.full(n, pente_rad),
        }

    def decomposer(
        self,
        charges_kNm: np.ndarray,
        pente_rad: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Chevron : pas de double flexion — tout en axe fort (perpendiculaire au rampant)."""
        return charges_kNm.copy(), np.zeros_like(charges_kNm)
