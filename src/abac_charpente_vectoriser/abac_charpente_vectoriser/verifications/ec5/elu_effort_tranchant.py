"""
verifications.ec5.elu_effort_tranchant
========================================
Vérifications ELU liées à l'effort tranchant V_d — EC5 §6.1.5 et §6.1.7.

Deux vérifications :
- ``Cisaillement`` : §6.1.7 — τ_d = 1.5 × V_d / A_eff ≤ f_v,d
- ``Appui``        : §6.1.5 — σ_c,90,d = R_d / (b × l_appui) ≤ k_c90 × f_c,90,d

Les deux utilisent V_d comme effort de base. ``Cisaillement`` vérifie la contrainte
tangentielle dans la section courante ; ``Appui`` vérifie la compression
perpendiculaire au fil à la réaction d'appui (R_d ≈ V_d en bi-appui simple).
Les deux vérifications sont toujours actives.
"""

from __future__ import annotations

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class Cisaillement(VerificationELU):
    """Cisaillement — EC5 §6.1.7.

    τ_d = 1.5 × V_d / A_eff ≤ f_v,d

    A_eff = A × k_cr (section efficace pour le cisaillement, EC5 §6.1.7(2)).
    k_cr est intégré dans ``ConfigMatériauVect.A_eff_cisaillement_cm2``.
    """

    @property
    def id_verification(self) -> str:
        return "tau_d"

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
        A_eff: np.ndarray = espace.A_eff_cis_cm2_arr[
            np.newaxis, np.newaxis, :
        ]  # (1, 1, n_M)
        f_v_d: np.ndarray = espace.f_v_d_CM[np.newaxis, :, :]  # (1, n_C, n_M)

        # τ_d = 1.5 × V / A_eff  [kN/cm²] × 10 = [MPa]
        tau_d: np.ndarray = 1.5 * espace.V_d_kN / A_eff * 10.0  # (n_L, n_C, n_M) [MPa]

        taux: np.ndarray = tau_d / f_v_d
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=tau_d, unite_intermediaire="MPa",
        )


class Appui(VerificationELU):
    """Compression perpendiculaire au fil à l'appui — EC5 §6.1.5.

    σ_c,90,d = R_d / A_appui ≤ k_c90 × f_c,90,d
    A_appui = b_mm × longueur_appui_mm   [mm²]

    R_d = V_d (réaction d'appui en bi-appui simple, hypothèse conservatrice).
    b   = largeur de la section (champ ``b_mm`` du matériau).
    l_appui = longueur d'appui (champ ``longueur_appui_mm`` de la config).
    """

    @property
    def id_verification(self) -> str:
        return "sigma_c90"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.1.5"

    def calculer(self, espace) -> ResultatVerification:
        """Calcule le taux de compression à l'appui.

        R_d = V_d [kN]. A_appui [mm²] → σ_c90 [MPa] = R_d × 1000 / A_appui.

        Si ``b_mm`` est None (section personnalisée), la largeur efficace est estimée
        depuis A_eff_cis_cm2 / (h_mm/10) — approximation conservatrice.

        Shapes :
            V_d_kN       : (n_L, n_C, n_M)
            b_appui_arr  : (n_M,) → (1, 1, n_M)
            f_c90_d_CM   : (n_C, n_M) → (1, n_C, n_M)
        """
        # Largeur de section par matériau [mm]
        b_arr: np.ndarray = np.array(
            [
                m.b_mm
                if m.b_mm is not None
                else (m.A_cm2 * 100.0 / (m.h_mm if m.h_mm else 100.0))
                for m in espace.materiaux
            ],
            dtype=float,
        )  # (n_M,)

        l_appui_mm: float = espace.longueur_appui_mm
        A_appui_mm2: np.ndarray = b_arr * l_appui_mm  # (n_M,) [mm²]

        # σ_c90 [MPa] = R_d [kN] × 1000 / A_appui [mm²]
        A_appui_11M: np.ndarray = A_appui_mm2[np.newaxis, np.newaxis, :]  # (1, 1, n_M)
        sigma_c90: np.ndarray = (
            espace.V_d_kN * 1000.0 / A_appui_11M
        )  # (n_L, n_C, n_M) [MPa]

        k_c90: float = espace.k_c90
        f_c90_d: np.ndarray = espace.f_c90_d_CM[np.newaxis, :, :]  # (1, n_C, n_M)

        taux: np.ndarray = sigma_c90 / (k_c90 * f_c90_d)
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=sigma_c90, unite_intermediaire="MPa",
        )
