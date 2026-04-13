"""
verifications.ec5.els_fleche
==============================
Vérifications ELS de flèche — EC5 §7.2 + AN française.

Douze vérifications (4 combinées + 4 variantes axe fort + 4 variantes axe faible) :

Flèche instantanée sous charges variables seules (AN France) :
  ``FlecheInst``          : Winst(Q) ≤ L/lim   (flèche verticale combinée)
  ``FlecheInst_y``        : Winst,y(Q) ≤ L/lim  (axe fort seul)
  ``FlecheInst_z``        : Winst,z(Q) ≤ L/lim  (axe faible — double flexion)

Flèche finale brute avant contre-flèche (MD Bat L/125) :
  ``FlecheFinBrute``      : Wfin ≤ L/125  (combiné)
  ``FlecheFinBrute_y``    : Wfin,y ≤ L/125  (axe fort)
  ``FlecheFinBrute_z``    : Wfin,z ≤ L/125  (axe faible — double flexion)

Flèche nette finale après contre-flèche (MD Bat L/200) :
  ``FlecheFin``           : Wnet,fin ≤ L/200  (combiné)
  ``FlecheFin_y``         : Wnet,fin,y ≤ L/200  (axe fort)
  ``FlecheFin_z``         : Wnet,fin,z ≤ L/200  (axe faible — double flexion)

Flèche second-œuvre (EC5 §7.2 L/500) :
  ``FlecheSecondOeuvre``  : Wtot,2 ≤ L/500  (combiné)
  ``FlecheSecondOeuvre_y``: Wtot,2,y ≤ L/500  (axe fort)
  ``FlecheSecondOeuvre_z``: Wtot,2,z ≤ L/500  (axe faible — double flexion)

Formule bi-appui chargement uniforme (EC5 §7.2) :
    w_inst = 5 × q × L⁴ / (384 × E × I)

Pour les éléments à double flexion (fleches_double=True) :
  - Les composantes y (axe fort) et z (axe faible) sont calculées séparément.
  - La flèche verticale combinée :
      w_vert = w_y × cos(α) + w_z × sin(α)   si pente_rad connu
      w_vert = √(w_y² + w_z²)                 fallback si pente_rad=None

Pour les chevrons, conversion rampant → vertical :
    w_vert = w_rampant / cos(α)   (portée de référence = longueur_projetee_m)

Décomposition G/Q par axe :
  - Charges permanentes (G) projetées via cos/sin(α) si pente connue, via ratios
    de moment |M_y|/(|M_y|+|M_z|) sinon.
  - q_Q forcé à 0 pour les combinaisons ELU (masque els_mask) afin de n'utiliser
    que les charges caractéristiques (γ=1.0) dans les calculs de flèche.
"""

from __future__ import annotations

import math

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELS


# ── Helpers de calcul ────────────────────────────────────────────────────────


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
        Charge linéique en kN/m — tableau (n_L, n_C, n_M) ou scalaire broadcastable.
    L_m:
        Portées en mètres — vecteur (n_L,).
    E_MPa:
        Module d'élasticité en MPa — vecteur (n_M,).
    I_cm4:
        Moment quadratique en cm⁴ — vecteur (n_M,).

    Returns
    -------
    np.ndarray
        Flèche instantanée en mm — broadcast vers ``(n_L, n_C, n_M)``.
    """
    # Conversions vers unités cohérentes [N, mm]
    q_Nmm: np.ndarray = q_kNm * 1000.0 / 1000.0    # kN/m → N/mm
    L_mm: np.ndarray = L_m[:, np.newaxis, np.newaxis] * 1000.0   # m → mm, (n_L, 1, 1)
    E_Nmm2: np.ndarray = E_MPa[np.newaxis, np.newaxis, :]         # MPa = N/mm², (1, 1, n_M)
    I_mm4: np.ndarray = I_cm4[np.newaxis, np.newaxis, :] * 1e4   # cm⁴ → mm⁴, (1, 1, n_M)

    return 5.0 * q_Nmm * L_mm**4 / (384.0 * E_Nmm2 * I_mm4)   # [mm]


class FlecheInst(VerificationELS):
    """Flèche instantanée combinée — EC5 §7.2 + AN française.

    Winst(Q) ≤ L / limite_fleche_inst   (flèche verticale combinée)

    AN française : flèche calculée sous **charges variables seules** (Q+S).
    Pour double flexion : w_vert = w_y×cos(α) + w_z×sin(α).
    Désactivée si ``limite_fleche_inst is None``.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheInst"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 + AN — flèche instantanée Winst(Q) combinée"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.limite_fleche_inst is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_inst

        w_y, w_z, w_comb, L_ref = _calculer_w_inst_composantes(espace, L_m)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_comb / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_comb, unite_intermediaire="mm",
        )


class FlecheInstY(VerificationELS):
    """Flèche instantanée axe fort — EC5 §7.2 + AN française.

    Winst,y(Q) ≤ L / limite_fleche_inst   (composante axe fort seul)

    Désactivée si ``limite_fleche_inst is None``.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheInst_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 + AN — flèche instantanée Winst,y(Q) axe fort"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.limite_fleche_inst is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_inst

        w_y, _w_z, _w_comb, L_ref = _calculer_w_inst_composantes(espace, L_m)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_y / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_y, unite_intermediaire="mm",
        )


class FlecheInstZ(VerificationELS):
    """Flèche instantanée axe faible — EC5 §7.2 + AN française.

    Winst,z(Q) ≤ L / limite_fleche_inst   (composante axe faible seul)

    Désactivée si ``limite_fleche_inst is None`` ou si simple flexion.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheInst_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 + AN — flèche instantanée Winst,z(Q) axe faible"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.limite_fleche_inst is None or not espace.fleches_double:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_inst

        _w_y, w_z, _w_comb, L_ref = _calculer_w_inst_composantes(espace, L_m)

        if w_z is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_z / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_z, unite_intermediaire="mm",
        )


