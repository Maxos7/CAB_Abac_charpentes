"""
verifications.ec5.els_fleche
==============================
Vérifications ELS de flèche — EC5 §7.2.

Trois vérifications :
- ``FlecheInst``         : flèche instantanée w_inst ≤ L / limite_inst
- ``FlecheFin``          : flèche finale w_fin = w_inst × (1 + k_def) ≤ L / limite_fin
- ``FlecheSecondOeuvre`` : flèche nette second-œuvre w_2 ≤ L / limite_2

Formule de flèche bi-appui chargement uniforme (EC5 §7.2) :
    w_inst = 5 × q × L⁴ / (384 × E × I)

Pour les types à double flexion, la flèche résultante est utilisée pour
la vérification globale, mais les composantes séparées sont retournées pour
l'abaque complet.

Pour les chevrons, la flèche est convertie en vertical :
    w_vert = w_rampant / cos(α)   (via ``longueur_projetee_m`` / ``longueurs_m``)
"""

from __future__ import annotations

import math

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELS


def _fleche_inst_bi_appui(
    q_kNm: np.ndarray,
    L_m: np.ndarray,
    E_MPa: np.ndarray,
    I_cm4: np.ndarray,
) -> np.ndarray:
    """Flèche instantanée bi-appui chargement uniforme — EC5 §7.2.

    w = 5 × q × L⁴ / (384 × E × I)

    Toutes les unités sont converties en mm pour le résultat en mm.

    Parameters
    ----------
    q_kNm:
        Charge linéique en kN/m — tableau (n_L, n_C, n_M).
    L_m:
        Portées en mètres — vecteur (n_L,).
    E_MPa:
        Module d'élasticité en MPa — vecteur (n_M,).
    I_cm4:
        Moment quadratique en cm⁴ — vecteur (n_M,).

    Returns
    -------
    np.ndarray
        Flèche instantanée en mm ``(n_L, n_C, n_M)``.
    """
    # Conversions vers unités cohérentes [N, mm]
    q_Nmm: np.ndarray = q_kNm * 1000.0 / 1000.0    # kN/m → N/mm
    L_mm: np.ndarray = L_m[:, np.newaxis, np.newaxis] * 1000.0   # m → mm, (n_L, 1, 1)
    E_Nmm2: np.ndarray = E_MPa[np.newaxis, np.newaxis, :]         # MPa = N/mm², (1, 1, n_M)
    I_mm4: np.ndarray = I_cm4[np.newaxis, np.newaxis, :] * 1e4   # cm⁴ → mm⁴, (1, 1, n_M)

    return 5.0 * q_Nmm * L_mm**4 / (384.0 * E_Nmm2 * I_mm4)   # [mm]


class FlecheInst(VerificationELS):
    """Flèche instantanée — EC5 §7.2.

    w_inst ≤ L / limite_fleche_inst
    Taux = w_inst / (L / limite)
    """

    @property
    def id_verification(self) -> str:
        return "FlecheInst"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche instantanée"

    def calculer(self, espace) -> ResultatVerification:
        """Calcule le taux de flèche instantanée.

        Utilise les combinaisons CAR (ELS caractéristique) pour la charge variable.
        Pour la double flexion, la flèche résultante √(w_y² + w_z²) est comparée
        à la limite.
        """
        L_m: np.ndarray = espace.longueurs_m
        E: np.ndarray = espace.E_mean_MPa_arr          # (n_M,)
        I_y: np.ndarray = espace.I_y_cm4_arr           # (n_M,)
        lim: float = espace.limite_fleche_inst         # L/x

        # Charge sur axe fort (ou totale si pas de double flexion)
        q_y: np.ndarray = (
            espace.M_y_kNm * 8.0 / (L_m[:, np.newaxis, np.newaxis] ** 2)
            if espace.M_y_kNm is not None
            else espace.q_d_kNm
        )

        w_y: np.ndarray = _fleche_inst_bi_appui(q_y, L_m, E, I_y)  # (n_L, n_C, n_M) [mm]

        if espace.M_z_kNm is not None:
            I_z: np.ndarray = espace.I_z_cm4_arr
            q_z: np.ndarray = espace.M_z_kNm * 8.0 / (L_m[:, np.newaxis, np.newaxis] ** 2)
            w_z: np.ndarray = _fleche_inst_bi_appui(q_z, L_m, E, I_z)
            w_inst: np.ndarray = np.sqrt(w_y**2 + w_z**2)
        else:
            w_inst = w_y

        # Conversion de la flèche rampant en vertical pour Chevron
        if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
            w_inst = w_inst / math.cos(espace.pente_rad)
            L_ref: np.ndarray = espace.longueur_projetee_m
        else:
            L_ref = L_m

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]   # (n_L, 1, 1) [mm]
        taux: np.ndarray = w_inst / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)


