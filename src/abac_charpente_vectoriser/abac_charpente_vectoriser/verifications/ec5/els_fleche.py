"""
verifications.ec5.els_fleche
==============================
Vérifications ELS de flèche — EC5 §7.2 + AN française.

Douze vérifications (4 combinées + 4 variantes axe fort + 4 variantes axe faible) :

Flèche instantanée sous charges variables seules (AN France) :
  ``FlecheInst``          : Winst(Q) <= L/lim   (flèche verticale combinée)
  ``FlecheInst_y``        : Winst,y(Q) <= L/lim  (axe fort seul)
  ``FlecheInst_z``        : Winst,z(Q) <= L/lim  (axe faible — double flexion)

Flèche finale brute avant contre-flèche (MD Bat L/125) :
  ``FlecheFinBrute``      : Wfin <= L/125  (combiné)
  ``FlecheFinBrute_y``    : Wfin,y <= L/125  (axe fort)
  ``FlecheFinBrute_z``    : Wfin,z <= L/125  (axe faible — double flexion)

Flèche nette finale après contre-flèche (MD Bat L/200) :
  ``FlecheFin``           : Wnet,fin <= L/200  (combiné)
  ``FlecheFin_y``         : Wnet,fin,y <= L/200  (axe fort)
  ``FlecheFin_z``         : Wnet,fin,z <= L/200  (axe faible — double flexion)

Flèche second-oeuvre (EC5 §7.2 L/500) :
  ``FlecheSecondOeuvre``  : Wtot,2 <= L/500  (combiné)
  ``FlecheSecondOeuvre_y``: Wtot,2,y <= L/500  (axe fort)
  ``FlecheSecondOeuvre_z``: Wtot,2,z <= L/500  (axe faible — double flexion)

Formule bi-appui chargement uniforme (EC5 §7.2) :
    w_inst = 5 x q x L^4 / (384 x E x I)

Pour les éléments à double flexion (fleches_double=True) :
  - Les composantes y (axe fort) et z (axe faible) sont calculées séparément.
  - La flèche verticale combinée :
      w_vert = w_y x cos(a) + w_z x sin(a)   si pente_rad connu
      w_vert = sqrt(w_y^2 + w_z^2)           fallback si pente_rad=None

Pour les chevrons, conversion rampant -> vertical :
    w_vert = w_rampant / cos(a)   (portée de référence = longueur_projetee_m)

Décomposition G/Q par axe :
  - Charges permanentes (G) projetées via cos/sin(a) si pente connue, via ratios
    de moment |M_y|/(|M_y|+|M_z|) sinon.
  - q_Q forcé à 0 pour les combinaisons ELU (masque els_mask) afin de n'utiliser
    que les charges caractéristiques (gamma=1.0) dans les calculs de flèche.
"""

from __future__ import annotations

import math

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELS


# ---------------------------------------------------------------------------
# Helpers internes — non exportés
# ---------------------------------------------------------------------------


def _fleche_bi_appui(
    q_kNm: np.ndarray,
    L_m: np.ndarray,
    E_MPa: np.ndarray,
    I_cm4: np.ndarray,
) -> np.ndarray:
    """Flèche bi-appui, chargement uniforme — EC5 §7.2.

    w = 5 * q * L^4 / (384 * E * I)   [mm]

    Parameters
    ----------
    q_kNm : charge en kN/m (broadcastable vers (n_L, n_C, n_M))
    L_m   : portées en m, vecteur (n_L,)
    E_MPa : module en MPa, vecteur (n_M,)
    I_cm4 : inertie en cm^4, vecteur (n_M,)

    Returns
    -------
    np.ndarray — flèche en mm, broadcast vers (n_L, n_C, n_M)
    """
    q_Nmm = q_kNm  # kN/m = N/mm (numeriquement identique)
    L_mm: np.ndarray = L_m[:, np.newaxis, np.newaxis] * 1000.0
    E_Nmm2: np.ndarray = E_MPa[np.newaxis, np.newaxis, :]
    I_mm4: np.ndarray = I_cm4[np.newaxis, np.newaxis, :] * 1.0e4
    return 5.0 * q_Nmm * L_mm**4 / (384.0 * E_Nmm2 * I_mm4)


