"""
modeles.config_calcul
=====================
Configuration d'un cas de calcul (une ligne ``[[config_calcul]]`` du fichier TOML).

Les champs multi-valués (``float | list[float]`` etc.) génèrent un produit cartésien
des configurations géo-matériau. Le moteur développe ce produit en interne — le fichier
TOML reste lisible et compact.

Le fichier TOML est **externe** au package (chemin passé en argument à ``moteur_vect.run``).
Il peut contenir plusieurs sections ``[[config_calcul]]``, chacune indépendante avec ses
propres règles de filtrage matériau.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RegleFiltre(BaseModel):
    """Règle de filtrage sur un champ de ``ConfigMatériauVect``.

    Le moteur applique un ET logique entre toutes les règles d'une config.

    Parameters
    ----------
    champ:
        Nom de l'attribut de ``ConfigMatériauVect`` à filtrer
        (ex: "classe_resistance", "h_mm", "famille").
    operateur:
        Opérateur de comparaison.
        - ``"=="``  : égalité stricte
        - ``"in"``  : appartenance à une liste de valeurs
        - ``">="``  : supérieur ou égal (champs numériques)
        - ``"<="``  : inférieur ou égal (champs numériques)
        - ``">"``   : strictement supérieur (champs numériques)
        - ``"<"``   : strictement inférieur (champs numériques)
        - ``"!="``  : différent de
    valeur:
        Valeur de référence. Pour ``"in"`` : liste de valeurs acceptées.
    """

    champ: str
    operateur: Literal["==", "in", ">=", "<=", ">", "<", "!="]
    valeur: float | int | str | list[float | int | str]


class ConfigCalculVect(BaseModel):
    """Configuration d'un cas de calcul EC5 vectorisé.

    Les champs de type ``float | list[float]`` (ou ``int | list[int]``) admettent
    une valeur scalaire ou une liste de valeurs. Le moteur calcule le produit
    cartésien de tous les champs multi-valués pour former les configurations
    géo-matériau.

    Parameters
    ----------
    id_config_calcul:
        Identifiant unique de la configuration (ex: "PANNE_C24_SC1").
    type_poutre:
        Clé dans le registre ``TYPES_POUTRE`` (ex: "Panne", "Solive", "Chevron").
    usage:
        Usage pour la sélection des limites de flèche ELS depuis
        ``donnees/limites_fleche_ec5.csv`` (ex: "panne_standard", "plancher_courant").
    L_min_m:
        Longueur(s) minimale(s) à calculer en mètres.
    L_max_m:
        Longueur(s) maximale(s) à calculer en mètres.
    pas_longueur_m:
        Pas de discrétisation des longueurs en mètres.
    pente_deg:
        Pente(s) du rampant en degrés.
    entraxe_m:
        Entraxe(s) entre poutres en mètres.
    classe_service:
        Classe(s) de service EC5 (1, 2 ou 3).
    g_k_kNm2:
        Charges permanentes G caractéristiques en kN/m² (hors poids propre).
    g2_k_kNm2:
        Charges permanentes fragiles G2 caractéristiques en kN/m²
        (carrelage, chapes, cloisons légères — toujours défavorables).
    q_k_kNm2:
        Charges variables Q caractéristiques en kN/m².
    categorie_q:
        Catégorie de charge variable pour lookup ψ (ex: "H", "A", "B").
    s_k_kNm2:
        Charges de neige S caractéristiques en kN/m² (sur projection horizontale).
    w_k_kNm2:
        Pression de vent W caractéristique en kN/m².
    type_toiture_vent:
        Type de toiture pour lookup c_pe vent ("1_pan", "2_pans", "terrasse").
    second_oeuvre:
        Si True, active la vérification ELS flèche second-œuvre (w_2).
    limite_fleche_inst:
        Override de la limite ELS instantanée (L/x). None → valeur de la table.
    limite_fleche_fin:
        Override de la limite ELS finale. None → valeur de la table.
    limite_fleche_2:
        Override de la limite ELS second-œuvre. None → valeur de la table.
    longueur_appui_mm:
        Longueur(s) d'appui en mm pour la vérification à l'appui (EC5 §6.1.5).
    k_c90:
        Facteur d'appui k_c90 (EC5 §6.1.5(4)). Scalaire ou multi-valué.
    double_flexion:
        Si True, active les vérifications de double flexion (ELU §6.1.6 + ELS).
        Automatiquement forcé à True pour PanneAplombVect.
    entraxe_antideversement_mm:
        Entraxe entre contreventements anti-déversement en mm.
        0 → longueur de déversement = portée complète.
    filtres:
        Règles de filtrage des matériaux pour cette configuration.
        ET logique entre toutes les règles.
    """

    id_config_calcul: str
    type_poutre: str
    usage: str

    L_min_m: float | list[float] = Field(default=1.0, ge=0.1)
    L_max_m: float | list[float] = Field(default=8.0, ge=0.1)
    pas_longueur_m: float = Field(default=0.10, gt=0.0)

    pente_deg: float | list[float] = 0.0
    entraxe_m: float | list[float] = 0.60

    classe_service: int | list[int] = 1

    g_k_kNm2: float | list[float] = 0.0
    g2_k_kNm2: float | list[float] = 0.0
    q_k_kNm2: float | list[float] = 0.0
    categorie_q: str = "H"
    s_k_kNm2: float | list[float] = 0.0
    w_k_kNm2: float | list[float] = 0.0
    type_toiture_vent: str = "1_pan"

    second_oeuvre: bool = False
    limite_fleche_inst: float | None = None
    limite_fleche_fin: float | None = None
    limite_fleche_2: float | None = None

    longueur_appui_mm: float | list[float] = 50.0
    k_c90: float | list[float] = 1.0

    double_flexion: bool = False
    entraxe_antideversement_mm: float = 0.0

    filtres: list[RegleFiltre] = Field(default_factory=list)

    @field_validator("classe_service", mode="before")
    @classmethod
    def _valider_classe_service(cls, v: int | list[int]) -> int | list[int]:
        """Vérifie que la classe de service est 1, 2 ou 3."""
        valeurs = v if isinstance(v, list) else [v]
        for cs in valeurs:
            if cs not in (1, 2, 3):
                raise ValueError(f"classe_service doit être 1, 2 ou 3 — reçu : {cs}")
        return v
