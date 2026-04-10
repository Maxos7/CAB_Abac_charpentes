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

from ..modeles.config_calcul import ConfigCalculVect
from ..protocoles.type_poutre import TypePoutreVect


class ChevronVect(TypePoutreVect):
    """Chevron bi-appuyé — portée sur rampant, charges ⊥ au rampant.

    Pas de double flexion. Flèche verticale = flèche rampant / cos(α).
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
        """Toujours False — le chevron travaille en flexion simple ⊥ au rampant."""
        return False

    def decomposer_charges(
        self,
        q_d_kNm: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Toute la charge est perpendiculaire au rampant (axe fort y).

        Le pipeline ``p1_charges`` fournit directement la composante
        perpendiculaire au rampant dans ``q_d_kNm`` pour les chevrons.
        Aucune décomposition supplémentaire n'est donc nécessaire ici.

        Parameters
        ----------
        q_d_kNm:
            Charge perpendiculaire au rampant en kN/m (par mètre de rampant).

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
        """Longueur de déversement = portée de rampant (chevron retenu par couverture).

        En pratique, les chevrons sont retenus latéralement par les voligeages /
        liteaux, réduisant le risque de déversement. Faute de contreventement
        explicite (entraxe_antideversement_mm = 0), l'élancement est pris sur
        la portée complète (hypothèse conservatrice).

        Parameters
        ----------
        longueurs_m:
            Vecteur de portées de rampant ``(n_L,)``.

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
