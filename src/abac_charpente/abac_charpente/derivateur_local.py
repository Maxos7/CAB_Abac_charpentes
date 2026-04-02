"""Dérivation locale ConfigMatériau pour abac_charpente (T041 / EF-004).

Ce module fait le pont entre sapeg_regen_stock (ProduitValide) et abac_charpente.ec5
en construisant un ConfigMatériau complet avec toutes les propriétés mécaniques.

Aucun import métier EC5/EC0/EC1 interdit dans sapeg_regen_stock — la dérivation
mécanique se fait ici, du côté abac_charpente.
"""
from __future__ import annotations

from sapeg_regen_stock.modeles import ConfigMatériau, ProduitValide
from sapeg_regen_stock.derivateur import deriver_config_materiau
from abac_charpente.ec5.proprietes import get_proprietes, calculer_section


def deriver_materiau(produit: ProduitValide) -> ConfigMatériau:
    """Dérive un ConfigMatériau complet depuis un ProduitValide.

    Charge les propriétés mécaniques EN 338 / EN 14080, calcule les
    propriétés de section (A, I, W, I_z, W_z, poids propre) et
    construit le ConfigMatériau.

    Lève KeyError si la classe de résistance est inconnue.
    """
    proprietes = get_proprietes(produit.classe_resistance)
    section = calculer_section(produit.b_mm, produit.h_mm, proprietes["rho_k_kgm3"])
    return deriver_config_materiau(produit, proprietes, section)
