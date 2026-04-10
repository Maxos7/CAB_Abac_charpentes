"""
sortie.vues
===========
Moteur d'application des vues de sortie depuis ``abaque_complet_global.csv``.

Chaque vue est définie dans un fichier TOML externe (``configs_sortie_vect.toml``).
Elle produit un fichier CSV dérivé selon deux types :

- ``agregation`` : longueur maximale admissible par groupe.
  Les champs ``groupby`` et ``colonnes`` sont déclarés dans le TOML.
  La vérification déterminante et le taux déterminant sont calculés automatiquement.
- ``filtre``     : sélection de lignes + colonnes sans agrégation.
  Utile pour isoler une classe, une config ou une plage de portées.

Les filtres s'appliquent avant l'agrégation ou la sélection (AND logic).

Usage standalone (après un run CLI) :
    from pathlib import Path
    import pandas as pd
    from abac_charpente_vectoriser.sortie.vues import appliquer_vues_depuis_toml

    df = pd.read_csv("resultats/abaque_complet_global.csv", sep=";")
    appliquer_vues_depuis_toml(df, Path("configs_sortie_vect.toml"), Path("resultats"))
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


def _lire_toml(chemin: Path) -> dict:
    """Lit un fichier TOML. Compatible Python 3.11+ (tomllib stdlib) et 3.10 (tomli)."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
    with open(chemin, "rb") as f:
        return tomllib.load(f)


# ── Filtrage ──────────────────────────────────────────────────────────────────

def _appliquer_filtres(df: pd.DataFrame, filtres: list[dict]) -> pd.DataFrame:
    """Applique une liste de filtres (AND logic) sur le DataFrame.

    Chaque filtre est un dict avec les clés ``champ``, ``operateur``, ``valeur``.

    Opérateurs supportés
    --------------------
    egal, different, inferieur, superieur, inferieur_egal, superieur_egal,
    contient (sous-chaîne, insensible à la casse), in (liste de valeurs).

    Parameters
    ----------
    df:
        DataFrame source.
    filtres:
        Liste de dicts décrivant les filtres (issus du TOML).

    Returns
    -------
    pd.DataFrame
        Sous-ensemble filtré (copie).
    """
    masque: pd.Series = pd.Series(True, index=df.index)
    for f in filtres:
        champ: str = f["champ"]
        op: str = f["operateur"]
        valeur = f["valeur"]

        if champ not in df.columns:
            continue

        col: pd.Series = df[champ]

        if op == "egal":
            masque &= col == valeur
        elif op == "different":
            masque &= col != valeur
        elif op == "inferieur":
            masque &= col < valeur
        elif op == "superieur":
            masque &= col > valeur
        elif op == "inferieur_egal":
            masque &= col <= valeur
        elif op == "superieur_egal":
            masque &= col >= valeur
        elif op == "contient":
            masque &= col.astype(str).str.contains(str(valeur), case=False, na=False)
        elif op == "in":
            valeur_list: list = valeur if isinstance(valeur, list) else [valeur]
            masque &= col.isin(valeur_list)
        else:
            raise ValueError(
                f"Opérateur de filtre inconnu : '{op}'. "
                f"Disponibles : egal, different, inferieur, superieur, "
                f"inferieur_egal, superieur_egal, contient, in"
            )

    return df[masque].copy()


# ── Agrégation ────────────────────────────────────────────────────────────────

def _produire_agregation(
    df: pd.DataFrame,
    groupby: list[str],
    colonnes: list[str],
    trier_par: list[str],
) -> pd.DataFrame:
    """Longueur maximale admissible par groupe, avec vérification déterminante.

    Pour chaque groupe défini par ``groupby``, trouve la ligne avec la plus grande
    ``longueur_m`` où ``verifie == True``. Calcule automatiquement :
    - ``longueur_max_admissible_m`` : portée max vérifiée
    - ``verif_determinante``        : vérification elu_*/els_* au taux le plus élevé
    - ``taux_determinant``          : valeur de ce taux

    Parameters
    ----------
    df:
        DataFrame complet (filtré au préalable si nécessaire).
    groupby:
        Colonnes de regroupement (déclarées dans le TOML).
    colonnes:
        Colonnes à retenir dans la sortie (déclarées dans le TOML).
        Liste vide = toutes les colonnes disponibles après agrégation.
    trier_par:
        Colonnes de tri de la sortie (déclarées dans le TOML).

    Returns
    -------
    pd.DataFrame
        Une ligne par groupe. Si aucune portée n'est vérifiée pour un groupe,
        la ligne est exclue.
    """
    taux_cols: list[str] = [c for c in df.columns if c.startswith(("elu_", "els_"))]

    df_ok: pd.DataFrame = df[df["verifie"]].copy() if "verifie" in df.columns else df.copy()
    if df_ok.empty:
        return pd.DataFrame()

    idx: pd.Series = df_ok.groupby(groupby)["longueur_m"].idxmax()
    df_max: pd.DataFrame = df_ok.loc[idx].copy()

    if taux_cols:
        df_max["verif_determinante"] = (
            df_max[taux_cols].idxmax(axis=1)
            .str.replace(r"^(elu_|els_)", "", regex=True)
        )
        df_max["taux_determinant"] = df_max[taux_cols].max(axis=1).round(4)

    df_max = df_max.rename(columns={"longueur_m": "longueur_max_admissible_m"})
    df_max = df_max.reset_index(drop=True)

    if trier_par:
        trier_valides: list[str] = [c for c in trier_par if c in df_max.columns]
        if trier_valides:
            df_max = df_max.sort_values(trier_valides).reset_index(drop=True)

    if colonnes:
        cols_valides: list[str] = [c for c in colonnes if c in df_max.columns]
        return df_max[cols_valides]

    return df_max


