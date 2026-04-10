"""
moteur_vect
===========
Point d'entrée du pipeline de calcul EC5 vectorisé.

Orchestration complète :
1. Régénération du stock via ``sapeg_regen_stock`` (sauf si ``--stock`` direct fourni)
2. Lecture du fichier TOML externe (chemin passé en argument)
3. Chargement des matériaux depuis le CSV stock enrichi
4. Pour chaque ``[[config_calcul]]`` du TOML :
   a. Développement du produit cartésien des paramètres multi-valués
   b. Filtrage des matériaux
   c. Génération des combinaisons EC0
   d. Pour chaque combinaison de paramètres scalaires :
      - Construction de l'espace tenseur (p2_combinaison)
      - Vérifications ELU (p3_elu) + ELS (p4_els)
      - Synthèse (p5_synthese)
   e. Export CSV (synthétique + complet + réduit)
5. Optionnel : sauvegarde zarr + enregistrement DuckDB

Résolution du stock (par ordre de priorité) :
    1. ``chemin_stock`` fourni directement → utilisé tel quel (sans régénération)
    2. ``chemin_source`` (répertoire) → ``sapeg_regen_stock`` auto-détecte
       ``ALL_PRODUIT_*.csv`` et génère ``<sortie>/stock_enrichi.csv``
    3. Par défaut : ``chemin_source = Path(".")`` (répertoire courant)

Le fichier TOML est **externe** au package. Il peut contenir plusieurs sections
``[[config_calcul]]``, chacune indépendante avec ses propres filtres et paramètres.

Usage CLI (stock auto-régénéré depuis le répertoire courant) :
    abac-vect --toml configs_calcul_vect.toml

Usage CLI (répertoire source explicite) :
    abac-vect --toml configs_calcul_vect.toml --source /chemin/vers/ALL_PRODUIT/

Usage CLI (fichier stock direct, sans régénération) :
    abac-vect --toml configs_calcul_vect.toml --stock stock_enrichi.csv

Usage Python :
    from abac_charpente_vectoriser.moteur_vect import run
    run(chemin_toml=Path("configs_calcul_vect.toml"))
    run(chemin_toml=Path("configs_calcul_vect.toml"), chemin_stock=Path("mon_stock.csv"))
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .chargeur.depuis_csv import charger_depuis_csv
from .chargeur.filtre import appliquer_filtres
from .ec0.combinaisons import generer_combinaisons
from .modeles.config_calcul import ConfigCalculVect, RegleFiltre
from .pipeline.p1_charges import calculer_charges_caracteristiques
from .pipeline.p2_combinaison import construire_espace
from .pipeline.p3_elu import verifier_elu
from .pipeline.p4_els import verifier_els
from .pipeline.p5_synthese import ResultatPortee, synthetiser
from .sortie.abaque_complet import construire_df_complet, exporter_abaque_complet
from .sortie.vues import appliquer_vues_depuis_toml
from .types_poutre import TYPES_POUTRE


def _configurer_loguru(verbose: bool) -> None:
    """Configure loguru : INFO par défaut, DEBUG si verbose.

    Supprime le handler par défaut de loguru et en installe un nouveau avec
    un format adapté au niveau demandé.

    Parameters
    ----------
    verbose:
        Si True, active le niveau DEBUG (détail des calculs par combo).
        Si False, niveau INFO (progression générale du pipeline).
    """
    import sys
    from loguru import logger

    logger.remove()
    if verbose:
        logger.add(
            sys.stderr,
            level="DEBUG",
            colorize=True,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
                "<level>{message}</level>"
            ),
        )
    else:
        logger.add(
            sys.stderr,
            level="INFO",
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
        )


# Abréviations pour construire les IDs de combinaisons uniques
_ABBREV_COMBO: dict[str, str] = {
    "pente_deg":        "P",
    "entraxe_m":        "E",
    "classe_service":   "CS",
    "longueur_appui_mm": "La",
    "k_c90":            "kc90",
}


def _lire_toml(chemin_toml: Path) -> dict:
    """Lit un fichier TOML et retourne son contenu sous forme de dictionnaire."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

    with open(chemin_toml, "rb") as f:
        return tomllib.load(f)


