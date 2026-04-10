"""
types_poutre
============
Registre extensible des types de poutres du pipeline EC5 vectorisé.

Pour ajouter un nouveau type de poutre :
1. Créer une sous-classe de ``TypePoutreVect`` dans un nouveau fichier.
2. L'importer et l'ajouter dans ``TYPES_POUTRE`` ci-dessous.
3. Aucune modification des modules pipeline ou vérifications n'est requise.
"""

from .chevron import ChevronVect
from .panne_aplomb import PanneAplombVect
from .panne_deversee import PanneDeverseeVect
from .solive import SoliveVect
from .sommier import SommierVect
from ..protocoles.type_poutre import TypePoutreVect

TYPES_POUTRE: dict[str, type[TypePoutreVect]] = {
    # ── Pannes (pièces inclinées, section variable selon orientation) ──────────
    "PanneDeversee": PanneDeverseeVect,
    # Section ⊥ au rampant (normale à la surface) — double flexion si activée.

    "PanneAplomb": PanneAplombVect,
    # Section verticale (normale au sol) — double flexion intrinsèque.

    # ── Chevron ────────────────────────────────────────────────────────────────
    "Chevron": ChevronVect,
    # Pièce posée dans le sens du rampant, charges ⊥ au rampant.

    # ── Poutres horizontales ───────────────────────────────────────────────────
    "Solive": SoliveVect,
    # Plancher ou toiture accessible — bi-appui horizontal.

    "Sommier": SommierVect,
    # Poutre principale horizontale — bi-appui horizontal.

    # ── Futures extensions (commentées — à implémenter dans des modules dédiés) ─
    # "Arbaletrier":  ArbaletierVect,   # compression + flexion §6.2.4, N_d < 0
    # "Entrait":      EntraitVect,      # traction + flexion §6.2.3, N_d > 0
    # "Faitiere":     FaitiereVect,     # faîtière bi-chargée symétrique
    # "PoutreCont":   PoutreContVect,   # multi-portée, multi-appui
}

__all__ = [
    "TYPES_POUTRE",
    "TypePoutreVect",
    "ChevronVect",
    "PanneAplombVect",
    "PanneDeverseeVect",
    "SoliveVect",
    "SommierVect",
]
