"""
verifications.ec5.elu_compression
===================================
Vérification ELU de compression parallèle au fil — EC5 §6.1.4.

σ_c,0,d = |N_d| / A ≤ f_c,0,d

Active uniquement si N_d < 0 (effort de compression). Retourne 0.0 si N_d est None
ou si N_d ≥ 0. Le flambement n'est pas vérifié ici (nécessite longueur de flambement).
"""

from __future__ import annotations

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class Compression(VerificationELU):
    """Compression parallèle au fil — EC5 §6.1.4.

    σ_c,0,d = |N_d| / A ≤ f_c,0,d
    (Sans vérification du flambement — EC5 §6.3.2 à implémenter en extension.)
    """

    @property
    def id_verification(self) -> str:
        return "Compression"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.1.4"

    def calculer(self, espace) -> ResultatVerification:
        """Active uniquement si N_d < 0.

        N_d [kN], A [cm²] → σ_c0 [MPa] : |N_d| / A × 10.

        Shapes :
            N_d_kN    : (n_L, n_C, n_M) ou None
            A_cm2_arr : (n_M,) → (1, 1, n_M)
            f_c0_d_CM : (n_C, n_M) → (1, n_C, n_M)
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.N_d_kN is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        A: np.ndarray = np.array([m.A_cm2 for m in espace.materiaux], dtype=float)
        A_11M: np.ndarray = A[np.newaxis, np.newaxis, :]
        f_c0_d: np.ndarray = espace.f_c0_d_CM[np.newaxis, :, :]

        N_d: np.ndarray = espace.N_d_kN
        active: np.ndarray = N_d < 0

        sigma_c0: np.ndarray = np.where(active, np.abs(N_d) / A_11M * 10.0, 0.0)
        taux: np.ndarray = np.where(active, sigma_c0 / f_c0_d, 0.0)

        return ResultatVerification(self.id_verification, taux, active)
