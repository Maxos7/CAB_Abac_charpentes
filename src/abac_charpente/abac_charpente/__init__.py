"""Initialisation du paquet abac_charpente.

Configure loguru pour les messages en français :
    - Avertissements et erreurs sur stderr
    - Informations sur stdout
    - Format : NIVEAU [contexte] : message
"""
import sys

from loguru import logger

# Supprimer le handler par défaut
logger.remove()

# Stderr — avertissements, erreurs, critiques
logger.add(
    sys.stderr,
    level="WARNING",
    format="<level>{level: <12}</level> {message}",
    colorize=True,
)

# Stdout — informations (niveau INFO et DEBUG)
logger.add(
    sys.stdout,
    level="INFO",
    filter=lambda record: record["level"].no < 30,  # < WARNING
    format="<cyan>{level: <12}</cyan> {message}",
    colorize=True,
)

__version__ = "0.1.0"