def _ratios_moment_yz(
    M_y: np.ndarray,
    M_z: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Ratios de répartition axe fort / axe faible depuis les moments fléchissants.

    r_y = |M_y| / (|M_y| + |M_z|),  r_z = 1 - r_y.
    Fallback r_y = 1.0 si M_tot ~ 0 (division par zéro).
    """
    M_tot: np.ndarray = np.abs(M_y) + np.abs(M_z)
    r_y: np.ndarray = np.where(M_tot > 1.0e-12, np.abs(M_y) / M_tot, 1.0)
    return r_y, 1.0 - r_y


def _decomposer_G_Q(
    espace,
    L_m: np.ndarray,
    total_g_for_inst: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Décompose la charge de calcul en parts permanente (G) et variable (Q) par axe.

    AN française EC5 : Winst est calculé sous charges variables seules (q_Q).
    Les combinaisons ELU (gamma=1.35) sont masquées : q_Q forcé à 0 via els_mask.

    Parameters
    ----------
    total_g_for_inst : True -> inclut G2 dans q_G (FlecheInst, q_Q = variables seules).
                       False -> q_G = G1 seul (FlecheFin, FlecheSecondOeuvre).

    Returns
    -------
    (q_G_y, q_Q_y, q_G_z | None, q_Q_z | None)  en kN/m.
    q_G_z, q_Q_z sont None si simple flexion.
    """
    L_L11: np.ndarray = L_m[:, np.newaxis, np.newaxis]
    els_1C1: np.ndarray = espace.els_mask[np.newaxis, :, np.newaxis]

    q_G2_sc: float = float(espace.q_G2_kNm)
    q_G_eff: np.ndarray = (
        espace.q_G_kNm + q_G2_sc if total_g_for_inst else espace.q_G_kNm
    )

    if espace.fleches_double and espace.M_y_kNm is not None and espace.M_z_kNm is not None:
        r_y, r_z = _ratios_moment_yz(espace.M_y_kNm, espace.M_z_kNm)

        q_d_y: np.ndarray = espace.M_y_kNm * 8.0 / L_L11**2
        q_d_z: np.ndarray = espace.M_z_kNm * 8.0 / L_L11**2

        if espace.pente_rad is not None:
            ca: float = math.cos(espace.pente_rad)
            sa: float = math.sin(espace.pente_rad)
            q_G_y: np.ndarray = q_G_eff * ca
            q_G_z: np.ndarray = q_G_eff * sa
        else:
            q_G_y = q_G_eff * r_y
            q_G_z = q_G_eff * r_z

        q_Q_y: np.ndarray = np.maximum(np.where(els_1C1, q_d_y - q_G_y, 0.0), 0.0)
        q_Q_z: np.ndarray = np.maximum(np.where(els_1C1, q_d_z - q_G_z, 0.0), 0.0)
        return q_G_y, q_Q_y, q_G_z, q_Q_z

    else:
        q_d_y = (
            espace.M_y_kNm * 8.0 / L_L11**2
            if espace.M_y_kNm is not None
            else espace.q_d_kNm
        )
        q_G_y = q_G_eff
        q_Q_y = np.maximum(np.where(els_1C1, q_d_y - q_G_y, 0.0), 0.0)
        return q_G_y, q_Q_y, None, None


def _composante_verticale(
    w_y: np.ndarray,
    w_z: np.ndarray | None,
    pente_rad: float | None,
) -> np.ndarray:
    """Flèche verticale resultante depuis les composantes axiales.

    Pour une panne déversée à pente alpha :
      w_vert = w_y * cos(a) + w_z * sin(a)

    Fallback vectoriel (pas de pente) :
      w_vert = sqrt(w_y^2 + w_z^2)

    Simple flexion (w_z = None) :
      w_vert = w_y
    """
    if w_z is not None and pente_rad is not None:
        return w_y * math.cos(pente_rad) + w_z * math.sin(pente_rad)
    if w_z is not None:
        return np.sqrt(w_y**2 + w_z**2)
    return w_y


def _w_inst_composantes(
    espace,
    L_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    """Flèche instantanée sous charges variables seules (AN France).

    Returns (w_y_mm, w_z_mm|None, w_comb_mm, L_ref_m)
    """
    E: np.ndarray = espace.E_mean_MPa_arr
    I_y: np.ndarray = espace.I_y_cm4_arr
    q_G_y, q_Q_y, q_G_z, q_Q_z = _decomposer_G_Q(espace, L_m, total_g_for_inst=True)

    w_y: np.ndarray = _fleche_bi_appui(q_Q_y, L_m, E, I_y)
    w_z: np.ndarray | None = None
    if q_Q_z is not None:
        w_z = _fleche_bi_appui(q_Q_z, L_m, E, espace.I_z_cm4_arr)
    w_comb: np.ndarray = _composante_verticale(w_y, w_z, espace.pente_rad)

    if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
        w_comb = w_comb / math.cos(espace.pente_rad)
        return w_y, w_z, w_comb, espace.longueur_projetee_m
    return w_y, w_z, w_comb, L_m


def _w_fin_composantes(
    espace,
    L_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    """Flèche finale Wfin = w_G*(1+k_def) + w_Q — composantes par axe.

    Returns (w_fin_y_mm, w_fin_z_mm|None, w_fin_comb_mm, L_ref_m)
    """
    E: np.ndarray = espace.E_mean_MPa_arr
    I_y: np.ndarray = espace.I_y_cm4_arr
    k11M: np.ndarray = espace.k_def_arr[np.newaxis, np.newaxis, :]
    q_G_y, q_Q_y, q_G_z, q_Q_z = _decomposer_G_Q(espace, L_m)

    w_G_y: np.ndarray = _fleche_bi_appui(q_G_y, L_m, E, I_y)
    w_Q_y: np.ndarray = _fleche_bi_appui(q_Q_y, L_m, E, I_y)
    w_fin_y: np.ndarray = w_G_y * (1.0 + k11M) + w_Q_y

    w_fin_z: np.ndarray | None = None
    if q_Q_z is not None:
        I_z: np.ndarray = espace.I_z_cm4_arr
        w_G_z: np.ndarray = _fleche_bi_appui(q_G_z, L_m, E, I_z)  # type: ignore[arg-type]
        w_Q_z: np.ndarray = _fleche_bi_appui(q_Q_z, L_m, E, I_z)
        w_fin_z = w_G_z * (1.0 + k11M) + w_Q_z

    w_fin_comb: np.ndarray = _composante_verticale(w_fin_y, w_fin_z, espace.pente_rad)
    if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
        w_fin_comb = w_fin_comb / math.cos(espace.pente_rad)
        return w_fin_y, w_fin_z, w_fin_comb, espace.longueur_projetee_m
    return w_fin_y, w_fin_z, w_fin_comb, L_m


def _w2_composantes(
    espace,
    L_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    """Flèche second-oeuvre Wtot,2 = w_Q + k_def*(w_G + w_G2) — composantes par axe.

    Returns (w2_y_mm, w2_z_mm|None, w2_comb_mm, L_ref_m)
    """
    E: np.ndarray = espace.E_mean_MPa_arr
    I_y: np.ndarray = espace.I_y_cm4_arr
    k11M: np.ndarray = espace.k_def_arr[np.newaxis, np.newaxis, :]
    L_L11: np.ndarray = L_m[:, np.newaxis, np.newaxis]
    q_G_y, q_Q_y, q_G_z, q_Q_z = _decomposer_G_Q(espace, L_m, total_g_for_inst=False)
    g2: float = float(espace.q_G2_kNm)

    w2_z: np.ndarray | None = None

    if espace.fleches_double and espace.M_y_kNm is not None and espace.M_z_kNm is not None:
        I_z: np.ndarray = espace.I_z_cm4_arr
        if espace.pente_rad is not None:
            g2_y: float = g2 * math.cos(espace.pente_rad)
            g2_z: float = g2 * math.sin(espace.pente_rad)
        else:
            r_y, r_z = _ratios_moment_yz(espace.M_y_kNm, espace.M_z_kNm)
            g2_y = g2 * r_y  # type: ignore[assignment]
            g2_z = g2 * r_z  # type: ignore[assignment]

        w_G_y: np.ndarray = _fleche_bi_appui(q_G_y, L_m, E, I_y)
        w_G_z: np.ndarray = _fleche_bi_appui(q_G_z, L_m, E, I_z)  # type: ignore[arg-type]
        w_G2_y: np.ndarray = _fleche_bi_appui(g2_y, L_m, E, I_y)  # type: ignore[arg-type]
        w_G2_z: np.ndarray = _fleche_bi_appui(g2_z, L_m, E, I_z)  # type: ignore[arg-type]
        w_Q_y: np.ndarray = _fleche_bi_appui(q_Q_y, L_m, E, I_y)
        w_Q_z: np.ndarray = _fleche_bi_appui(q_Q_z, L_m, E, I_z)  # type: ignore[arg-type]

        w2_y: np.ndarray = w_Q_y + k11M * (w_G_y + w_G2_y)
        w2_z = w_Q_z + k11M * (w_G_z + w_G2_z)
        w2_comb: np.ndarray = _composante_verticale(w2_y, w2_z, espace.pente_rad)
        return w2_y, w2_z, w2_comb, L_m

    else:
        w_G_s: np.ndarray = _fleche_bi_appui(espace.q_G_kNm, L_m, E, I_y)
        w_G2_s: np.ndarray = (
            5.0 * g2 * (L_L11 * 1000.0)**4
            / (384.0 * E[np.newaxis, np.newaxis, :] * I_y[np.newaxis, np.newaxis, :] * 1.0e4)
        )
        w_Q_s: np.ndarray = _fleche_bi_appui(q_Q_y, L_m, E, I_y)
        w2_y = w_Q_s + k11M * (w_G_s + w_G2_s)
        w2_comb = w2_y

        if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
            w2_comb = w2_comb / math.cos(espace.pente_rad)
            return w2_y, None, w2_comb, espace.longueur_projetee_m
        return w2_y, None, w2_comb, L_m


# ---------------------------------------------------------------------------
# Classes ELS — flèche instantanée
# ---------------------------------------------------------------------------


class FlecheInst(VerificationELS):
    """Winst(Q) <= L / limite_inst  (flèche combinée verticale, AN France)."""

    @property
    def id_verification(self) -> str:
        return "w_inst"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 + AN — flèche instantanée Winst(Q) combinée"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
        if espace.limite_fleche_inst is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim: float = espace.limite_fleche_inst
        _wy, _wz, w_comb, L_ref = _w_inst_composantes(espace, espace.longueurs_m)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_comb / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_comb, unite_intermediaire="mm",
        )


class FlecheInstY(VerificationELS):
    """Winst,y(Q) <= L / limite_inst  (composante axe fort)."""

    @property
    def id_verification(self) -> str:
        return "w_inst_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 + AN — flèche instantanée Winst,y(Q) axe fort"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
        if espace.limite_fleche_inst is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim: float = espace.limite_fleche_inst
        w_y, _wz, _wcomb, L_ref = _w_inst_composantes(espace, espace.longueurs_m)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_y / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_y, unite_intermediaire="mm",
        )


class FlecheInstZ(VerificationELS):
    """Winst,z(Q) <= L / limite_inst  (composante axe faible, double flexion)."""

    @property
    def id_verification(self) -> str:
        return "w_inst_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 + AN — flèche instantanée Winst,z(Q) axe faible"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
        if espace.limite_fleche_inst is None or not espace.fleches_double:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim: float = espace.limite_fleche_inst
        _wy, w_z, _wcomb, L_ref = _w_inst_composantes(espace, espace.longueurs_m)
        if w_z is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_z / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_z, unite_intermediaire="mm",
        )


# ---------------------------------------------------------------------------
# Classes ELS — flèche finale brute (avant contre-flèche)
# ---------------------------------------------------------------------------


class FlecheFinBrute(VerificationELS):
    """Wfin <= L/125  (flèche brute combinée, MD Bat)."""

    @property
    def id_verification(self) -> str:
        return "w_fin_brut"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) eq.(7.3) — flèche finale brute Wfin <= L/125"

    def calculer(self, espace) -> ResultatVerification:
        lim: float = espace.limite_fleche_fin_brut
        _wfy, _wfz, w_fin_comb, L_ref = _w_fin_composantes(espace, espace.longueurs_m)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin_comb / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_fin_comb, unite_intermediaire="mm",
        )


