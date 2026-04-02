"""Chargement du fichier stock CSV SAPEG (EF-002).

Lecture avec pandas (latin-1, séparateur |).
Validation des colonnes obligatoires et des valeurs numériques.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from sapeg_regen_stock.modeles import ConfigIngestion, ProduitStock


# Mapping colonnes CSV → champs ProduitStock
# Les noms de colonnes exacts du fichier ALL_PRODUIT_*.csv seront détectés dynamiquement.
# Format SAPEG : colonnes avec préfixe "produit_", dimensions en cm.
_COL_CODE_ARTICLE = ["produit_code_article", "Code article", "code_article", "CODE_ARTICLE", "Reference"]
_COL_DESIGNATION = ["produit_libelle", "Désignation", "designation", "Designation"]
_COL_FAMILLE = ["Famille", "famille"]
_COL_DISPONIBILITE = ["produit_commandable", "Disponibilité", "disponibilite", "Disponibilite"]
# SAPEG : produit_longueur = longueur en cm ; génériques en mm
_COL_LONGUEUR = ["produit_longueur", "Longueur", "longueur", "LONGUEUR", "L_max"]
# SAPEG : produit_epaisseur = b (épaisseur, dim. plus petite) en cm
_COL_LARGEUR = ["produit_epaisseur", "Largeur", "largeur", "LARGEUR", "b_mm"]
# SAPEG : produit_largeur = h (largeur/hauteur, dim. plus grande) en cm
_COL_HAUTEUR = ["produit_largeur", "Hauteur", "hauteur", "HAUTEUR", "h_mm"]
# Classe de résistance : extraite du libellé si colonne absente
_COL_CLASSE = ["Classe", "classe", "CLASSE", "Classe_resistance", "produit_mots_cles"]
_COL_FOURNISSEUR = ["produit_nom_fournisseur", "Fournisseur", "fournisseur", "FOURNISSEUR"]


def _trouver_colonne(df: pd.DataFrame, candidats: list[str]) -> str | None:
    """Trouve la première colonne disponible parmi les candidats."""
    for col in candidats:
        if col in df.columns:
            return col
    return None


def _lire_unite(row: pd.Series, col: str, df_columns: pd.Index) -> str:
    """Retourne l'unité depuis la colonne '{col}_unite' si disponible, sinon 'mm'."""
    unite_col = f"{col}_unite"
    if unite_col in df_columns:
        return str(row.get(unite_col, "mm")).strip().lower()
    return "mm"


def _vers_mm(valeur: float, unite: str) -> float:
    """Convertit une dimension vers mm selon l'unité."""
    if unite == "cm":
        return valeur * 10.0
    if unite == "m":
        return valeur * 1000.0
    return valeur  # mm par défaut


def _vers_m(valeur: float, unite: str) -> float:
    """Convertit une longueur vers m selon l'unité."""
    if unite == "cm":
        return valeur / 100.0
    if unite == "mm":
        return valeur / 1000.0
    if unite == "m":
        return valeur
    return valeur / 1000.0  # mm par défaut


