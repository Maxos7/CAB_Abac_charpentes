"""
types_poutre.panne_aplomb
=========================
Panne aplomb — section verticale (âme verticale).

Orientation courante pour les pannes en bois lamellé-collé apparent.
La section est posée avec h vertical : l'axe fort y est vertical,
l'axe faible z est horizontal.

Décomposition des charges verticales (par mètre de rampant) :
    q_y = q          → flexion axe fort y (vertical = chargement direct)
    q_z = q × tan(α) → flexion axe faible z (horizontal, dû à l'inclinaison du rampant)

Formulation simplifiée standard française (section verticale sur rampant incliné).

La double flexion est **intrinsèque** : elle est toujours activée, indépendamment
du flag ``config.double_flexion``. Une section verticale sous charge verticale sur
rampant incliné crée systématiquement de la flexion biaxiale.
"""

from __future__ import annotations

import math

import numpy as np

from ..modeles.config_calcul import ConfigCalculVect
from ..protocoles.type_poutre import TypePoutreVect


class PanneAplombVect(TypePoutreVect):
    """Panne aplomb bi-appuyée — section verticale sur rampant incliné.

    La double flexion est intrinsèque et toujours active.
    La pente α est issue de ``config.pente_deg``.
    """

    def __init__(self, config: ConfigCalculVect) -> None:
        super().__init__(config)
        pente_deg: float = float(
            config.pente_deg[0] if isinstance(config.pente_deg, list) else config.pente_deg
        )
        self._pente_rad: float = math.radians(pente_deg)

    @property
    def double_flexion_active(self) -> bool:
        """Toujours True — la double flexion est intrinsèque à la panne aplomb."""
        return True

    def decomposer_charges(
        self,
        q_d_kNm: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Décomposition charge verticale sur section verticale en rampant incliné.

        Formulation simplifiée AN France (section verticale) :
            q_y = q              → axe fort y (vertical)
            q_z = q × tan(α)    → axe faible z (horizontal, effet de l'inclinaison)

        Parameters
        ----------
        q_d_kNm:
            Charge linéique de calcul totale en kN/m (par mètre de rampant).

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            ``(q_y_kNm, q_z_kNm)``
        """
        tan_a: float = math.tan(self._pente_rad)
        q_y: np.ndarray = q_d_kNm
        q_z: np.ndarray = q_d_kNm * tan_a
        return q_y, q_z

    def longueur_deversement_m(self, longueurs_m: np.ndarray) -> np.ndarray:
        """Longueur de déversement effective — EC5 §6.3.3.

        Parameters
        ----------
        longueurs_m:
            Vecteur de portées (longueurs de rampant) ``(n_L,)``.

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

    def longueur_projetee_m(self, longueurs_m: np.ndarray) -> np.ndarray | None:
        """Retourne None — la panne aplomb s'appuie sur la longueur de rampant."""
        return None
