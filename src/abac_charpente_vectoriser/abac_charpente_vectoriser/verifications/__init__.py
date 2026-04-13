"""
verifications
=============
Registres des vérifications ELU et ELS.

``VERIFICATIONS_ELU`` : liste ordonnée des 18 vérifications ELU (+ 1 = 19 avec FlexionAxeFaible).
``VERIFICATIONS_ELS`` : liste ordonnée des 3 vérifications ELS.

Le pipeline ``p3_elu`` et ``p4_els`` itère sur ces listes sans connaître
les classes concrètes — extensibilité garantie par le protocole ABC.

Pour ajouter une vérification :
1. Créer une sous-classe de ``VerificationELU`` ou ``VerificationELS``.
2. L'instancier et l'ajouter dans la liste ci-dessous.
"""

from ..protocoles.verification import VerificationELU, VerificationELS
from .ec5.elu_flexion import DoubleFlexionFaible, DoubleFlexionForte, FlexionAxeFort, FlexionAxeFaible
from .ec5.elu_cisaillement import Cisaillement
from .ec5.elu_appui import Appui
from .ec5.elu_deversement import Deversement
from .ec5.elu_traction import Traction, TractionTransversale
from .ec5.elu_compression import Compression
from .ec5.elu_combines import (
    FlexionTraction,
    FlexionCompressionForte,
    FlexionCompressionFaible,
    FlexionDevComprimeeForte,
    FlexionDevComprimeeFaible,
)
from .ec5.elu_flambement import FlambementAxeFort, FlambementAxeFaible
from .ec5.elu_compression_oblique import CompressionOblique
from .ec5.els_fleche import FlecheInst, FlecheFinBrute, FlecheFin, FlecheSecondOeuvre

VERIFICATIONS_ELU: list[VerificationELU] = [
    # ── Flexion ──────────────────────────────────────────────────────────────
    FlexionAxeFort(),              #  0 — §6.1.6 Eq.(6.11) — toujours actif (retombée)
    FlexionAxeFaible(),            #  1 — §6.1.6 Eq.(6.12) — rampant (double flexion)
    DoubleFlexionForte(),          #  2 — §6.1.6 Eq.(6.19) — taux combiné, axe fort déterminant
    DoubleFlexionFaible(),         #  3 — §6.1.6 Eq.(6.20) — taux combiné, axe faible déterminant
    # ── Cisaillement & appui ─────────────────────────────────────────────────
    Cisaillement(),                #  3 — §6.1.7 — toujours actif
    Appui(),                       #  4 — §6.1.5 — compression ⊥ au fil
    CompressionOblique(),          #  5 — §6.2.2 — Hankinson (pente définie)
    # ── Déversement ──────────────────────────────────────────────────────────
    Deversement(),                 #  6 — §6.3.3 — indicateur k_crit
    # ── Traction ─────────────────────────────────────────────────────────────
    Traction(),                    #  7 — §6.1.2 — N_d > 0
    TractionTransversale(),        #  8 — §6.1.3 — N_d > 0 + pente définie
    # ── Compression ──────────────────────────────────────────────────────────
    Compression(),                 #  9 — §6.1.4 — N_d < 0 (sans flambement)
    FlambementAxeFort(),           # 10 — §6.3.2 axe fort — N_d < 0
    FlambementAxeFaible(),         # 11 — §6.3.2 axe faible — N_d < 0
    # ── Combinées ────────────────────────────────────────────────────────────
    FlexionTraction(),             # 12 — §6.2.3 — N_d > 0
    FlexionCompressionForte(),     # 13 — §6.2.4 Eq.(6.23) — N_d < 0
    FlexionCompressionFaible(),    # 14 — §6.2.4 Eq.(6.24) — N_d < 0
    FlexionDevComprimeeForte(),    # 15 — §6.3.2 Eq.(6.23) — N_d < 0 + double flex
    FlexionDevComprimeeFaible(),   # 16 — §6.3.2 Eq.(6.24) — N_d < 0 + double flex
]

VERIFICATIONS_ELS: list[VerificationELS] = [
    FlecheInst(),              # 0 — §7.2 + AN — Winst,Q (vars seules), None=désactivé
    FlecheFinBrute(),          # 1 — §7.2 — Wfin brut (avant contre-flèche) ≤ L/125
    FlecheFin(),               # 2 — §7.2 — Wnet,fin (après contre-flèche) ≤ L/200
    FlecheSecondOeuvre(),      # 3 — §7.2 — Wtot,2 second-œuvre ≤ L/500
]

__all__ = ["VERIFICATIONS_ELU", "VERIFICATIONS_ELS"]
