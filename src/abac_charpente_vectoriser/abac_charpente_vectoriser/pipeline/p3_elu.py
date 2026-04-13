"""
pipeline.p3_elu
===============
Étape 3 — Vérifications ELU sur l'espace tenseur.

Itère sur ``VERIFICATIONS_ELU`` et appelle ``calculer()`` sur chaque vérification.
Retourne le taux maximal par combinaison (``np.max(axis=1)``) ainsi que
l'identifiant normatif de la combinaison déterminante (ex. "ELU_STR_G+S").

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
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Calcule les taux ELU max et la combinaison déterminante pour chaque vérification.

    Pour chaque vérification, le taux maximal sur toutes les combinaisons
    ELU est retenu (enveloppe défavorable), ainsi que l'identifiant normatif
    de la combinaison qui l'a produit.

    Parameters
    ----------
    espace:
        Espace de combinaison tenseur (contient ELU + ELS — les vérifications
        ELU filtrent automatiquement sur ``type_etat_limite == "ELU"``).

    Returns
    -------
    tuple[dict[str, np.ndarray], dict[str, np.ndarray]]
        - ``taux_elu``  : ``{id_verif: (n_L, n_M)}`` — taux maximal par vérification.
        - ``combo_elu`` : ``{id_verif: (n_L, n_M)}`` — ``id_combinaison`` (str) de la
          combinaison ayant produit le taux maximal (ex. ``"ELU_STR_G+S"``).
    """
    # Indices et identifiants des combinaisons ELU
    idx_elu: list[int] = [
        i for i, c in enumerate(espace.combinaisons)
        if c.type_etat_limite == "ELU"
    ]
    ids_elu: np.ndarray = np.array(
        [espace.combinaisons[i].id_combinaison for i in idx_elu],
        dtype=object,
    )  # (n_C_elu,)

    taux_resultats: dict[str, np.ndarray] = {}
    combo_resultats: dict[str, np.ndarray] = {}

    for verif in VERIFICATIONS_ELU:
        res = verif.calculer(espace)
        taux_arr: np.ndarray = res.taux_LCM[:, idx_elu, :]   # (n_L, n_C_elu, n_M)
        taux_max: np.ndarray = np.max(taux_arr, axis=1)       # (n_L, n_M)
        idx_win: np.ndarray  = np.argmax(taux_arr, axis=1)    # (n_L, n_M) — indice gagnant
        taux_resultats[verif.id_verification] = taux_max
        combo_resultats[verif.id_verification] = ids_elu[idx_win]  # (n_L, n_M) str

    return taux_resultats, combo_resultats
