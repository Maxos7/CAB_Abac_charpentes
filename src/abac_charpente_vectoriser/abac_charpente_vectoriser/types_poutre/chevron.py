"""
types_poutre.chevron
====================
Chevron — pièce de charpente posée dans le sens du rampant.

Le chevron est perpendiculaire aux pannes et supporte la couverture directement.
Les charges sont appliquées perpendiculairement à la surface du rampant
(pas de décomposition biaxiale — tout va sur l'axe fort).

La portée est mesurée sur le rampant. Pour la vérification ELS, la flèche
verticale est calculée depuis la flèche dans le plan du rampant :
    w_vert = w_rampant / cos(α)

Les charges caractéristiques de calcul :
    g_k  (poids propre couverture) → cos(α) ×  g_perp = g × cos²(α) / cos(α) = g × cos(α)
         (poids propre du chevron) → composante perpendiculaire = g_pp × cos(α)
    q_k  (charges exploitations) → q × cos²(α) / cos(α) sur rampant ≈ q × cos(α)
    s_k  (neige sur horizontal)  → déjà projeté via μ₁, appliqué directement
    w_k  (vent) → perpendiculaire au rampant, cos(α) appliqué
    N_d  → None (le chevron n'a pas d'effort normal en modèle bi-appui simple)
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
