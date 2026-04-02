"""Auto-détection du fichier stock SAPEG le plus récent (EF-001).

Le fichier ALL_PRODUIT_*.csv le plus récent est sélectionné par tri lexicographique
décroissant sur le nom du fichier (format AAAA-MM-JJ_HH_MM_SS).
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger


def detecter_fichier_stock(repertoire: Path) -> Path:
    """Détecte le fichier ALL_PRODUIT_*.csv le plus récent dans le répertoire.

    Paramètres :
        repertoire : répertoire où chercher (chemin absolu ou relatif)

    Retourne :
        Chemin absolu du fichier le plus récent.

    Lève :
        FileNotFoundError : si aucun fichier ALL_PRODUIT_*.csv n'est trouvé.
    """
    repertoire = Path(repertoire).resolve()
    fichiers = sorted(
        repertoire.glob("ALL_PRODUIT_*.csv"),
        reverse=True,  # tri décroissant → plus récent en premier
    )

    if not fichiers:
        raise FileNotFoundError(
            f"Aucun fichier ALL_PRODUIT_*.csv trouvé dans : {repertoire}"
        )

    sélectionné = fichiers[0]
    logger.info(f"Fichier stock sélectionné : {sélectionné.name}")
    return sélectionné
