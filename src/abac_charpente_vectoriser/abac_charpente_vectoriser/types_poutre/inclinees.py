"""
types_poutre.inclinees
======================
Pièces de charpente posées sur un rampant incliné.

Regroupe les trois types dont la géométrie dépend de la pente α :

- ``ChevronVect``       — portée sur rampant, charges ⊥ au rampant,
                          pas de double flexion.
- ``PanneDeverseeVect`` — section ⊥ au rampant (normale à la surface),
                          double flexion optionnelle via ``config.double_flexion``.
- ``PanneAplombVect``   — section verticale (âme verticale),
                          double flexion intrinsèque (toujours active).

Toutes héritent de ``TypePoutreInclineeVect`` qui factorise l'extraction
de ``_pente_rad`` depuis ``config.pente_deg``.
"""

from __future__ import annotations

import math

import numpy as np

from ..protocoles.type_poutre import TypePoutreInclineeVect


class ChevronVect(TypePoutreInclineeVect):
    """Chevron bi-appuyé — portée sur rampant, charges ⊥ au rampant.

    Pas de double flexion. Flèche verticale = flèche rampant / cos(α).
    La pente α est issue de ``config.pente_deg``.
    """

    _DOUBLE_FLEXION = False

    def longueur_projetee_m(
        self,
        longueurs_m: np.ndarray,
    ) -> np.ndarray | None:
        """Retourne la portée horizontale projetée pour la vérification ELS.

        La flèche verticale est calculée par le module ELS :
            w_vert = w_rampant / cos(α)

        Cette méthode fournit la portée projetée pour l'information dans l'abaque
        (utile pour comparer avec les critères L_horiz / x).

        Parameters
        ----------
        longueurs_m:
            Vecteur de portées de rampant ``(n_L,)``.

        Returns
        -------
        np.ndarray
            Portées horizontales projetées ``(n_L,)`` en mètres.
        """
        return longueurs_m * math.cos(self._pente_rad)


class PanneDeverseeVect(TypePoutreInclineeVect):
    """Panne déversée bi-appuyée — section ⊥ au rampant (normale à la surface).

    La pente α est issue de ``config.pente_deg`` (scalaire après développement
    du produit cartésien par le moteur).
    """

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


class PanneAplombVect(TypePoutreInclineeVect):
    """Panne aplomb bi-appuyée — section verticale sur rampant incliné.

    La double flexion est intrinsèque et toujours active.
    La pente α est issue de ``config.pente_deg``.
    """

    _DOUBLE_FLEXION = True

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
