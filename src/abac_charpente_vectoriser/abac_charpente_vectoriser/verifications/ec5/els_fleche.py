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
    q_Nmm = q_kNm * 1000.0 / 1000.0                                # kN/m → N/mm
    L_mm: np.ndarray = L_m[:, np.newaxis, np.newaxis] * 1000.0     # m → mm, (n_L, 1, 1)
    E_Nmm2: np.ndarray = E_MPa[np.newaxis, np.newaxis, :]           # MPa = N/mm², (1, 1, n_M)
    I_mm4: np.ndarray = I_cm4[np.newaxis, np.newaxis, :] * 1e4     # cm⁴ → mm⁴, (1, 1, n_M)
    return 5.0 * q_Nmm * L_mm**4 / (384.0 * E_Nmm2 * I_mm4)       # [mm]


def _ratios_moment_yz(
    M_y: np.ndarray,
    M_z: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Ratios de répartition de la charge par axe depuis les moments fléchissants.

    r_y = |M_y| / (|M_y| + |M_z|),  r_z = 1 − r_y.
    Fallback r_y = 1.0 si M_tot ≈ 0 (protection division par zéro).

    Parameters
    ----------
    M_y:
        Moment axe fort ``(n_L, n_C, n_M)`` en kN·m.
    M_z:
        Moment axe faible ``(n_L, n_C, n_M)`` en kN·m.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(r_y, r_z)`` de même forme que les entrées.
    """
    M_tot: np.ndarray = np.abs(M_y) + np.abs(M_z)
    r_y: np.ndarray = np.where(M_tot > 1e-12, np.abs(M_y) / M_tot, 1.0)
    return r_y, 1.0 - r_y


def _decomposer_G_Q(
    espace,
    L_m: np.ndarray,
    total_g_for_inst: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Décompose la charge de calcul en parts permanente (G) et variable (Q) par axe.

    AN française EC5 : la flèche instantanée est calculée sur les **charges variables
    seules** (Winst(Q)), contrairement à Winst = f(G+Q) de l'EN.

    Seules les combinaisons ELS (γ=1.0) contribuent à q_Q — les combinaisons ELU
    (γ=1.35) sont masquées : leur q_Q est forcé à 0. Cela garantit que les vérifications
    de flèche utilisent les charges caractéristiques (ELS), pas les charges majorées.

    Parameters
    ----------
    espace:
        EspaceCombinaisonTenseur avec les champs requis.
    L_m:
        Vecteur de portées (n_L,).
    total_g_for_inst:
        Si True, inclut G2 dans la charge permanente de référence → q_Q = variables seules.
        Utiliser True pour FlecheInst (Winst,Q = AN France).
        Si False (défaut), q_G = G1 seul → q_Q = G2 + variables (pour FlecheFin, FlecheSecondOeuvre).

    Returns
    -------
    tuple
        ``(q_G_y, q_Q_y, q_G_z, q_Q_z)`` en kN/m.
        ``q_G_z`` et ``q_Q_z`` sont None si simple flexion.
    """
    L_L11: np.ndarray = L_m[:, np.newaxis, np.newaxis]  # (n_L, 1, 1)

    # Masque ELS : seules les combinaisons ELS alimentent q_Q
    els_1C1: np.ndarray = espace.els_mask[np.newaxis, :, np.newaxis]  # (1, n_C, 1)

    # Charge permanente effective : G1 seul ou G_total selon le type de vérification
    q_G2_scalar: float = float(espace.q_G2_kNm)
    if total_g_for_inst:
        # FlecheInst : q_G = g_pp + G1 + G2 = G_total → q_Q = variables seules
        q_G_eff: np.ndarray = espace.q_G_kNm + q_G2_scalar
    else:
        # FlecheFin / FlecheSecondOeuvre : q_G = g_pp + G1 → q_Q = G2 + variables
        q_G_eff = espace.q_G_kNm

    if (
        espace.fleches_double
        and espace.M_y_kNm is not None
        and espace.M_z_kNm is not None
    ):
        # Ratios de moment par axe → décomposition de q_d par axe
        r_y: np.ndarray
        r_z: np.ndarray
        r_y, r_z = _ratios_moment_yz(espace.M_y_kNm, espace.M_z_kNm)

        # Charge de calcul par axe (inverse de M = q×L²/8)
        q_d_y: np.ndarray = espace.M_y_kNm * 8.0 / (L_L11 ** 2)
        q_d_z: np.ndarray = espace.M_z_kNm * 8.0 / (L_L11 ** 2)

        # Part permanente par axe — projection géométrique si pente connue, ratio de moment sinon
        if espace.pente_rad is not None:
            _cos_a: float = math.cos(espace.pente_rad)
            _sin_a: float = math.sin(espace.pente_rad)
            q_G_y: np.ndarray = q_G_eff * _cos_a
            q_G_z: np.ndarray = q_G_eff * _sin_a
        else:
            q_G_y = q_G_eff * r_y
            q_G_z = q_G_eff * r_z

        # Part variable par axe — forcée à 0 pour les combinaisons ELU
        q_Q_y: np.ndarray = np.maximum(np.where(els_1C1, q_d_y - q_G_y, 0.0), 0.0)
        q_Q_z: np.ndarray = np.maximum(np.where(els_1C1, q_d_z - q_G_z, 0.0), 0.0)

        return q_G_y, q_Q_y, q_G_z, q_Q_z

    else:
        # Simple flexion — axe fort uniquement
        q_d_y = (
            espace.M_y_kNm * 8.0 / (L_L11 ** 2)
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
    """Composante verticale de la flèche résultante.

    Pour une section perpendiculaire au rampant (panne déversée) à pente α :
    - Axe fort y ⊥ au rampant → déflexion w_y contribue : ``w_y × cos(α)``
    - Axe faible z le long du rampant → déflexion w_z contribue : ``w_z × sin(α)``
    - Composante verticale totale : ``w_vert = w_y×cos(α) + w_z×sin(α)``

    Sans pente connue, la résultante vectorielle est retournée comme fallback.

    Parameters
    ----------
    w_y:
        Flèche selon l'axe fort (n_L, n_C, n_M) [mm].
    w_z:
        Flèche selon l'axe faible (n_L, n_C, n_M) [mm] — None si simple flexion.
    pente_rad:
        Pente en radians — None si inconnue.

    Returns
    -------
    np.ndarray
        Flèche verticale (ou résultante) en mm (n_L, n_C, n_M).
    """
    if w_z is not None and pente_rad is not None:
        return w_y * math.cos(pente_rad) + w_z * math.sin(pente_rad)
    elif w_z is not None:
        return np.sqrt(w_y**2 + w_z**2)
    return w_y


def _calculer_w_inst_composantes(
    espace,
    L_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    """Flèche instantanée sous charges variables seules (AN France) — composantes par axe.

    Calcule Winst,y, Winst,z (si double flexion) et la flèche combinée/verticale.

    Parameters
    ----------
    espace:
        EspaceCombinaisonTenseur.
    L_m:
        Vecteur de portées (n_L,) en mètres.

    Returns
    -------
    tuple
        ``(w_y_mm, w_z_mm | None, w_comb_mm, L_ref_m)``
        - w_y_mm : flèche axe fort en mm ``(n_L, n_C, n_M)``
        - w_z_mm : flèche axe faible en mm ``(n_L, n_C, n_M)`` — None si simple flexion
        - w_comb_mm : flèche verticale combinée en mm ``(n_L, n_C, n_M)``
        - L_ref_m : portée de référence (projetée pour chevron) ``(n_L,)``
    """
    E: np.ndarray = espace.E_mean_MPa_arr
    I_y: np.ndarray = espace.I_y_cm4_arr

    q_G_y, q_Q_y, q_G_z, q_Q_z = _decomposer_G_Q(espace, L_m, total_g_for_inst=True)

    w_y: np.ndarray = _fleche_inst_bi_appui(q_Q_y, L_m, E, I_y)   # (n_L, n_C, n_M) [mm]

    w_z: np.ndarray | None = None
    if q_Q_z is not None:
        I_z: np.ndarray = espace.I_z_cm4_arr
        w_z = _fleche_inst_bi_appui(q_Q_z, L_m, E, I_z)
        w_comb: np.ndarray = _composante_verticale(w_y, w_z, espace.pente_rad)
    else:
        w_comb = w_y

    # Conversion rampant → vertical pour Chevron
    if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
        w_comb = w_comb / math.cos(espace.pente_rad)
        L_ref: np.ndarray = espace.longueur_projetee_m
    else:
        L_ref = L_m

    return w_y, w_z, w_comb, L_ref


def _calculer_w_fin_composantes(
    espace,
    L_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    """Flèche finale Wfin = w_G×(1+k_def) + w_Q — composantes par axe.

    EC5 §7.2(2) eq.(7.3) avec ψ_2=0 (neige catégorie H, toitures).

    Parameters
    ----------
    espace:
        EspaceCombinaisonTenseur.
    L_m:
        Vecteur de portées (n_L,) en mètres.

    Returns
    -------
    tuple
        ``(w_fin_y_mm, w_fin_z_mm | None, w_fin_comb_mm, L_ref_m)``
    """
    E: np.ndarray = espace.E_mean_MPa_arr
    I_y: np.ndarray = espace.I_y_cm4_arr
    k_def_11M: np.ndarray = espace.k_def_arr[np.newaxis, np.newaxis, :]

    q_G_y, q_Q_y, q_G_z, q_Q_z = _decomposer_G_Q(espace, L_m)

    w_G_y: np.ndarray = _fleche_inst_bi_appui(q_G_y, L_m, E, I_y)
    w_Q_y: np.ndarray = _fleche_inst_bi_appui(q_Q_y, L_m, E, I_y)
    w_fin_y: np.ndarray = w_G_y * (1.0 + k_def_11M) + w_Q_y

    w_fin_z: np.ndarray | None = None
    if q_Q_z is not None:
        I_z: np.ndarray = espace.I_z_cm4_arr
        w_G_z: np.ndarray = _fleche_inst_bi_appui(q_G_z, L_m, E, I_z)
        w_Q_z: np.ndarray = _fleche_inst_bi_appui(q_Q_z, L_m, E, I_z)
        w_fin_z = w_G_z * (1.0 + k_def_11M) + w_Q_z
        w_fin_comb: np.ndarray = _composante_verticale(w_fin_y, w_fin_z, espace.pente_rad)
    else:
        w_fin_comb = w_fin_y

    # Conversion rampant → vertical pour Chevron
    if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
        w_fin_comb = w_fin_comb / math.cos(espace.pente_rad)
        L_ref: np.ndarray = espace.longueur_projetee_m
    else:
        L_ref = L_m

    return w_fin_y, w_fin_z, w_fin_comb, L_ref


def _calculer_w2_composantes(
    espace,
    L_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    """Flèche second-œuvre Wtot,2 = w_Q + k_def×(w_G + w_G2) — composantes par axe.

    Parameters
    ----------
    espace:
        EspaceCombinaisonTenseur.
    L_m:
        Vecteur de portées (n_L,) en mètres.

    Returns
    -------
    tuple
        ``(w2_y_mm, w2_z_mm | None, w2_comb_mm, L_ref_m)``
    """
    E: np.ndarray = espace.E_mean_MPa_arr
    I_y: np.ndarray = espace.I_y_cm4_arr
    k_def_11M: np.ndarray = espace.k_def_arr[np.newaxis, np.newaxis, :]
    L_L11: np.ndarray = L_m[:, np.newaxis, np.newaxis]

    # q_G = g_pp + G1 (sans G2), q_Q = G2 + variables
    q_G_y, q_Q_y, q_G_z, q_Q_z = _decomposer_G_Q(espace, L_m, total_g_for_inst=False)
    q_G2_scalar: float = float(espace.q_G2_kNm)

    w2_z: np.ndarray | None = None

    if (
        espace.fleches_double
        and espace.M_y_kNm is not None
        and espace.M_z_kNm is not None
    ):
        # ── Double flexion : décomposition par axe ─────────────────────────────
        I_z: np.ndarray = espace.I_z_cm4_arr

        # G2 par axe : projection géométrique si pente disponible, ratios sinon
        if espace.pente_rad is not None:
            _cos_a: float = math.cos(espace.pente_rad)
            _sin_a: float = math.sin(espace.pente_rad)
            q_G2_y: float = q_G2_scalar * _cos_a
            q_G2_z: float = q_G2_scalar * _sin_a
        else:
            r_y, r_z = _ratios_moment_yz(espace.M_y_kNm, espace.M_z_kNm)
            q_G2_y = q_G2_scalar * r_y   # type: ignore[assignment]
            q_G2_z = q_G2_scalar * r_z   # type: ignore[assignment]

        w_G_y: np.ndarray = _fleche_inst_bi_appui(q_G_y, L_m, E, I_y)
        w_G_z: np.ndarray = _fleche_inst_bi_appui(q_G_z, L_m, E, I_z)   # type: ignore[arg-type]
        w_G2_y: np.ndarray = _fleche_inst_bi_appui(q_G2_y, L_m, E, I_y)   # type: ignore[arg-type]
        w_G2_z: np.ndarray = _fleche_inst_bi_appui(q_G2_z, L_m, E, I_z)   # type: ignore[arg-type]
        w_Q_y: np.ndarray = _fleche_inst_bi_appui(q_Q_y, L_m, E, I_y)
        w_Q_z: np.ndarray = _fleche_inst_bi_appui(q_Q_z, L_m, E, I_z)   # type: ignore[arg-type]

        w2_y: np.ndarray = w_Q_y + k_def_11M * (w_G_y + w_G2_y)
        w2_z = w_Q_z + k_def_11M * (w_G_z + w_G2_z)
        w2_comb: np.ndarray = _composante_verticale(w2_y, w2_z, espace.pente_rad)
        L_ref: np.ndarray = L_m   # PanneDeversee : pas de longueur_projetee_m

    else:
        # ── Simple flexion — axe fort uniquement ──────────────────────────────
        q_G_LCM: np.ndarray = espace.q_G_kNm
        w_G_s: np.ndarray = _fleche_inst_bi_appui(q_G_LCM, L_m, E, I_y)

        # G2 scalar : calcul inline sans créer un tableau intermédiaire
        w_G2_s: np.ndarray = 5.0 * q_G2_scalar * (L_L11 * 1000.0) ** 4 / (
            384.0 * E[np.newaxis, np.newaxis, :] * I_y[np.newaxis, np.newaxis, :] * 1e4
        )

        w_Q_s: np.ndarray = _fleche_inst_bi_appui(q_Q_y, L_m, E, I_y)

        w2_y = w_Q_s + k_def_11M * (w_G_s + w_G2_s)
        w2_comb = w2_y

        # Conversion rampant → vertical pour Chevron
        if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
            w2_comb = w2_comb / math.cos(espace.pente_rad)
            L_ref = espace.longueur_projetee_m
        else:
            L_ref = L_m

    return w2_y, w2_z, w2_comb, L_ref


# ── Classes ELS flèche instantanée ──────────────────────────────────────────


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
        lim: float = espace.limite_fleche_fin_brut

        w_fin_y, _w_fin_z, _w_fin_comb, L_ref = _calculer_w_fin_composantes(espace, L_m)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin_y / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_fin_y, unite_intermediaire="mm",
        )


class FlecheFinBruteZ(VerificationELS):
    """Flèche finale brute axe faible — EC5 §7.2(2) (Wfin,z ≤ L/125).

    Wfin,z = w_G,z×(1+k_def) + w_Q,z   (composante axe faible seul)

    Désactivée si simple flexion.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFinBrute_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) — flèche finale brute Wfin,z ≤ L/125 axe faible"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if not espace.fleches_double:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_fin_brut

        _w_fin_y, w_fin_z, _w_fin_comb, L_ref = _calculer_w_fin_composantes(espace, L_m)

        if w_fin_z is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin_z / limite_mm
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
        lim: float = espace.limite_fleche_fin

        w_fin_y, _w_fin_z, _w_fin_comb, L_ref = _calculer_w_fin_composantes(espace, L_m)

        w_net_y: np.ndarray = w_fin_y
        if espace.contre_fleche_mm > 0.0:
            w_net_y = np.maximum(w_fin_y - espace.contre_fleche_mm, 0.0)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_net_y / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w_net_y, unite_intermediaire="mm",
        )


class FlecheFinZ(VerificationELS):
    """Flèche nette finale axe faible — EC5 §7.2(2) (Wnet,fin,z ≤ L/200).

    Wnet,fin,z = Wfin,z − Wc   (composante axe faible après contre-flèche)

    Désactivée si simple flexion.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFin_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) — flèche nette Wnet,fin,z axe faible"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if not espace.fleches_double:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_fin

        _w_fin_y, w_fin_z, _w_fin_comb, L_ref = _calculer_w_fin_composantes(espace, L_m)

        if w_fin_z is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        w_net_z: np.ndarray = w_fin_z
        if espace.contre_fleche_mm > 0.0:
            w_net_z = np.maximum(w_fin_z - espace.contre_fleche_mm, 0.0)

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

        w2_y, _w2_z, _w2_comb, L_ref = _calculer_w2_composantes(espace, L_m)

        w2_net_y: np.ndarray = w2_y
        if espace.contre_fleche_mm > 0.0:
            w2_net_y = np.maximum(w2_y - espace.contre_fleche_mm, 0.0)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w2_net_y / limite_mm
        active: np.ndarray = np.ones((n_L, n_C, n_M), dtype=bool)

        return ResultatVerification(
            self.id_verification, taux, active,
            valeur_intermediaire=w2_net_y, unite_intermediaire="mm",
        )


class FlecheSecondOeuvreZ(VerificationELS):
    """Flèche second-œuvre axe faible — EC5 §7.2 (Wtot,2,z ≤ L/lim).

    Wtot,2,z = w_Q,z + k_def × (w_G,z + w_G2,z)   (composante axe faible)

    Active uniquement si ``limite_fleche_2`` définie ET double flexion.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheSecondOeuvre_z"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche second-œuvre Wtot,2,z axe faible"

    def calculer(self, espace) -> ResultatVerification:
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

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
