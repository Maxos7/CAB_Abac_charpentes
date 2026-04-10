"""
pipeline.p4_els
===============
Étape 4 — Vérifications ELS sur l'espace tenseur.

Itère sur ``VERIFICATIONS_ELS`` et appelle ``calculer()`` sur chaque vérification.
Le taux maximal sur toutes les combinaisons ELS est retenu pour chaque type
de vérification (flèche instantanée, finale, second-œuvre).

Pour les chevrons, la flèche dans le plan du rampant est convertie en flèche
verticale : ``w_vert = w_rampant / cos(α)``.

Aucun ``if/match`` sur le type de poutre ici.
"""

from __future__ import annotations

import numpy as np

from ..verifications import VERIFICATIONS_ELS
from .espace import EspaceCombinaisonTenseur


def verifier_els(
    espace: EspaceCombinaisonTenseur,
) -> dict[str, np.ndarray]:
    """Calcule les taux ELS max pour toutes les vérifications.

    Parameters
    ----------
    espace:
        Espace de combinaison tenseur.

    Returns
    -------
    dict[str, np.ndarray]
        Dictionnaire ``{id_verification: taux_max_LM}`` où ``taux_max_LM``
        est un tableau ``(n_L, n_M)`` contenant le taux maximal sur toutes
        les combinaisons ELS actives.
    """
    # Indices des combinaisons ELS
    idx_els: list[int] = [
        i for i, c in enumerate(espace.combinaisons)
        if c.type_etat_limite == "ELS"
    ]

    resultats: dict[str, np.ndarray] = {}

    for verif in VERIFICATIONS_ELS:
        res = verif.calculer(espace)
        # Sélection des combinaisons ELS et max sur l'axe 1
        taux_els: np.ndarray = res.taux_LCM[:, idx_els, :]          # (n_L, n_C_els, n_M)
        taux_max: np.ndarray = np.max(taux_els, axis=1)              # (n_L, n_M)
        resultats[verif.id_verification] = taux_max

    return resultats
