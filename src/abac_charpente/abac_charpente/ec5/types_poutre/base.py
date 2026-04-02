"""Classe abstraite TypePoutre — Principe X + EF-019.

Hiérarchie OOP : toute extension DOIT hériter de TypePoutre.
Interdit : if/match type_poutre dans elu.py / els.py.

Notation française EC5 obligatoire (Principe IX).
Unités explicites dans les noms de variables (Principe VI).
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod

import numpy as np

from sapeg_regen_stock.modeles import ConfigMatériau
from abac_charpente.modeles.combinaison import CombinaisonEC0
from abac_charpente.modeles.config_calcul import ConfigCalcul


class TypePoutre(ABC):
    """Classe abstraite représentant un type de poutre bois (panne, solive, sommier, chevron…).

    Toutes les méthodes opèrent sur des tableaux numpy (vectorisation, Principe VI).
    Les sous-classes définissent la décomposition des charges selon leur géométrie propre.

    Notation :
        σ_m_d  : contrainte de flexion de calcul (MPa)
        f_m_d  : résistance de flexion de calcul (MPa)
        k_mod  : facteur de modification EC5 Tableau 3.1
        γ_M    : coefficient partiel matériau EC5 §2.4
        ψ₀     : coefficient de combinaison EN 1990 Tableau A1.1
        w_inst : flèche instantanée (mm)
    """

    @abstractmethod
    def charges_lineaires(
        self,
        config: ConfigCalcul,
        materiau: ConfigMatériau,
        longueurs_m: np.ndarray,
        combi: CombinaisonEC0,
    ) -> dict[str, np.ndarray]:
        """Calcule les charges linéaires de calcul (kN/m) pour chaque longueur.

        Retourne un dict contenant au minimum :
            'q_G_kNm'  : charge permanente (kN/m)
            'q_Q_kNm'  : charge variable d'exploitation (kN/m)
            'q_S_kNm'  : charge de neige (kN/m)
            'q_W_kNm'  : charge de vent (kN/m)
            'q_d_kNm'  : charge de calcul totale (kN/m) — combinaison EC0
            'M_d_kNm'  : moment de calcul (kN·m) — shape (n_longueurs,)
            'V_d_kN'   : effort tranchant de calcul (kN) — shape (n_longueurs,)

        Pour double flexion (EF-024) :
            'q_y_kNm'  : charge selon l'axe fort (kN/m)
            'q_z_kNm'  : charge selon l'axe faible (kN/m)
            'M_y_kNm'  : moment selon l'axe fort (kN·m)
            'M_z_kNm'  : moment selon l'axe faible (kN·m)
        """
        ...

    @abstractmethod
    def decomposer(
        self,
        charges_kNm: np.ndarray,
        pente_rad: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Décompose une charge linéaire selon les axes fort/faible de la poutre.

        Retourne (q_y_kNm, q_z_kNm) pour la double flexion.
        Pour les poutres sans double flexion, retourne (charges_kNm, zeros).

        Paramètres :
            charges_kNm : array de charges totales (kN/m)
            pente_rad   : angle de la pente en radians

        Retourne :
            q_y_kNm : composante selon l'axe fort (kN/m)
            q_z_kNm : composante selon l'axe faible (kN/m)
        """
        ...

    def longueur_deversement_m(
        self,
        longueur_m: float,
        entraxe_antideversement_mm: float,
    ) -> float:
        """Calcule la longueur de déversement selon EF-024.

        Règle :
            entraxe = 0              → L_dever = L (portée complète)
            L ≤ 2×entraxe           → L_dever = L / 2
            L > 2×entraxe           → L_dever = entraxe (en m)

        Paramètres :
            longueur_m                  : longueur de portée (m)
            entraxe_antideversement_mm  : entraxe des anti-déversements (mm)
        """
        if entraxe_antideversement_mm <= 0:
            return longueur_m
        a_m = entraxe_antideversement_mm / 1000.0
        if longueur_m <= 2 * a_m:
            return longueur_m / 2.0
        return a_m
