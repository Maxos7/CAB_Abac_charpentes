"""
verifications
=============
Registres des vérifications ELU et ELS.

``VERIFICATIONS_ELU`` : liste ordonnée des vérifications ELU.
``VERIFICATIONS_ELS`` : liste ordonnée des 12 vérifications ELS
                        (4 combinées + 4 axe fort + 4 axe faible).

Le pipeline ``p3_elu`` et ``p4_els`` itère sur ces listes sans connaître
les classes concrètes — extensibilité garantie par le protocole ABC.
"""

from ..protocoles.verification import VerificationELU, VerificationELS
from .ec5.elu_flexion import (
    DoubleFlexionFaible,
    DoubleFlexionForte,
    FlexionAxeFaible,
    FlexionAxeFort,
)
from .ec5.elu_effort_tranchant import Appui, Cisaillement
from .ec5.elu_effort_normal import Compression, Traction, TractionTransversale
from .ec5.elu_deversement import Deversement
from .ec5.elu_flambement import FlambementAxeFaible, FlambementAxeFort
from .ec5.elu_combines import (
    FlexionCompressionFaible,
    FlexionCompressionForte,
    FlexionDevComprimeeFaible,
    FlexionDevComprimeeForte,
    FlexionTraction,
)
from .ec5.elu_compression_oblique import CompressionOblique
from .ec5.els_fleche import (
    FlecheFin,
    FlecheFinBrute,
    FlecheFinBruteY,
    FlecheFinBruteZ,
    FlecheFinY,
    FlecheFinZ,
    FlecheInst,
    FlecheInstY,
    FlecheInstZ,
    FlecheSecondOeuvre,
    FlecheSecondOeuvreY,
    FlecheSecondOeuvreZ,
)

VERIFICATIONS_ELU: list[VerificationELU] = [
    FlexionAxeFort(),           # §6.1.6 Eq.(6.11) — toujours
    FlexionAxeFaible(),         # §6.1.6 Eq.(6.12) — double flexion
    DoubleFlexionForte(),       # §6.1.6 Eq.(6.19) — double flexion
    DoubleFlexionFaible(),      # §6.1.6 Eq.(6.20) — double flexion
    Cisaillement(),             # §6.1.7 — toujours
    Appui(),                    # §6.1.5 — toujours
    Deversement(),              # §6.3.3 — toujours
    Traction(),                 # §6.1.2 — N_d > 0
    TractionTransversale(),     # §6.1.3 — N_d > 0 et incliné
    Compression(),              # §6.1.4 — N_d < 0
    FlambementAxeFort(),        # §6.3.2 axe fort — N_d < 0
    FlambementAxeFaible(),      # §6.3.2 axe faible — N_d < 0
    FlexionTraction(),          # §6.2.3 — N_d > 0
    FlexionCompressionForte(),  # §6.2.4 Eq.(6.23) — N_d < 0
    FlexionCompressionFaible(), # §6.2.4 Eq.(6.24) — N_d < 0
    FlexionDevComprimeeForte(), # §6.3.2 Eq.(6.23) — N_d < 0 + double flex
    FlexionDevComprimeeFaible(),# §6.3.2 Eq.(6.24) — N_d < 0 + double flex
    CompressionOblique(),       # §6.2.2 Hankinson — incliné
]

VERIFICATIONS_ELS: list[VerificationELS] = [
    FlecheInst(),           # §7.2 + AN — Winst(Q) combiné
    FlecheInstY(),          # §7.2 + AN — Winst,y(Q) axe fort
    FlecheInstZ(),          # §7.2 + AN — Winst,z(Q) axe faible
    FlecheFinBrute(),       # §7.2(2) — Wfin brut combiné (L/125)
    FlecheFinBruteY(),      # §7.2(2) — Wfin,y axe fort
    FlecheFinBruteZ(),      # §7.2(2) — Wfin,z axe faible
    FlecheFin(),            # §7.2(2) — Wnet,fin combiné (L/200)
    FlecheFinY(),           # §7.2(2) — Wnet,fin,y axe fort
    FlecheFinZ(),           # §7.2(2) — Wnet,fin,z axe faible
    FlecheSecondOeuvre(),   # §7.2 — Wtot,2 combiné (L/500)
    FlecheSecondOeuvreY(),  # §7.2 — Wtot,2,y axe fort
    FlecheSecondOeuvreZ(),  # §7.2 — Wtot,2,z axe faible
]

__all__ = ["VERIFICATIONS_ELU", "VERIFICATIONS_ELS"]
