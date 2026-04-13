"""
verifications.ec5.els_fleche
==============================
Vérifications ELS de flèche — EC5 §7.2 + AN française.

Quatre vérifications (conformes au logiciel de référence MD Bat) :
- ``FlecheInst``     : Winst(Q) ≤ L / limite_inst
  AN française : flèche instantanée sous **charges variables seules** (Q+S).
  Désactivée si ``limite_fleche_inst is None`` (ex. Chevron simple).
- ``FlecheFinBrute`` : Wfin = w_G×(1+k_def) + w_Q ≤ L / 125
  Flèche finale BRUTE avant soustraction de la contre-flèche.
  Toujours vérifiée, indépendamment de la contre-flèche.
- ``FlecheFin``      : Wnet,fin = Wfin − Wc ≤ L / 200
  Flèche nette après soustraction de la contre-flèche.
  EC5 §7.2(2) eq.(7.3) avec ψ_2=0 (neige cat. H, toitures).
- ``FlecheSecondOeuvre`` : Wtot,2 = w_Q + k_def×(w_G + w_G2) ≤ L / limite_2

Formule bi-appui chargement uniforme (EC5 §7.2) :
    w_inst = 5 × q × L⁴ / (384 × E × I)

Pour les éléments à double flexion (fleches_double=True) :
- Les composantes y et z sont calculées séparément.
- La flèche de vérification est la **composante verticale** :
    w_vert = w_y × cos(α) + w_z × sin(α)   si pente_rad est connu
    w_vert = √(w_y² + w_z²)                 fallback si pente_rad=None

Pour les chevrons, la flèche est convertie en vertical :
    w_vert = w_rampant / cos(α)   (via longueur_projetee_m / longueurs_m)
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


def _decomposer_G_Q(
    espace,
    L_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Décompose la charge de calcul en parts permanente (G) et variable (Q) par axe.

    AN française EC5 : la flèche instantanée est calculée sur les **charges variables
    seules** (Winst(Q)), contrairement à Winst = f(G+Q) de l'EN.

    Pour la double flexion (fleches_double=True), les composantes y et z sont obtenues
    depuis les moments M_y et M_z via la proportion de moment par axe.

    Parameters
    ----------
    espace:
        EspaceCombinaisonTenseur avec les champs requis.
    L_m:
        Vecteur de portées (n_L,).

    Returns
    -------
    tuple
        ``(q_G_y, q_Q_y, q_G_z, q_Q_z)`` en kN/m.
        ``q_G_z`` et ``q_Q_z`` sont None si simple flexion.
    """
    L_L11: np.ndarray = L_m[:, np.newaxis, np.newaxis]  # (n_L, 1, 1)

    if (
        espace.fleches_double
        and espace.M_y_kNm is not None
        and espace.M_z_kNm is not None
    ):
        # Ratios de moment par axe → décomposition de q_d par axe
        M_tot: np.ndarray = np.abs(espace.M_y_kNm) + np.abs(espace.M_z_kNm)
        r_y: np.ndarray = np.where(M_tot > 1e-12, np.abs(espace.M_y_kNm) / M_tot, 1.0)
        r_z: np.ndarray = 1.0 - r_y

        # Charge de calcul par axe (inverse de M = q×L²/8)
        q_d_y: np.ndarray = espace.M_y_kNm * 8.0 / (L_L11 ** 2)
        q_d_z: np.ndarray = espace.M_z_kNm * 8.0 / (L_L11 ** 2)

        # Part permanente par axe
        q_G_y: np.ndarray = espace.q_G_kNm * r_y
        q_G_z: np.ndarray = espace.q_G_kNm * r_z

        # Part variable par axe (≥ 0)
        q_Q_y: np.ndarray = np.maximum(q_d_y - q_G_y, 0.0)
        q_Q_z: np.ndarray = np.maximum(q_d_z - q_G_z, 0.0)

        return q_G_y, q_Q_y, q_G_z, q_Q_z

    else:
        # Simple flexion — axe fort uniquement
        q_d_y = (
            espace.M_y_kNm * 8.0 / (L_L11 ** 2)
            if espace.M_y_kNm is not None
            else espace.q_d_kNm
        )
        q_G_y = espace.q_G_kNm
        q_Q_y = np.maximum(q_d_y - q_G_y, 0.0)
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
        # Fallback si pente non disponible
        return np.sqrt(w_y**2 + w_z**2)
    return w_y


