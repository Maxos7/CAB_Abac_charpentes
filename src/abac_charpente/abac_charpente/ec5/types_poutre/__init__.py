"""Registre des types de poutre — Principe X + EF-019.

Usage :
    from abac_charpente.ec5.types_poutre import TYPES_POUTRE, instancier, TypePoutre

    poutre = instancier("Panne")   # → instance de Panne()
    TYPES_POUTRE["MonType"] = MonType  # extension par héritage

INTERDIT dans elu.py / els.py : if/match type_poutre (EF-019).
"""
from abac_charpente.ec5.types_poutre.base import TypePoutre
from abac_charpente.ec5.types_poutre.panne import Panne
from abac_charpente.ec5.types_poutre.solive import Solive
from abac_charpente.ec5.types_poutre.sommier import Sommier
from abac_charpente.ec5.types_poutre.chevron import Chevron

TYPES_POUTRE: dict[str, type[TypePoutre]] = {
    "Panne": Panne,
    "Solive": Solive,
    "Sommier": Sommier,
    "Chevron": Chevron,
}


def instancier(type_poutre: str) -> TypePoutre:
    """Instancie un TypePoutre depuis son nom (chaîne).

    Lève ValueError si le type est inconnu — utiliser le registre pour l'extensibilité.
    """
    cls = TYPES_POUTRE.get(type_poutre)
    if cls is None:
        connus = sorted(TYPES_POUTRE.keys())
        raise ValueError(
            f"Type de poutre '{type_poutre}' inconnu. "
            f"Types disponibles : {connus}. "
            "Pour ajouter un nouveau type : TYPES_POUTRE['MonType'] = MonType."
        )
    return cls()


__all__ = ["TypePoutre", "Panne", "Solive", "Sommier", "Chevron", "TYPES_POUTRE", "instancier"]
