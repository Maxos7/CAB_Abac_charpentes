"""
types_poutre.panne_deversee
===========================
Panne déversée bi-appuyée — section perpendiculaire au rampant (normale à la surface).

C'est la configuration standard pour les pannes en charpente traditionnelle :
la section est posée avec h perpendiculaire à la surface du rampant.

Décomposition des charges verticales (par mètre de rampant) :
    q_y = q × cos(α)    → flexion axe fort y (⊥ au rampant)
    q_z = q × sin(α)    → flexion axe faible z (le long de la pente)

La double flexion est activée via ``config.double_flexion = True``.
Pour la section verticale, utiliser ``PanneAplombVect``.
"""

from __future__ import annotations

import math

import numpy as np

from ..modeles.config_calcul import ConfigCalculVect
from ..protocoles.type_poutre import TypePoutreVect


class PanneDeverseeVect(TypePoutreVect):
    """Panne déversée bi-appuyée — section ⊥ au rampant (normale à la surface).

    La pente α est issue de ``config.pente_deg`` (scalaire après développement
    du produit cartésien par le moteur).
    """

    def __init__(self, config: ConfigCalculVect) -> None:
        super().__init__(config)
        pente_deg: float = float(
            config.pente_deg[0] if isinstance(config.pente_deg, list) else config.pente_deg
        )
        self._pente_rad: float = math.radians(pente_deg)

    def decomposer_charges(
        self,
        q_d_kNm: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Décomposition charge verticale selon les axes de la section ⊥ au rampant.

        La charge q_d est exprimée par mètre de rampant (longueur inclinée).

        Parameters
        ----------
        q_d_kNm:
            Charge linéique de calcul totale en kN/m (par mètre de rampant).

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            ``(q_y_kNm, q_z_kNm)``
            - q_y = q × cos(α) : flexion axe fort y (⊥ rampant)
            - q_z = q × sin(α) : flexion axe faible z (le long de la pente),
              nul si ``double_flexion`` non activé.
        """
        q_y: np.ndarray = q_d_kNm * math.cos(self._pente_rad)
        q_z: np.ndarray = (
            q_d_kNm * math.sin(self._pente_rad)
            if self.double_flexion_active
            else np.zeros_like(q_d_kNm)
        )
        return q_y, q_z

    def longueur_deversement_m(self, longueurs_m: np.ndarray) -> np.ndarray:
        """Longueur de déversement effective — EC5 §6.3.3.

        Si ``entraxe_antideversement_mm = 0`` → l_ef = L (rampant complet).
        Si ``entraxe_antideversement_mm > 0`` et ``L ≤ 2 × e_andev`` → l_ef = L / 2.
        Sinon → l_ef = entraxe_antideversement_mm / 1000.

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
        """Retourne None — la panne s'appuie sur la longueur de rampant."""
        return None
