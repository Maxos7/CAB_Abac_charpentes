"""
ec1.vent
========
Calcul de la charge de vent linéique sur une poutre — EN 1991-1-4 (AN France).

Le coefficient de pression extérieure c_pe est lu depuis ``donnees/ec1_cpe_vent.csv``.
Simplification AN France : c_pe global par type de toiture (pression = 0.8).
La pression de référence ``w_k`` est fournie dans la config (en kN/m²).
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

import pandas as pd


@lru_cache(maxsize=1)
def _charger_cpe_table() -> dict[str, float]:
    """Charge les coefficients c_pe depuis le CSV normatif.

    Returns
    -------
    dict[str, float]
        Dictionnaire ``{type_toiture: c_pe}``.
    """
    chemin_csv = files("abac_charpente_vectoriser.donnees").joinpath("ec1_cpe_vent.csv")
    df = pd.read_csv(str(chemin_csv), sep=";", comment="#")
    return dict(zip(df["type_toiture"], df["c_pe"]))


def c_pe(type_toiture: str) -> float:
    """Coefficient de pression extérieure c_pe — AN France.

    Parameters
    ----------
    type_toiture:
        Type de toiture ("1_pan", "2_pans", "terrasse").

    Returns
    -------
    float
        Coefficient c_pe (valeur absolue — toujours positif pour pression).

    Raises
    ------
    KeyError
        Si ``type_toiture`` n'est pas dans la table normative.
    """
    table = _charger_cpe_table()
    if type_toiture not in table:
        raise KeyError(
            f"type_toiture '{type_toiture}' non trouvé dans ec1_cpe_vent.csv. "
            f"Valeurs disponibles : {list(table.keys())}"
        )
    return table[type_toiture]


def charge_vent_kNm(
    w_k_kNm2: float,
    type_toiture: str,
    entraxe_m: float,
) -> float:
    """Charge linéique caractéristique de vent sur une poutre — EN 1991-1-4.

    q_w_kNm = |w_k × c_pe × entraxe|   [kN/m linéaire]

    La valeur absolue est retournée — la direction du vent (pression/dépression)
    est gérée par les combinaisons EC0 (le vent est toujours pris en pression
    dans la simplification AN France).

    Parameters
    ----------
    w_k_kNm2:
        Pression de référence de vent en kN/m².
    type_toiture:
        Type de toiture pour sélection de c_pe.
    entraxe_m:
        Entraxe entre poutres en mètres.

    Returns
    -------
    float
        Charge linéique caractéristique de vent en kN/m.
    """
    return abs(w_k_kNm2 * c_pe(type_toiture) * entraxe_m)
