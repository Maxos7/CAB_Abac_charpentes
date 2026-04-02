"""Modèles de configuration de calcul EC5.

Notation française obligatoire (Principe IX).
Entités domaine en dataclasses/pydantic (Principe X).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated

from pydantic import BaseModel, field_validator, model_validator


@dataclass
class ConfigCalculDefaults:
    """Valeurs par défaut pour les paramètres d'appui et de flèche (EF-005b)."""
    longueur_appui_mm: float = 50.0
    k_c90: float = 1.0
    taux_cible_appui: float = 0.80
    limite_fleche_inst: float | None = None  # L/x, None = depuis limites_fleche_ec5.csv
    limite_fleche_fin: float | None = None
    limite_fleche_2: float | None = None


class ConfigCalcul(BaseModel):
    """Configuration d'un calcul EC5 (un [[config_calcul]] dans configs_calcul.toml).

    Paramètres multivalués (EF-005c) : float | list[float] → produit cartésien auto.
    Validation pydantic en français.
    """
    id_config_calcul: str
    type_poutre: str  # "Panne" | "Solive" | "Sommier" | "Chevron"
    usage: str        # TOITURE_INACC | TOITURE_ACC | PLANCHER_HAB | ... (EF-023)

    # Portées
    L_min_m: float | list[float] = 1.0
    pas_longueur_m: float = 0.10

    # Géométrie
    pente_deg: float | list[float] = 0.0
    entraxe_m: float | list[float] = 0.60

    # Classe de service EC5
    classe_service: int | list[int] = 1  # 1, 2 ou 3

    # Charges caractéristiques (kN/m² ou kN/m)
    g_k_kNm2: float | list[float] = 0.0
    q_k_kNm2: float | list[float] = 0.0
    categorie_q: str = "H"  # catégorie d'utilisation EN 1990
    s_k_kNm2: float | list[float] = 0.0
    w_k_kNm2: float | list[float] = 0.0
    type_toiture_vent: str = "1_pan"

    # Limites de flèche ELS (0 = depuis limites_fleche_ec5.csv)
    second_oeuvre: bool = False
    limite_fleche_inst: float | None = None   # inverseur L/x
    limite_fleche_fin: float | None = None
    limite_fleche_2: float | None = None      # flèche de second-œuvre

    # Paramètres d'appui
    longueur_appui_mm: float | list[float] = 50.0
    k_c90: float | list[float] = 1.0
    taux_cible_appui: float = 0.80

    # Double flexion (EF-024)
    double_flexion: bool = False
    entraxe_antideversement_mm: float = 0.0  # 0 = portée complète

    # Marge de sécurité (EF-026) : [0.0, 1.0[
    marge_securite: float = 0.0

    @field_validator("marge_securite")
    @classmethod
    def _valider_marge(cls, v: float) -> float:
        if not (0.0 <= v < 1.0):
            raise ValueError(
                f"marge_securite doit être dans [0.0, 1.0[ — valeur reçue : {v}"
            )
        return v

    @field_validator("usage")
    @classmethod
    def _valider_usage(cls, v: str) -> str:
        usages_valides = {
            "TOITURE_INACC", "TOITURE_ACC", "PLANCHER_HAB", "PLANCHER_BUR",
            "PLANCHER_REU", "PLANCHER_COM", "PLANCHER_STO", "PLANCHER_PAR", "AGRICOLE",
        }
        if v not in usages_valides:
            raise ValueError(
                f"usage '{v}' invalide — valeurs acceptées : {sorted(usages_valides)}"
            )
        return v

    @field_validator("type_poutre")
    @classmethod
    def _valider_type_poutre(cls, v: str) -> str:
        types_valides = {"Panne", "Solive", "Sommier", "Chevron"}
        if v not in types_valides:
            raise ValueError(
                f"type_poutre '{v}' invalide — valeurs acceptées : {sorted(types_valides)}"
            )
        return v

    @field_validator("classe_service")
    @classmethod
    def _valider_classe_service(cls, v: int | list[int]) -> int | list[int]:
        vals = [v] if isinstance(v, int) else v
        for cs in vals:
            if cs not in (1, 2, 3):
                raise ValueError(
                    f"classe_service {cs} invalide — doit être 1, 2 ou 3"
                )
        return v

    model_config = {"arbitrary_types_allowed": True}