def _developper_produit_cartesien(config_dict: dict) -> list[dict]:
    """Développe les champs multi-valués en produit cartésien de configs scalaires.

    Les champs de type ``list`` sont développés. Les scalaires sont conservés.

    Parameters
    ----------
    config_dict:
        Dictionnaire d'une ``ConfigCalculVect`` brut depuis le TOML.

    Returns
    -------
    list[dict]
        Liste de dictionnaires avec uniquement des valeurs scalaires.
    """
    # Champs multi-valués (scalar ou list) — exclure les champs non-numériques
    champs_multi: list[str] = [
        "L_min_m", "L_max_m", "pente_deg", "entraxe_m", "classe_service",
        "g_k_kNm2", "g2_k_kNm2", "q_k_kNm2", "s_k_kNm2", "w_k_kNm2",
        "longueur_appui_mm", "k_c90",
    ]

    listes: dict[str, list] = {}
    scalaires: dict[str, object] = {}
    for k, v in config_dict.items():
        if k in champs_multi and isinstance(v, list):
            listes[k] = v
        else:
            scalaires[k] = v

    if not listes:
        return [config_dict]

    combinaisons: list[tuple] = list(itertools.product(*listes.values()))
    cles: list[str] = list(listes.keys())

    resultats: list[dict] = []
    for combo in combinaisons:
        d: dict = dict(scalaires)
        for cle, val in zip(cles, combo):
            d[cle] = val
        resultats.append(d)

    return resultats


def _charger_filtres_sapeg(chemin_filtres: Path) -> list:
    """Charge les filtres depuis un fichier ``configs_filtre.toml`` (format sapeg_regen_stock).

    Parameters
    ----------
    chemin_filtres:
        Chemin vers le fichier TOML des filtres.

    Returns
    -------
    list[ConfigFiltre]
        Liste des filtres chargés. Liste vide si le fichier est absent.
    """
    from loguru import logger
    from sapeg_regen_stock.modeles import ConfigFiltre, RegleEgal, ReglePlage, RegleListe, RegleNonNul

    if not chemin_filtres.exists():
        logger.warning(f"configs_filtre introuvable : {chemin_filtres} — aucun filtre appliqué")
        return []

    toml_data: dict = _lire_toml(chemin_filtres)
    filtres: list = []
    for bloc in toml_data.get("filtre", []):
        regles_raw: list[dict] = bloc.get("regles", [])
        regles: list = []
        for r in regles_raw:
            t: str = r.get("type", "")
            if t == "egal":
                regles.append(RegleEgal(**r))
            elif t == "plage":
                regles.append(ReglePlage(**r))
            elif t == "liste":
                regles.append(RegleListe(**r))
            elif t == "non_nul":
                regles.append(RegleNonNul(**r))
        filtres.append(ConfigFiltre(
            nom=bloc["nom"],
            sortie=bloc["sortie"],
            description=bloc.get("description", ""),
            regles=regles,
        ))
    return filtres