class FlecheFinBruteY(VerificationELS):
    """Wfin,y <= L/125  (composante axe fort)."""

    @property
    def id_verification(self) -> str:
        return "w_fin_brut_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) — flèche finale brute Wfin,y <= L/125 axe fort"

    def calculer(self, espace) -> ResultatVerification:
        lim: float = espace.limite_fleche_fin_brut
        w_fin_y, _wfz, _wcomb, L_ref = _w_fin_composantes(espace, espace.longueurs_m)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin_y / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_fin_y, unite_intermediaire="mm",
        )


class FlecheFinBruteZ(VerificationELS):
    """Wfin,z <= L/125  (composante axe faible, double flexion)."""

    @property
    def id_verification(self) -> str:
        return "w_fin_brut_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) — flèche finale brute Wfin,z <= L/125 axe faible"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
        if not espace.fleches_double:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim: float = espace.limite_fleche_fin_brut
        _wfy, w_fin_z, _wcomb, L_ref = _w_fin_composantes(espace, espace.longueurs_m)
        if w_fin_z is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin_z / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_fin_z, unite_intermediaire="mm",
        )


# ---------------------------------------------------------------------------
# Classes ELS — flèche nette finale (après contre-flèche)
# ---------------------------------------------------------------------------


class FlecheFin(VerificationELS):
    """Wnet,fin <= L/200  (flèche nette combinée, après contre-flèche)."""

    @property
    def id_verification(self) -> str:
        return "w_net_fin"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) eq.(7.3) — flèche nette Wnet,fin combinée"

    def calculer(self, espace) -> ResultatVerification:
        lim: float = espace.limite_fleche_fin
        _wfy, _wfz, w_fin_comb, L_ref = _w_fin_composantes(espace, espace.longueurs_m)
        w_net: np.ndarray = w_fin_comb
        if espace.contre_fleche_mm > 0.0:
            w_net = np.maximum(w_fin_comb - espace.contre_fleche_mm, 0.0)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_net / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_net, unite_intermediaire="mm",
        )


