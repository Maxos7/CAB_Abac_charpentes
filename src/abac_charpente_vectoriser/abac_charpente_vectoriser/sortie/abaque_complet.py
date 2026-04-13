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
    combo_elu: dict[str, np.ndarray] | None = None,
    combo_els: dict[str, np.ndarray] | None = None,
) -> pd.DataFrame:
    """Construit le DataFrame de l'abaque complet sans l'écrire.

    Une ligne par couple (matériau × longueur). Contient tous les taux ELU et ELS,
    ainsi que la combinaison EC0 déterminante pour chaque vérification.

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
    combo_elu:
        Combinaisons ELU déterminantes ``{id_verif: (n_L, n_M)}`` de strings
        (ex. ``"ELU_STR_G+S"``). Ajoutées en colonne ``elu_<verif>_combo`` si fourni.
    combo_els:
        Combinaisons ELS déterminantes ``{id_verif: (n_L, n_M)}`` de strings
        (ex. ``"ELS_CAR_G+Q"``). Ajoutées en colonne ``els_<verif>_combo`` si fourni.

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
                if combo_elu is not None:
                    ligne[f"elu_{id_v}_combo"] = str(combo_elu[id_v][l_idx, m])
            for id_v, taux in taux_els.items():
                ligne[f"els_{id_v}"] = round(float(taux[l_idx, m]), 4)
                if combo_els is not None:
                    ligne[f"els_{id_v}_combo"] = str(combo_els[id_v][l_idx, m])

            tous_taux_items: dict[str, float] = {
                id_v: float(t[l_idx, m])
                for id_v, t in {**taux_elu, **taux_els}.items()
            }
            id_verif_win: str = max(tous_taux_items, key=tous_taux_items.__getitem__)
            taux_global_val: float = tous_taux_items[id_verif_win]

            tous_combos: dict[str, np.ndarray] = {
                **(combo_elu or {}), **(combo_els or {})
            }
            ligne["taux_global"] = round(taux_global_val, 4)
            ligne["verif_globale"] = id_verif_win
            ligne["combo_global"] = (
                str(tous_combos[id_verif_win][l_idx, m])
                if tous_combos and id_verif_win in tous_combos
                else ""
            )
            ligne["verifie"] = taux_global_val <= 1.0

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
