"""Propriétés mécaniques EC5 — chargement des tables normatives EN 338 / EN 14080.

Fonctions exportées :
    get_proprietes(classe_resistance) -> dict
    calculer_section(b_mm, h_mm, rho_k) -> dict
    get_kmod(famille, classe_service, duree_charge) -> float
    get_kdef(famille, classe_service) -> float
    get_gamma_m(famille) -> float
    get_famille(classe_resistance) -> str

Toutes les tables sont chargées à l'import depuis src/abac_charpente/data/.
Notation EC5 française (Principe IX). Unités explicites (Principe VI).
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import pandas as pd

_DATA = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Chargement des tables (une seule fois à l'import)
# ---------------------------------------------------------------------------

def _charger_materiaux() -> pd.DataFrame:
    df = pd.read_csv(_DATA / "materiaux_bois.csv", sep=";",index_col="classe")
    return df


def _charger_kmod() -> pd.DataFrame:
    return pd.read_csv(_DATA / "kmod.csv", sep=";")


def _charger_kdef() -> pd.DataFrame:
    return pd.read_csv(_DATA / "kdef.csv", sep=";")


def _charger_gamma_m() -> pd.DataFrame:
    return pd.read_csv(_DATA / "gamma_m.csv", sep=";")


def _charger_params() -> dict[str, float]:
    df = pd.read_csv(_DATA / "params_ec5.csv", sep=";")
    return dict(zip(df["parametre"], df["valeur"]))


_DF_MAT = _charger_materiaux()
_DF_KMOD = _charger_kmod()
_DF_KDEF = _charger_kdef()
_DF_GAMMA_M = _charger_gamma_m()
_PARAMS = _charger_params()

# Coefficient E_0.05 = E_0_mean / 1.65 (EC5 §3.3(3))
_E005_FACTEUR: float = float(_PARAMS.get("E_0_05_facteur", 1.65))
# Facteur de forme k_cr (EN 1995-1-1 §6.1.7)
_K_CR: float = float(_PARAMS.get("k_cr", 0.67))


def get_famille(classe_resistance: str) -> str:
    """Retourne la famille de matériau depuis la classe de résistance."""
    c = classe_resistance.upper()
    if c.startswith("GL"):
        return "bois_lamelle_colle"
    if c.startswith("GT"):
        return "bois_reconstitue"
    return "bois_massif"


def get_proprietes(classe_resistance: str) -> dict:
    """Retourne les propriétés mécaniques d'une classe de résistance (kN, m, MPa).

    Lève KeyError si la classe est inconnue.
    """
    c = classe_resistance.upper()
    # GL/GT : suffixe h/c en minuscules (EN 14080)
    if c.startswith(("GL", "GT")):
        c = c[:-1] + c[-1].lower()
    if c not in _DF_MAT.index:
        raise KeyError(
            f"Classe de résistance '{classe_resistance}' inconnue. "
            f"Classes disponibles : {sorted(_DF_MAT.index.tolist())}"
        )
    row = _DF_MAT.loc[c]
    return {
        "f_m_k_MPa": float(row["f_m_k_MPa"]),
        "f_v_k_MPa": float(row["f_v_k_MPa"]),
        "f_c90_k_MPa": float(row["f_c90_k_MPa"]),
        "E_0_mean_MPa": float(row["E_0_mean_MPa"]),
        "E_0_05_MPa": float(row["E_0_mean_MPa"]) / _E005_FACTEUR,
        "rho_k_kgm3": float(row["rho_k_kgm3"]),
    }


def calculer_section(b_mm: float, h_mm: float, rho_k_kgm3: float) -> dict:
    """Calcule les propriétés de section à partir des dimensions.

    Paramètres :
        b_mm        : largeur (mm)
        h_mm        : hauteur (mm)
        rho_k_kgm3  : densité caractéristique (kg/m³)

    Retourne un dict avec :
        A_cm2           : aire de section (cm²)
        I_cm4           : moment quadratique axe fort (cm⁴)
        W_cm3           : module de résistance axe fort (cm³)
        I_z_cm4         : moment quadratique axe faible (cm⁴)
        W_z_cm3         : module de résistance axe faible (cm³)
        poids_propre_kNm: poids linéique (kN/m)
    """
    b_cm = b_mm / 10.0
    h_cm = h_mm / 10.0

    A_cm2 = b_cm * h_cm
    I_cm4 = b_cm * h_cm ** 3 / 12.0       # axe fort (flexion dans la hauteur)
    W_cm3 = I_cm4 / (h_cm / 2.0)
    I_z_cm4 = h_cm * b_cm ** 3 / 12.0     # axe faible (flexion dans la largeur)
    W_z_cm3 = I_z_cm4 / (b_cm / 2.0)

    # Poids propre (kN/m) : ρ_k × A × g / 1000
    # A en m², ρ en kg/m³ → kN/m = ρ × A × 9.81 / 1000
    A_m2 = A_cm2 * 1e-4
    poids_propre_kNm = rho_k_kgm3 * A_m2 * 9.81 / 1000.0

    return {
        "A_cm2": A_cm2,
        "I_cm4": I_cm4,
        "W_cm3": W_cm3,
        "I_z_cm4": I_z_cm4,
        "W_z_cm3": W_z_cm3,
        "poids_propre_kNm": poids_propre_kNm,
    }


def get_kmod(famille: str, classe_service: int, duree_charge: str) -> float:
    """Retourne k_mod selon EC5 Tableau 3.1."""
    mask = (
        (_DF_KMOD["famille"] == famille)
        & (_DF_KMOD["classe_service"] == classe_service)
        & (_DF_KMOD["duree_charge"] == duree_charge)
    )
    rows = _DF_KMOD[mask]
    if rows.empty:
        raise KeyError(
            f"k_mod introuvable pour famille={famille}, "
            f"classe_service={classe_service}, duree_charge={duree_charge}"
        )
    return float(rows.iloc[0]["k_mod"])


def get_kdef(famille: str, classe_service: int) -> float:
    """Retourne k_def selon EC5 Tableau 3.2."""
    mask = (
        (_DF_KDEF["famille"] == famille)
        & (_DF_KDEF["classe_service"] == classe_service)
    )
    rows = _DF_KDEF[mask]
    if rows.empty:
        raise KeyError(
            f"k_def introuvable pour famille={famille}, classe_service={classe_service}"
        )
    return float(rows.iloc[0]["k_def"])


def get_gamma_m(famille: str) -> float:
    """Retourne γ_M selon AN France §2.4.1."""
    mask = _DF_GAMMA_M["famille"] == famille
    rows = _DF_GAMMA_M[mask]
    if rows.empty:
        raise KeyError(f"γ_M introuvable pour famille={famille}")
    return float(rows.iloc[0]["gamma_M"])


def get_k_cr() -> float:
    """Retourne k_cr (facteur de fissuration EN 1995-1-1 §6.1.7)."""
    return _K_CR
