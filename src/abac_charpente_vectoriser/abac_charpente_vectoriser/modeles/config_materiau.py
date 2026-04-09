"""
modeles.config_materiau
=======================
Données matériau + section pour un matériau donné.

Les propriétés de section (A, I, W) peuvent être calculées depuis b/h (section
rectangulaire) ou fournies directement pour les sections non-rectangulaires.
Les unités suivent la convention du package : suffixe _mm, _cm2, _cm4, _MPa, etc.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigMatériauVect:
    """Propriétés caractéristiques d'un matériau bois avec sa section.

    Tous les champs géométriques sont en mm ou cm selon la convention indiquée.
    Les champs de résistance sont en MPa (= N/mm²).
    Les champs de rigidité (module E) sont en MPa.

    Parameters
    ----------
    id_config_materiau:
        Identifiant unique de la configuration matériau (ex: "C24_63x175").
    classe_resistance:
        Classe de résistance EN 338 ou EN 14080 (ex: "C24", "GL28h").
    famille:
        Famille de produit pour lookup kmod/kdef/gamma_M
        ("bois_massif", "bois_lamelle_colle", "bois_reconstitue").
    b_mm:
        Largeur de la section en mm. None si section personnalisée.
    h_mm:
        Hauteur de la section en mm (axe fort = y). None si section personnalisée.
    A_cm2:
        Aire de la section en cm². Calculée par le derivateur ou fournie.
    I_y_cm4:
        Moment quadratique axe fort y en cm⁴.
    I_z_cm4:
        Moment quadratique axe faible z en cm⁴.
    W_y_cm3:
        Module résistant axe fort y en cm³.
    W_z_cm3:
        Module résistant axe faible z en cm³.
    A_eff_cisaillement_cm2:
        Section efficace pour le cisaillement en cm² (EC5 §6.1.7).
        Pour une section rectangulaire : A × k_cr = b×h × 0.67.
    f_m_k_MPa:
        Résistance caractéristique en flexion (EN 338 / EN 14080).
    f_v_k_MPa:
        Résistance caractéristique en cisaillement.
    f_c90_k_MPa:
        Résistance caractéristique en compression perpendiculaire au fil.
    f_t0_k_MPa:
        Résistance caractéristique en traction parallèle au fil (EN 338 Table 1).
    f_c0_k_MPa:
        Résistance caractéristique en compression parallèle au fil (EN 338 Table 1).
    E_0_mean_MPa:
        Module d'élasticité moyen parallèle au fil (ELS).
    E_0_05_MPa:
        Module d'élasticité caractéristique à 5 % (ELU déversement).
    rho_k_kgm3:
        Masse volumique caractéristique en kg/m³ (poids propre).
    """

    id_config_materiau: str
    classe_resistance: str
    famille: str

    # Géométrie brute (None si section personnalisée)
    b_mm: float | None
    h_mm: float | None

    # Propriétés de section calculées — toujours renseignées
    A_cm2: float
    I_y_cm4: float
    I_z_cm4: float
    W_y_cm3: float
    W_z_cm3: float
    A_eff_cisaillement_cm2: float

    # Résistances caractéristiques [MPa]
    f_m_k_MPa: float
    f_v_k_MPa: float
    f_c90_k_MPa: float
    f_t0_k_MPa: float
    f_c0_k_MPa: float

    # Rigidité [MPa]
    E_0_mean_MPa: float
    E_0_05_MPa: float

    # Masse volumique [kg/m³]
    rho_k_kgm3: float
