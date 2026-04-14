"""Auto-détection du fichier stock SAPEG le plus récent (EF-001).

Le fichier ALL_PRODUIT_*.csv le plus récent est sélectionné par tri lexicographique
décroissant sur le nom du fichier (format AAAA-MM-JJ_HH_MM_SS).
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger


def detecter_fichier_stock(
    repertoire: Path,
    pattern: str = "ALL_PRODUIT_*.csv",
) -> Path:
    """Détecte le fichier stock le plus récent dans le répertoire.

    Paramètres :
        repertoire : répertoire où chercher (chemin absolu ou relatif)
        pattern    : glob de sélection du fichier (défaut : "ALL_PRODUIT_*.csv")

    Retourne :
        Chemin absolu du fichier le plus récent.

    Lève :
        FileNotFoundError : si aucun fichier correspondant au pattern n'est trouvé.
    """
    repertoire = Path(repertoire).resolve()
    fichiers = sorted(
        repertoire.glob(pattern),
        reverse=True,  # tri décroissant → plus récent en premier
    )

    if not fichiers:
        raise FileNotFoundError(
            f"Aucun fichier '{pattern}' trouvé dans : {repertoire}"
        )

    sélectionné = fichiers[0]
    logger.info(f"Fichier stock sélectionné : {sélectionné.name}")
    return sélectionné
