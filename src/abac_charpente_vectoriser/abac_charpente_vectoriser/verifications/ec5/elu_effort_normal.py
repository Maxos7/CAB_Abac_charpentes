"""
verifications.ec5.elu_effort_normal
=====================================
Vérifications ELU liées à l'effort normal N_d — EC5 §6.1.2, §6.1.3, §6.1.4.

Trois vérifications :
- ``Traction``             : §6.1.2 — σ_t,0,d = N_d / A ≤ f_t,0,d (parallèle au fil)
- ``TractionTransversale`` : §6.1.3 — σ_t,90,d ≤ f_t,90,d (perpendiculaire au fil)
- ``Compression``          : §6.1.4 — σ_c,0,d = |N_d| / A ≤ f_c,0,d (parallèle au fil)

``Traction`` et ``TractionTransversale`` sont actives si N_d > 0.
``TractionTransversale`` requiert en outre que l'élément soit incliné (pente_rad défini).
``Compression`` est active si N_d < 0. Le flambement n'est pas traité ici (voir
``elu_flambement.py``, EC5 §6.3.2).
"""

from __future__ import annotations

import math

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class Traction(VerificationELU):
    """Traction parallèle au fil — EC5 §6.1.2.

    σ_t,0,d = N_d / A ≤ f_t,0,d
    """

    @property
    def id_verification(self) -> str:
        return "sigma_t0"

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

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=sigma_t0, unite_intermediaire="MPa",
        )


class TractionTransversale(VerificationELU):
    """Traction perpendiculaire au fil — EC5 §6.1.3.

    σ_t,90,d ≤ f_t,90,d

    Active si N_d > 0 ET pente_rad est défini. La composante perpendiculaire
    au fil de l'effort de traction axiale vaut :
        σ_t,90,d = N_d × sin(pente_rad) / A

    Cette vérification est pertinente pour les éléments inclinés (chevrons,
    arbalétriers) soumis à un effort de traction avec une composante transversale
    par rapport au fil du bois.
    """

    @property
    def id_verification(self) -> str:
        return "sigma_t90"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.1.3"

    def calculer(self, espace) -> ResultatVerification:
        """Active si N_d > 0 et pente_rad défini.

        σ_t,90,d = N_d × sin(α) / A   [MPa]
        Taux = σ_t,90,d / f_t,90,d
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.N_d_kN is None or espace.pente_rad is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        sin_alpha: float = math.sin(espace.pente_rad)

        A: np.ndarray = np.array([m.A_cm2 for m in espace.materiaux], dtype=float)
        A_11M: np.ndarray = A[np.newaxis, np.newaxis, :]
        f_t90_d: np.ndarray = espace.f_t90_d_CM[np.newaxis, :, :]  # (1, n_C, n_M)

        N_d: np.ndarray = espace.N_d_kN
        active: np.ndarray = N_d > 0

        # σ_t,90 = composante transversale de la traction axiale [MPa]
        sigma_t90: np.ndarray = np.where(active, N_d * sin_alpha / A_11M * 10.0, 0.0)
        taux: np.ndarray = np.where(active, sigma_t90 / f_t90_d, 0.0)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=sigma_t90, unite_intermediaire="MPa",
        )


class Compression(VerificationELU):
    """Compression parallèle au fil — EC5 §6.1.4.

    σ_c,0,d = |N_d| / A ≤ f_c,0,d
    (Sans vérification du flambement — EC5 §6.3.2 traité dans ``elu_flambement.py``.)
    """

    @property
    def id_verification(self) -> str:
        return "sigma_c0"

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

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=sigma_c0, unite_intermediaire="MPa",
        )
