"""
verifications.ec5.elu_flambement
=================================
Vérifications ELU de flambement (instabilité par compression axiale) — EC5 §6.3.2.

Deux vérifications indépendantes :
- ``FlambementAxeFort``   : §6.3.2 — σ_c,0,d / (k_c,y × f_c,0,d) ≤ 1.0
- ``FlambementAxeFaible`` : §6.3.2 — σ_c,0,d / (k_c,z × f_c,0,d) ≤ 1.0

k_c,y et k_c,z sont les facteurs d'instabilité calculés depuis les élancements
relatifs λ_rel,y et λ_rel,z (voir ``ec5.proprietes.calculer_k_c_LM``).

Ces vérifications sont inactives si N_d est None (pas d'effort normal) ou si
N_d ≥ 0 (traction — flambement non applicable).

Pour les membres de faible élancement (λ_rel ≤ 0.3), k_c = 1.0 et la vérification
est identique à la compression simple §6.1.4 (classe Compression).
"""

from __future__ import annotations

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class FlambementAxeFort(VerificationELU):
    """Flambement par rapport à l'axe fort y — EC5 §6.3.2.

    σ_c,0,d / (k_c,y × f_c,0,d) ≤ 1.0

    Active uniquement si N_d < 0 (compression).
    """

    @property
    def id_verification(self) -> str:
        return "k_c_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.3.2 — flambement axe fort"

    def calculer(self, espace) -> ResultatVerification:
        """Active si N_d < 0.

        σ_c0 = |N_d| / A   [MPa]
        Taux = σ_c0 / (k_c,y × f_c,0,d)
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.N_d_kN is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        A: np.ndarray = np.array([m.A_cm2 for m in espace.materiaux], dtype=float)
        A_11M: np.ndarray = A[np.newaxis, np.newaxis, :]
        k_c_y: np.ndarray = espace.k_c_y_LM[:, np.newaxis, :]  # (n_L, 1, n_M)
        f_c0_d: np.ndarray = espace.f_c0_d_CM[np.newaxis, :, :]  # (1, n_C, n_M)

        N_d: np.ndarray = espace.N_d_kN
        active: np.ndarray = N_d < 0

        sigma_c0: np.ndarray = np.where(active, np.abs(N_d) / A_11M * 10.0, 0.0)
        taux: np.ndarray = np.where(active, sigma_c0 / (k_c_y * f_c0_d), 0.0)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=sigma_c0, unite_intermediaire="MPa",
        )


class FlambementAxeFaible(VerificationELU):
    """Flambement par rapport à l'axe faible z — EC5 §6.3.2.

    σ_c,0,d / (k_c,z × f_c,0,d) ≤ 1.0

    Active uniquement si N_d < 0 (compression). Condition généralement
    déterminante pour les sections élancées (h >> b).
    """

    @property
    def id_verification(self) -> str:
        return "k_c_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.3.2 — flambement axe faible"

    def calculer(self, espace) -> ResultatVerification:
        """Active si N_d < 0.

        σ_c0 = |N_d| / A   [MPa]
        Taux = σ_c0 / (k_c,z × f_c,0,d)
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.N_d_kN is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        A: np.ndarray = np.array([m.A_cm2 for m in espace.materiaux], dtype=float)
        A_11M: np.ndarray = A[np.newaxis, np.newaxis, :]
        k_c_z: np.ndarray = espace.k_c_z_LM[:, np.newaxis, :]  # (n_L, 1, n_M)
        f_c0_d: np.ndarray = espace.f_c0_d_CM[np.newaxis, :, :]  # (1, n_C, n_M)

        N_d: np.ndarray = espace.N_d_kN
        active: np.ndarray = N_d < 0

        sigma_c0: np.ndarray = np.where(active, np.abs(N_d) / A_11M * 10.0, 0.0)
        taux: np.ndarray = np.where(active, sigma_c0 / (k_c_z * f_c0_d), 0.0)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=sigma_c0, unite_intermediaire="MPa",
        )