# ── Filtre brut ────────────────────────────────────────────────────────────────

def _produire_filtre(
    df: pd.DataFrame,
    colonnes: list[str],
    trier_par: list[str],
) -> pd.DataFrame:
    """Sélection de colonnes + tri, sans agrégation.

    Parameters
    ----------
    df:
        DataFrame filtré.
    colonnes:
        Colonnes à retenir. Liste vide = toutes les colonnes.
    trier_par:
        Colonnes de tri.

    Returns
    -------
    pd.DataFrame
        Sous-ensemble trié.
    """
    if colonnes:
        cols_valides: list[str] = [c for c in colonnes if c in df.columns]
        df_out: pd.DataFrame = df[cols_valides].copy()
    else:
        df_out = df.copy()

    if trier_par:
        trier_valides: list[str] = [c for c in trier_par if c in df_out.columns]
        if trier_valides:
            df_out = df_out.sort_values(trier_valides)

    return df_out.reset_index(drop=True)


# ── Point d'entrée public ─────────────────────────────────────────────────────

def appliquer_vues_depuis_toml(
    df_complet: pd.DataFrame,
    chemin_toml: Path,
    chemin_sortie: Path,
) -> dict[str, Path]:
    """Applique toutes les vues définies dans le TOML et écrit les CSV.

    Parameters
    ----------
    df_complet:
        DataFrame complet issu de ``construire_df_complet`` (global).
    chemin_toml:
        Chemin vers ``configs_sortie_vect.toml``.
    chemin_sortie:
        Répertoire de sortie des CSV produits.

    Returns
    -------
    dict[str, Path]
        ``{nom_vue: chemin_csv}`` pour chaque vue produite.
    """
    from loguru import logger

    toml_data: dict = _lire_toml(chemin_toml)
    vues: list[dict] = toml_data.get("vue", [])
    chemin_sortie.mkdir(parents=True, exist_ok=True)

    produits: dict[str, Path] = {}

    for vue in vues:
        nom: str = vue.get("nom", "sans_nom")
        type_vue: str = vue.get("type", "filtre")
        fichier: str = vue.get("fichier_sortie", f"{nom}.csv")
        filtres_raw: list[dict] = vue.get("filtres", [])
        colonnes: list[str] = vue.get("colonnes", [])
        trier_par: list[str] = vue.get("trier_par", [])

        logger.info(f"Vue '{nom}' ({type_vue}) → {fichier}")

        # Filtrage commun (avant agrégation ou sélection)
        df_filtre: pd.DataFrame = _appliquer_filtres(df_complet, filtres_raw)

        if df_filtre.empty:
            logger.warning(f"  Vue '{nom}' : DataFrame vide après filtres — fichier non produit")
            continue

        if type_vue == "agregation":
            groupby: list[str] = vue.get("groupby", [])
            if not groupby:
                raise ValueError(
                    f"Vue '{nom}' de type 'agregation' : "
                    f"le champ 'groupby' est obligatoire dans le TOML."
                )
            df_vue: pd.DataFrame = _produire_agregation(df_filtre, groupby, colonnes, trier_par)

        elif type_vue == "filtre":
            df_vue = _produire_filtre(df_filtre, colonnes, trier_par)

        else:
            raise ValueError(
                f"Type de vue inconnu : '{type_vue}'. "
                f"Disponibles : agregation, filtre"
            )

        chemin_csv: Path = chemin_sortie / fichier
        df_vue.to_csv(chemin_csv, sep=";", index=False, encoding="utf-8-sig")
        logger.info(f"  → {len(df_vue)} lignes écrites dans {chemin_csv}")
        produits[nom] = chemin_csv

    return produits
