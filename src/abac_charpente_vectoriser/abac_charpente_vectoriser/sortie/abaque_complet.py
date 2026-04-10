"""
sortie.abaque_complet
=====================
Export CSV complet — une ligne par couple (matériau, longueur).

Colonnes : identifiants + longueur + tous les taux ELU + tous les taux ELS.
Usage : analyse détaillée par vérification, tracé de courbes taux = f(L).

Le fichier global est écrit une seule fois en fin de pipeline (toutes configs
confondues) dans ``abaque_complet_global.csv``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..modeles.config_calcul import ConfigCalculVect
from ..modeles.config_materiau import ConfigMatériauVect


def construire_df_complet(
    longueurs_m: np.ndarray,
    taux_elu: dict[str, np.ndarray],
    taux_els: dict[str, np.ndarray],
    materiaux: list[ConfigMatériauVect],
    config: ConfigCalculVect,
) -> pd.DataFrame:
    """Construit le DataFrame de l'abaque complet sans l'écrire.

    Une ligne par couple (matériau × longueur). Contient tous les taux ELU et ELS.

    Parameters
    ----------
    longueurs_m:
        Vecteur de portées ``(n_L,)``.
    taux_elu:
        Résultats ELU ``{id_verif: (n_L, n_M)}``.
    taux_els:
        Résultats ELS ``{id_verif: (n_L, n_M)}``.
    materiaux:
        Liste des configurations matériau ``(n_M,)``.
    config:
        Configuration de calcul (``id_config_calcul`` doit être l'ID unique du combo).

    Returns
    -------
    pd.DataFrame
        DataFrame prêt pour concaténation ou export.
    """
    n_L: int = len(longueurs_m)
    lignes: list[dict] = []

    for m, mat in enumerate(materiaux):
        for l_idx in range(n_L):
            ligne: dict = {
                "id_config_calcul": config.id_config_calcul,
                "id_produit": mat.id_produit,
                "libelle": mat.libelle,
                "id_config_materiau": mat.id_config_materiau,
                "classe_resistance": mat.classe_resistance,
                "b_mm": mat.b_mm,
                "h_mm": mat.h_mm,
                "longueur_m": round(float(longueurs_m[l_idx]), 3),
            }
            for id_v, taux in taux_elu.items():
                ligne[f"elu_{id_v}"] = round(float(taux[l_idx, m]), 4)
            for id_v, taux in taux_els.items():
                ligne[f"els_{id_v}"] = round(float(taux[l_idx, m]), 4)

            tous: list[float] = [float(t[l_idx, m]) for t in {**taux_elu, **taux_els}.values()]
            ligne["taux_global"] = round(max(tous), 4)
            ligne["verifie"] = max(tous) <= 1.0

            lignes.append(ligne)

    return pd.DataFrame(lignes)


def exporter_abaque_complet(
    df: pd.DataFrame,
    chemin_sortie: Path,
) -> None:
    """Écrit le DataFrame de l'abaque complet en CSV.

    Parameters
    ----------
    df:
        DataFrame issu de ``construire_df_complet`` (une ou plusieurs configs).
    chemin_sortie:
        Chemin du fichier CSV de sortie (écrasé à chaque appel).
    """
    chemin_sortie.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(chemin_sortie, sep=";", index=False, encoding="utf-8-sig")
