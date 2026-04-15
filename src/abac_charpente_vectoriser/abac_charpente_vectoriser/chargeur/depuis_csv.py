"""
chargeur.depuis_csv
===================
Chargement des matériaux depuis un fichier CSV stock.

Le CSV doit au minimum contenir les colonnes ``b_mm``, ``h_mm`` et
``classe_resistance`` (ou leurs équivalents déclarés dans ``mappage_colonnes``).
Les propriétés mécaniques sont jointes vectoriellement depuis
``donnees/materiaux_bois.csv`` sur ``classe_resistance``.
Les propriétés de section sont calculées vectoriellement selon la forme de
chaque ligne (rectangle | rond | custom), pilotée par une colonne du CSV.

Toute la configuration d'ingestion est pilotée depuis ``configs_entree_vect.toml`` :
mappage colonnes, filtrage, forme de section.

``id_config_materiau`` n'est jamais lu depuis le CSV ; il est auto-généré par
``ConfigMatériauVect.__post_init__``.
"""

from __future__ import annotations

import math
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

import numpy as np
import pandas as pd

from ..modeles.config_materiau import ConfigMatériauVect
from ..modeles.type_section import TypeSection


@lru_cache(maxsize=1)
def _charger_materiaux_bois() -> pd.DataFrame:
    """Charge la table des propriétés mécaniques depuis donnees/materiaux_bois.csv."""
    chemin: str = str(
        files("abac_charpente_vectoriser.donnees").joinpath("materiaux_bois.csv")
    )
    return pd.read_csv(chemin, sep=";", comment="#")


@lru_cache(maxsize=1)
def _k_cr() -> float:
    """Lit le facteur k_cr depuis params_ec5.csv — EC5 §6.1.7(2)."""
    chemin: str = str(
        files("abac_charpente_vectoriser.donnees").joinpath("params_ec5.csv")
    )
    df: pd.DataFrame = pd.read_csv(chemin, sep=";", comment="#")
    return float(df.set_index("parametre").loc["k_cr", "valeur"])


