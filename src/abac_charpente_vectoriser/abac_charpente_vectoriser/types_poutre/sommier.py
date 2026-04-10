"""
types_poutre.sommier
====================
Sommier (poutre principale horizontale) bi-appuyé.

Identique à la solive pour la décomposition des charges (flexion axe fort uniquement,
pas de double flexion). Le sommier est différencié de la solive par son usage
(limites de flèche ELS différentes dans ``limites_fleche_ec5.csv``) et typiquement
par des sections plus importantes.

Usage typique : poutre porteuse principale, poutre de plancher sur grande portée.
"""

from __future__ import annotations

import numpy as np

from ..modeles.config_calcul import ConfigCalculVect
from ..protocoles.type_poutre import TypePoutreVect


class SommierVect(TypePoutreVect):
    """Sommier horizontal bi-appuyé — flexion axe fort uniquement.

    Comportement identique à ``SoliveVect`` pour le calcul. La distinction
    avec la solive est portée par ``config.usage`` pour la sélection des limites ELS.
    """

    def __init__(self, config: ConfigCalculVect) -> None:
        super().__init__(config)

    @property
    def double_flexion_active(self) -> bool:
        """Toujours False pour un sommier (flexion axe fort uniquement)."""
        return False

    def decomposer_charges(
        self,
        q_d_kNm: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Toute la charge va sur l'axe fort y — pas de composante z.

        Parameters
        ----------
        q_d_kNm:
            Charge linéique de calcul totale en kN/m ``(n_L, n_C, n_M)``.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            ``(q_y = q_d, q_z = 0.0)``
        """
        return q_d_kNm, np.zeros_like(q_d_kNm)

    def longueur_deversement_m(
        self,
        longueurs_m: np.ndarray,
    ) -> np.ndarray:
        """Longueur de déversement effective — EC5 §6.3.3.

        Parameters
        ----------
        longueurs_m:
            Vecteur de portées ``(n_L,)``.

        Returns
        -------
        np.ndarray
            Longueurs de déversement ``(n_L,)``.
        """
        e_mm: float = self._config.entraxe_antideversement_mm
        if e_mm <= 0.0:
            return longueurs_m.copy()
        e_m: float = e_mm / 1000.0
        return np.where(longueurs_m <= 2.0 * e_m, longueurs_m / 2.0, e_m)

    def longueur_projetee_m(
        self,
        longueurs_m: np.ndarray,
    ) -> np.ndarray | None:
        """Retourne None — le sommier est horizontal."""
        return None