# ── Classes ELS flèche finale brute ─────────────────────────────────────────


class FlecheFinBrute(VerificationELS):
    """Flèche finale brute combinée — EC5 §7.2(2) + MD Bat (Wfin ≤ L/125).

    Wfin = w_G×(1+k_def) + w_Q ≤ L / limite_fleche_fin_brut   (flèche combinée)

    Vérification AVANT soustraction de la contre-flèche. Toujours active.
    Limite MD Bat : L/125 pour tous les éléments de toiture.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFinBrute"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) eq.(7.3) — flèche finale brute Wfin ≤ L/125"

    def calculer(self, espace) -> ResultatVerification:
        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_fin_brut

        w_fin_y, w_fin_z, w_fin_comb, L_ref = _calculer_w_fin_composantes(espace, L_m)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin_comb / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_fin_comb, unite_intermediaire="mm",
        )


class FlecheFinBruteY(VerificationELS):
    """Flèche finale brute axe fort — EC5 §7.2(2) (Wfin,y ≤ L/125).

    Wfin,y = w_G,y×(1+k_def) + w_Q,y   (composante axe fort seul)

    Toujours active.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFinBrute_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) — flèche finale brute Wfin,y ≤ L/125 axe fort"

    def calculer(self, espace) -> ResultatVerification:
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

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_fin_z, unite_intermediaire="mm",
        )


# ── Classes ELS flèche nette finale ─────────────────────────────────────────


class FlecheFin(VerificationELS):
    """Flèche nette finale combinée — EC5 §7.2(2) + MD Bat (Wnet,fin ≤ L/200).

    Wnet,fin = Wfin − Wc ≤ L / limite_fleche_fin   (flèche combinée après contre-flèche)

    Wfin = w_G×(1+k_def) + w_Q  (ψ_2=0 pour neige catégorie H)
    Limite MD Bat : L/200 (pannes), L/150 (chevrons).
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFin"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) eq.(7.3) — flèche nette Wnet,fin combinée"

    def calculer(self, espace) -> ResultatVerification:
        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_fin

        w_fin_y, w_fin_z, w_fin_comb, L_ref = _calculer_w_fin_composantes(espace, L_m)

        # Contre-flèche soustraite de la composante combinée uniquement
        w_net: np.ndarray = w_fin_comb
        if espace.contre_fleche_mm > 0.0:
            w_net = np.maximum(w_fin_comb - espace.contre_fleche_mm, 0.0)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_net / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_net, unite_intermediaire="mm",
        )


class FlecheFinY(VerificationELS):
    """Flèche nette finale axe fort — EC5 §7.2(2) (Wnet,fin,y ≤ L/200).

    Wnet,fin,y = Wfin,y − Wc   (composante axe fort après contre-flèche)

    Toujours active.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFin_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) — flèche nette Wnet,fin,y axe fort"

    def calculer(self, espace) -> ResultatVerification:
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
        taux: np.ndarray = w_net_z / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_net_z, unite_intermediaire="mm",
        )


# ── Classes ELS flèche second-œuvre ─────────────────────────────────────────


class FlecheSecondOeuvre(VerificationELS):
    """Flèche second-œuvre combinée — EC5 §7.2 (Wtot,2 ≤ L/lim).

    Wtot,2 = w_Q + k_def × (w_G + w_G2) ≤ L / limite_fleche_2   (flèche combinée)

    Active uniquement si ``limite_fleche_2`` est définie dans l'espace.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheSecondOeuvre"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche nette second-œuvre Wtot,2 combinée"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.limite_fleche_2 is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_2

        w2_y, w2_z, w2_comb, L_ref = _calculer_w2_composantes(espace, L_m)

        # Contre-flèche soustraite de la composante combinée
        w2_net: np.ndarray = w2_comb
        if espace.contre_fleche_mm > 0.0:
            w2_net = np.maximum(w2_comb - espace.contre_fleche_mm, 0.0)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w2_net / limite_mm
        active: np.ndarray = np.ones((n_L, n_C, n_M), dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w2_net, unite_intermediaire="mm",
        )


class FlecheSecondOeuvreY(VerificationELS):
    """Flèche second-œuvre axe fort — EC5 §7.2 (Wtot,2,y ≤ L/lim).

    Wtot,2,y = w_Q,y + k_def × (w_G,y + w_G2,y)   (composante axe fort)

    Active uniquement si ``limite_fleche_2`` est définie.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheSecondOeuvre_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche second-œuvre Wtot,2,y axe fort"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.limite_fleche_2 is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
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

        if espace.limite_fleche_2 is None or not espace.fleches_double:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_2

        _w2_y, w2_z, _w2_comb, L_ref = _calculer_w2_composantes(espace, L_m)

        if w2_z is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        w2_net_z: np.ndarray = w2_z
        if espace.contre_fleche_mm > 0.0:
            w2_net_z = np.maximum(w2_z - espace.contre_fleche_mm, 0.0)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w2_net_z / limite_mm
        active: np.ndarray = np.ones((n_L, n_C, n_M), dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w2_net_z, unite_intermediaire="mm",
        )