class FlecheFin(VerificationELS):
    """Flèche finale (avec fluage) — EC5 §7.2.

    w_fin = w_inst × (1 + k_def) ≤ L / limite_fleche_fin

    Approximation conservatrice : tout le chargement est traité avec le même
    facteur (1 + k_def). Pour un calcul plus précis, décomposer G et Q.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFin"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche finale"

    def calculer(self, espace) -> ResultatVerification:
        """Calcule le taux de flèche finale.

        w_fin = w_inst × (1 + k_def)
        """
        L_m: np.ndarray = espace.longueurs_m
        E: np.ndarray = espace.E_mean_MPa_arr
        I_y: np.ndarray = espace.I_y_cm4_arr
        k_def: np.ndarray = espace.k_def_arr           # (n_M,)
        lim: float = espace.limite_fleche_fin

        q_y: np.ndarray = (
            espace.M_y_kNm * 8.0 / (L_m[:, np.newaxis, np.newaxis] ** 2)
            if espace.M_y_kNm is not None
            else espace.q_d_kNm
        )

        w_y: np.ndarray = _fleche_inst_bi_appui(q_y, L_m, E, I_y)
        k_def_11M: np.ndarray = k_def[np.newaxis, np.newaxis, :]

        if espace.M_z_kNm is not None:
            I_z: np.ndarray = espace.I_z_cm4_arr
            q_z: np.ndarray = espace.M_z_kNm * 8.0 / (L_m[:, np.newaxis, np.newaxis] ** 2)
            w_z: np.ndarray = _fleche_inst_bi_appui(q_z, L_m, E, I_z)
            w_fin: np.ndarray = np.sqrt((w_y * (1.0 + k_def_11M))**2 + (w_z * (1.0 + k_def_11M))**2)
        else:
            w_fin = w_y * (1.0 + k_def_11M)

        if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
            w_fin = w_fin / math.cos(espace.pente_rad)
            L_ref: np.ndarray = espace.longueur_projetee_m
        else:
            L_ref = L_m

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)


class FlecheSecondOeuvre(VerificationELS):
    """Flèche nette second-œuvre — EC5 §7.2.

    w_2 = w_Q,fin + k_def × (w_G + w_G2)_qperm ≤ L / limite_fleche_2

    Active uniquement si ``config.second_oeuvre = True`` et
    ``limite_fleche_2`` est définie dans l'espace.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheSecondOeuvre"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche nette second-œuvre"

    def calculer(self, espace) -> ResultatVerification:
        """Active uniquement si ``limite_fleche_2`` est définie."""
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.limite_fleche_2 is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        E: np.ndarray = espace.E_mean_MPa_arr
        I_y: np.ndarray = espace.I_y_cm4_arr
        k_def: np.ndarray = espace.k_def_arr
        lim: float = espace.limite_fleche_2
        k_def_11M: np.ndarray = k_def[np.newaxis, np.newaxis, :]

        # Flèche due aux charges permanentes (quasi-permanente) pour le fluage
        q_G_LCM: np.ndarray = espace.q_G_kNm
        w_G: np.ndarray = _fleche_inst_bi_appui(q_G_LCM, L_m, E, I_y)

        # Flèche due à G2 (scalaire → broadcast)
        q_G2_Nmm: float = float(espace.q_G2_kNm)   # kN/m → N/mm (déjà linéique)
        w_G2: np.ndarray = 5.0 * q_G2_Nmm * (L_m[:, np.newaxis, np.newaxis] * 1000.0)**4 / (
            384.0 * E[np.newaxis, np.newaxis, :] * I_y[np.newaxis, np.newaxis, :] * 1e4
        )

        # Flèche due aux charges variables (quasi-permanente pour w_Q,fin)
        # En pratique : w_Q,fin ≈ w_inst_Q (psi_2 = 0 pour toitures)
        # Ici : approximé par la flèche totale moins la flèche permanente
        w_total: np.ndarray = _fleche_inst_bi_appui(espace.q_d_kNm, L_m, E, I_y)
        w_Q: np.ndarray = np.maximum(w_total - w_G, 0.0)

        w_2: np.ndarray = w_Q + k_def_11M * (w_G + w_G2)

        if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
            w_2 = w_2 / math.cos(espace.pente_rad)
            L_ref: np.ndarray = espace.longueur_projetee_m
        else:
            L_ref = L_m

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_2 / limite_mm
        active: np.ndarray = np.ones((n_L, n_C, n_M), dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)
