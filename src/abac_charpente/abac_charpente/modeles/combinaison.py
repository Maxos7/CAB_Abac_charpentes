"""Entité CombinaisonEC0 — combinaison EN 1990.

Notation française EC5 (Principe IX). Entité dataclass (Principe X).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CombinaisonEC0:
    """Combinaison d'actions EN 1990 (ELU ou ELS).

    Paramètres :
        id_combinaison : identifiant unique de la combinaison.
        type_combinaison : 'ELU_STR' | 'ELS_CAR' | 'ELS_FREQ' | 'ELS_QPERM'.
        charge_principale : type d'action principale ('G' | 'Q' | 'S' | 'W').
        gamma_G : coefficient partiel sur actions permanentes.
        gamma_Q1 : coefficient partiel sur action variable principale.
        psi_0_Q2 : ψ₀ de la 2e action variable d'accompagnement.
        psi_0_Q3 : ψ₀ de la 3e action variable d'accompagnement.
        duree_charge : durée de chargement EC5 T3.1 ('permanent' | 'long_terme' |
                        'moyen_terme' | 'court_terme' | 'instantane').
    """
    id_combinaison: str
    type_combinaison: str
    charge_principale: str
    gamma_G: float
    gamma_Q1: float
    psi_0_Q2: float
    psi_0_Q3: float
    duree_charge: str
