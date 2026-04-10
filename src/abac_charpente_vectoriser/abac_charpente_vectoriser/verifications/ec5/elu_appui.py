"""
verifications.ec5.elu_appui
============================
Vérification ELU à l'appui (compression perpendiculaire au fil) — EC5 §6.1.5.

σ_c,90,d = R_d / (b × l_appui) ≤ k_c90 × f_c,90,d

R_d = V_d (réaction d'appui en bi-appui simple, hypothèse conservatrice).
b   = largeur de la section (champ ``b_mm`` du matériau).
l_appui = longueur d'appui (champ ``longueur_appui_mm`` de la config).
"""

from __future__ import annotations

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class Appui(VerificationELU):
    """Compression perpendiculaire au fil à l'appui — EC5 §6.1.5.

    σ_c,90,d = R_d / A_appui ≤ k_c90 × f_c,90,d
    A_appui = b_mm × longueur_appui_mm   [mm²]
    """

    @property
    def id_verification(self) -> str:
        return "Appui"

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
            [m.b_mm if m.b_mm is not None else (m.A_cm2 * 100.0 / (m.h_mm if m.h_mm else 100.0))
             for m in espace.materiaux],
            dtype=float,
        )  # (n_M,)

        l_appui_mm: float = espace.longueur_appui_mm
        A_appui_mm2: np.ndarray = b_arr * l_appui_mm  # (n_M,) [mm²]

        # σ_c90 [MPa] = R_d [kN] × 1000 / A_appui [mm²]
        A_appui_11M: np.ndarray = A_appui_mm2[np.newaxis, np.newaxis, :]  # (1, 1, n_M)
        sigma_c90: np.ndarray = espace.V_d_kN * 1000.0 / A_appui_11M     # (n_L, n_C, n_M) [MPa]

        k_c90: float = espace.k_c90
        f_c90_d: np.ndarray = espace.f_c90_d_CM[np.newaxis, :, :]         # (1, n_C, n_M)

        taux: np.ndarray = sigma_c90 / (k_c90 * f_c90_d)
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)