def _regenerer_stock(
    chemin_source: Path,
    chemin_sortie: Path,
    chemin_filtres: Path = Path("configs_filtre.toml"),
    nom_filtre: str = "charpente",
) -> Path:
    """Appelle ``sapeg_regen_stock`` pour générer le stock filtré.

    Suit le même processus que ``abac_charpente`` : auto-détection du fichier
    ``ALL_PRODUIT_*.csv`` dans ``chemin_source``, enrichissement des propriétés
    mécaniques, application du filtre ``nom_filtre`` depuis ``configs_filtre.toml``.

    Parameters
    ----------
    chemin_source:
        Répertoire contenant ``ALL_PRODUIT_*.csv`` (ou chemin direct du fichier).
    chemin_sortie:
        Répertoire de sortie — ``stock_enrichi.csv`` y sera écrit.
    chemin_filtres:
        Chemin vers ``configs_filtre.toml``. Défaut : ``./configs_filtre.toml``.
    nom_filtre:
        Nom du filtre à utiliser comme stock de calcul. Défaut : ``"charpente"``.
        Si le filtre n'existe pas dans le TOML, ``stock_enrichi.csv`` est utilisé.

    Returns
    -------
    Path
        Chemin du CSV stock filtré (ou ``stock_enrichi.csv`` en fallback).
    """
    from loguru import logger
    import sapeg_regen_stock

    stock_enrichi_path: Path = chemin_sortie / "stock_enrichi.csv"
    filtres: list = _charger_filtres_sapeg(chemin_filtres)

    logger.info(f"Régénération stock depuis : {chemin_source}")
    dict_filtres: dict[str, Path] = sapeg_regen_stock.run(
        chemin_source,
        filtres=filtres,
        stock_enrichi_path=stock_enrichi_path,
    )

    # Utiliser le CSV du filtre nommé si disponible, sinon fallback stock_enrichi
    if nom_filtre in dict_filtres:
        chemin_calcul: Path = dict_filtres[nom_filtre]
        logger.info(f"Stock filtré '{nom_filtre}' : {chemin_calcul}")
    else:
        chemin_calcul = stock_enrichi_path
        if filtres:
            logger.warning(
                f"Filtre '{nom_filtre}' introuvable dans configs_filtre.toml "
                f"— utilisation de stock_enrichi.csv"
            )
        logger.info(f"Stock enrichi : {chemin_calcul}")

    return chemin_calcul


