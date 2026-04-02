"""Vérifications ELU EC5 (EF-012).

Calculs vectorisés sur np.ndarray.
RÈGLE NON-NÉGOCIABLE (Principe X + EF-019) : aucun branchement conditionnel sur
le nom du type de poutre dans ce module. La décomposition des charges est déléguée
à type_poutre.charges_lineaires() par polymorphisme OOP.

Notation française EC5 obligatoire (Principe IX).
Unités explicites dans les noms de variables (Principe VI).
"""
from __future__ import annotations

import math

import numpy as np

from sapeg_regen_stock.modeles import ConfigMatériau
from abac_charpente.modeles.config_calcul import ConfigCalcul
from abac_charpente.modeles.combinaison import CombinaisonEC0
from abac_charpente.ec5.types_poutre.base import TypePoutre
from abac_charpente.ec5.proprietes import get_kmod, get_gamma_m, get_famille, get_k_cr


def calculer_flexion(
    materiau: ConfigMatériau,
    M_d_kNm: np.ndarray,
    k_mod: float,
    gamma_M: float,
) -> dict[str, np.ndarray]:
    """Flexion §6.1.6 : σ_m_d = M_d / W_y ; taux = σ_m_d / f_m_d.

    Conversion : M_kNm × 1000 / W_cm3 / 10 → MPa
    (M en kNm × 1e3 Nm/kNm = 1e3 Nm = 1e6 Nmm ; W en cm3 × 1e3 mm3/cm3 = 1e3 mm3
     → σ = 1e6 / (W_cm3 × 1e3) = 1e3 / W_cm3 N/mm2 = 1e3/W_cm3 MPa) ✓
    """
    W_cm3 = materiau.W_cm3
    f_m_k_MPa = materiau.f_m_k_MPa

    f_m_d_MPa = f_m_k_MPa * k_mod / gamma_M
    sigma_m_MPa = M_d_kNm * 1e3 / W_cm3 / 10.0  # kNm → MPa

    return {
        "f_m_d_MPa": np.full_like(sigma_m_MPa, f_m_d_MPa),
        "sigma_m_MPa": sigma_m_MPa,
        "taux_flexion_ELU": sigma_m_MPa / f_m_d_MPa,
    }


def calculer_cisaillement(
    materiau: ConfigMatériau,
    V_d_kN: np.ndarray,
    k_mod: float,
    gamma_M: float,
    k_cr: float,
) -> dict[str, np.ndarray]:
    """Cisaillement §6.1.7 : τ_d = 1.5 × V_d / A_eff ; A_eff = b_eff × h.

    b_eff = k_cr × b (réduction de fissuration EC5 §6.1.7(2)).
    τ_d en MPa : V_d en kN × 1000 N/kN / A_eff_mm2.
    """
    b_mm = materiau.b_mm
    h_mm = materiau.h_mm
    f_v_k_MPa = materiau.f_v_k_MPa

    b_eff_mm = k_cr * b_mm
    A_eff_mm2 = b_eff_mm * h_mm
    f_v_d_MPa = f_v_k_MPa * k_mod / gamma_M

    tau_d_MPa = 1.5 * V_d_kN * 1000.0 / A_eff_mm2

    return {
        "f_v_d_MPa": np.full_like(tau_d_MPa, f_v_d_MPa),
        "tau_MPa": tau_d_MPa,
        "taux_cisaillement_ELU": tau_d_MPa / f_v_d_MPa,
    }


def calculer_appui(
    materiau: ConfigMatériau,
    V_d_kN: np.ndarray,
    longueur_appui_mm: float,
    k_c90: float,
    k_mod: float,
    gamma_M: float,
) -> dict[str, np.ndarray]:
    """Appui §6.1.5 : σ_c90_d = V_d / A_appui ; taux = σ_c90_d / (k_c90 × f_c90_d)."""
    b_mm = materiau.b_mm
    f_c90_k_MPa = materiau.f_c90_k_MPa

    A_appui_mm2 = b_mm * longueur_appui_mm
    f_c90_d_MPa = f_c90_k_MPa * k_mod / gamma_M

    # σ_c90_d = V_d [kN] × 1000 / A_appui [mm²] → N/mm² = MPa
    sigma_c90_MPa = V_d_kN * 1000.0 / A_appui_mm2
    taux_appui = sigma_c90_MPa / (k_c90 * f_c90_d_MPa)

    return {
        "f_c90_d_MPa": np.full_like(sigma_c90_MPa, f_c90_d_MPa),
        "sigma_c90_MPa": sigma_c90_MPa,
        "taux_appui_ELU": taux_appui,
    }


