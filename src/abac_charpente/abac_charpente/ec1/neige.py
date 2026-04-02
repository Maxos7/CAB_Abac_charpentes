"""Coefficient de forme μ₁ pour les charges de neige (EN 1991-1-3 §5.3).

μ₁(α) selon EN 1991-1-3 §5.3(3) :
    α ≤ 30°  → μ₁ = 0.8
    30° < α < 60° → interpolation linéaire [0.8 → 0.0]
    α ≥ 60°  → μ₁ = 0.0

Implémentation vectorisée numpy (np.interp).
"""
from __future__ import annotations

import numpy as np


# Points de référence EN 1991-1-3 §5.3(3)
_ANGLES_DEG = np.array([0.0, 30.0, 60.0])
_MU1_VALS = np.array([0.8, 0.8, 0.0])


def mu1(pente_deg_arr: np.ndarray) -> np.ndarray:
    """Calcule μ₁ (coefficient de forme neige) pour un tableau de pentes.

    Paramètres :
        pente_deg_arr : tableau de pentes en degrés (numpy array)

    Retourne :
        Tableau de valeurs μ₁ (sans dimension), même forme que pente_deg_arr.

    Référence : EN 1991-1-3 §5.3(3).
    """
    return np.interp(np.asarray(pente_deg_arr, dtype=float), _ANGLES_DEG, _MU1_VALS)
