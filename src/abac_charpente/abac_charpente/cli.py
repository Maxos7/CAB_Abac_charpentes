"""Interface CLI ABAC-Charpente — point d'entrée click.

Ce module ne contient que le parsing des arguments — aucune logique métier (Principe X).
La logique est déléguée à moteur.lancer_calcul().
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from abac_charpente import __version__


@click.group()
@click.version_option(version=__version__, prog_name="abac-charpente")
def cli() -> None:
    """ABAC-Charpente — Calcul de portées admissibles EN 1990/EC5 pour structures bois."""


@cli.command("calculer")
@click.option(
    "--config", "-c",
    type=click.Path(exists=False, path_type=Path),
    default=Path("config.toml"),
    show_default=True,
    help="Chemin vers config.toml.",
)
@click.option(
    "--stock",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="Chemin direct vers un fichier ALL_PRODUIT_*.csv (priorité max).",
)
@click.option(
    "--stock-dir",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    default=None,
    help="Répertoire où chercher ALL_PRODUIT_*.csv (auto-détection du plus récent).",
)
@click.option(
    "--sortie", "-o",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="Chemin du CSV de sortie (écrase [sortie].fichier_csv de config.toml).",
)
@click.option(
    "--recalcul-complet",
    is_flag=True,
    default=False,
    help="Ignore le registre et recalcule tout.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Affiche les détails de progression.",
)
def calculer(
    config: Path,
    stock: Path | None,
    stock_dir: Path | None,
    sortie: Path | None,
    recalcul_complet: bool,
    verbose: bool,
) -> None:
    """Lance le calcul de portées admissibles pour tous les produits du stock.

    Codes de sortie :
        0 — Succès
        1 — Erreur de configuration
        2 — Colonnes manquantes dans le CSV stock
        3 — Aucun produit après filtrage
        4 — Erreur d'écriture fichier de sortie
        5 — Erreur interne inattendue
    """
    # Mutex --stock / --stock-dir
    if stock is not None and stock_dir is not None:
        click.echo(
            "ERREUR : --stock et --stock-dir sont mutuellement exclusifs.", err=True
        )
        sys.exit(1)

    try:
        from abac_charpente.config import charger_config, charger_filtres, expandre_configs
        from abac_charpente.moteur import lancer_calcul

        app_config = charger_config(config)

        # Résolution priorité stock : --stock > --stock-dir > [stock].repertoire > répertoire courant
        if stock is not None:
            app_config.stock.repertoire = str(stock.parent)
            stock_override = stock
        elif stock_dir is not None:
            app_config.stock.repertoire = str(stock_dir)
            stock_override = None
        else:
            stock_override = None

        if sortie is not None:
            app_config.sortie.fichier_csv = str(sortie)

        # Charger les filtres
        filtres_path = config.parent / app_config.filtres.fichier_configs_filtre
        filtres = charger_filtres(filtres_path)

        # Expansion cartésienne des configs de calcul
        configs_expandees = []
        for cfg in app_config.configs_calcul:
            configs_expandees.extend(expandre_configs(cfg))
        app_config.configs_calcul = configs_expandees

        lancer_calcul(
            app_config=app_config,
            filtres=filtres,
            stock_override=stock_override,
            recalcul_complet=recalcul_complet,
            verbose=verbose,
        )

    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"ERREUR inattendue : {e}", err=True)
        sys.exit(5)