def calculer_longueur_appui_min(
    materiau: ConfigMatériau,
    V_d_kN: float,
    k_c90: float,
    taux_cible: float,
    k_mod: float,
    gamma_M: float,
) -> float:
    """Longueur d'appui minimale (mm) pour satisfaire le taux cible (EF-012).

    l_min = ⌈V_d × 1000 / (b × taux_cible × k_c90 × f_c90_d)⌉

    Toujours calculé quelle que soit l'issue de la vérification (T052).
    """
    b_mm = materiau.b_mm
    f_c90_d_MPa = materiau.f_c90_k_MPa * k_mod / gamma_M
    dénominateur = b_mm * taux_cible * k_c90 * f_c90_d_MPa
    if dénominateur <= 0:
        return 0.0
    return math.ceil(V_d_kN * 1000.0 / dénominateur)


def calculer_k_crit(
    materiau: ConfigMatériau,
    L_deversement_m: float,
) -> float:
    """Coefficient de déversement k_crit §6.3.3.

    λ_rel_m = √(f_m_k / σ_m_crit)

    σ_m_crit pour section rectangulaire — EC5 Éq. (6.32) :
        σ_m_crit = 0.78 × b² × E_0.05 / (h × L_ef)
        (unités : mm, mm, MPa → MPa ✓)

    Règles §6.3.3(3) :
        λ_rel_m ≤ 0.75 → k_crit = 1.0
        0.75 < λ_rel_m ≤ 1.4 → k_crit = 1.56 − 0.75 × λ_rel_m
        λ_rel_m > 1.4 → k_crit = 1 / λ_rel_m²
    """
    E_005_MPa = materiau.E_0_05_MPa
    b_mm = materiau.b_mm
    h_mm = materiau.h_mm
    f_m_k_MPa = materiau.f_m_k_MPa

    if L_deversement_m <= 0:
        return 1.0

    L_dev_mm = L_deversement_m * 1000.0

    # Contrainte critique de déversement (MPa) — EC5 Éq. (6.32) section rectangulaire
    # σ_m_crit [MPa] = 0.78 × b[mm]² × E_0.05[MPa] / (h[mm] × L_ef[mm])
    sigma_m_crit_MPa = 0.78 * b_mm ** 2 * E_005_MPa / (h_mm * L_dev_mm)

    if sigma_m_crit_MPa <= 0:
        return 0.0

    lambda_rel_m = math.sqrt(f_m_k_MPa / sigma_m_crit_MPa)

    if lambda_rel_m <= 0.75:
        return 1.0
    elif lambda_rel_m <= 1.4:
        return 1.56 - 0.75 * lambda_rel_m
    else:
        return 1.0 / (lambda_rel_m ** 2)


