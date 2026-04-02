"""Entités domaine du paquet sapeg_regen_stock.

Toutes les entités sont des dataclasses ou modèles pydantic (Principe X).
Aucune importation depuis abac_charpente (Constitution IV).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Entités stock brutes
# ---------------------------------------------------------------------------

@dataclass
class ProduitStock:
    """Produit issu du fichier stock SAPEG (avant dérivation mécanique)."""
    id_produit: str
    b_mm: float
    h_mm: float
    L_max_m: float
    classe_resistance: str
    famille: str
    disponible: bool
    fournisseur: str
    libelle: str = ""
    classe_dans_libelle: bool = True
    ligne_csv_source: int = 0


@dataclass
class ProduitValide:
    """Produit ayant passé toutes les validations, enrichi avec id_config_materiau."""
    id_produit: str
    libelle: str
    b_mm: float
    h_mm: float
    L_max_m: float
    classe_resistance: str
    famille: str
    disponible: bool
    fournisseur: str
    id_config_materiau: str
    classe_dans_libelle: bool = True
    ligne_csv_source: int = 0


@dataclass
class ProduitExclu:
    """Produit rejeté lors du filtrage ou de la dérivation."""
    id_produit: str
    ligne_csv: int
    raison: str
    regle_violee: str = ""


# ---------------------------------------------------------------------------
# Configuration ingestion CSV
# ---------------------------------------------------------------------------

@dataclass
class ConfigIngestion:
    """Paramètres de lecture du fichier stock CSV SAPEG."""
    encodage: str = "latin-1"
    separateur: str = "|"
    # Liste vide : la validation des colonnes est faite dynamiquement dans charger_stock().
    # Le format SAPEG ALL_PRODUIT_*.csv (colonnes "produit_*") et le format générique
    # (colonnes "Code article", "Longueur"…) sont tous deux supportés par auto-détection.
    colonnes_obligatoires: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Règles de filtrage (union discriminée)
# ---------------------------------------------------------------------------

class RegleEgal(BaseModel):
    """Règle d'égalité (insensible à la casse pour les chaînes)."""
    type: Literal["egal"] = "egal"
    champ: str
    valeur: str | float | int


class ReglePlage(BaseModel):
    """Règle de plage numérique [min, max] (bornes inclusives, min ou max seul autorisé)."""
    type: Literal["plage"] = "plage"
    champ: str
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def _au_moins_une_borne(self) -> "ReglePlage":
        if self.min is None and self.max is None:
            raise ValueError("ReglePlage doit avoir au moins une borne (min ou max)")
        return self


class RegleListe(BaseModel):
    """Règle d'appartenance à une liste de valeurs."""
    type: Literal["liste"] = "liste"
    champ: str
    valeurs: list[str | float | int]


class RegleNonNul(BaseModel):
    """Règle de non-nullité (rejette None, '', NaN)."""
    type: Literal["non_nul"] = "non_nul"
    champ: str


RegleFiltre = RegleEgal | ReglePlage | RegleListe | RegleNonNul


# ---------------------------------------------------------------------------
# Configuration filtre (un [[filtre]] TOML)
# ---------------------------------------------------------------------------

class ConfigFiltre(BaseModel):
    """Représente un [[filtre]] nommé du fichier configs_filtre.toml."""
    nom: str
    sortie: str
    description: str = ""
    regles: list[RegleEgal | ReglePlage | RegleListe | RegleNonNul] = field(
        default_factory=list
    )

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("nom")
    @classmethod
    def _nom_non_vide(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le nom du filtre ne peut pas être vide")
        return v

    @field_validator("sortie")
    @classmethod
    def _sortie_non_vide(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le champ 'sortie' du filtre ne peut pas être vide")
        return v


# ---------------------------------------------------------------------------
# Entité matériau dérivée (ConfigMatériau)
# ---------------------------------------------------------------------------

@dataclass
class ConfigMatériau:
    """Configuration matériau dérivée d'un ProduitValide.

    Contient toutes les propriétés mécaniques calculées selon EN 338 / EN 14080.
    Champ id_config_materiau : hash SHA-256 de (b_mm, h_mm, classe_resistance, L_max_m).
    """
    id_config_materiau: str
    b_mm: float
    h_mm: float
    classe_resistance: str
    L_max_m: float
    # Propriétés de section (cm²/cm⁴/cm³)
    A_cm2: float
    I_cm4: float
    W_cm3: float
    I_z_cm4: float    # requis EF-024 (double flexion)
    W_z_cm3: float    # requis EF-024
    # Propriétés élastiques (MPa)
    E_0_05_MPa: float  # = E_0_mean / 1.65, EC5 §3.3(3), requis EF-024 pour k_crit
    E_0_mean_MPa: float
    # Poids propre
    poids_propre_kNm: float
    # Résistances caractéristiques (MPa)
    f_m_k_MPa: float
    f_v_k_MPa: float
    f_c90_k_MPa: float
    rho_k_kgm3: float
