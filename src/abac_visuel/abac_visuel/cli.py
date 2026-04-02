"""Interface CLI abac_visuel — point d'entrée."""
from __future__ import annotations

from pathlib import Path

import click

from abac_visuel import __version__


@click.group()
@click.version_option(version=__version__, prog_name="abac-visuel")
def cli() -> None:
    """abac-visuel — Visualisation des portées admissibles EN 1990/EC5."""


@cli.command("generer")
@click.option(
    "--donnees", "-d",
    type=click.Path(exists=True, path_type=Path),
    default=Path("resultats/portees_admissibles.csv"),
    show_default=True,
    help="Chemin vers portees_admissibles.csv.",
)
@click.option(
    "--configs", "-c",
    type=click.Path(exists=True, path_type=Path),
    default=Path("configs_calcul.toml"),
    show_default=True,
    help="Chemin vers configs_calcul.toml (pour les entraxes).",
)
@click.option(
    "--sortie", "-o",
    type=click.Path(path_type=Path),
    default=Path("resultats/graphiques"),
    show_default=True,
    help="Dossier de sortie des graphiques.",
)
@click.option(
    "--format", "-f",
    "fmt",
    type=click.Choice(["png", "pdf"]),
    default="png",
    show_default=True,
    help="Format de sortie.",
)
def generer(donnees: Path, configs: Path, sortie: Path, fmt: str) -> None:
    """Genere les abaques de portees admissibles."""
    from abac_visuel.generateur import generer_graphiques

    generer_graphiques(donnees, configs, sortie, fmt)
