"""
verifications
=============
Registres des vérifications ELU et ELS.

``VERIFICATIONS_ELU`` : liste ordonnée des 11 vérifications ELU.
``VERIFICATIONS_ELS`` : liste ordonnée des 3 vérifications ELS.

Le pipeline ``p3_elu`` et ``p4_els`` itère sur ces listes sans connaître
les classes concrètes — extensibilité garantie par le protocole ABC.

Pour ajouter une vérification :
1. Créer une sous-classe de ``VerificationELU`` ou ``VerificationELS``.
2. L'instancier et l'ajouter dans la liste ci-dessous.
"""

from ..protocoles.verification import VerificationELU, VerificationELS
from .ec5.elu_flexion import DoubleFlexionFaible, DoubleFlexionForte, FlexionSimple
from .ec5.elu_cisaillement import Cisaillement
from .ec5.elu_appui import Appui
from .ec5.elu_deversement import Deversement
from .ec5.elu_traction import Traction
from .ec5.elu_compression import Compression
from .ec5.elu_combines import FlexionTraction, FlexionCompressionForte, FlexionCompressionFaible
from .ec5.els_fleche import FlecheInst, FlecheFin, FlecheSecondOeuvre

VERIFICATIONS_ELU: list[VerificationELU] = [
    FlexionSimple(),           # 0 — §6.1.6 Eq.(6.11) — toujours
    DoubleFlexionForte(),      # 1 — §6.1.6 Eq.(6.19) — double flexion
    DoubleFlexionFaible(),     # 2 — §6.1.6 Eq.(6.20) — double flexion
    Cisaillement(),            # 3 — §6.1.7 — toujours
    Appui(),                   # 4 — §6.1.5 — toujours
    Deversement(),             # 5 — §6.3.3 — toujours
    Traction(),                # 6 — §6.1.2 — N_d > 0
    Compression(),             # 7 — §6.1.4 — N_d < 0
    FlexionTraction(),         # 8 — §6.2.3 — N_d > 0
    FlexionCompressionForte(), # 9 — §6.2.4 équation forte — N_d < 0
    FlexionCompressionFaible(),# 10 — §6.2.4 équation faible — N_d < 0
]

VERIFICATIONS_ELS: list[VerificationELS] = [
    FlecheInst(),              # 0 — §7.2 flèche instantanée
    FlecheFin(),               # 1 — §7.2 flèche finale (avec fluage)
    FlecheSecondOeuvre(),      # 2 — §7.2 flèche nette second-œuvre
]

__all__ = ["VERIFICATIONS_ELU", "VERIFICATIONS_ELS"]