def verifier_elu(
    materiau: ConfigMatériau,
    config: ConfigCalcul,
    type_poutre: TypePoutre,
    longueurs_m: np.ndarray,
    combinaisons: list[CombinaisonEC0],
) -> list[dict]:
    """Vérifie les ELU pour toutes les combinaisons et longueurs (EF-012).

    Appelle type_poutre.charges_lineaires() par polymorphisme — OOP Principe X.
    Retourne une liste de dicts contenant toutes les valeurs intermédiaires ELU.
    """
    famille = get_famille(materiau.classe_resistance)
    classe_service = int(config.classe_service if isinstance(config.classe_service, int)
                         else config.classe_service[0])
    k_cr = get_k_cr()
    longueur_appui_mm = float(config.longueur_appui_mm if isinstance(config.longueur_appui_mm, (int, float))
                              else config.longueur_appui_mm[0])
    k_c90 = float(config.k_c90 if isinstance(config.k_c90, (int, float)) else config.k_c90[0])
    taux_cible_appui = config.taux_cible_appui

    résultats: list[dict] = []

    for combi in combinaisons:
        k_mod = get_kmod(famille, classe_service, combi.duree_charge)
        gamma_M = get_gamma_m(famille)

        # Polymorphisme OOP (Principe X) — dispatch via type_poutre.charges_lineaires()
        charges = type_poutre.charges_lineaires(config, materiau, longueurs_m, combi)

        M_d_kNm = charges["M_d_kNm"]
        V_d_kN = charges["V_d_kN"]

        # Flexion §6.1.6
        res_flex = calculer_flexion(materiau, M_d_kNm, k_mod, gamma_M)
        # Cisaillement §6.1.7
        res_cis = calculer_cisaillement(materiau, V_d_kN, k_mod, gamma_M, k_cr)
        # Appui §6.1.5
        res_app = calculer_appui(materiau, V_d_kN, longueur_appui_mm, k_c90, k_mod, gamma_M)

        # Longueur appui minimale — calculée QUELLE QUE SOIT l'issue (T052)
        n = len(longueurs_m)
        long_appui_min = np.array([
            calculer_longueur_appui_min(materiau, float(V_d_kN[i]), k_c90, taux_cible_appui, k_mod, gamma_M)
            for i in range(n)
        ])

        # Déversement §6.3.3 (scalaire par longueur)
        entraxe_adv = config.entraxe_antideversement_mm
        k_crit_arr = np.array([
            calculer_k_crit(
                materiau,
                type_poutre.longueur_deversement_m(float(longueurs_m[i]), entraxe_adv),
            )
            for i in range(n)
        ])
        taux_dever = res_flex["sigma_m_MPa"] / (k_crit_arr * res_flex["f_m_d_MPa"])

        # Double flexion (EF-024) — délégué à double_flexion.py via moteur.py
        M_z_kNm = charges.get("M_z_kNm", None)

        for i in range(n):
            L_dev_m_i = type_poutre.longueur_deversement_m(float(longueurs_m[i]), entraxe_adv)
            résultats.append({
                "longueur_m": float(longueurs_m[i]),
                "longueur_projetee_m": float(charges.get("longueur_projetee_m", [None] * n)[i])
                    if "longueur_projetee_m" in charges else None,
                "id_combinaison": combi.id_combinaison,
                "type_combinaison": combi.type_combinaison,
                "charge_principale": combi.charge_principale,
                "gamma_G": combi.gamma_G,
                "gamma_Q1": combi.gamma_Q1,
                "psi_0_Q2": combi.psi_0_Q2,
                "psi_0_Q3": combi.psi_0_Q3,
                "q_G_kNm": float(charges["q_G_kNm"][i]),
                "q_Q_kNm": float(charges["q_Q_kNm"][i]),
                "q_S_kNm": float(charges["q_S_kNm"][i]),
                "q_W_kNm": float(charges["q_W_kNm"][i]),
                "q_combinee_kNm": float(charges["q_d_kNm"][i]),
                "M_max_kNm": float(M_d_kNm[i]),
                "V_max_kN": float(V_d_kN[i]),
                "M_z_kNm": float(M_z_kNm[i]) if M_z_kNm is not None else None,
                "k_mod": k_mod,
                "gamma_M": gamma_M,
                "f_m_d_MPa": float(res_flex["f_m_d_MPa"][i]),
                "f_v_d_MPa": float(res_cis["f_v_d_MPa"][i]),
                "sigma_m_MPa": float(res_flex["sigma_m_MPa"][i]),
                "taux_flexion_ELU": float(res_flex["taux_flexion_ELU"][i]),
                "tau_MPa": float(res_cis["tau_MPa"][i]),
                "taux_cisaillement_ELU": float(res_cis["taux_cisaillement_ELU"][i]),
                "f_c90_k_MPa": materiau.f_c90_k_MPa,
                "f_c90_d_MPa": float(res_app["f_c90_d_MPa"][i]),
                "sigma_c90_MPa": float(res_app["sigma_c90_MPa"][i]),
                "k_c90": k_c90,
                "longueur_appui_mm": longueur_appui_mm,
                "taux_cible_appui": taux_cible_appui,
                "longueur_appui_min_mm": float(long_appui_min[i]),
                "taux_appui_ELU": float(res_app["taux_appui_ELU"][i]),
                "k_crit": float(k_crit_arr[i]),
                "L_deversement_m": L_dev_m_i if config.double_flexion else None,
                "taux_deversement_ELU": float(taux_dever[i]),
                "duree_charge": combi.duree_charge,
            })

    return résultats
