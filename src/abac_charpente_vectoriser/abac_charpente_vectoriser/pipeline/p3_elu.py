"""
pipeline.p3_elu
===============
Étape 3 — Vérifications ELU sur l'espace tenseur.

Itère sur ``VERIFICATIONS_ELU`` et appelle ``calculer()`` sur chaque vérification.
Retourne le taux maximal par combinaison ELU ainsi que l'identifiant normatif
de la combinaison déterminante (ex. "ELU_STR_G+S"), et la valeur intermédiaire
physique à la combinaison déterminante (contrainte en MPa ou k_crit).

Aucun ``if/match`` sur le type de poutre ou le type de vérification ici.
"""

from __future__ import annotations

import numpy as np

from ..verifications import VERIFICATIONS_ELU
from .espace import EspaceCombinaisonTenseur


def verifier_elu(
    espace: EspaceCombinaisonTenseur,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Calcule les taux ELU max, combinaison déterminante et valeur intermédiaire.

    Parameters
    ----------
    espace:
        Espace de combinaison tenseur.

    Returns
    -------
    tuple[dict, dict, dict]
        - ``taux_elu``    : ``{id_verif: (n_L, n_M)}`` — taux maximal.
        - ``combo_elu``   : ``{id_verif: (n_L, n_M)}`` — id_combinaison déterminante.
        - ``valeur_elu``  : ``{id_verif: (n_L, n_M)}`` — valeur physique (MPa ou —).
                            Clé présente uniquement si valeur_intermediaire non None.
    """
    idx_elu: list[int] = [
        i for i, c in enumerate(espace.combinaisons) if c.type_etat_limite == "ELU"
    ]
    ids_elu: np.ndarray = np.array(
        [espace.combinaisons[i].id_combinaison for i in idx_elu], dtype=object
    )  # (n_C_elu,)

    taux_resultats: dict[str, np.ndarray] = {}
    combo_resultats: dict[str, np.ndarray] = {}
    valeur_resultats: dict[str, np.ndarray] = {}

    n_L: int = espace.M_d_kNm.shape[0]
    n_M: int = espace.M_d_kNm.shape[2]
    arange_L: np.ndarray = np.arange(n_L)[:, np.newaxis]
    arange_M: np.ndarray = np.arange(n_M)[np.newaxis, :]

    for verif in VERIFICATIONS_ELU:
        res = verif.calculer(espace)

        taux_sub: np.ndarray = res.taux_LCM[:, idx_elu, :]   # (n_L, n_C_elu, n_M)
        idx_win: np.ndarray = np.argmax(taux_sub, axis=1)     # (n_L, n_M)

        taux_resultats[verif.id_verification] = taux_sub[arange_L, idx_win, arange_M]
        combo_resultats[verif.id_verification] = ids_elu[idx_win]

        if res.valeur_intermediaire is not None:
            val_sub: np.ndarray = res.valeur_intermediaire[:, idx_elu, :]
            valeur_resultats[verif.id_verification] = val_sub[arange_L, idx_win, arange_M]

    return taux_resultats, combo_resultats, valeur_resultats
