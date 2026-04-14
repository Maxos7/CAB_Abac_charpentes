"""
types_poutre.sommier
====================
Sommier (poutre principale horizontale) bi-appuyé.

Identique à la solive pour la décomposition des charges (flexion axe fort uniquement,
pas de double flexion). Le sommier est différencié de la solive par son usage
(limites de flèche ELS différentes dans ``limites_fleche_ec5.csv``) et typiquement
par des sections plus importantes.

Usage typique : poutre porteuse principale, poutre de plancher sur grande portée.
"""

from __future__ import annotations

from ..protocoles.type_poutre import PoutreHorizontaleVect


class SommierVect(PoutreHorizontaleVect):
    """Sommier horizontal bi-appuyé — flexion axe fort uniquement.

    Comportement identique à ``SoliveVect`` pour le calcul. La distinction
    avec la solive est portée par ``config.usage`` pour la sélection des limites ELS.
    """

