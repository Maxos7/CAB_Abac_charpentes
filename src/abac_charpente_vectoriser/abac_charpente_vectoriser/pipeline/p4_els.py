"""
pipeline.p4_els
===============
Étape 4 — Vérifications ELS sur l'espace tenseur.

Itère sur ``VERIFICATIONS_ELS`` et appelle ``calculer()`` sur chaque vérification.
Le taux maximal sur toutes les combinaisons ELS est retenu pour chaque type
de vérification (flèche instantanée, finale, second-œuvre), ainsi que
l'identifiant normatif de la combinaison déterminante (ex. "ELS_CAR_G+S").

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
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Calcule les taux ELS max et la combinaison déterminante pour chaque vérification.

    Parameters
    ----------
    espace:
        Espace de combinaison tenseur.

    Returns
    -------
    tuple[dict[str, np.ndarray], dict[str, np.ndarray]]
        - ``taux_els``  : ``{id_verif: (n_L, n_M)}`` — taux maximal par vérification.
        - ``combo_els`` : ``{id_verif: (n_L, n_M)}`` — ``id_combinaison`` (str) de la
          combinaison ayant produit le taux maximal (ex. ``"ELS_CAR_G+S"``).
    """
    # Indices et identifiants des combinaisons ELS
    idx_els: list[int] = [
        i for i, c in enumerate(espace.combinaisons)
        if c.type_etat_limite == "ELS"
    ]
    ids_els: np.ndarray = np.array(
        [espace.combinaisons[i].id_combinaison for i in idx_els],
        dtype=object,
    )  # (n_C_els,)

    taux_resultats: dict[str, np.ndarray] = {}
    combo_resultats: dict[str, np.ndarray] = {}

    for verif in VERIFICATIONS_ELS:
        res = verif.calculer(espace)
        taux_arr: np.ndarray = res.taux_LCM[:, idx_els, :]   # (n_L, n_C_els, n_M)
        taux_max: np.ndarray = np.max(taux_arr, axis=1)       # (n_L, n_M)
        idx_win: np.ndarray  = np.argmax(taux_arr, axis=1)    # (n_L, n_M) — indice gagnant
        taux_resultats[verif.id_verification] = taux_max
        combo_resultats[verif.id_verification] = ids_els[idx_win]  # (n_L, n_M) str

    return taux_resultats, combo_resultats
