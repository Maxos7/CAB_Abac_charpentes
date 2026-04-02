"""Générateur de combinaisons EN 1990 + AN France (EF-009, EF-016).

Coefficients AN France :
    γ_G = 1.35 (défavorable) / 1.0 (favorable)
    γ_Q = 1.50
    ψ₀ catégorie H (toiture) = 0.0  → non, ψ₀ H=0 EC8, ici 0.5
    ψ₀ catégorie A-B (habitation) = 0.7
    ψ₀ neige (altitude ≤ 1000m) = 0.5
    ψ₀ vent = 0.6

Durées de charge EC5 Tableau 3.1 :
    G → permanent
    Q (habitation/bureau) → moyen_terme
    Q (catégorie H toiture) → court_terme
    S → court_terme
    W → instantane
"""
from __future__ import annotations

from abac_charpente.modeles.combinaison import CombinaisonEC0
from abac_charpente.modeles.config_calcul import ConfigCalcul


# Coefficients AN France
_GAMMA_G_DEF = 1.35   # défavorable
_GAMMA_G_FAV = 1.00   # favorable
_GAMMA_Q = 1.50

# ψ₀ par catégorie d'utilisation (EN 1990 Tableau A1.1 + AN France)
_PSI_0: dict[str, float] = {
    "A": 0.7, "B": 0.7, "C": 0.7, "D": 0.7,
    "E": 1.0, "F": 0.7, "G": 0.7,
    "H": 0.5,   # toiture non accessible (valeur courante)
    "S": 0.5,   # neige (altitude ≤ 1000m)
    "W": 0.6,   # vent
    "G": 1.0,   # permanent (ψ₀ non applicable)
}

# Durée de charge par type d'action
_DUREE_CHARGE: dict[str, str] = {
    "G": "permanent",
    "Q_A": "moyen_terme",   # habitation
    "Q_B": "moyen_terme",   # bureau
    "Q_C": "moyen_terme",
    "Q_D": "moyen_terme",
    "Q_H": "court_terme",   # toiture
    "S": "court_terme",
    "W": "instantane",
}


def _duree_charge_q(categorie_q: str) -> str:
    key = f"Q_{categorie_q.upper()}"
    return _DUREE_CHARGE.get(key, "moyen_terme")


def _psi_0_q(categorie_q: str) -> float:
    return _PSI_0.get(categorie_q.upper(), 0.5)


