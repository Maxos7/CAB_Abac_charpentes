"""Double flexion + déversement composé biaxial EC5 §6.1.6/§6.3.3 (EF-024).

Vérifications biaxiales §6.1.6 :
    σ_m_y_d / f_m_d + k_m × σ_m_z_d / f_m_d ≤ 1
    k_m × σ_m_y_d / f_m_d + σ_m_z_d / f_m_d ≤ 1

k_m = 0.7 (section rectangulaire, EC5 §6.1.6(2))
k_crit composé : calculé avec I_z, W_z, E_0.05

Notation française EC5 (Principe IX). Unités explicites (Principe VI).
"""
from __future__ import annotations

import math

import numpy as np

from sapeg_regen_stock.modeles import ConfigMatériau
from abac_charpente.modeles.config_calcul import ConfigCalcul
from abac_charpente.ec5.elu import calculer_k_crit, calculer_flexion
from abac_charpente.ec5.els import calculer_w_inst
from abac_charpente.ec5.types_poutre.base import TypePoutre

_K_M = 0.7  # section rectangulaire EC5 §6.1.6(2)


def calculer_k_crit_compose(
    materiau: ConfigMatériau,
    L_deversement_m: float,
) -> float:
    """k_crit composé pour double flexion §6.3.3 (utilise I_z, E_0.05).

    Identique à calculer_k_crit() mais avec le matériau complet (I_z, W_z requis EF-024).
    """
    return calculer_k_crit(materiau, L_deversement_m)


def verifier_double_flexion(
    materiau: ConfigMatériau,
    config: ConfigCalcul,
    longueurs_m: np.ndarray,
    q_y_kNm: np.ndarray,
    q_z_kNm: np.ndarray,
    k_mod: float,
    gamma_M: float,
) -> list[dict]:
    """Vérifications biaxiales ELU + ELS pour double flexion (EF-024).

    Paramètres :
        materiau   : propriétés mécaniques
        config     : configuration de calcul
        longueurs_m: tableau des longueurs de portée (m)
        q_y_kNm    : charges selon axe fort (kN/m)
        q_z_kNm    : charges selon axe faible (kN/m)
        k_mod      : coefficient de modification
        gamma_M    : coefficient partiel matériau

    Retourne liste de dicts avec les vérifications biaxiales par longueur.
    """
    f_m_k_MPa = materiau.f_m_k_MPa
    f_m_d_MPa = f_m_k_MPa * k_mod / gamma_M

    W_y_cm3 = materiau.W_cm3
    W_z_cm3 = materiau.W_z_cm3
    I_z_cm4 = materiau.I_z_cm4
    E_0_mean_MPa = materiau.E_0_mean_MPa

    entraxe_adv = config.entraxe_antideversement_mm

    résultats: list[dict] = []

    for i, L_m in enumerate(longueurs_m):
        L_m_f = float(L_m)
        q_y = float(q_y_kNm[i])
        q_z = float(q_z_kNm[i])

        # Moments de calcul (portée simple)
        M_y_kNm = q_y * L_m_f**2 / 8.0
        M_z_kNm = q_z * L_m_f**2 / 8.0

        # Contraintes (MPa)
        sigma_m_y_MPa = M_y_kNm * 1e3 / W_y_cm3 / 10.0
        sigma_m_z_MPa = M_z_kNm * 1e3 / W_z_cm3 / 10.0 if W_z_cm3 > 0 else 0.0

        # k_crit composé
        from abac_charpente.ec5.types_poutre.base import TypePoutre
        L_dev_m = TypePoutre.longueur_deversement_m(None, L_m_f, entraxe_adv)  # type: ignore
        # Appel via une instance factice
        from abac_charpente.ec5.types_poutre import instancier
        _poutre = instancier(config.type_poutre)
        L_dev_m = _poutre.longueur_deversement_m(L_m_f, entraxe_adv)
        k_crit = calculer_k_crit_compose(materiau, L_dev_m)

        # Taux biaxiaux §6.1.6(2)
        # σ_m_y / (k_crit × f_m_d) + k_m × σ_m_z / f_m_d ≤ 1
        f_m_crit_MPa = k_crit * f_m_d_MPa if k_crit > 0 else f_m_d_MPa
        taux_biaxial_1 = sigma_m_y_MPa / f_m_crit_MPa + _K_M * sigma_m_z_MPa / f_m_d_MPa
        taux_biaxial_2 = _K_M * sigma_m_y_MPa / f_m_crit_MPa + sigma_m_z_MPa / f_m_d_MPa

        # ELS double axe
        w_y_inst_mm = calculer_w_inst(q_y, L_m_f, E_0_mean_MPa, materiau.I_cm4)
        w_z_inst_mm = calculer_w_inst(q_z, L_m_f, E_0_mean_MPa, I_z_cm4) if I_z_cm4 > 0 else 0.0
        w_res_inst_mm = math.sqrt(w_y_inst_mm**2 + w_z_inst_mm**2)

        from abac_charpente.ec5.proprietes import get_kdef, get_famille
        famille = get_famille(materiau.classe_resistance)
        classe_service = int(config.classe_service if isinstance(config.classe_service, int)
                             else config.classe_service[0])
        k_def = get_kdef(famille, classe_service)
        w_y_fin_mm = w_y_inst_mm * (1 + k_def)
        w_z_fin_mm = w_z_inst_mm * (1 + k_def)
        w_res_fin_mm = math.sqrt(w_y_fin_mm**2 + w_z_fin_mm**2)

        résultats.append({
            "longueur_m": L_m_f,
            "M_y_kNm": M_y_kNm,
            "M_z_kNm": M_z_kNm,
            "sigma_m_y_MPa": sigma_m_y_MPa,
            "sigma_m_z_MPa": sigma_m_z_MPa,
            "k_m": _K_M,
            "k_crit": k_crit,
            "L_deversement_m": L_dev_m,
            "taux_biaxial_1_ELU": taux_biaxial_1,
            "taux_biaxial_2_ELU": taux_biaxial_2,
            "w_y_inst_mm": w_y_inst_mm,
            "w_z_inst_mm": w_z_inst_mm,
            "w_res_inst_mm": w_res_inst_mm,
            "w_y_fin_mm": w_y_fin_mm,
            "w_z_fin_mm": w_z_fin_mm,
            "w_res_fin_mm": w_res_fin_mm,
        })

    return résultats