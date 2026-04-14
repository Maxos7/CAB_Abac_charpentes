"""
protocoles.type_poutre
======================
Classe de base abstraite pour tous les types de poutres du pipeline vectorisé.

Principe : aucun ``if/match`` sur le type de poutre dans les modules ELU/ELS.
Tout le comportement spécifique (décomposition des charges, longueur de
déversement, effort normal, etc.) est encapsulé dans les sous-classes concrètes
via surcharge de méthodes. Le pipeline appelle uniquement l'interface définie ici.

Extensibilité : pour ajouter un nouveau type de poutre, créer une sous-classe
de ``TypePoutreVect`` et l'enregistrer dans ``types_poutre.TYPES_POUTRE``.
Aucune modification des modules pipeline ou vérifications n'est requise.
"""

from __future__ import annotations

import math
from abc import ABC

import numpy as np

from ..modeles.config_calcul import ConfigCalculVect
from ..modeles.config_materiau import ConfigMatériauVect


class TypePoutreVect(ABC):
    """Interface abstraite d'un type de poutre pour le pipeline tensoriel.

    Chaque méthode reçoit les paramètres nécessaires à sa computation et retourne
    des tableaux numpy compatibles avec le broadcast ``(n_L, n_C, n_M)``.

    La convention d'axes est :
    - Axe 0 : longueurs (n_L)
    - Axe 1 : combinaisons EC0 (n_C)
    - Axe 2 : matériaux / configurations (n_M)

    Parameters
    ----------
    config:
        Configuration de calcul pour cette instance (scalaires — après développement
        du produit cartésien par le moteur).
    """

    _DOUBLE_FLEXION: bool | None = None

    def __init__(self, config: ConfigCalculVect) -> None:
        self._config = config

    @property
    def config(self) -> ConfigCalculVect:
        """Configuration de calcul associée."""
        return self._config

    @property
    def double_flexion_active(self) -> bool:
        """True si les vérifications de double flexion doivent être appliquées.

        Si ``_DOUBLE_FLEXION`` est défini sur la classe, retourne cette constante.
        Sinon : valeur du champ ``config.double_flexion``.
        """
        if self._DOUBLE_FLEXION is not None:
            return self._DOUBLE_FLEXION
        return self._config.double_flexion

    def decomposer_charges(
        self,
        q_d_kNm: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Décompose la charge linéique pondérée selon les axes de la section.

        Comportement par défaut : toute la charge va sur l'axe fort y, pas de
        composante z. Convient aux poutres horizontales (Solive, Sommier) et au
        Chevron (charges déjà projetées ⊥ au rampant en amont).
        Les pannes (PanneAplombVect, PanneDeverseeVect) surchargent cette méthode
        pour effectuer la décomposition biaxiale.

        Parameters
        ----------
        q_d_kNm:
            Charge linéique de calcul totale en kN/m — tableau ``(n_L, n_C, n_M)``
            ou scalaire broadcastable.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            ``(q_y_kNm, q_z_kNm)`` — composantes selon l'axe fort y et l'axe
            faible z, de même forme que ``q_d_kNm``.
        """
        return q_d_kNm, np.zeros_like(q_d_kNm)

    def longueur_deversement_m(
        self,
        longueurs_m: np.ndarray,
    ) -> np.ndarray:
        """Calcule la longueur de déversement effective en mètres — EC5 §6.3.3.

        Comportement par défaut (tous les types de poutres) :
        - ``entraxe_antideversement_mm = 0``  →  l_ef = L (portée complète)
        - ``L ≤ 2 × e_andev``                 →  l_ef = L / 2
        - Sinon                               →  l_ef = entraxe_antideversement_mm / 1000

        Parameters
        ----------
        longueurs_m:
            Vecteur de portées en mètres ``(n_L,)``.

        Returns
        -------
        np.ndarray
            Longueurs de déversement ``(n_L,)`` en mètres.
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
        """Retourne la longueur projetée horizontale en mètres, ou None.

        Comportement par défaut : ``None`` — la pièce n'est pas en pente ou la
        portée de calcul est déjà la portée horizontale.
        Seul ``ChevronVect`` surcharge cette méthode pour retourner la projection
        ``longueurs_m × cos(α)``.

        Parameters
        ----------
        longueurs_m:
            Vecteur de portées en mètres ``(n_L,)`` (longueur du rampant).

        Returns
        -------
        np.ndarray | None
            Portée horizontale projetée ``(n_L,)``, ou ``None`` si non applicable.
        """
        return None

    def effort_normal_kN(
        self,
        longueurs_m: np.ndarray,
        n_C: int,
        n_M: int,
    ) -> np.ndarray | None:
        """Retourne l'effort normal de calcul N_d en kN, ou None.

        Par défaut : None (pas d'effort normal — cas des poutres simples).
        Surcharger dans les sous-classes modélisant des barres de treillis
        (Arbaletrier, Entrait) ou des pièces soumises à un effort axial.

        Parameters
        ----------
        longueurs_m:
            Vecteur de portées ``(n_L,)``.
        n_C:
            Nombre de combinaisons EC0.
        n_M:
            Nombre de matériaux.

        Returns
        -------
        np.ndarray | None
            Tableau ``(n_L, n_C, n_M)`` ou ``None``.
        """
        return None

    def poids_propre_kNm(self, materiaux: list[ConfigMatériauVect]) -> np.ndarray:
        """Calcule la charge linéique de poids propre caractéristique en kN/m.

        Formule : ``g_pp = ρ_k × g × A × entraxe / 1e6``
        où ρ_k est en kg/m³, A en cm², g = 9.81 m/s², résultat en kN/m.

        Adapté pour chaque matériau (axe n_M). Pour les pièces inclinées,
        la charge est exprimée par mètre de portée mesurée (rampant).

        Parameters
        ----------
        materiaux:
            Liste des configurations matériau ``(n_M,)``.

        Returns
        -------
        np.ndarray
            Vecteur ``(n_M,)`` de charges de poids propre en kN/m.
        """
        rho_k: np.ndarray = np.array([m.rho_k_kgm3 for m in materiaux], dtype=float)
        A_m2: np.ndarray = np.array(
            [m.A_cm2 * 1e-4 for m in materiaux], dtype=float
        )  # cm² → m²
        return rho_k * 9.81e-3 * A_m2  # kN/m


class TypePoutreInclineeVect(TypePoutreVect):
    """Classe intermédiaire abstraite pour les poutres posées sur un rampant incliné.

    Factorise l'extraction de l'angle de pente ``_pente_rad`` depuis
    ``config.pente_deg``. Héritée par :
    - ``ChevronVect``      — portée sur rampant, charges ⊥ au rampant
    - ``PanneDeverseeVect`` — section ⊥ au rampant, double flexion optionnelle
    - ``PanneAplombVect``  — section verticale, double flexion intrinsèque
    """

    def __init__(self, config: ConfigCalculVect) -> None:
        super().__init__(config)
        pente_deg: float = float(
            config.pente_deg[0]
            if isinstance(config.pente_deg, list)
            else config.pente_deg
        )
        self._pente_rad: float = math.radians(pente_deg)


class PoutreHorizontaleVect(TypePoutreVect):
    """Classe intermédiaire abstraite pour les poutres horizontales (pente nulle).

    La double flexion est toujours inactive — toute la charge va sur l'axe fort y.
    Héritée par SoliveVect et SommierVect.
    """

    _DOUBLE_FLEXION = False
