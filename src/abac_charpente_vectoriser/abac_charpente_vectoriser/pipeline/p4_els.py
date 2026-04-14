"""
pipeline.p4_els
===============
Étape 4 — Vérifications ELS sur l'espace tenseur.

Itère sur ``VERIFICATIONS_ELS`` et appelle ``calculer()`` sur chaque vérification.
Retourne le taux maximal par combinaison ELS ainsi que l'identifiant normatif
de la combinaison déterminante (ex. "ELS_CAR_G+S"), et la valeur intermédiaire
physique à la combinaison déterminante (flèche en mm).

Pour les chevrons, la flèche dans le plan du rampant est convertie en flèche
verticale à l'intérieur des classes ELS (pas de traitement ici).

Aucun ``if/match`` sur le type de poutre ici.
"""

from __future__ import annotations

import numpy as np

from ..verifications import VERIFICATIONS_ELS
from .espace import EspaceCombinaisonTenseur


def verifier_els(
    espace: EspaceCombinaisonTenseur,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Calcule les taux ELS max, combinaison déterminante et valeur intermédiaire.

    Parameters
    ----------
    espace:
        Espace de combinaison tenseur.

    Returns
    -------
    tuple[dict, dict, dict]
        - ``taux_els``    : ``{id_verif: (n_L, n_M)}`` — taux maximal.
        - ``combo_els``   : ``{id_verif: (n_L, n_M)}`` — id_combinaison déterminante.
        - ``valeur_els``  : ``{id_verif: (n_L, n_M)}`` — flèche en mm.
                            Clé présente uniquement si valeur_intermediaire non None.
    """
    idx_els: list[int] = [
        i for i, c in enumerate(espace.combinaisons) if c.type_etat_limite == "ELS"
    ]
    ids_els: np.ndarray = np.array(
        [espace.combinaisons[i].id_combinaison for i in idx_els], dtype=object
    )  # (n_C_els,)

    taux_resultats: dict[str, np.ndarray] = {}
    combo_resultats: dict[str, np.ndarray] = {}
    valeur_resultats: dict[str, np.ndarray] = {}

    n_L: int = espace.M_d_kNm.shape[0]
    n_M: int = espace.M_d_kNm.shape[2]
    arange_L: np.ndarray = np.arange(n_L)[:, np.newaxis]
    arange_M: np.ndarray = np.arange(n_M)[np.newaxis, :]

    for verif in VERIFICATIONS_ELS:
        res = verif.calculer(espace)

        taux_sub: np.ndarray = res.taux_LCM[:, idx_els, :]    # (n_L, n_C_els, n_M)
        idx_win: np.ndarray = np.argmax(taux_sub, axis=1)      # (n_L, n_M)

        taux_resultats[verif.id_verification] = taux_sub[arange_L, idx_win, arange_M]
        combo_resultats[verif.id_verification] = ids_els[idx_win]

        if res.valeur_intermediaire is not None:
            val_sub: np.ndarray = res.valeur_intermediaire[:, idx_els, :]
            valeur_resultats[verif.id_verification] = val_sub[arange_L, idx_win, arange_M]

    return taux_resultats, combo_resultats, valeur_resultats