def run(
    chemin_toml: Path,
    chemin_source: Path = Path("."),
    chemin_stock: Path | None = None,
    chemin_filtres: Path = Path("configs_filtre.toml"),
    nom_filtre: str = "charpente",
    chemin_sortie: Path = Path("resultats"),
    chemin_toml_sortie: Path = Path("configs_sortie_vect.toml"),
    sauvegarder_tenseurs: bool = False,
) -> list[ResultatPortee]:
    """Exécute le pipeline complet de calcul EC5 vectorisé.

    Parameters
    ----------
    chemin_toml:
        Chemin vers le fichier de configuration TOML (externe au package).
    chemin_source:
        Répertoire contenant ``ALL_PRODUIT_*.csv`` — utilisé si ``chemin_stock``
        est None. ``sapeg_regen_stock`` auto-détecte le fichier le plus récent
        et génère ``<chemin_sortie>/stock_enrichi.csv``.
        Défaut : répertoire courant ``"."``.
    chemin_stock:
        Chemin direct vers un CSV stock compatible (``b_mm``, ``h_mm``,
        ``classe_resistance``). Si fourni, la régénération via
        ``sapeg_regen_stock`` est ignorée.
    chemin_filtres:
        Chemin vers ``configs_filtre.toml`` (filtres sapeg_regen_stock).
        Défaut : ``./configs_filtre.toml``.
    nom_filtre:
        Nom du filtre à utiliser comme stock de calcul. Défaut : ``"charpente"``.
    chemin_sortie:
        Répertoire de sortie pour les CSV résultats. Défaut : ``./resultats``.
    chemin_toml_sortie:
        Chemin vers ``configs_sortie_vect.toml`` définissant les vues dérivées.
        Si le fichier n'existe pas, seul ``abaque_complet_global.csv`` est écrit.
        Défaut : ``./configs_sortie_vect.toml``.
    sauvegarder_tenseurs:
        Si True, sauvegarde les tenseurs de taux dans ``resultats/tenseurs.duckdb``
        (table ``taux`` avec colonnes ``FLOAT[]`` par matériau, table ``materiaux_combo``).

    Returns
    -------
    list[ResultatPortee]
        Tous les résultats agrégés (toutes configs, tous matériaux).
    """
    from loguru import logger

    chemin_sortie.mkdir(parents=True, exist_ok=True)

    # ── Stock : régénération ou fichier direct ────────────────────────────────
    if chemin_stock is not None:
        logger.info(f"Stock direct : {chemin_stock}")
        chemin_stock_calcul: Path = chemin_stock
    else:
        chemin_stock_calcul = _regenerer_stock(
            chemin_source, chemin_sortie, chemin_filtres, nom_filtre
        )

    # ── Lecture TOML ──────────────────────────────────────────────────────────
    logger.info(f"Lecture TOML : {chemin_toml}")
    toml_data: dict = _lire_toml(chemin_toml)
    configs_brutes: list[dict] = toml_data.get("config_calcul", [])
    if not configs_brutes:
        raise ValueError("Aucune [[config_calcul]] trouvée dans le fichier TOML.")

    # ── Chargement matériaux ──────────────────────────────────────────────────
    logger.info(f"Chargement stock : {chemin_stock_calcul}")
    tous_materiaux = charger_depuis_csv(chemin_stock_calcul)
    logger.info(f"{len(tous_materiaux)} matériaux chargés")

    # Store DuckDB tenseurs optionnel
    store_tenseurs = None
    if sauvegarder_tenseurs:
        from .sortie.tenseur_duck import TenseurDuck
        store_tenseurs = TenseurDuck(chemin_sortie / "tenseurs.duckdb")
        logger.info(f"Store tenseurs DuckDB : {chemin_sortie / 'tenseurs.duckdb'}")

    tous_resultats: list[ResultatPortee] = []
    tous_df_complet: list[pd.DataFrame] = []   # accumulateur pour le fichier global

    # ── Boucle sur les configs du TOML ────────────────────────────────────────
    for cfg_brut in configs_brutes:
        config_base: ConfigCalculVect = ConfigCalculVect(**cfg_brut)
        logger.info(f"Config : {config_base.id_config_calcul} — type {config_base.type_poutre}")

        # Filtrage matériaux pour cette config
        materiaux_filtres = appliquer_filtres(tous_materiaux, config_base.filtres)
        if not materiaux_filtres:
            logger.warning(f"  Aucun matériau après filtrage pour {config_base.id_config_calcul}")
            continue
        logger.info(f"  {len(materiaux_filtres)} matériaux retenus après filtrage")

        # Développement produit cartésien (hors filtres)
        cfg_sans_filtres: dict = cfg_brut.copy()
        cfg_sans_filtres.pop("filtres", None)
        combos_scalaires: list[dict] = _developper_produit_cartesien(cfg_sans_filtres)
        logger.info(f"  {len(combos_scalaires)} combinaisons de paramètres")

        resultats_config: list[ResultatPortee] = []

        for combo in combos_scalaires:
            config: ConfigCalculVect = ConfigCalculVect(**{**combo, "filtres": []})

            # ── ID unique du combo (paramètres variables uniquement) ──────────
            suffix_parts: list[str] = []
            for champ, abbrev in _ABBREV_COMBO.items():
                val_brut = cfg_brut.get(champ)
                if isinstance(val_brut, list):   # champ multi-valué → inclus dans l'ID
                    val = combo.get(champ)
                    if val is not None:
                        val_str: str = (
                            str(int(val)) if isinstance(val, float) and val == int(val)
                            else str(val)
                        )
                        suffix_parts.append(f"{abbrev}{val_str}")

            id_unique: str = (
                f"{config_base.id_config_calcul}_{'_'.join(suffix_parts)}"
                if suffix_parts
                else config_base.id_config_calcul
            )
            config.id_config_calcul = id_unique   # propagé dans tous les exports

            # Vérification type_poutre
            if config.type_poutre not in TYPES_POUTRE:
                raise ValueError(
                    f"Type de poutre inconnu : '{config.type_poutre}'. "
                    f"Types disponibles : {list(TYPES_POUTRE.keys())}"
                )

            # Instance du type de poutre
            type_poutre = TYPES_POUTRE[config.type_poutre](config)

            # Vecteur de longueurs
            L_min: float = float(config.L_min_m if not isinstance(config.L_min_m, list) else config.L_min_m[0])
            L_max: float = float(config.L_max_m if not isinstance(config.L_max_m, list) else config.L_max_m[0])
            pas: float = float(config.pas_longueur_m)
            longueurs_m: np.ndarray = np.arange(L_min, L_max + pas / 2, pas)

            # Combinaisons EC0
            combinaisons = generer_combinaisons(config)

            # Charges caractéristiques
            charges_k = calculer_charges_caracteristiques(config, materiaux_filtres, type_poutre)

            # Espace tenseur
            espace = construire_espace(
                longueurs_m, combinaisons, materiaux_filtres, config, type_poutre, charges_k
            )

            # Vérifications
            taux_elu = verifier_elu(espace)
            taux_els = verifier_els(espace)

            # ── Détail DEBUG ──────────────────────────────────────────────────
            logger.debug(f"    ── {id_unique} ──")
            g_pp_moy: float = float(np.mean(charges_k["g_pp_kNm"]))
            logger.debug(
                f"    Charges (kN/m) : "
                f"G_pp={g_pp_moy:.3f}  G={charges_k['g_kNm']:.3f}  "
                f"G2={charges_k['g2_kNm']:.3f}  Q={charges_k['q_kNm']:.3f}  "
                f"S={charges_k['s_kNm']:.3f}  W={charges_k['w_kNm']:.3f}"
            )
            logger.debug(f"    Longueurs : {longueurs_m[0]:.2f}→{longueurs_m[-1]:.2f} m  "
                         f"({len(longueurs_m)} pts)  |  {len(materiaux_filtres)} matériaux")
            logger.debug("    ELU — taux max (toutes L, tous matériaux) :")
            for id_v, taux_arr in sorted(taux_elu.items(), key=lambda x: -float(x[1].max())):
                idx = np.unravel_index(int(np.argmax(taux_arr)), taux_arr.shape)
                mat_det: str = materiaux_filtres[idx[1]].id_config_materiau
                logger.debug(
                    f"      {id_v:<28} max={float(taux_arr.max()):.3f}"
                    f"  @ L={longueurs_m[idx[0]]:.2f}m  mat={mat_det}"
                )
            logger.debug("    ELS — taux max :")
            for id_v, taux_arr in sorted(taux_els.items(), key=lambda x: -float(x[1].max())):
                idx = np.unravel_index(int(np.argmax(taux_arr)), taux_arr.shape)
                mat_det = materiaux_filtres[idx[1]].id_config_materiau
                logger.debug(
                    f"      {id_v:<28} max={float(taux_arr.max()):.3f}"
                    f"  @ L={longueurs_m[idx[0]]:.2f}m  mat={mat_det}"
                )

            # Synthèse
            resultats = synthetiser(longueurs_m, taux_elu, taux_els, materiaux_filtres, config)
            resultats_config.extend(resultats)

            # Accumulation abaque complet (global)
            df_combo: pd.DataFrame = construire_df_complet(
                longueurs_m, taux_elu, taux_els, materiaux_filtres, config
            )
            tous_df_complet.append(df_combo)

            # Sauvegarde tenseurs DuckDB optionnelle
            if store_tenseurs is not None:
                store_tenseurs.sauvegarder(
                    id_unique, longueurs_m, taux_elu, taux_els, materiaux_filtres
                )
                logger.debug(f"    Tenseurs sauvegardés dans tenseurs.duckdb")

            # Libération RAM
            del espace, taux_elu, taux_els

            logger.info(f"    {id_unique} → {len(resultats)} résultats")

        tous_resultats.extend(resultats_config)

    # ── Export global unique (toutes configs confondues) ──────────────────────
    df_complet_global: pd.DataFrame = pd.concat(tous_df_complet, ignore_index=True) if tous_df_complet else pd.DataFrame()
    chemin_complet: Path = chemin_sortie / "abaque_complet_global.csv"
    exporter_abaque_complet(df_complet_global, chemin_complet)
    logger.info(f"abaque_complet_global.csv → {len(df_complet_global)} lignes")

    # ── Vues dérivées depuis le TOML de sortie ────────────────────────────────
    if chemin_toml_sortie.exists():
        appliquer_vues_depuis_toml(df_complet_global, chemin_toml_sortie, chemin_sortie)
    else:
        logger.warning(
            f"configs_sortie_vect.toml introuvable ({chemin_toml_sortie}) "
            f"— aucune vue dérivée produite"
        )

    if store_tenseurs is not None:
        store_tenseurs.fermer()
        logger.info(f"Tenseurs DuckDB fermés → {chemin_sortie / 'tenseurs.duckdb'}")

    logger.info(f"Pipeline terminé — {len(tous_resultats)} résultats dans {chemin_sortie}/")
    return tous_resultats