class FlecheFinY(VerificationELS):
    """Wnet,fin,y <= L/200  (composante axe fort, après contre-flèche)."""

    @property
    def id_verification(self) -> str:
        return "w_net_fin_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) — flèche nette Wnet,fin,y axe fort"

    def calculer(self, espace) -> ResultatVerification:
        lim: float = espace.limite_fleche_fin
        w_fin_y, _wfz, _wcomb, L_ref = _w_fin_composantes(espace, espace.longueurs_m)
        w_net_y: np.ndarray = w_fin_y
        if espace.contre_fleche_mm > 0.0:
            w_net_y = np.maximum(w_fin_y - espace.contre_fleche_mm, 0.0)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_net_y / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_net_y, unite_intermediaire="mm",
        )


class FlecheFinZ(VerificationELS):
    """Wnet,fin,z <= L/200  (composante axe faible, double flexion)."""

    @property
    def id_verification(self) -> str:
        return "w_net_fin_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) — flèche nette Wnet,fin,z axe faible"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
        if not espace.fleches_double:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim: float = espace.limite_fleche_fin
        _wfy, w_fin_z, _wcomb, L_ref = _w_fin_composantes(espace, espace.longueurs_m)
        if w_fin_z is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        w_net_z: np.ndarray = w_fin_z
        if espace.contre_fleche_mm > 0.0:
            w_net_z = np.maximum(w_fin_z - espace.contre_fleche_mm, 0.0)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_net_z / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones_like(taux, dtype=bool),
            valeur_intermediaire=w_net_z, unite_intermediaire="mm",
        )


