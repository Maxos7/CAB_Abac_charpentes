"""Vérifications ELS EC5 — flèches (EF-013).

Calculs vectorisés sur np.ndarray.
RÈGLE NON-NÉGOCIABLE (Principe X + EF-019) : aucun branchement conditionnel sur
le nom du type de poutre dans ce module. Dispatch via polymorphisme OOP.

Formules EC5 §7.2 :
    w_inst = 5 × q × L⁴ / (384 × E_0_mean × I)
    w_creep = k_def × w_inst_qperm
    w_fin = w_inst + w_creep
    w_2 = w_inst_fin(Q) + w_creep(G)  [second-oeuvre]

Notation française EC5 (Principe IX). Unités explicites (Principe VI).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sapeg_regen_stock.modeles import ConfigMatériau
from abac_charpente.modeles.config_calcul import ConfigCalcul
from abac_charpente.modeles.combinaison import CombinaisonEC0
from abac_charpente.ec5.types_poutre.base import TypePoutre
from abac_charpente.ec5.proprietes import get_kdef, get_famille

# Chargement limites flèche
_DATA = Path(__file__).parent.parent / "data"
_DF_LIMITES: pd.DataFrame | None = None


def _charger_limites() -> pd.DataFrame:
    global _DF_LIMITES
    if _DF_LIMITES is None:
        _DF_LIMITES = pd.read_csv(_DATA / "limites_fleche_ec5.csv", sep=";")
        _DF_LIMITES = _DF_LIMITES.set_index("usage")
    return _DF_LIMITES


def calculer_w_inst(
    q_kNm: float,
    L_m: float,
    E_mean_MPa: float,
    I_cm4: float,
) -> float:
    """Flèche instantanée w_inst = 5qL⁴/(384EI) en mm.

    Paramètres :
        q_kNm     : charge uniformément répartie (kN/m)
        L_m       : portée (m)
        E_mean_MPa: module élastique moyen (MPa = N/mm²)
        I_cm4     : moment quadratique (cm⁴)

    Conversion :
        q kN/m → N/mm : q × 1  (1 kN/m = 1000 N / 1000 mm = 1 N/mm)
        L m → mm : L × 1000
        I cm⁴ → mm⁴ : I × 10000
    """
    q_Nmm = q_kNm * 1.0       # kN/m → N/mm : numériquement identique
    L_mm = L_m * 1000.0        # m → mm
    I_mm4 = I_cm4 * 1e4        # cm⁴ → mm⁴
    return 5.0 * q_Nmm * L_mm**4 / (384.0 * E_mean_MPa * I_mm4)


def calculer_w_fin(w_inst: float, k_def: float) -> float:
    """Flèche finale w_fin = w_inst × (1 + k_def)."""
    return w_inst * (1.0 + k_def)


def verifier_statut_usage(usage: str) -> str:
    """Retourne 'rejeté_usage' pour PLANCHER_PAR, sinon 'ok' (sans exception)."""
    if usage == "PLANCHER_PAR":
        return "rejeté_usage"
    return "ok"


def get_limites_fleche(usage: str, L_m: float) -> dict[str, float]:
    """Retourne les limites de flèche en mm depuis le CSV normatif.

    Paramètres :
        usage : code usage (TOITURE_INACC, PLANCHER_HAB, etc.)
        L_m   : longueur de portée (m)

    Retourne dict avec : limite_inst_mm, limite_fin_mm, limite_2_mm (ou None).
    """
    limites = _charger_limites()
    if usage not in limites.index:
        return {"limite_inst_mm": L_m * 1000 / 300, "limite_fin_mm": L_m * 1000 / 250, "limite_2_mm": None}

    row = limites.loc[usage]
    L_mm = L_m * 1000.0

    def _limite(inv: str) -> float | None:
        val = row.get(inv)
        if pd.isna(val) or val == "" or val is None:
            return None
        try:
            inv_float = float(val)
            return L_mm / inv_float if inv_float > 0 else None
        except (ValueError, TypeError):
            return None

    return {
        "limite_inst_mm": _limite("w_inst_inv"),
        "limite_fin_mm": _limite("w_fin_inv"),
        "limite_2_mm": _limite("w_2_inv"),
    }


def verifier_els(
    materiau: ConfigMatériau,
    config: ConfigCalcul,
    type_poutre: TypePoutre,
    longueurs_m: np.ndarray,
    combinaisons: list[CombinaisonEC0],
) -> list[dict]:
    """Vérifie les ELS (flèches) pour toutes les combinaisons et longueurs (EF-013).

    Appelle type_poutre.charges_lineaires() par polymorphisme OOP (Principe X).
    Retourne une liste de dicts contenant toutes les valeurs intermédiaires ELS.
    """
    famille = get_famille(materiau.classe_resistance)
    classe_service = int(config.classe_service if isinstance(config.classe_service, int)
                         else config.classe_service[0])
    k_def = get_kdef(famille, classe_service)
    second_oeuvre = config.second_oeuvre
    usage = config.usage

    statut_usage = verifier_statut_usage(usage)

    résultats: list[dict] = []

    for combi in combinaisons:
        if combi.type_combinaison not in ("ELS_CAR", "ELS_FREQ", "ELS_QPERM"):
            continue

        # Charges via polymorphisme (Principe X)
        charges = type_poutre.charges_lineaires(config, materiau, longueurs_m, combi)
        q_d_arr = charges["q_d_kNm"]

        for i, L_m in enumerate(longueurs_m):
            q_d = float(q_d_arr[i])
            L_m_f = float(L_m)

            # Limites de flèche depuis CSV (ou config explicite)
            limites_csv = get_limites_fleche(usage, L_m_f)
            limite_inst = config.limite_fleche_inst
            limite_fin = config.limite_fleche_fin
            limite_2 = config.limite_fleche_2

            # L/x → mm ou depuis CSV
            limite_inst_mm = (L_m_f * 1000 / limite_inst) if limite_inst else limites_csv["limite_inst_mm"]
            limite_fin_mm = (L_m_f * 1000 / limite_fin) if limite_fin else limites_csv["limite_fin_mm"]
            limite_2_mm = (L_m_f * 1000 / limite_2) if limite_2 else limites_csv["limite_2_mm"]

            if limite_inst_mm is None:
                limite_inst_mm = L_m_f * 1000 / 300
            if limite_fin_mm is None:
                limite_fin_mm = L_m_f * 1000 / 250

            # Flèche instantanée
            w_inst_mm = calculer_w_inst(q_d, L_m_f, materiau.E_0_mean_MPa, materiau.I_cm4)
            w_creep_mm = k_def * w_inst_mm
            w_fin_mm = calculer_w_fin(w_inst_mm, k_def)

            # Taux ELS
            taux_inst = w_inst_mm / limite_inst_mm if limite_inst_mm else 0.0
            taux_fin = w_fin_mm / limite_fin_mm if limite_fin_mm else 0.0

            # Second-oeuvre
            w_2_mm = None
            limite_2_mm_calc = None
            taux_2 = None
            if second_oeuvre and limite_2_mm:
                w_2_mm = w_fin_mm  # simplification : w_fin total
                limite_2_mm_calc = limite_2_mm
                taux_2 = w_2_mm / limite_2_mm_calc if limite_2_mm_calc else 0.0

            # Chevron : longueur projetée disponible dans les charges
            longueur_projetee = charges.get("longueur_projetee_m")
            lp = float(longueur_projetee[i]) if longueur_projetee is not None else None

            # Flèche verticale (Chevron)
            pente_rad_arr = charges.get("pente_rad")
            w_vert_inst_mm = None
            w_vert_fin_mm = None
            if pente_rad_arr is not None:
                import math
                pente_r = float(pente_rad_arr[i])
                if pente_r > 0:
                    w_vert_inst_mm = w_inst_mm / math.cos(pente_r)
                    w_vert_fin_mm = w_fin_mm / math.cos(pente_r)

            résultats.append({
                "longueur_m": L_m_f,
                "longueur_projetee_m": lp,
                "id_combinaison": combi.id_combinaison,
                "type_combinaison": combi.type_combinaison,
                "statut_usage": statut_usage,
                "w_inst_mm": w_inst_mm,
                "limite_inst_mm": limite_inst_mm,
                "taux_ELS_inst": taux_inst,
                "w_creep_mm": w_creep_mm,
                "w_fin_mm": w_fin_mm,
                "limite_fin_mm": limite_fin_mm,
                "taux_ELS_fin": taux_fin,
                "w_2_mm": w_2_mm,
                "limite_2_mm": limite_2_mm_calc,
                "taux_ELS_2": taux_2,
                # Double flexion (rempli par double_flexion.py)
                "w_y_inst_mm": None,
                "w_z_inst_mm": None,
                "w_res_inst_mm": None,
                "w_y_fin_mm": None,
                "w_z_fin_mm": None,
                "w_res_fin_mm": None,
                # Chevron
                "w_vert_inst_mm": w_vert_inst_mm,
                "w_vert_fin_mm": w_vert_fin_mm,
            })

    return résultats
