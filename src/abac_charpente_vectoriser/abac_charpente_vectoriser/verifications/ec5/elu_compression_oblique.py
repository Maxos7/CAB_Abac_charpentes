"""
verifications.ec5.elu_compression_oblique
==========================================
Vérification ELU de compression oblique (formule de Hankinson) — EC5 §6.2.2.

La résistance à la compression sous un angle α par rapport au fil est donnée
par la formule de Hankinson :

    f_c,α,d = f_c,0,d × f_c,90,d / (f_c,0,d × sin²α + f_c,90,d × cos²α)

Cas d'application typique : pied de chevron ou d'arbalétrier posé sur une
sablière ou une panne faîtière. L'angle α est la pente du rampant (pente_rad),
correspondant à l'angle entre la direction de la force de réaction (verticale)
et le fil du bois (direction du rampant).

Active uniquement si pente_rad est défini et non nul (élément incliné).
La contrainte de compression oblique est calculée depuis la réaction d'appui V_d,
identiquement à la vérification ``Appui`` (EC5 §6.1.5), mais la résistance
admissible est la résistance Hankinson plutôt que f_c,90,d seule.
"""

from __future__ import annotations

import math

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class CompressionOblique(VerificationELU):
    """Compression oblique à l'appui — formule de Hankinson — EC5 §6.2.2.

    σ_c,α,d = V_d / A_appui ≤ f_c,α,d = f_c,0,d × f_c,90,d / (f_c,0,d × sin²α + f_c,90,d × cos²α)

    Active uniquement si pente_rad est défini et non nul (α > 0).
    Si α = 0 : dégénère en compression parallèle (non applicable, vérif. non active).
    Si α = 90° : dégénère en compression transversale (vérif. Appui §6.1.5).
    """

    @property
    def id_verification(self) -> str:
        return "CompressionOblique"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.2.2 — Hankinson"

    def calculer(self, espace) -> ResultatVerification:
        """Active uniquement si pente_rad est défini et non nul.

        R_d = V_d [kN]. A_appui = b_mm × longueur_appui_mm [mm²].
        σ_c,α = R_d × 1000 / A_appui [MPa].
        f_c,α,d calculé par la formule de Hankinson.

        Shapes :
            V_d_kN       : (n_L, n_C, n_M)
            f_c0_d_CM    : (n_C, n_M) → (1, n_C, n_M)
            f_c90_d_CM   : (n_C, n_M) → (1, n_C, n_M)
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.pente_rad is None or math.isclose(espace.pente_rad, 0.0, abs_tol=1e-6):
            return ResultatVerification(self.id_verification, zeros, false_mask)

        alpha: float = espace.pente_rad
        sin2: float = math.sin(alpha) ** 2
        cos2: float = math.cos(alpha) ** 2

        # Largeur de section [mm] par matériau
        b_arr: np.ndarray = np.array(
            [m.b_mm if m.b_mm is not None else (m.A_cm2 * 100.0 / (m.h_mm if m.h_mm else 100.0))
             for m in espace.materiaux],
            dtype=float,
        )  # (n_M,)

        l_appui_mm: float = espace.longueur_appui_mm
        A_appui_mm2: np.ndarray = b_arr * l_appui_mm  # (n_M,) [mm²]
        A_appui_11M: np.ndarray = A_appui_mm2[np.newaxis, np.newaxis, :]  # (1, 1, n_M)

        # Contrainte de compression oblique à l'appui [MPa]
        sigma_c_alpha: np.ndarray = espace.V_d_kN * 1000.0 / A_appui_11M  # (n_L, n_C, n_M)

        # Résistance Hankinson [MPa]
        f_c0_d: np.ndarray = espace.f_c0_d_CM[np.newaxis, :, :]   # (1, n_C, n_M)
        f_c90_d: np.ndarray = espace.f_c90_d_CM[np.newaxis, :, :]  # (1, n_C, n_M)
        f_c_alpha_d: np.ndarray = (f_c0_d * f_c90_d) / (f_c0_d * sin2 + f_c90_d * cos2)

        taux: np.ndarray = sigma_c_alpha / (espace.k_c90 * f_c_alpha_d)
        active: np.ndarray = np.ones((n_L, n_C, n_M), dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)
