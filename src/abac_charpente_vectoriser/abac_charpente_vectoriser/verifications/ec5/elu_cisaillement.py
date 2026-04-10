"""
verifications.ec5.elu_cisaillement
===================================
Vérification ELU de cisaillement — EC5 §6.1.7.

τ_d = 1.5 × V_d / A_eff ≤ f_v,d

A_eff = A × k_cr (section efficace pour le cisaillement, EC5 §6.1.7(2)).
k_cr est intégré dans ``ConfigMatériauVect.A_eff_cisaillement_cm2``.
"""

from __future__ import annotations

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class Cisaillement(VerificationELU):
    """Cisaillement — EC5 §6.1.7.

    τ_d = 1.5 × V_d / A_eff ≤ f_v,d
    """

    @property
    def id_verification(self) -> str:
        return "Cisaillement"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.1.7"

    def calculer(self, espace) -> ResultatVerification:
        """Calcule le taux de cisaillement.

        V_d [kN], A_eff [cm²] → τ_d [MPa] : V_d / A_eff × 1.5 × 10 = MPa
        Facteur 10 : kN/cm² × 10 = MPa.

        Shapes :
            V_d_kN         : (n_L, n_C, n_M)
            A_eff_cm2_arr  : (n_M,)  → (1, 1, n_M)
            f_v_d_CM       : (n_C, n_M) → (1, n_C, n_M)
        """
        A_eff: np.ndarray = espace.A_eff_cis_cm2_arr[np.newaxis, np.newaxis, :]  # (1, 1, n_M)
        f_v_d: np.ndarray = espace.f_v_d_CM[np.newaxis, :, :]                    # (1, n_C, n_M)

        # τ_d = 1.5 × V / A_eff  [kN/cm²] × 10 = [MPa]
        tau_d: np.ndarray = 1.5 * espace.V_d_kN / A_eff * 10.0   # (n_L, n_C, n_M) [MPa]

        taux: np.ndarray = tau_d / f_v_d
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)
