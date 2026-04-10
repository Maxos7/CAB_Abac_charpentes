"""
types_poutre.solive
===================
Solive horizontale bi-appuyée — cas le plus simple du pipeline.

La solive est posée horizontalement (pente = 0°). Toutes les charges (G, Q, S)
s'appliquent verticalement selon l'axe fort y. Pas de double flexion.
Pas d'effort normal. La portée horizontale = portée de calcul.

Usage typique : plancher, toiture accessible.
"""

from __future__ import annotations

import numpy as np

from ..modeles.config_calcul import ConfigCalculVect
from ..protocoles.type_poutre import TypePoutreVect


class SoliveVect(TypePoutreVect):
    """Solive horizontale bi-appuyée — flexion axe fort uniquement.

    Toutes les charges sont appliquées selon l'axe fort y.
    La pente est nulle ou ignorée (la solive est horizontale par définition).
    Pas de déversement (k_crit = 1.0 sauf si entraxe_antideversement > 0).
    """

    def __init__(self, config: ConfigCalculVect) -> None:
        super().__init__(config)

    @property
    def double_flexion_active(self) -> bool:
        """Toujours False pour une solive (flexion axe fort uniquement)."""
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
        """Longueur de déversement = portée si pas de contreventement, sinon fraction.

        EC5 §6.3.3 — longueur d'élancement latéral pour une solive.
        Si ``entraxe_antideversement_mm = 0`` → l_ef = L (bi-appui simple).
        Si ``entraxe_antideversement_mm > 0`` et ``L ≤ 2 × e_andev`` → l_ef = L / 2.
        Sinon → l_ef = entraxe_antideversement_mm / 1000.

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
        """Retourne None — la solive est horizontale, pas de projection nécessaire."""
        return None