def generer_combinaisons(config: ConfigCalcul) -> list[CombinaisonEC0]:
    """Génère les combinaisons EN 1990 ELU + ELS selon la configuration.

    ELU_STR : γ_G × G + γ_Q1 × Q1 + Σψ₀ × Qi (G dominant, Q/S/W principal à tour de rôle)
    ELS_CAR : G + Q1 + Σψ₀ × Qi (caractéristique)
    ELS_FREQ : G + ψ₁ × Q1 + Σψ₂ × Qi (fréquente, simplifié)
    ELS_QPERM : G + Σψ₂ × Qi (quasi-permanente)

    Retourne la liste complète (non limitée ici — filtrage dans moteur.py).
    """
    g_k = float(config.g_k_kNm2 if isinstance(config.g_k_kNm2, (int, float)) else config.g_k_kNm2[0])
    q_k = float(config.q_k_kNm2 if isinstance(config.q_k_kNm2, (int, float)) else config.q_k_kNm2[0])
    s_k = float(config.s_k_kNm2 if isinstance(config.s_k_kNm2, (int, float)) else config.s_k_kNm2[0])
    w_k = float(config.w_k_kNm2 if isinstance(config.w_k_kNm2, (int, float)) else config.w_k_kNm2[0])
    cat_q = config.categorie_q

    psi0_Q = _psi_0_q(cat_q)
    psi0_S = _PSI_0["S"]
    psi0_W = _PSI_0["W"]
    duree_Q = _duree_charge_q(cat_q)

    combinaisons: list[CombinaisonEC0] = []

    # -------------------------------------------------
    # ELU_STR — cas G dominant (seul s'il n'y a pas d'autres actions)
    # -------------------------------------------------
    combinaisons.append(CombinaisonEC0(
        id_combinaison="ELU_G",
        type_combinaison="ELU_STR",
        charge_principale="G",
        gamma_G=_GAMMA_G_DEF,
        gamma_Q1=0.0,
        psi_0_Q2=psi0_Q * (1.0 if q_k > 0 else 0.0),
        psi_0_Q3=psi0_S * (1.0 if s_k > 0 else 0.0),
        duree_charge="permanent",
    ))

    # ELU_STR — Q principal
    if q_k > 0:
        combinaisons.append(CombinaisonEC0(
            id_combinaison="ELU_Q",
            type_combinaison="ELU_STR",
            charge_principale="Q",
            gamma_G=_GAMMA_G_DEF,
            gamma_Q1=_GAMMA_Q,
            psi_0_Q2=psi0_S * (1.0 if s_k > 0 else 0.0),
            psi_0_Q3=psi0_W * (1.0 if w_k > 0 else 0.0),
            duree_charge=duree_Q,
        ))

    # ELU_STR — S principal
    if s_k > 0:
        combinaisons.append(CombinaisonEC0(
            id_combinaison="ELU_S",
            type_combinaison="ELU_STR",
            charge_principale="S",
            gamma_G=_GAMMA_G_DEF,
            gamma_Q1=_GAMMA_Q,
            psi_0_Q2=psi0_Q * (1.0 if q_k > 0 else 0.0),
            psi_0_Q3=psi0_W * (1.0 if w_k > 0 else 0.0),
            duree_charge="court_terme",
        ))

    # ELU_STR — W principal
    if w_k > 0:
        combinaisons.append(CombinaisonEC0(
            id_combinaison="ELU_W",
            type_combinaison="ELU_STR",
            charge_principale="W",
            gamma_G=_GAMMA_G_DEF,
            gamma_Q1=_GAMMA_Q,
            psi_0_Q2=psi0_Q * (1.0 if q_k > 0 else 0.0),
            psi_0_Q3=psi0_S * (1.0 if s_k > 0 else 0.0),
            duree_charge="instantane",
        ))

    # -------------------------------------------------
    # ELS_CAR — caractéristique
    # -------------------------------------------------
    combinaisons.append(CombinaisonEC0(
        id_combinaison="ELS_CAR_G",
        type_combinaison="ELS_CAR",
        charge_principale="G",
        gamma_G=1.0,
        gamma_Q1=0.0,
        psi_0_Q2=psi0_Q * (1.0 if q_k > 0 else 0.0),
        psi_0_Q3=psi0_S * (1.0 if s_k > 0 else 0.0),
        duree_charge="permanent",
    ))

    if q_k > 0:
        combinaisons.append(CombinaisonEC0(
            id_combinaison="ELS_CAR_Q",
            type_combinaison="ELS_CAR",
            charge_principale="Q",
            gamma_G=1.0,
            gamma_Q1=1.0,
            psi_0_Q2=psi0_S * (1.0 if s_k > 0 else 0.0),
            psi_0_Q3=psi0_W * (1.0 if w_k > 0 else 0.0),
            duree_charge=duree_Q,
        ))

    if s_k > 0:
        combinaisons.append(CombinaisonEC0(
            id_combinaison="ELS_CAR_S",
            type_combinaison="ELS_CAR",
            charge_principale="S",
            gamma_G=1.0,
            gamma_Q1=1.0,
            psi_0_Q2=psi0_Q * (1.0 if q_k > 0 else 0.0),
            psi_0_Q3=psi0_W * (1.0 if w_k > 0 else 0.0),
            duree_charge="court_terme",
        ))

    # -------------------------------------------------
    # ELS quasi-permanente (pour flèches différées)
    # -------------------------------------------------
    combinaisons.append(CombinaisonEC0(
        id_combinaison="ELS_QPERM",
        type_combinaison="ELS_QPERM",
        charge_principale="G",
        gamma_G=1.0,
        gamma_Q1=0.0,
        psi_0_Q2=0.3 * (1.0 if q_k > 0 else 0.0),   # ψ₂_Q ≈ 0.3 (HAB)
        psi_0_Q3=0.0,
        duree_charge="permanent",
    ))

    return combinaisons
