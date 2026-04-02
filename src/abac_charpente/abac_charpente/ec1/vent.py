"""Coefficient de pression extérieure c_pe pour les charges de vent (EN 1991-1-4).

Implémentation simplifiée pour toitures 1 pan / 2 pans.
La valeur la plus défavorable est retournée.
"""
from __future__ import annotations


# Valeurs c_pe (pression extérieure) selon EN 1991-1-4
# Toiture 1 pan : c_pe,10 = -0.7 (aspiration dominante) ou +0.2 (pression)
# → valeur défavorable = +0.2 (pression) ou -0.7 (aspiration selon situation)
# Simplification : on prend c_pe = 0.8 comme valeur commune adverse
_CPE: dict[str, float] = {
    "1_pan": 0.8,   # pression sur versant au vent (simplifié AN France)
    "2_pans": 0.8,  # même simplification
}


def c_pe(type_toiture: str) -> float:
    """Retourne le coefficient de pression extérieure c_pe,10 pour le type de toiture.

    Paramètres :
        type_toiture : '1_pan' ou '2_pans'

    Retourne :
        Valeur c_pe,10 (sans dimension), positive = pression, négative = aspiration.
        Retourne 0.8 par défaut si type inconnu.

    Référence : EN 1991-1-4 §7.2.
    """
    return _CPE.get(type_toiture, 0.8)


def charge_vent_kNm(w_k_kNm2: float, cpe: float, entraxe_m: float) -> float:
    """Calcule la charge linéique de vent (kN/m).

    Paramètres :
        w_k_kNm2  : pression cinétique de référence (kN/m²)
        cpe       : coefficient de pression extérieure
        entraxe_m : entraxe des éléments porteurs (m)

    Retourne :
        Charge linéique de vent (kN/m).

    Référence : EF-011.
    """
    return abs(w_k_kNm2 * cpe * entraxe_m)