def charger_stock(chemin: Path, config: ConfigIngestion) -> list[ProduitStock]:
    """Charge le fichier CSV stock et retourne une liste de ProduitStock.

    Paramètres :
        chemin : chemin vers ALL_PRODUIT_*.csv
        config : paramètres d'ingestion (encodage, séparateur, colonnes obligatoires)

    Retourne :
        Liste de ProduitStock valides (lignes invalides ignorées avec avertissement).

    Lève :
        SystemExit(2) : si des colonnes obligatoires sont manquantes.
    """
    try:
        df = pd.read_csv(
            chemin,
            encoding=config.encodage,
            sep=config.separateur,
            dtype=str,
            on_bad_lines="skip",
        )
    except Exception as e:
        logger.error(f"Impossible de lire le fichier stock : {chemin} — {e}")
        sys.exit(2)

    # Vérification colonnes obligatoires
    colonnes_manquantes = [c for c in config.colonnes_obligatoires if c not in df.columns]
    if colonnes_manquantes:
        logger.error(
            f"Colonnes obligatoires manquantes dans {chemin.name} : "
            f"{colonnes_manquantes}"
        )
        sys.exit(2)

    # Détection colonnes dimensionnelles
    col_code = _trouver_colonne(df, _COL_CODE_ARTICLE)
    col_desi = _trouver_colonne(df, _COL_DESIGNATION)
    col_famille = _trouver_colonne(df, _COL_FAMILLE)
    col_dispo = _trouver_colonne(df, _COL_DISPONIBILITE)
    col_long = _trouver_colonne(df, _COL_LONGUEUR)
    col_larg = _trouver_colonne(df, _COL_LARGEUR)
    col_haut = _trouver_colonne(df, _COL_HAUTEUR)
    col_classe = _trouver_colonne(df, _COL_CLASSE)
    col_fournisseur = _trouver_colonne(df, _COL_FOURNISSEUR)

    if not col_code:
        logger.error("Colonne code article introuvable dans le stock.")
        sys.exit(2)

    from sapeg_regen_stock.derivateur import extraire_classe_resistance
    produits: list[ProduitStock] = []

    for idx, row in df.iterrows():
        id_produit = str(row.get(col_code, f"LIGNE_{idx}")).strip()

        # Extraction dimensions avec détection d'unité
        try:
            if col_long:
                unite_long = _lire_unite(row, col_long, df.columns)
                L_max_m = _vers_m(float(row[col_long]), unite_long)
            else:
                L_max_m = 0.0
            if col_larg:
                unite_larg = _lire_unite(row, col_larg, df.columns)
                b_mm = _vers_mm(float(row[col_larg]), unite_larg)
            else:
                b_mm = 0.0
            if col_haut:
                unite_haut = _lire_unite(row, col_haut, df.columns)
                h_mm = _vers_mm(float(row[col_haut]), unite_haut)
            else:
                h_mm = 0.0
        except (ValueError, TypeError):
            logger.warning(f"AVERTISSEMENT [{id_produit}] : dimensions non numériques — ligne ignorée")
            continue

        # S'assurer que b <= h (épaisseur <= largeur)
        if b_mm > h_mm and h_mm > 0:
            b_mm, h_mm = h_mm, b_mm

        # Validation basique
        if b_mm <= 0 or h_mm <= 0 or L_max_m <= 0:
            logger.warning(f"AVERTISSEMENT [{id_produit}] : dimensions invalides (b={b_mm}, h={h_mm}, L={L_max_m}) — ligne ignorée")
            continue

        # Extraction classe de résistance
        # Cherche dans : libellé produit → col_classe → code article
        # classe_estimee = True si non trouvée directement dans le libellé
        classe_raw = str(row[col_classe]).strip() if col_classe else ""
        libelle_raw = str(row[col_desi]).strip() if col_desi else str(row.get(col_code, ""))
        classe = extraire_classe_resistance(libelle=libelle_raw, mots_cles="")
        if classe:
            classe_dans_libelle = True
        else:
            classe = extraire_classe_resistance(libelle="", mots_cles=classe_raw)
            if not classe:
                classe = extraire_classe_resistance(libelle=str(row.get(col_code, "")), mots_cles="")
            if classe:
                classe_dans_libelle = False
            else:
                logger.warning(f"AVERTISSEMENT [{id_produit}] : classe de résistance non détectée ('{classe_raw[:50]}') — ligne ignorée")
                continue

        famille = str(row[col_famille]).strip() if col_famille else "INCONNU"
        disponible = str(row.get(col_dispo, "")).strip().lower() in (
            "disponible", "oui", "yes", "true", "1"
        )
        fournisseur = str(row[col_fournisseur]).strip() if col_fournisseur else ""

        produits.append(ProduitStock(
            id_produit=id_produit,
            b_mm=b_mm,
            h_mm=h_mm,
            L_max_m=L_max_m,
            classe_resistance=classe,
            famille=famille,
            disponible=disponible,
            fournisseur=fournisseur,
            libelle=libelle_raw,
            classe_dans_libelle=classe_dans_libelle,
            ligne_csv_source=int(idx) + 2,  # +2 : 1 pour l'en-tête, 1 pour base-1
        ))

    logger.info(f"{len(produits)} produits chargés depuis {chemin.name}")
    return produits
