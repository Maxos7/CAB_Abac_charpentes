"""Filtrage configurable du stock enrichi (EF-003).

Fonction exportée :
    filtrer_stock(produits, filtre) -> tuple[list[ProduitValide], list[ProduitExclu]]
"""
from __future__ import annotations

import math

from loguru import logger

from sapeg_regen_stock.modeles import (
    ConfigFiltre,
    ProduitExclu,
    ProduitValide,
    RegleEgal,
    RegleListe,
    RegleNonNul,
    ReglePlage,
)


def filtrer_stock(
    produits: list[ProduitValide],
    filtre: ConfigFiltre,
) -> tuple[list[ProduitValide], list[ProduitExclu]]:
    """Applique les règles du filtre (logique ET) sur la liste de produits.

    Émet un AVERTISSEMENT sur stderr pour chaque produit exclu.
    Retourne (produits_retenus, produits_exclus).
    """
    retenus: list[ProduitValide] = []
    exclus: list[ProduitExclu] = []

    for produit in produits:
        regle_violee = _verifier_regles(produit, filtre)
        if regle_violee is None:
            retenus.append(produit)
        else:
            logger.warning(
                f"AVERTISSEMENT [filtre:{filtre.nom}] [{produit.id_produit}] : "
                f"règle {regle_violee} violée"
            )
            exclus.append(
                ProduitExclu(
                    id_produit=produit.id_produit,
                    ligne_csv=produit.ligne_csv_source,
                    raison=f"filtre '{filtre.nom}' : règle {regle_violee}",
                    regle_violee=regle_violee,
                )
            )

    if not retenus:
        logger.warning(f"Filtre '{filtre.nom}' : aucun produit retenu.")

    return retenus, exclus


def _valeur_champ(produit: ProduitValide, champ: str):
    """Retourne la valeur d'un champ du produit, ou None si inexistant."""
    return getattr(produit, champ, None)


def _verifier_regles(produit: ProduitValide, filtre: ConfigFiltre) -> str | None:
    """Vérifie toutes les règles (ET logique).

    Retourne la description de la première règle violée, ou None si tout passe.
    """
    for regle in filtre.regles:
        violation = _verifier_regle(produit, regle)
        if violation:
            return violation
    return None


def _verifier_regle(produit: ProduitValide, regle) -> str | None:
    """Retourne une description de la violation ou None si la règle est respectée."""
    val = _valeur_champ(produit, regle.champ)

    if isinstance(regle, RegleNonNul):
        if val is None or val == "" or (isinstance(val, float) and math.isnan(val)):
            return f"non_nul({regle.champ})"
        return None

    if isinstance(regle, RegleEgal):
        cible = regle.valeur
        if isinstance(val, str) and isinstance(cible, str):
            if val.strip().lower() != cible.strip().lower():
                return f"egal({regle.champ}={cible})"
        else:
            if val != cible:
                return f"egal({regle.champ}={cible})"
        return None

    if isinstance(regle, ReglePlage):
        if val is None:
            return f"plage({regle.champ}: valeur absente)"
        try:
            v = float(val)
        except (TypeError, ValueError):
            return f"plage({regle.champ}: non numérique)"
        if regle.min is not None and v < regle.min:
            return f"plage({regle.champ}>={regle.min})"
        if regle.max is not None and v > regle.max:
            return f"plage({regle.champ}<={regle.max})"
        return None

    if isinstance(regle, RegleListe):
        valeurs_norm = [
            str(v).strip().lower() if isinstance(v, str) else v
            for v in regle.valeurs
        ]
        val_norm = str(val).strip().lower() if isinstance(val, str) else val
        if val_norm not in valeurs_norm:
            return f"liste({regle.champ} ∈ {regle.valeurs})"
        return None

    return None  # type inconnu → laisser passer (sécurité permissive)
