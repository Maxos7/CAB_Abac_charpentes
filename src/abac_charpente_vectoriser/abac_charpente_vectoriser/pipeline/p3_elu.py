"""
pipeline.p3_elu
===============
Étape 3 — Vérifications ELU sur l'espace tenseur.

Itère sur ``VERIFICATIONS_ELU`` et appelle ``calculer()`` sur chaque vérification.
Retourne le taux maximal par combinaison (``np.max(axis=1)``), conservant
l'identifiant de la combinaison déterminante pour l'abaque complet.

Aucun ``if/match`` sur le type de poutre ou le type de vérification ici.
Le dispatch est entièrement géré par le registre ``VERIFICATIONS_ELU``
et le polymorphisme de ``TypePoutreVect``.
"""

from __future__ import annotations

import numpy as np

from ..verifications import VERIFICATIONS_ELU
from .espace import EspaceCombinaisonTenseur


def verifier_elu(
    espace: EspaceCombinaisonTenseur,
) -> dict[str, np.ndarray]:
    """Calcule les taux ELU max pour toutes les vérifications.

    Pour chaque vérification, le taux maximal sur toutes les combinaisons
    ELU est retenu (enveloppe défavorable).

    Parameters
    ----------
    espace:
        Espace de combinaison tenseur (contient ELU + ELS — les vérifications
        ELU filtrent automatiquement sur ``type_etat_limite == "ELU"``).

    Returns
    -------
    dict[str, np.ndarray]
        Dictionnaire ``{id_verification: taux_max_LM}`` où ``taux_max_LM``
        est un tableau ``(n_L, n_M)`` contenant le taux maximal sur toutes
        les combinaisons ELU actives.
    """
    # Indices des combinaisons ELU
    idx_elu: list[int] = [
        i for i, c in enumerate(espace.combinaisons)
        if c.type_etat_limite == "ELU"
    ]

    resultats: dict[str, np.ndarray] = {}

    for verif in VERIFICATIONS_ELU:
        res = verif.calculer(espace)
        # Sélection des combinaisons ELU et max sur l'axe 1
        taux_elu: np.ndarray = res.taux_LCM[:, idx_elu, :]          # (n_L, n_C_elu, n_M)
        taux_max: np.ndarray = np.max(taux_elu, axis=1)              # (n_L, n_M)
        resultats[verif.id_verification] = taux_max

    return resultats
