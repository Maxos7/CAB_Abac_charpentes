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

from ..protocoles.type_poutre import TypePoutreInclineeVect


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

