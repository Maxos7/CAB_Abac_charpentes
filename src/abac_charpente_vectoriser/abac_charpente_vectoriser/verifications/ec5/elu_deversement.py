"""
verifications.ec5.elu_deversement
===================================
Vérification ELU au déversement — EC5 §6.3.3.

Le taux de déversement est directement k_crit (pré-calculé dans l'espace).
Le taux d'utilisation combine flexion et déversement :

    σ_m,d / f_m,d est déjà réduit par k_crit dans FlexionSimple.
    Cette vérification reporte k_crit comme indicateur de risque de déversement.

    Taux = σ_m,d / (k_crit × f_m,d)   (identique à FlexionSimple)

Note : en EC5, la vérification de déversement est intégrée dans la vérification
de flexion via la réduction k_crit. Cette classe est conservée comme vérification
distincte pour la traçabilité dans l'abaque (colonne dédiée k_crit + taux).
"""

from __future__ import annotations

import numpy as np

from ...protocoles.verification import ResultatVerification, VerificationELU


class Deversement(VerificationELU):
    """Indicateur de déversement — EC5 §6.3.3.

    Retourne 1 - k_crit comme indicateur de réduction due au déversement.
    Taux = 0 si k_crit = 1 (pas de déversement). Taux = 1 si k_crit = 0 (instable).
    Ce n'est pas une vérification au sens strict mais un indicateur de risque.
    """

    @property
    def id_verification(self) -> str:
        return "Deversement"

    @property
    def article_ec5(self) -> str:
        return "EC5 §6.3.3"

    def calculer(self, espace) -> ResultatVerification:
        """Retourne (1 - k_crit) comme indicateur de réduction par déversement.

        Shapes :
            k_crit_LM : (n_L, n_M) → (n_L, 1, n_M) broadcasté sur n_C
        """
        n_L, n_C, n_M = espace.M_d_kNm.shape
        k_crit: np.ndarray = espace.k_crit_LM[:, np.newaxis, :]  # (n_L, 1, n_M)

        # Taux = 1 - k_crit : indicateur de réduction. 0 = pas de déversement.
        taux: np.ndarray = np.broadcast_to(1.0 - k_crit, (n_L, n_C, n_M)).copy()
        active: np.ndarray = np.ones((n_L, n_C, n_M), dtype=bool)

        return ResultatVerification(self.id_verification, taux, active)
