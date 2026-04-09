"""
modeles.combinaison
===================
Représentation d'une combinaison EC0 (EN 1990) pour le pipeline vectorisé.

Chaque instance porte tous les coefficients nécessaires pour pondérer les charges
dans l'espace tenseur (n_L, n_C, n_M). Le champ ``gamma_G2`` modélise les charges
permanentes fragiles (carrelage, chapes) qui sont toujours défavorables et nécessitent
un traitement séparé pour les vérifications ELS second-œuvre et futures vérifications EC8.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CombinaisonEC0Vect:
    """Coefficients d'une combinaison EC0 pour le pipeline tensoriel.

    Parameters
    ----------
    id_combinaison:
        Identifiant lisible (ex: "ELU_STR_G+Q", "ELS_CAR_G+S").
    type_etat_limite:
        "ELU" ou "ELS".
    type_combinaison:
        Sous-type — ex. "STR", "CAR", "FREQ", "QPERM".
    gamma_G:
        Coefficient de pondération sur les charges permanentes G normales.
        ELU : 1.35 (défavorable) ou 1.0 (favorable). ELS : 1.0.
    gamma_G2:
        Coefficient de pondération sur les charges permanentes fragiles G2
        (carrelage, chapes, cloisons légères).
        Toujours ≥ 1.0 — ELU : 1.35, ELS : 1.0.
        Séparé de gamma_G pour permettre le calcul ELS second-œuvre (EC5 §2.2.3)
        et la compatibilité EC8 futur (G2 toujours amplifiée).
    gamma_Q1:
        Coefficient de pondération sur la charge variable principale Q1.
        ELU : 1.5. ELS : 1.0 (CAR) ou 0.0 (QPERM).
    gamma_Q_accomp:
        Coefficient de pondération sur les charges variables d'accompagnement.
        ELU : 1.5 × ψ₀. ELS : ψ₁ (FREQ) ou ψ₂ (QPERM).
    type_charge_principale:
        Identifiant de la charge variable principale dans cette combinaison
        ("Q", "S", "W" — détermine quelle charge porte gamma_Q1).
    duree_charge:
        Durée de charge de la combinaison pour lookup k_mod (EC5 Table 3.1).
        Valeurs : "permanent", "long_terme", "moyen_terme", "court_terme", "instantane".
    """

    id_combinaison: str
    type_etat_limite: str       # "ELU" | "ELS"
    type_combinaison: str       # "STR" | "CAR" | "FREQ" | "QPERM"

    gamma_G: float
    gamma_G2: float
    gamma_Q1: float
    gamma_Q_accomp: float

    type_charge_principale: str  # "Q" | "S" | "W"
    duree_charge: str
