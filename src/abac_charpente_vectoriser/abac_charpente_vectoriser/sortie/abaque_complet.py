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
    valeur_elu: dict[str, np.ndarray] | None = None,
    valeur_els: dict[str, np.ndarray] | None = None,
) -> pd.DataFrame:
    """Construit le DataFrame de l'abaque complet sans l'écrire.

    Une ligne par couple (matériau × longueur). Contient tous les taux ELU et ELS,
    les combinaisons déterminantes, et les valeurs intermédiaires physiques (MPa / mm).

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
        Configuration de calcul.
    combo_elu:
        Combinaisons ELU déterminantes ``{id_verif: (n_L, n_M)}``.
        Colonne ``elu_<verif>_combo`` si fourni.
    combo_els:
        Combinaisons ELS déterminantes ``{id_verif: (n_L, n_M)}``.
        Colonne ``els_<verif>_combo`` si fourni.
    valeur_elu:
        Valeurs intermédiaires ELU ``{id_verif: (n_L, n_M)}`` (MPa ou —).
        Colonne ``elu_<verif>_val`` si fourni. Exclues de ``taux_global``.
    valeur_els:
        Valeurs intermédiaires ELS ``{id_verif: (n_L, n_M)}`` (mm).
        Colonne ``els_<verif>_val`` si fourni. Exclues de ``taux_global``.

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
                # ── Composantes de la configuration de calcul ──────────────────
                "type_poutre": config.type_poutre,
                "usage": config.usage,
                "pente_deg": config.pente_deg,
                "entraxe_m": config.entraxe_m,
                "classe_service": config.classe_service,
                # Charges brutes surfaciques (kN/m²)
                "g_k_kNm2": config.g_k_kNm2,
                "g2_k_kNm2": config.g2_k_kNm2,
                "q_k_kNm2": config.q_k_kNm2,
                "categorie_q": config.categorie_q,
                "s_k_kNm2": config.s_k_kNm2,
                "w_k_kNm2": config.w_k_kNm2,
                # ── Article ────────────────────────────────────────────────────
                "id_produit": mat.id_produit,
                "libelle": mat.libelle,
                "essence": mat.essence,
                "id_config_materiau": mat.id_config_materiau,
                "classe_resistance": mat.classe_resistance,
                "b_mm": mat.b_mm,
                "h_mm": mat.h_mm,
                "longueur_m": round(float(longueurs_m[l_idx]), 3),
            }
            # Vérifications adimensionnelles (k_crit, k_c_y, k_c_z)
            _ELU_ADIM: frozenset[str] = frozenset({"k_crit", "k_c_y", "k_c_z"})

            # Taux ELU + combis + valeurs intermédiaires
            for id_v, taux in taux_elu.items():
                ligne[f"elu_{id_v}"] = round(float(taux[l_idx, m]), 4)
                if combo_elu is not None:
                    ligne[f"elu_{id_v}_combi"] = str(combo_elu[id_v][l_idx, m])
                if valeur_elu is not None and id_v in valeur_elu:
                    unite = "adim" if id_v in _ELU_ADIM else "MPa"
                    ligne[f"elu_{id_v}_val_{unite}"] = round(float(valeur_elu[id_v][l_idx, m]), 4)

            # Taux ELS + combis + valeurs intermédiaires
            for id_v, taux in taux_els.items():
                ligne[f"els_{id_v}"] = round(float(taux[l_idx, m]), 4)
                if combo_els is not None and id_v in combo_els:
                    ligne[f"els_{id_v}_combi"] = str(combo_els[id_v][l_idx, m])
                if valeur_els is not None and id_v in valeur_els:
                    ligne[f"els_{id_v}_val_mm"] = round(float(valeur_els[id_v][l_idx, m]), 4)

            # taux_global = max des taux uniquement (exclut les colonnes _val)
            tous_ids: list[str] = list({**taux_elu, **taux_els}.keys())
            tous: list[float] = [
                float(t[l_idx, m]) for t in {**taux_elu, **taux_els}.values()
            ]
            taux_max: float = max(tous)
            ligne["taux_global"] = round(taux_max, 4)
            ligne["verifie"] = taux_max <= 1.0
            ligne["verifie_raison"] = tous_ids[tous.index(taux_max)]

            lignes.append(ligne)

    return pd.DataFrame(lignes)


def renommer_cols_elu_els(df: pd.DataFrame) -> pd.DataFrame:
    """Renomme les colonnes ``elu_*``/``els_*`` → ``*_[elu]``/``*_[els]`` pour l'export CSV.

    Exemple : ``elu_FlexionAxeFort_val_MPa`` → ``FlexionAxeFort_val_MPa_[elu]``.
    Les colonnes sans préfixe ``elu_``/``els_`` ne sont pas modifiées.
    """
    renaming: dict[str, str] = {}
    for col in df.columns:
        if col.startswith("elu_"):
            renaming[col] = col[4:] + "_[elu]"
        elif col.startswith("els_"):
            renaming[col] = col[4:] + "_[els]"
    return df.rename(columns=renaming) if renaming else df


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
    renommer_cols_elu_els(df).to_csv(chemin_sortie, sep=";", index=False, encoding="utf-8-sig")
