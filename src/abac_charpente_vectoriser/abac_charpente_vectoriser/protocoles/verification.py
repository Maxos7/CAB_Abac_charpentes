"""
protocoles.verification
=======================
Classes de base abstraites pour les vérifications ELU et ELS.

Principe : aucun ``if/match`` dans le pipeline — toutes les vérifications sont
des objets enregistrés dans ``VERIFICATIONS_ELU`` et ``VERIFICATIONS_ELS``.
Le pipeline itère sur ces registres et appelle ``calculer()`` sur chacun.

Une vérification retourne un taux d'utilisation (rapport demande/capacité).
Convention : taux ≤ 1.0 → vérifié. taux > 1.0 → non vérifié.
Une vérification inactive (condition non remplie) retourne 0.0.

Extensibilité : enregistrer la nouvelle classe dans ``verifications/__init__.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ResultatVerification:
    """Résultat d'une vérification ELU ou ELS.

    Parameters
    ----------
    id_verification:
        Identifiant lisible (ex: "FlexionSimple", "FlecheInst").
    taux_LCM:
        Tableau ``(n_L, n_C, n_M)`` des taux d'utilisation.
        0.0 = vérification inactive pour cette combinaison/matériau.
    active_LCM:
        Masque booléen ``(n_L, n_C, n_M)`` — True si la vérification s'applique.
    """

    id_verification: str
    taux_LCM: np.ndarray
    active_LCM: np.ndarray


class VerificationELU(ABC):
    """Interface abstraite pour une vérification à l'État Limite Ultime.

    Chaque sous-classe implémente une formule EC5 (§6.x) et est enregistrée
    dans ``VERIFICATIONS_ELU``. Elle est appelée par ``pipeline.p3_elu``.
    """

    @property
    @abstractmethod
    def id_verification(self) -> str:
        """Identifiant unique de la vérification (ex: "FlexionSimple")."""

    @property
    @abstractmethod
    def article_ec5(self) -> str:
        """Référence normative (ex: "EC5 §6.1.6 Eq.(6.11)")."""

    @abstractmethod
    def calculer(self, espace: "EspaceCombinaisonTenseur") -> ResultatVerification:  # type: ignore[name-defined]
        """Calcule le taux d'utilisation pour tous les points du tenseur.

        Parameters
        ----------
        espace:
            Espace de combinaison tensoriel contenant toutes les sollicitations
            et résistances de calcul.

        Returns
        -------
        ResultatVerification
            Taux ``(n_L, n_C, n_M)`` + masque d'activation.
        """


class VerificationELS(ABC):
    """Interface abstraite pour une vérification à l'État Limite de Service.

    Chaque sous-classe implémente une formule EC5 (§7.x) et est enregistrée
    dans ``VERIFICATIONS_ELS``. Elle est appelée par ``pipeline.p4_els``.
    """

    @property
    @abstractmethod
    def id_verification(self) -> str:
        """Identifiant unique de la vérification (ex: "FlecheInst")."""

    @property
    @abstractmethod
    def article_ec5(self) -> str:
        """Référence normative (ex: "EC5 §7.2")."""

    @abstractmethod
    def calculer(self, espace: "EspaceCombinaisonTenseur") -> ResultatVerification:  # type: ignore[name-defined]
        """Calcule le taux de flèche pour tous les points du tenseur.

        Parameters
        ----------
        espace:
            Espace de combinaison tensoriel (combinaisons ELS uniquement).

        Returns
        -------
        ResultatVerification
            Taux ``(n_L, n_C_els, n_M)`` + masque d'activation.
        """