class FlecheInst(VerificationELS):
    """Flèche instantanée — EC5 §7.2 + AN française.

    Winst(Q) ≤ L / limite_fleche_inst

    AN française : flèche calculée sous **charges variables seules** (Q+S),
    et non sous le chargement total G+Q.
    Taux = Winst(Q) / (L / limite)
    """

    @property
    def id_verification(self) -> str:
        return "FlecheInst"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 + AN — flèche instantanée Winst(Q)"

    def calculer(self, espace) -> ResultatVerification:
        """Calcule le taux de flèche instantanée sous charges variables seules (AN française).

        Désactivée si ``limite_fleche_inst is None`` (ex. Chevron simple — vérification
        Winst,Q non requise par l'AN française pour cet usage).
        Pour la double flexion, la flèche verticale w_y×cos(α)+w_z×sin(α) est comparée
        à la limite (et non la résultante vectorielle).
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        zeros: np.ndarray = np.zeros((n_L, n_C, n_M))
        false_mask: np.ndarray = np.zeros((n_L, n_C, n_M), dtype=bool)

        if espace.limite_fleche_inst is None:
            return ResultatVerification(self.id_verification, zeros, false_mask)

        L_m: np.ndarray = espace.longueurs_m
        E: np.ndarray = espace.E_mean_MPa_arr          # (n_M,)
        I_y: np.ndarray = espace.I_y_cm4_arr           # (n_M,)
        lim: float = espace.limite_fleche_inst         # L/x

        q_G_y, q_Q_y, q_G_z, q_Q_z = _decomposer_G_Q(espace, L_m)

        # Flèche sous charges variables seules (AN française : Q seul)
        w_y: np.ndarray = _fleche_inst_bi_appui(q_Q_y, L_m, E, I_y)  # (n_L, n_C, n_M) [mm]

        if q_Q_z is not None:
            I_z: np.ndarray = espace.I_z_cm4_arr
            w_z: np.ndarray = _fleche_inst_bi_appui(q_Q_z, L_m, E, I_z)
            w_inst: np.ndarray = _composante_verticale(w_y, w_z, espace.pente_rad)
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


def _calculer_w_fin_brut(espace, L_m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Calcule Wfin brut (avant contre-flèche) et retourne (w_fin_brut, L_ref).

    Wfin = w_G×(1+k_def) + w_Q  — EC5 §7.2(2) eq.(7.3), ψ_2=0.
    Partagé par FlecheFinBrute et FlecheFin pour éviter la duplication.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(w_fin_mm, L_ref_m)`` — flèche brute en mm, portée de référence en m.
    """
    E: np.ndarray = espace.E_mean_MPa_arr
    I_y: np.ndarray = espace.I_y_cm4_arr
    k_def: np.ndarray = espace.k_def_arr
    k_def_11M: np.ndarray = k_def[np.newaxis, np.newaxis, :]

    q_G_y, q_Q_y, q_G_z, q_Q_z = _decomposer_G_Q(espace, L_m)

    w_G_y: np.ndarray = _fleche_inst_bi_appui(q_G_y, L_m, E, I_y)
    w_Q_y: np.ndarray = _fleche_inst_bi_appui(q_Q_y, L_m, E, I_y)
    w_fin_y: np.ndarray = w_G_y * (1.0 + k_def_11M) + w_Q_y

    if q_Q_z is not None:
        I_z: np.ndarray = espace.I_z_cm4_arr
        w_G_z: np.ndarray = _fleche_inst_bi_appui(q_G_z, L_m, E, I_z)
        w_Q_z: np.ndarray = _fleche_inst_bi_appui(q_Q_z, L_m, E, I_z)
        w_fin_z: np.ndarray = w_G_z * (1.0 + k_def_11M) + w_Q_z
        w_fin: np.ndarray = _composante_verticale(w_fin_y, w_fin_z, espace.pente_rad)
    else:
        w_fin = w_fin_y

    # Chevron : conversion rampant → vertical
    if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
        w_fin = w_fin / math.cos(espace.pente_rad)
        L_ref: np.ndarray = espace.longueur_projetee_m
    else:
        L_ref = L_m

    return w_fin, L_ref