def cli() -> None:
    """Point d'entrée CLI : ``abac-vect``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="abac-vect",
        description="Pipeline EC5 vectorisé — calcul d'abaques paramétriques",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Résolution du stock (priorité décroissante) :\n"
            "  1. --stock <fichier>   → utilisé directement, sans régénération\n"
            "  2. --source <dossier>  → sapeg-regen-stock auto-détecte ALL_PRODUIT_*.csv\n"
            "  3. (défaut)            → --source=. (répertoire courant)\n\n"
            "Exemples :\n"
            "  abac-vect --toml-calcul configs_calcul_vect.toml\n"
            "  abac-vect --toml-calcul configs_calcul_vect.toml --source C:/SAPEG/exports/\n"
            "  abac-vect --toml-calcul configs_calcul_vect.toml --stock mon_stock.csv\n"
        ),
    )
    parser.add_argument(
        "--toml-calcul", default=Path("configs_calcul_vect.toml"), type=Path,
        dest="toml_calcul",
        metavar="FICHIER",
        help="TOML de configuration du calcul EC5 (défaut : ./configs_calcul_vect.toml)",
    )
    parser.add_argument(
        "--source", default=Path("."), type=Path,
        metavar="DOSSIER",
        help="Dossier contenant ALL_PRODUIT_*.csv (défaut : répertoire courant)",
    )
    parser.add_argument(
        "--stock", default=None, type=Path,
        metavar="FICHIER",
        help="CSV stock direct — court-circuite la régénération via sapeg-regen-stock",
    )
    parser.add_argument(
        "--filtres", default=Path("configs_filtre.toml"), type=Path,
        metavar="FICHIER",
        help="Fichier configs_filtre.toml (défaut : ./configs_filtre.toml)",
    )
    parser.add_argument(
        "--filtre", default="charpente",
        metavar="NOM",
        help="Nom du filtre à utiliser comme stock de calcul (défaut : charpente)",
    )
    parser.add_argument(
        "--sortie", default=Path("resultats"), type=Path,
        help="Répertoire de sortie (défaut : ./resultats)",
    )
    parser.add_argument(
        "--toml-sortie", default=Path("configs_sortie_vect.toml"), type=Path,
        metavar="FICHIER",
        dest="toml_sortie",
        help="TOML de configuration des vues de sortie (défaut : ./configs_sortie_vect.toml)",
    )
    parser.add_argument(
        "--tenseurs", action="store_true",
        help="Sauvegarder les tenseurs de taux dans resultats/tenseurs.duckdb (FLOAT[] par matériau)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Affiche le détail des calculs par combo (charges, taux ELU/ELS)",
    )
    args = parser.parse_args()

    _configurer_loguru(args.verbose)

    run(
        chemin_toml=args.toml_calcul,
        chemin_source=args.source,
        chemin_stock=args.stock,
        chemin_filtres=args.filtres,
        nom_filtre=args.filtre,
        chemin_sortie=args.sortie,
        chemin_toml_sortie=args.toml_sortie,
        sauvegarder_tenseurs=args.tenseurs,
    )
