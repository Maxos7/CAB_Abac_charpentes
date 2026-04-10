"""
verifications.ec5.elu_combines
================================
Vérifications ELU des sollicitations combinées — EC5 §6.2.3 et §6.2.4.

Trois vérifications :
- ``FlexionTraction``          : §6.2.3 — flexion + traction (N_d > 0)
- ``FlexionCompressionForte``  : §6.2.4 Eq.(6.23) — condition axe fort (N_d < 0)
- ``FlexionCompressionFaible`` : §6.2.4 Eq.(6.24) — condition axe faible (N_d < 0)

Ces vérifications sont inactives si N_d est None (cas des poutres simples sans
effort normal — solives, pannes, chevrons en bi-appui simple).
"""

from __future__ import annotations

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class FlexionTraction(VerificationELU):
    """Flexion combinée à la traction — EC5 §6.2.3.

    σ_t,0,d / f_t,0,d + σ_m,d / f_m,d ≤ 1.0
    """

    @property
    def id_verification(self) -> str:
        return "FlexionTraction"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.2.3"

    def calculer(self, espace) -> ResultatVerification:
        """Active si N_d > 0.

        σ_t0 = N_d / A,   σ_m = M_d / W_y
        Taux = σ_t0 / f_t0,d + σ_m / f_m,d
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.N_d_kN is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        A: np.ndarray = np.array([m.A_cm2 for m in espace.materiaux], dtype=float)
        A_11M: np.ndarray = A[np.newaxis, np.newaxis, :]
        W_y: np.ndarray = espace.W_y_cm3_arr[np.newaxis, np.newaxis, :]
        f_t0_d: np.ndarray = espace.f_t0_d_CM[np.newaxis, :, :]
        f_m_d: np.ndarray = espace.f_m_d_CM[np.newaxis, :, :]

        N_d: np.ndarray = espace.N_d_kN
        active: np.ndarray = N_d > 0

        sigma_t0: np.ndarray = np.where(active, N_d / A_11M * 10.0, 0.0)
        sigma_m: np.ndarray = espace.M_d_kNm / W_y * 1e3

        taux: np.ndarray = np.where(active, sigma_t0 / f_t0_d + sigma_m / f_m_d, 0.0)

        return ResultatVerification(self.id_verification, taux, active)


class FlexionCompressionForte(VerificationELU):
    """Flexion + compression — condition axe fort — EC5 §6.2.4 Eq.(6.23).

    (σ_c,0,d / f_c,0,d)² + σ_m,y,d / (k_crit × f_m,d) ≤ 1.0
    """

    @property
    def id_verification(self) -> str:
        return "FlexionCompressionForte"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.2.4 Eq.(6.23)"

    def calculer(self, espace) -> ResultatVerification:
        """Active si N_d < 0."""
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros = np.zeros((n_L, n_C, n_M))
        false_mask = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.N_d_kN is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        A: np.ndarray = np.array([m.A_cm2 for m in espace.materiaux], dtype=float)
        A_11M: np.ndarray = A[np.newaxis, np.newaxis, :]
        W_y: np.ndarray = espace.W_y_cm3_arr[np.newaxis, np.newaxis, :]
        k_crit: np.ndarray = espace.k_crit_LM[:, np.newaxis, :]
        f_c0_d: np.ndarray = espace.f_c0_d_CM[np.newaxis, :, :]
        f_m_d: np.ndarray = espace.f_m_d_CM[np.newaxis, :, :]

        N_d: np.ndarray = espace.N_d_kN
        active: np.ndarray = N_d < 0

        sigma_c0: np.ndarray = np.where(active, np.abs(N_d) / A_11M * 10.0, 0.0)
        sigma_m_y: np.ndarray = espace.M_d_kNm / W_y * 1e3

        taux: np.ndarray = np.where(
            active,
            (sigma_c0 / f_c0_d) ** 2 + sigma_m_y / (k_crit * f_m_d),
            0.0,
        )

        return ResultatVerification(self.id_verification, taux, active)


class FlexionCompressionFaible(VerificationELU):
    """Flexion + compression — condition axe faible — EC5 §6.2.4 Eq.(6.24).

    (σ_c,0,d / f_c,0,d)² + k_m × σ_m,y,d / (k_crit × f_m,d) ≤ 1.0

    Cette condition est généralement moins déterminante que Eq.(6.23) pour les
    sections rectangulaires (k_m = 0.7 < 1.0), mais est requise par la norme.
    """

    @property
    def id_verification(self) -> str:
        return "FlexionCompressionFaible"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.2.4 Eq.(6.24)"

    def calculer(self, espace) -> ResultatVerification:
        """Active si N_d < 0."""
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros = np.zeros((n_L, n_C, n_M))
        false_mask = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.N_d_kN is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        # k_m depuis params_ec5.csv
        from ..ec5.elu_flexion import _k_m
        km: float = _k_m()

        A: np.ndarray = np.array([m.A_cm2 for m in espace.materiaux], dtype=float)
        A_11M: np.ndarray = A[np.newaxis, np.newaxis, :]
        W_y: np.ndarray = espace.W_y_cm3_arr[np.newaxis, np.newaxis, :]
        k_crit: np.ndarray = espace.k_crit_LM[:, np.newaxis, :]
        f_c0_d: np.ndarray = espace.f_c0_d_CM[np.newaxis, :, :]
        f_m_d: np.ndarray = espace.f_m_d_CM[np.newaxis, :, :]

        N_d: np.ndarray = espace.N_d_kN
        active: np.ndarray = N_d < 0

        sigma_c0: np.ndarray = np.where(active, np.abs(N_d) / A_11M * 10.0, 0.0)
        sigma_m_y: np.ndarray = espace.M_d_kNm / W_y * 1e3

        taux: np.ndarray = np.where(
            active,
            (sigma_c0 / f_c0_d) ** 2 + km * sigma_m_y / (k_crit * f_m_d),
            0.0,
        )

        return ResultatVerification(self.id_verification, taux, active)
