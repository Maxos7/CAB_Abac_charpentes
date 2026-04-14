"""
types_poutre.solive
===================
Solive horizontale bi-appuyée — cas le plus simple du pipeline.

La solive est posée horizontalement (pente = 0°). Toutes les charges (G, Q, S)
s'appliquent verticalement selon l'axe fort y. Pas de double flexion.
Pas d'effort normal. La portée horizontale = portée de calcul.

Usage typique : plancher, toiture accessible.
"""

from __future__ import annotations

from ..protocoles.type_poutre import PoutreHorizontaleVect


class SoliveVect(PoutreHorizontaleVect):
    """Solive horizontale bi-appuyée — flexion axe fort uniquement.

    Toutes les charges sont appliquées selon l'axe fort y.
    La pente est nulle ou ignorée (la solive est horizontale par définition).
    Pas de déversement (k_crit = 1.0 sauf si entraxe_antideversement > 0).
    """

