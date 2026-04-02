"""Interface CLI sapeg_regen_stock — point d'entrée click.

Ce module ne contient que le parsing des arguments (Principe X).
La logique est déléguée à pipeline.run().
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from sapeg_regen_stock import __version__


@click.group()
@click.version_option(version=__version__, prog_name="sapeg-regen-stock")
def cli() -> None:
    """sapeg-regen-stock — Filtre et enrichissement du stock SAPEG pour le calcul EC5."""


@cli.command("regenerer")
@click.option(
    "--source", "-s",
    type=click.Path(exists=False, path_type=Path),
    required=True,
    help="Répertoire ou chemin direct du fichier ALL_PRODUIT_*.csv.",
)
@click.option(
    "--filtres", "-f",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="Chemin vers configs_filtre.toml (optionnel).",
)
@click.option(
    "--stock-enrichi", "-o",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="Chemin du CSV stock_enrichi.csv de sortie.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Affiche les détails de progression.",
)
def regenerer(
    source: Path,
    filtres: Path | None,
    stock_enrichi: Path | None,
    verbose: bool,
) -> None:
    """Filtre et enrichit le fichier stock SAPEG.

    Codes de sortie :
        0 — Succès
        1 — Erreur de configuration
        2 — Colonnes manquantes dans le CSV stock
        4 — Erreur d'écriture fichier de sortie
    """
    try:
        from sapeg_regen_stock.pipeline import run
        from sapeg_regen_stock.modeles import ConfigFiltre

        # Chargement des filtres
        liste_filtres: list[ConfigFiltre] = []
        if filtres is not None and filtres.exists():
            try:
                import tomllib
                with open(filtres, "rb") as f:
                    donnees = tomllib.load(f)
                for bloc in donnees.get("filtre", []):
                    liste_filtres.append(ConfigFiltre(**bloc))
            except Exception as e:
                click.echo(f"ERREUR configs_filtre.toml : {e}", err=True)
                sys.exit(1)
        elif filtres is not None:
            click.echo(
                f"AVERTISSEMENT : {filtres} introuvable — aucun filtre appliqué.",
                err=True,
            )

        # Résolution stock_enrichi
        stock_enrichi_path = stock_enrichi

        # Appel pipeline
        dict_résultats = run(source, liste_filtres, stock_enrichi_path)

        # Rapport FR sur stdout
        click.echo("Enrichissement termine.")
        for nom, chemin in dict_résultats.items():
            click.echo(f"  Filtre '{nom}' -> {chemin}")

        if not dict_résultats:
            click.echo("  (aucun filtre defini -- seul stock_enrichi.csv genere)")

    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"ERREUR inattendue : {e}", err=True)
        sys.exit(1)
