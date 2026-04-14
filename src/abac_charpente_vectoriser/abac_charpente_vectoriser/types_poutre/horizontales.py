"""
types_poutre.horizontales
=========================
Poutres horizontales bi-appuyées (pente nulle).

Regroupe les deux types dont la section est posée à l'horizontal :

- ``SoliveVect``  — plancher ou toiture accessible.
- ``SommierVect`` — poutre principale horizontale (grandes portées).

Les deux héritent de ``PoutreHorizontaleVect`` sans surcharge de méthode.
Leur distinction est portée par ``config.usage`` pour la sélection des
limites ELS dans ``limites_fleche_ec5.csv``.
"""

from __future__ import annotations

from ..protocoles.type_poutre import PoutreHorizontaleVect


class SoliveVect(PoutreHorizontaleVect):
    """Solive horizontale bi-appuyée — flexion axe fort uniquement.

    Toutes les charges sont appliquées selon l'axe fort y.
    La pente est nulle ou ignorée (la solive est horizontale par définition).
    Pas de déversement (k_crit = 1.0 sauf si entraxe_antideversement > 0).
    """


class SommierVect(PoutreHorizontaleVect):
    """Sommier horizontal bi-appuyé — flexion axe fort uniquement.

    Comportement identique à ``SoliveVect`` pour le calcul. La distinction
    avec la solive est portée par ``config.usage`` pour la sélection des limites ELS.
    """