def charger_depuis_csv(
    chemin_stock: Path,
    separateur: str = ";",
    mappage_colonnes: dict[str, str] | None = None,
    filtrage_colonne: str | None = None,
    filtrage_valeur: str | None = None,
    section_colonne_forme: str | None = None,
    section_colonne_diametre: str | None = None,
) -> list[ConfigMatériauVect]:
    """Charge une liste de configurations matériau depuis un CSV stock.

    Le CSV stock doit contenir au minimum (noms internes, ou équivalents via
    ``mappage_colonnes``) :

    - ``b_mm``              : largeur de la section en mm
    - ``h_mm``              : hauteur de la section en mm
    - ``classe_resistance`` : classe EN 338 / EN 14080 (ex: "C24", "GL28h")

    Colonnes de forme de section (optionnelles) :

    - ``forme_section``       : "rectangle" (défaut) | "rond" | "custom"
    - ``d_mm``                : diamètre [mm] pour sections rondes

    Colonnes pour sections custom (optionnelles — fallback formule rectangulaire) :

    - ``A_cm2``, ``I_y_cm4``, ``I_z_cm4``, ``W_y_cm3``, ``W_z_cm3``
    - ``A_eff_cisaillement_cm2``

    Colonnes propagées jusqu'aux CSV de sortie :

    - ``id_produit``   : code article SAPEG
    - ``libelle``      : désignation commerciale

    Filtrage et mappage entièrement pilotés depuis ``configs_entree_vect.toml``.
    ``id_config_materiau`` jamais lu — toujours généré par ``__post_init__``.

    Parameters
    ----------
    chemin_stock:
        Chemin vers le fichier CSV stock.
    separateur:
        Séparateur de colonnes (défaut ``";"``).
    mappage_colonnes:
        ``{nom_interne: nom_dans_csv}`` — issu de ``[mappage_colonnes]``.
    filtrage_colonne:
        Colonne de statut (après mappage) pour le filtrage des lignes valides.
    filtrage_valeur:
        Valeur attendue dans ``filtrage_colonne`` pour qu'une ligne soit retenue.
    section_colonne_forme:
        Nom interne de la colonne de forme de section (issu de ``[section].colonne_forme``).
    section_colonne_diametre:
        Nom interne de la colonne du diamètre pour sections rondes
        (issu de ``[section].colonne_diametre``).

    Returns
    -------
    list[ConfigMatériauVect]
        Liste de configurations matériau, une par ligne retenue du CSV.

    Raises
    ------
    ValueError
        Si une classe de résistance du CSV n'est pas dans la table normative.
    """
    df: pd.DataFrame = pd.read_csv(
        chemin_stock, sep=separateur, comment="#", low_memory=False
    )

    # ── 1. Renommage selon mappage (noms CSV → noms internes) ─────────────────
    if mappage_colonnes:
        df = df.rename(columns={v: k for k, v in mappage_colonnes.items() if v != k})

    # ── 2. Filtrage des lignes valides ────────────────────────────────────────
    if filtrage_colonne and filtrage_colonne in df.columns:
        df = df[df[filtrage_colonne] == filtrage_valeur]
    else:
        df = df[df["classe_resistance"].notna()]
    df = df.reset_index(drop=True)

    # ── 3. Jointure vectorisée — propriétés mécaniques ────────────────────────
    df_mat: pd.DataFrame = _charger_materiaux_bois()
    df = df.merge(df_mat, left_on="classe_resistance", right_on="classe", how="left")
    inconnus: list = df.loc[df["famille"].isna(), "classe_resistance"].unique().tolist()
    if inconnus:
        raise ValueError(
            f"Classe(s) de résistance inconnue(s) : {inconnus}. "
            f"Classes disponibles : {df_mat['classe'].tolist()}"
        )

    # ── 4. Forme de section par ligne ─────────────────────────────────────────
    col_forme: str | None = section_colonne_forme
    col_diam: str | None = section_colonne_diametre

    forme_arr: pd.Series = (
        df[col_forme].fillna("rectangle").astype(str).str.strip().str.lower()
        if col_forme and col_forme in df.columns
        else pd.Series("rectangle", index=df.index)
    )
    is_rect: np.ndarray   = (forme_arr == "rectangle").to_numpy()
    is_rond: np.ndarray   = (forme_arr == "rond").to_numpy()
    is_custom: np.ndarray = (forme_arr == "custom").to_numpy()

    # Diamètre pour sections rondes [cm]
    d_cm: pd.Series = (
        df[col_diam].fillna(0.0) / 10.0
        if col_diam and col_diam in df.columns
        else pd.Series(0.0, index=df.index)
    )

    # ── 5. Propriétés de section vectorisées ──────────────────────────────────
    k_cr: float = _k_cr()
    b: pd.Series = df["b_mm"] / 10.0
    h: pd.Series = df["h_mm"] / 10.0

    # Rectangle
    A_rect    = b * h
    I_y_rect  = b * h ** 3 / 12.0
    I_z_rect  = h * b ** 3 / 12.0
    W_y_rect  = b * h ** 2 / 6.0
    W_z_rect  = h * b ** 2 / 6.0
    A_eff_rect = A_rect * k_cr

    # Rond — section pleine circulaire (pas de k_cr, EC5 §6.1.7 concerne les rect.)
    A_rond    = math.pi * d_cm ** 2 / 4.0
    I_rond    = math.pi * d_cm ** 4 / 64.0
    W_rond    = math.pi * d_cm ** 3 / 32.0
    A_eff_rond = A_rond

    # Custom — lire depuis le CSV, fallback rectangle si colonne absente
    def _col_ou(col: str, fallback: pd.Series) -> pd.Series:
        """Lit une colonne du CSV avec fallback sur valeur calculée."""
        if col in df.columns:
            return df[col].where(df[col].notna(), other=fallback)
        return fallback

    A_custom    = _col_ou("A_cm2",                  A_rect)
    I_y_custom  = _col_ou("I_y_cm4",                I_y_rect)
    I_z_custom  = _col_ou("I_z_cm4",                I_z_rect)
    W_y_custom  = _col_ou("W_y_cm3",                W_y_rect)
    W_z_custom  = _col_ou("W_z_cm3",                W_z_rect)
    A_eff_custom = _col_ou("A_eff_cisaillement_cm2", A_eff_rect)

    # Sélection par forme (vectorisée)
    def _sel(rect: pd.Series, rond: pd.Series, cust: pd.Series) -> np.ndarray:
        return np.where(is_rect, rect, np.where(is_rond, rond, cust))

    df["A_cm2"]                  = _sel(A_rect,    A_rond, A_custom)
    df["I_y_cm4"]                = _sel(I_y_rect,  I_rond, I_y_custom)
    df["I_z_cm4"]                = _sel(I_z_rect,  I_rond, I_z_custom)
    df["W_y_cm3"]                = _sel(W_y_rect,  W_rond, W_y_custom)
    df["W_z_cm3"]                = _sel(W_z_rect,  W_rond, W_z_custom)
    df["A_eff_cisaillement_cm2"] = _sel(A_eff_rect, A_eff_rond, A_eff_custom)

    # Pour sections rondes : b_mm = h_mm = d_mm (appui + déversement)
    if col_diam and col_diam in df.columns:
        df["b_mm"] = np.where(is_rond, df[col_diam], df["b_mm"])
        df["h_mm"] = np.where(is_rond, df[col_diam], df["h_mm"])

    # ── 6. Colonnes optionnelles de sortie ────────────────────────────────────
    df["col_id_produit"] = (
        df["id_produit"].fillna("").astype(str)
        if "id_produit" in df.columns
        else ""
    )
    df["col_libelle"] = (
        df["libelle"].fillna("").astype(str)
        if "libelle" in df.columns
        else ""
    )
    df["col_essence"] = (
        df["essence"].fillna("").astype(str)
        if "essence" in df.columns
        else ""
    )

    # Type de section interne (pour les vérifications EC5)
    df["col_type_section"] = np.where(
        is_rond,   TypeSection.RONDE.value,
        np.where(
            is_custom, TypeSection.PERSONNALISEE.value,
            TypeSection.RECTANGULAIRE.value,
        ),
    )

    # ── 7. Construction des objets ────────────────────────────────────────────
    # id_config_materiau généré par ConfigMatériauVect.__post_init__
    return [
        ConfigMatériauVect(
            classe_resistance       = str(row.classe_resistance),
            famille                 = str(row.famille),
            b_mm                    = float(row.b_mm),
            h_mm                    = float(row.h_mm),
            A_cm2                   = float(row.A_cm2),
            I_y_cm4                 = float(row.I_y_cm4),
            I_z_cm4                 = float(row.I_z_cm4),
            W_y_cm3                 = float(row.W_y_cm3),
            W_z_cm3                 = float(row.W_z_cm3),
            A_eff_cisaillement_cm2  = float(row.A_eff_cisaillement_cm2),
            f_m_k_MPa               = float(row.f_m_k_MPa),
            f_v_k_MPa               = float(row.f_v_k_MPa),
            f_c90_k_MPa             = float(row.f_c90_k_MPa),
            f_t0_k_MPa              = float(row.f_t0_k_MPa),
            f_c0_k_MPa              = float(row.f_c0_k_MPa),
            f_t90_k_MPa             = float(row.f_t90_k_MPa),
            E_0_mean_MPa            = float(row.E_0_mean_MPa),
            E_0_05_MPa              = float(row.E_0_05_MPa),
            rho_k_kgm3              = float(row.rho_k_kgm3),
            type_section            = TypeSection(row.col_type_section),
            id_produit              = row.col_id_produit,
            libelle                 = row.col_libelle,
            essence                 = row.col_essence,
        )
        for row in df.itertuples(index=False)
    ]
