"""TypePoutre : Panne — flexion sous charges horizontales.

EF-024 : double flexion si double_flexion=True.
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


class Panne(TypePoutre):
    """Panne de toiture — chargement descendant.

    Si double_flexion=True (EF-024) :
        - décomposition des charges q_y = q × cos(α), q_z = q × sin(α)
        - si pente=0 ET double_flexion=True → avertissement + q_z=0
    """

    def charges_lineaires(
        self,
        config: ConfigCalcul,
        materiau: ConfigMatériau,
        longueurs_m: np.ndarray,
        combi: CombinaisonEC0,
    ) -> dict[str, np.ndarray]:
        """Charges linéaires pour panne (kN/m) selon EN 1991 et EC0."""
        from abac_charpente.ec1.neige import mu1
        from abac_charpente.ec1.vent import c_pe, charge_vent_kNm

        # Pente (scalaire)
        pente_deg = config.pente_deg if isinstance(config.pente_deg, (int, float)) else config.pente_deg[0]
        pente_rad = math.radians(float(pente_deg))
        entraxe_m = config.entraxe_m if isinstance(config.entraxe_m, (int, float)) else config.entraxe_m[0]
        entraxe_m = float(entraxe_m)

        # Charges caractéristiques (kN/m)
        g_k_kNm2 = float(config.g_k_kNm2 if isinstance(config.g_k_kNm2, (int, float)) else config.g_k_kNm2[0])
        q_k_kNm2 = float(config.q_k_kNm2 if isinstance(config.q_k_kNm2, (int, float)) else config.q_k_kNm2[0])
        s_k_kNm2 = float(config.s_k_kNm2 if isinstance(config.s_k_kNm2, (int, float)) else config.s_k_kNm2[0])
        w_k_kNm2 = float(config.w_k_kNm2 if isinstance(config.w_k_kNm2, (int, float)) else config.w_k_kNm2[0])

        # Charges linéaires (kN/m) — panne horizontale
        q_G_kNm = g_k_kNm2 * entraxe_m + materiau.poids_propre_kNm
        q_Q_kNm = q_k_kNm2 * entraxe_m
        # Neige : μ₁ selon pente (EN 1991-1-3)
        _mu1 = float(mu1(np.array([pente_deg]))[0])
        q_S_kNm = _mu1 * s_k_kNm2 * entraxe_m
        # Vent
        _cpe = c_pe(config.type_toiture_vent)
        q_W_kNm = charge_vent_kNm(w_k_kNm2, _cpe, entraxe_m)

        # Charge de calcul EC0 (kN/m) — scalaire
        q_d_kNm = (
            combi.gamma_G * q_G_kNm
            + combi.gamma_Q1 * _charge_principale(combi, q_Q_kNm, q_S_kNm, q_W_kNm)
            + combi.psi_0_Q2 * _charge_accomp_2(combi, q_Q_kNm, q_S_kNm, q_W_kNm)
            + combi.psi_0_Q3 * _charge_accomp_3(combi, q_Q_kNm, q_S_kNm, q_W_kNm)
        )

        # Efforts internes — portée simple (kN·m, kN) vectorisé
        n = len(longueurs_m)
        q_d_arr = np.full(n, q_d_kNm)  # shape (n,)
        M_d_kNm = q_d_arr * longueurs_m ** 2 / 8.0
        V_d_kN = q_d_arr * longueurs_m / 2.0

        résultat: dict[str, np.ndarray] = {
            "q_G_kNm": np.full(n, q_G_kNm),
            "q_Q_kNm": np.full(n, q_Q_kNm),
            "q_S_kNm": np.full(n, q_S_kNm),
            "q_W_kNm": np.full(n, q_W_kNm),
            "q_d_kNm": q_d_arr,
            "M_d_kNm": M_d_kNm,
            "V_d_kN": V_d_kN,
        }

        # Double flexion (EF-024)
        if config.double_flexion:
            if pente_deg == 0.0:
                logger.warning(
                    "Panne : double_flexion=True avec pente=0° — composante q_z nulle."
                )
                q_y_arr = q_d_arr.copy()
                q_z_arr = np.zeros(n)
            else:
                q_y_arr = q_d_arr * math.cos(pente_rad)
                q_z_arr = q_d_arr * math.sin(pente_rad)

            résultat["q_y_kNm"] = q_y_arr
            résultat["q_z_kNm"] = q_z_arr
            résultat["M_y_kNm"] = q_y_arr * longueurs_m ** 2 / 8.0
            résultat["M_z_kNm"] = q_z_arr * longueurs_m ** 2 / 8.0

        return résultat

    def decomposer(
        self,
        charges_kNm: np.ndarray,
        pente_rad: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Décompose selon cos(α) / sin(α) pour double flexion."""
        q_y = charges_kNm * math.cos(pente_rad)
        q_z = charges_kNm * math.sin(pente_rad)
        return q_y, q_z


def _charge_principale(combi: CombinaisonEC0, q_Q: float, q_S: float, q_W: float) -> float:
    """Retourne la charge principale selon le type de combinaison."""
    mapping = {"Q": q_Q, "S": q_S, "W": q_W, "G": 0.0}
    return mapping.get(combi.charge_principale, 0.0)


def _charge_accomp_2(combi: CombinaisonEC0, q_Q: float, q_S: float, q_W: float) -> float:
    """Retourne la 2e charge d'accompagnement (hors principale)."""
    charges = {"Q": q_Q, "S": q_S, "W": q_W}
    charges.pop(combi.charge_principale, None)
    vals = list(charges.values())
    return vals[0] if len(vals) > 0 else 0.0


def _charge_accomp_3(combi: CombinaisonEC0, q_Q: float, q_S: float, q_W: float) -> float:
    """Retourne la 3e charge d'accompagnement (hors principale et 2e)."""
    charges = {"Q": q_Q, "S": q_S, "W": q_W}
    charges.pop(combi.charge_principale, None)
    vals = list(charges.values())
    return vals[1] if len(vals) > 1 else 0.0