class FlecheFinBrute(VerificationELS):
    """Flèche finale brute — EC5 §7.2(2) + MD Bat (Wfin ≤ L/125).

    Wfin = w_G×(1+k_def) + w_Q ≤ L / limite_fleche_fin_brut

    Vérification AVANT soustraction de la contre-flèche. Toujours active.
    Limite de référence MD Bat : L/125 pour tous les éléments de toiture.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFinBrute"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) eq.(7.3) — flèche finale brute Wfin ≤ L/125"

    def calculer(self, espace) -> ResultatVerification:
        """Calcule le taux Wfin (brut, avant contre-flèche) / (L/125)."""
        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_fin_brut

        w_fin, L_ref = _calculer_w_fin_brut(espace, L_m)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)


class FlecheFin(VerificationELS):
    """Flèche nette finale (après contre-flèche) — EC5 §7.2(2) + MD Bat (Wnet,fin ≤ L/200).

    Wnet,fin = Wfin − Wc ≤ L / limite_fleche_fin

    Wfin = w_G×(1+k_def) + w_Q  (ψ_2=0 pour neige catégorie H)
    La contre-flèche éventuelle est soustraite avant comparaison à la limite.
    Limite de référence MD Bat : L/200 (pannes), L/150 (chevrons).
    """

    @property
    def id_verification(self) -> str:
        return "FlecheFin"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2(2) eq.(7.3) — flèche nette Wnet,fin"

    def calculer(self, espace) -> ResultatVerification:
        """Calcule le taux Wnet,fin = (Wfin − Wc) / (L/limite)."""
        L_m: np.ndarray = espace.longueurs_m
        lim: float = espace.limite_fleche_fin

        w_fin, L_ref = _calculer_w_fin_brut(espace, L_m)

        # Contre-flèche : Wnet,fin = Wfin − Wc  (≥ 0)
        if espace.contre_fleche_mm > 0.0:
            w_fin = np.maximum(w_fin - espace.contre_fleche_mm, 0.0)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_fin / limite_mm
        active: np.ndarray = np.ones_like(taux, dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)


class FlecheSecondOeuvre(VerificationELS):
    """Flèche nette second-œuvre — EC5 §7.2.

    Wtot,2 = w_Q + k_def × (w_G + w_G2) ≤ L / limite_fleche_2

    Pour la double flexion, les composantes G, Q et G2 sont décomposées par axe
    via les ratios de moment, puis combinées en composante verticale.

    Active uniquement si ``config.second_oeuvre = True`` et
    ``limite_fleche_2`` est définie dans l'espace.
    """

    @property
    def id_verification(self) -> str:
        return "FlecheSecondOeuvre"

    @property
    def article_ec5(self) -> str:
        return "EC5 §7.2 — flèche nette second-œuvre Wtot,2"

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
        L_L11: np.ndarray = L_m[:, np.newaxis, np.newaxis]

        if (
            espace.fleches_double
            and espace.M_y_kNm is not None
            and espace.M_z_kNm is not None
        ):
            # ── Double flexion : décomposition par axe ─────────────────────────
            I_z: np.ndarray = espace.I_z_cm4_arr

            # Ratios de moment par axe (identiques à _decomposer_G_Q)
            M_tot: np.ndarray = np.abs(espace.M_y_kNm) + np.abs(espace.M_z_kNm)
            r_y: np.ndarray = np.where(
                M_tot > 1e-12, np.abs(espace.M_y_kNm) / M_tot, 1.0
            )
            r_z: np.ndarray = 1.0 - r_y

            # Charges de calcul par axe
            q_d_y: np.ndarray = espace.M_y_kNm * 8.0 / (L_L11 ** 2)
            q_d_z: np.ndarray = espace.M_z_kNm * 8.0 / (L_L11 ** 2)

            # Part permanente G par axe
            q_G_y: np.ndarray = espace.q_G_kNm * r_y
            q_G_z: np.ndarray = espace.q_G_kNm * r_z

            # Part permanente G2 par axe (G2 est vertical → projection géométrique cos/sin)
            # Si pente_rad est disponible (PanneDeversee) : q_G2_y = g2 × cos(α)
            # Sinon fallback sur les ratios de moment (cas sans pente connue)
            q_G2_scalar: float = float(espace.q_G2_kNm)
            if espace.pente_rad is not None:
                _cos_a: float = math.cos(espace.pente_rad)
                _sin_a: float = math.sin(espace.pente_rad)
                q_G2_y: np.ndarray = q_G2_scalar * _cos_a
                q_G2_z: np.ndarray = q_G2_scalar * _sin_a
            else:
                q_G2_y = q_G2_scalar * r_y
                q_G2_z = q_G2_scalar * r_z

            # Part variable par axe
            q_Q_y: np.ndarray = np.maximum(q_d_y - q_G_y, 0.0)
            q_Q_z: np.ndarray = np.maximum(q_d_z - q_G_z, 0.0)

            # Flèches par axe
            w_G_y: np.ndarray = _fleche_inst_bi_appui(q_G_y, L_m, E, I_y)
            w_G_z: np.ndarray = _fleche_inst_bi_appui(q_G_z, L_m, E, I_z)
            w_G2_y: np.ndarray = _fleche_inst_bi_appui(q_G2_y, L_m, E, I_y)
            w_G2_z: np.ndarray = _fleche_inst_bi_appui(q_G2_z, L_m, E, I_z)
            w_Q_y: np.ndarray = _fleche_inst_bi_appui(q_Q_y, L_m, E, I_y)
            w_Q_z: np.ndarray = _fleche_inst_bi_appui(q_Q_z, L_m, E, I_z)

            # Wtot,2 par axe
            w_2_y: np.ndarray = w_Q_y + k_def_11M * (w_G_y + w_G2_y)
            w_2_z: np.ndarray = w_Q_z + k_def_11M * (w_G_z + w_G2_z)

            # Composante verticale
            w_2: np.ndarray = _composante_verticale(w_2_y, w_2_z, espace.pente_rad)
            L_ref: np.ndarray = L_m   # longueur_projetee_m=None pour PanneDeversee

        else:
            # ── Simple flexion — axe fort uniquement ───────────────────────────
            q_G_LCM: np.ndarray = espace.q_G_kNm
            w_G_s: np.ndarray = _fleche_inst_bi_appui(q_G_LCM, L_m, E, I_y)

            # G2 : scalaire → calcul inline
            q_G2_Nmm: float = float(espace.q_G2_kNm)   # kN/m → N/mm
            w_G2_s: np.ndarray = 5.0 * q_G2_Nmm * (L_L11 * 1000.0)**4 / (
                384.0 * E[np.newaxis, np.newaxis, :] * I_y[np.newaxis, np.newaxis, :] * 1e4
            )

            # Part variable = total - permanente
            w_total: np.ndarray = _fleche_inst_bi_appui(espace.q_d_kNm, L_m, E, I_y)
            w_Q_s: np.ndarray = np.maximum(w_total - w_G_s, 0.0)

            w_2 = w_Q_s + k_def_11M * (w_G_s + w_G2_s)

            # Conversion rampant → vertical pour Chevron
            if espace.longueur_projetee_m is not None and espace.pente_rad is not None:
                w_2 = w_2 / math.cos(espace.pente_rad)
                L_ref = espace.longueur_projetee_m
            else:
                L_ref = L_m

        # Contre-flèche (Wtot,2 = w_2 - w_c, ≥ 0)
        if espace.contre_fleche_mm > 0.0:
            w_2 = np.maximum(w_2 - espace.contre_fleche_mm, 0.0)

        limite_mm: np.ndarray = (L_ref * 1000.0 / lim)[:, np.newaxis, np.newaxis]
        taux: np.ndarray = w_2 / limite_mm
        active: np.ndarray = np.ones((n_L, n_C, n_M), dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)
