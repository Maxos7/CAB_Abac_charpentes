"""Pipeline complet sapeg_regen_stock (EF-021).

Orchestration :
    1. Détection du fichier stock le plus récent
    2. Chargement du CSV (latin-1, sep=|)
    3. Dérivation (id_config_materiau + propriétés mécaniques via abac_charpente.ec5.proprietes)
    4. Écriture stock_enrichi.csv (toujours, UTF-8, sep=;, écrasement)
    5. Pour chaque ConfigFiltre : filtrage + écriture CSV dédié (écrasement)
    6. Retourne {filtre.nom: Path(filtre.sortie), ...}

IMPORTANT : aucun import depuis abac_charpente.ec5 / ec0 / ec1 / moteur / sortie (Constitution IV).
Les propriétés mécaniques sont importées depuis abac_charpente.ec5.proprietes uniquement
pour la dérivation — ce module SAPEG DOIT rester indépendant du calcul EC5.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from sapeg_regen_stock.modeles import ConfigFiltre, ConfigIngestion, ProduitStock, ProduitValide
from sapeg_regen_stock.detecteur import detecter_fichier_stock
from sapeg_regen_stock.chargeur import charger_stock
from sapeg_regen_stock.derivateur import hash_id_materiau, enrichir_produit


def run(
    source: Path | str,
    filtres: list[ConfigFiltre],
    stock_enrichi_path: Path | None = None,
) -> dict[str, Path]:
    """Pipeline complet : détection → chargement → enrichissement → filtrage.

    Paramètres :
        source            : répertoire (auto-détection) ou chemin direct du CSV stock
        filtres           : liste de ConfigFiltre (chaque filtre génère un CSV)
        stock_enrichi_path: chemin du CSV enrichi global (défaut : stock_enrichi.csv)

    Retourne :
        dict {filtre.nom: Path(filtre.sortie)} pour chaque filtre traité.
    """
    source = Path(source)

    # 1. Détection du fichier stock
    if source.is_file():
        fichier_stock = source
    else:
        fichier_stock = detecter_fichier_stock(source)

    # 2. Chargement
    config_ingestion = ConfigIngestion()
    produits_stock = charger_stock(fichier_stock, config_ingestion)

    if not produits_stock:
        logger.warning("Aucun produit chargé depuis le fichier stock.")

    # 3. Enrichissement — calcul id_config_materiau
    produits_valides: list[ProduitValide] = []
    produits_exclus_derivation: list[dict] = []

    for produit in produits_stock:
        try:
            _id = hash_id_materiau(
                produit.b_mm, produit.h_mm, produit.classe_resistance, produit.L_max_m
            )
            pv = enrichir_produit(produit, _id)
            produits_valides.append(pv)
        except Exception as e:
            logger.warning(f"AVERTISSEMENT [{produit.id_produit}] : échec dérivation — {e}")
            produits_exclus_derivation.append({
                "id_produit": produit.id_produit,
                "raison": str(e),
                "ligne_csv": produit.ligne_csv_source,
            })

    # 4. Écriture stock_enrichi.csv
    if stock_enrichi_path is None:
        stock_enrichi_path = fichier_stock.parent / "stock_enrichi.csv"
    else:
        stock_enrichi_path = Path(stock_enrichi_path)

    _ecrire_stock_enrichi(produits_valides, produits_exclus_derivation, stock_enrichi_path)

    # 5. Filtrage + écriture CSV par filtre
    résultats: dict[str, Path] = {}
    if filtres:
        from sapeg_regen_stock.filtre import filtrer_stock
        for filtre in filtres:
            valides, exclus = filtrer_stock(produits_valides, filtre)
            _ecrire_csv_filtre(valides, exclus, filtre)
            résultats[filtre.nom] = Path(filtre.sortie)

    return résultats


def _ecrire_stock_enrichi(
    valides: list[ProduitValide],
    exclus_derivation: list[dict],
    chemin: Path,
) -> None:
    """Écrit stock_enrichi.csv (UTF-8, sep=;, écrasement)."""
    lignes = []

    for pv in valides:
        lignes.append({
            "id_produit": pv.id_produit,
            "libelle": pv.libelle,
            "b_mm": pv.b_mm,
            "h_mm": pv.h_mm,
            "L_max_m": pv.L_max_m,
            "classe_resistance": pv.classe_resistance,
            "famille": pv.famille,
            "id_config_materiau": pv.id_config_materiau,
            "libelle_config_materiau": f"{int(pv.b_mm)}x{int(pv.h_mm)} {pv.classe_resistance} L={pv.L_max_m}m",
            "classe_dans_libelle": pv.classe_dans_libelle,  # True = classe visible dans libellé ; False = estimée depuis mots-clés ou code article
            "disponible": pv.disponible,
            "fournisseur": pv.fournisseur,
            "statut_ingestion": "valide",
            "raison_exclusion": "",
            "ligne_csv_source": pv.ligne_csv_source,
        })

    for ex in exclus_derivation:
        lignes.append({
            "id_produit": ex["id_produit"],
            "libelle": None,
            "b_mm": None,
            "h_mm": None,
            "L_max_m": None,
            "classe_resistance": None,
            "famille": None,
            "id_config_materiau": None,
            "libelle_config_materiau": None,
            "classe_dans_libelle": None,
            "disponible": None,
            "fournisseur": None,
            "statut_ingestion": "exclu_derivation",
            "raison_exclusion": ex["raison"],
            "ligne_csv_source": ex["ligne_csv"],
        })

    df = pd.DataFrame(lignes)
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(chemin, sep=";", encoding="utf-8", index=False)
        logger.info(f"stock_enrichi.csv écrit : {len(valides)} valides, {len(exclus_derivation)} exclus")
    except Exception as e:
        logger.error(f"Impossible d'écrire stock_enrichi.csv : {e}")
        sys.exit(4)


def _ecrire_csv_filtre(
    valides: list[ProduitValide],
    exclus: list,
    filtre: ConfigFiltre,
) -> None:
    """Écrit le CSV de sortie d'un filtre (UTF-8, sep=;, écrasement)."""
    from sapeg_regen_stock.modeles import ProduitExclu
    lignes = []
    for pv in valides:
        lignes.append({
            "id_produit": pv.id_produit,
            "libelle": pv.libelle,
            "b_mm": pv.b_mm,
            "h_mm": pv.h_mm,
            "L_max_m": pv.L_max_m,
            "classe_resistance": pv.classe_resistance,
            "famille": pv.famille,
            "id_config_materiau": pv.id_config_materiau,
            "disponible": pv.disponible,
            "statut_filtre": "retenu",
            "regle_violee": "",
        })
    for ex in exclus:
        lignes.append({
            "id_produit": ex.id_produit,
            "libelle": None,
            "b_mm": None, "h_mm": None, "L_max_m": None,
            "classe_resistance": None, "famille": None,
            "id_config_materiau": None, "disponible": None,
            "statut_filtre": "exclu",
            "regle_violee": ex.regle_violee,
        })

    df = pd.DataFrame(lignes)
    chemin = Path(filtre.sortie)
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(chemin, sep=";", encoding="utf-8", index=False)
        logger.info(f"Filtre '{filtre.nom}' : {len(valides)} retenus -> {chemin}")
    except Exception as e:
        logger.error(f"Impossible d'écrire {chemin} : {e}")
        sys.exit(4)
