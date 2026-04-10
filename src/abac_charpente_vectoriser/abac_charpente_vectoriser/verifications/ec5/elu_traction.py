"""
verifications.ec5.elu_traction
================================
Vérification ELU de traction parallèle au fil — EC5 §6.1.2.

σ_t,0,d = N_d / A ≤ f_t,0,d

Active uniquement si N_d > 0 (effort de traction). Retourne 0.0 si N_d est None
ou si N_d ≤ 0 pour tous les éléments.
"""

from __future__ import annotations

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class Traction(VerificationELU):
    """Traction parallèle au fil — EC5 §6.1.2.

    σ_t,0,d = N_d / A ≤ f_t,0,d
    """

    @property
    def id_verification(self) -> str:
        return "Traction"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.1.2"

    def calculer(self, espace) -> ResultatVerification:
        """Active uniquement si N_d > 0.

        N_d [kN], A [cm²] → σ_t0 [MPa] : N_d / A × 10.

        Shapes :
            N_d_kN    : (n_L, n_C, n_M) ou None
            A_cm2_arr : (n_M,) → (1, 1, n_M)
            f_t0_d_CM : (n_C, n_M) → (1, n_C, n_M)
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.N_d_kN is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        A: np.ndarray = np.array([m.A_cm2 for m in espace.materiaux], dtype=float)
        A_11M: np.ndarray = A[np.newaxis, np.newaxis, :]
        f_t0_d: np.ndarray = espace.f_t0_d_CM[np.newaxis, :, :]

        N_d: np.ndarray = espace.N_d_kN
        active: np.ndarray = N_d > 0

        sigma_t0: np.ndarray = np.where(active, N_d / A_11M * 10.0, 0.0)
        taux: np.ndarray = np.where(active, sigma_t0 / f_t0_d, 0.0)

        return ResultatVerification(self.id_verification, taux, active)
