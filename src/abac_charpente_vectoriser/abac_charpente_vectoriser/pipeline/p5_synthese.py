"""
pipeline.p5_synthese
====================
Étape 5 — Synthèse des taux ELU/ELS en résultats finaux par matériau.

Pour chaque matériau (colonne n_M), détermine :
- Le taux global maximal = max(tous ELU, tous ELS)
- La longueur maximale admissible (premier L où taux_global > 1.0)
- Le taux déterminant et la vérification déterminante

Les résultats sont structurés pour être exportés par les modules ``sortie/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..modeles.config_calcul import ConfigCalculVect
from ..modeles.config_materiau import ConfigMatériauVect


@dataclass
class ResultatPortee:
    """Résultats de calcul pour un couple (matériau, configuration).

    Ce dataclass est l'unité de sortie du pipeline. Une instance par matériau.
    Il agrège tous les taux et la longueur maximale admissible.

    Parameters
    ----------
    id_config_materiau:
        Identifiant de la configuration matériau.
    id_config_calcul:
        Identifiant de la configuration de calcul.
    longueur_max_admissible_m:
        Longueur maximale pour laquelle tous les taux sont ≤ 1.0. ``None``
        si aucune longueur n'est admissible (trop chargé dès L_min).
    taux_determinant:
        Taux d'utilisation maximal sur toutes vérifications et toutes portées ≤ L_max.
    verif_determinante:
        Identifiant de la vérification déterminante (ex: "FlexionSimple").
    taux_par_verif:
        Dictionnaire ``{id_verif: taux_max_sur_L}`` pour toutes les vérifications.
    """

    id_config_materiau: str
    id_config_calcul: str
    longueur_max_admissible_m: float | None
    taux_determinant: float
    verif_determinante: str
    taux_par_verif: dict[str, float] = field(default_factory=dict)


def synthetiser(
    longueurs_m: np.ndarray,
    taux_elu: dict[str, np.ndarray],
    taux_els: dict[str, np.ndarray],
    materiaux: list[ConfigMatériauVect],
    config: ConfigCalculVect,
) -> list[ResultatPortee]:
    """Synthétise les taux ELU/ELS en résultats finaux par matériau.

    Parameters
    ----------
    longueurs_m:
        Vecteur de portées ``(n_L,)``.
    taux_elu:
        Résultats ELU depuis ``p3_elu.verifier_elu`` — ``{id: (n_L, n_M)}``.
    taux_els:
        Résultats ELS depuis ``p4_els.verifier_els`` — ``{id: (n_L, n_M)}``.
    materiaux:
        Liste des configurations matériau ``(n_M,)``.
    config:
        Configuration de calcul.

    Returns
    -------
    list[ResultatPortee]
        Un ``ResultatPortee`` par matériau.
    """
    tous_taux: dict[str, np.ndarray] = {**taux_elu, **taux_els}
    taux_stack: np.ndarray = np.stack(list(tous_taux.values()), axis=0)  # (n_verif, n_L, n_M)
    ids_verif: list[str] = list(tous_taux.keys())

    n_M: int = len(materiaux)
    resultats: list[ResultatPortee] = []

    for m in range(n_M):
        taux_global_L: np.ndarray = np.max(taux_stack[:, :, m], axis=0)  # (n_L,)

        admissible: np.ndarray = taux_global_L <= 1.0
        L_max: float | None
        if admissible.any():
            idx_max: int = int(np.where(admissible)[0][-1])
            L_max = float(longueurs_m[idx_max])
        else:
            L_max = None

        taux_det: float = float(np.max(taux_global_L))
        idx_verif_det: int = int(np.argmax(np.max(taux_stack[:, :, m], axis=1)))
        verif_det: str = ids_verif[idx_verif_det]

        taux_par_verif: dict[str, float] = {
            id_v: float(np.max(taux_stack[i, :, m]))
            for i, id_v in enumerate(ids_verif)
        }

        resultats.append(ResultatPortee(
            id_config_materiau=materiaux[m].id_config_materiau,
            id_config_calcul=config.id_config_calcul,
            longueur_max_admissible_m=L_max,
            taux_determinant=taux_det,
            verif_determinante=verif_det,
            taux_par_verif=taux_par_verif,
        ))

    return resultats