# ---------------------------------------------------------------------------
# Classes ELS — flèche second-oeuvre
# ---------------------------------------------------------------------------


class FlecheSecondOeuvre(VerificationELS):
    """Wtot,2 <= L/lim  (flèche second-oeuvre combinée)."""

    @property
    def id_verification(self) -> str:
        return "w_2"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche nette second-oeuvre Wtot,2 combinée"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
        if espace.limite_fleche_2 is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim: float = espace.limite_fleche_2
        _w2y, _w2z, w2_comb, L_ref = _w2_composantes(espace, espace.longueurs_m)
        w2_net: np.ndarray = w2_comb
        if espace.contre_fleche_mm > 0.0:
            w2_net = np.maximum(w2_comb - espace.contre_fleche_mm, 0.0)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w2_net / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones((n_L, n_C, n_M), dtype=bool),
            valeur_intermediaire=w2_net, unite_intermediaire="mm",
        )


class FlecheSecondOeuvreY(VerificationELS):
    """Wtot,2,y <= L/lim  (composante axe fort)."""

    @property
    def id_verification(self) -> str:
        return "w_2_y"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche second-oeuvre Wtot,2,y axe fort"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
        if espace.limite_fleche_2 is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim: float = espace.limite_fleche_2
        w2_y, _w2z, _wcomb, L_ref = _w2_composantes(espace, espace.longueurs_m)
        w2_net_y: np.ndarray = w2_y
        if espace.contre_fleche_mm > 0.0:
            w2_net_y = np.maximum(w2_y - espace.contre_fleche_mm, 0.0)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w2_net_y / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones((n_L, n_C, n_M), dtype=bool),
            valeur_intermediaire=w2_net_y, unite_intermediaire="mm",
        )


class FlecheSecondOeuvreZ(VerificationELS):
    """Wtot,2,z <= L/lim  (composante axe faible, double flexion)."""

    @property
    def id_verification(self) -> str:
        return "w_2_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche second-oeuvre Wtot,2,z axe faible"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)
        if espace.limite_fleche_2 is None or not espace.fleches_double:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        lim: float = espace.limite_fleche_2
        _w2y, w2_z, _wcomb, L_ref = _w2_composantes(espace, espace.longueurs_m)
        if w2_z is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)
        w2_net_z: np.ndarray = w2_z
        if espace.contre_fleche_mm > 0.0:
            w2_net_z = np.maximum(w2_z - espace.contre_fleche_mm, 0.0)
        lim_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w2_net_z / lim_mm
        return ResultatVerification(
            self.id_verification, taux, np.ones((n_L, n_C, n_M), dtype=bool),
            valeur_intermediaire=w2_net_z, unite_intermediaire="mm",
        )
