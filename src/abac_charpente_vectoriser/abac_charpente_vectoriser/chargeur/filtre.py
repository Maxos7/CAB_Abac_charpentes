"""
chargeur.filtre
===============
Application des règles de filtrage sur une liste de ``ConfigMatériauVect``.

Les règles sont définies dans ``ConfigCalculVect.filtres`` (liste de ``RegleFiltre``).
La logique est un ET entre toutes les règles : un matériau est retenu uniquement
s'il satisfait **toutes** les règles de la configuration.

Opérateurs supportés : ``==``, ``!=``, ``in``, ``>=``, ``<=``, ``>``, ``<``.
"""

from __future__ import annotations

from ..modeles.config_calcul import RegleFiltre
from ..modeles.config_materiau import ConfigMatériauVect


def appliquer_filtres(
    materiaux: list[ConfigMatériauVect],
    filtres: list[RegleFiltre],
) -> list[ConfigMatériauVect]:
    """Filtre une liste de matériaux selon les règles de la configuration.

    Applique un ET logique entre toutes les règles. Un matériau est retenu
    si et seulement s'il satisfait toutes les règles.

    Parameters
    ----------
    materiaux:
        Liste de configurations matériau à filtrer.
    filtres:
        Liste de règles de filtrage (peut être vide → tous les matériaux retenus).

    Returns
    -------
    list[ConfigMatériauVect]
        Sous-liste des matériaux satisfaisant toutes les règles.

    Raises
    ------
    AttributeError
        Si une règle référence un champ inexistant dans ``ConfigMatériauVect``.
    ValueError
        Si l'opérateur d'une règle n'est pas supporté (normalement impossible
        grâce à la validation Pydantic de ``RegleFiltre``).
    """
    if not filtres:
        return list(materiaux)

    retenus: list[ConfigMatériauVect] = []
    for mat in materiaux:
        if _satisfait_toutes(mat, filtres):
            retenus.append(mat)
    return retenus


def _satisfait_toutes(mat: ConfigMatériauVect, filtres: list[RegleFiltre]) -> bool:
    """Vérifie si un matériau satisfait toutes les règles (ET logique)."""
    return all(_satisfait_regle(mat, regle) for regle in filtres)


def _satisfait_regle(mat: ConfigMatériauVect, regle: RegleFiltre) -> bool:
    """Vérifie si un matériau satisfait une règle de filtrage.

    Parameters
    ----------
    mat:
        Configuration matériau à tester.
    regle:
        Règle de filtrage à appliquer.

    Returns
    -------
    bool
        True si le matériau satisfait la règle.
    """
    valeur_mat: float | int | str | None = getattr(mat, regle.champ)
    ref: float | int | str | list[float | int | str] = regle.valeur
    op: str = regle.operateur

    if op == "==":
        return valeur_mat == ref
    if op == "!=":
        return valeur_mat != ref
    if op == "in":
        return valeur_mat in ref  # type: ignore[operator]
    if op == ">=":
        return valeur_mat >= ref  # type: ignore[operator]
    if op == "<=":
        return valeur_mat <= ref  # type: ignore[operator]
    if op == ">":
        return valeur_mat > ref   # type: ignore[operator]
    if op == "<":
        return valeur_mat < ref   # type: ignore[operator]

    raise ValueError(f"Opérateur non supporté : '{op}'")
