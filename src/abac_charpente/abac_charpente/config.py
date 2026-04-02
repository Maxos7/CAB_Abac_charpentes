"""Chargement et validation de la configuration TOML (config.toml + configs_calcul.toml).

Modèles pydantic (Principe X). Validation en français.
Résolution des limites de flèche depuis data/limites_fleche_ec5.csv (EF-023).
Expansion cartésienne EF-005c dans expandre_configs().
"""
from __future__ import annotations

import itertools
import sys
import tomllib
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from pydantic import BaseModel, field_validator, model_validator

from sapeg_regen_stock.modeles import ConfigFiltre, RegleEgal, ReglePlage, RegleListe, RegleNonNul
from abac_charpente.modeles.config_calcul import ConfigCalcul

# Limites de flèche depuis le CSV normatif
_DATA = Path(__file__).parent / "data"
_DF_LIMITES: pd.DataFrame | None = None


def _charger_limites_fleche() -> pd.DataFrame:
    global _DF_LIMITES
    if _DF_LIMITES is None:
        _DF_LIMITES = pd.read_csv(_DATA / "limites_fleche_ec5.csv", sep=";")
        _DF_LIMITES = _DF_LIMITES.set_index("usage")
    return _DF_LIMITES


# ---------------------------------------------------------------------------
# Modèles pydantic de configuration
# ---------------------------------------------------------------------------

class ConfigStock(BaseModel):
    repertoire: str = "."
    encodage: str = "latin-1"
    filtre_calcul: str | None = None


class ConfigSortie(BaseModel):
    fichier_csv: str = "resultats/portees_admissibles.csv"
    registre: str = "resultats/registre_calcul.csv"
    stock_enrichi: str = "stock_enrichi.csv"


class ConfigCalculGlobal(BaseModel):
    recalcul_complet: bool = False
    fichier_configs_calcul: str = "configs_calcul.toml"


class ConfigFiltresRef(BaseModel):
    fichier_configs_filtre: str = "configs_filtre.toml"


class ConfigCalculDefaults(BaseModel):
    longueur_appui_mm: float = 50.0
    k_c90: float = 1.0
    taux_cible_appui: float = 0.80


class AppConfig(BaseModel):
    stock: ConfigStock = ConfigStock()
    sortie: ConfigSortie = ConfigSortie()
    calcul: ConfigCalculGlobal = ConfigCalculGlobal()
    filtres: ConfigFiltresRef = ConfigFiltresRef()
    defaults: ConfigCalculDefaults = ConfigCalculDefaults()
    configs_calcul: list[ConfigCalcul] = []


# ---------------------------------------------------------------------------
# Chargement TOML
# ---------------------------------------------------------------------------

def charger_config(chemin: Path) -> AppConfig:
    """Charge config.toml et configs_calcul.toml, valide avec pydantic.

    Lève SystemExit(1) si le fichier est absent ou invalide.
    """
    if not chemin.exists():
        logger.error(f"Fichier de configuration introuvable : {chemin}")
        sys.exit(1)

    with open(chemin, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Erreur de lecture config.toml : {e}")
            sys.exit(1)

    try:
        stock = ConfigStock(**data.get("stock", {}))
        sortie = ConfigSortie(**data.get("sortie", {}))
        calcul = ConfigCalculGlobal(**data.get("calcul", {}) if not isinstance(data.get("calcul"), dict)
                                    else {k: v for k, v in data["calcul"].items() if k != "defaults"})
        filtres_ref = ConfigFiltresRef(**data.get("filtres", {}))
        defaults_data = data.get("calcul", {}).get("defaults", {})
        defaults = ConfigCalculDefaults(**defaults_data)
    except Exception as e:
        logger.error(f"Configuration invalide : {e}")
        sys.exit(1)

    # Chargement configs_calcul.toml
    configs_calcul_path = chemin.parent / calcul.fichier_configs_calcul
    configs_calcul = charger_configs_calcul(configs_calcul_path, defaults)

    return AppConfig(
        stock=stock,
        sortie=sortie,
        calcul=calcul,
        filtres=filtres_ref,
        defaults=defaults,
        configs_calcul=configs_calcul,
    )


def charger_configs_calcul(
    chemin: Path,
    defaults: ConfigCalculDefaults,
) -> list[ConfigCalcul]:
    """Charge configs_calcul.toml — liste de [[config_calcul]]."""
    if not chemin.exists():
        logger.error(f"Fichier de configs de calcul introuvable : {chemin}")
        sys.exit(1)

    with open(chemin, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Erreur de lecture configs_calcul.toml : {e}")
            sys.exit(1)

    blocs = data.get("config_calcul", [])
    if not blocs:
        logger.warning("configs_calcul.toml : aucune [[config_calcul]] trouvée.")
        return []

    limites = _charger_limites_fleche()
    configs: list[ConfigCalcul] = []

    for bloc in blocs:
        # Appliquer les défauts
        bloc.setdefault("longueur_appui_mm", defaults.longueur_appui_mm)
        bloc.setdefault("k_c90", defaults.k_c90)
        bloc.setdefault("taux_cible_appui", defaults.taux_cible_appui)

        # Résolution EF-023 : limites de flèche depuis CSV selon usage
        usage = bloc.get("usage", "TOITURE_INACC")
        if usage in limites.index:
            row = limites.loc[usage]
            # second_oeuvre par défaut depuis le CSV
            if "second_oeuvre" not in bloc:
                bloc["second_oeuvre"] = bool(row.get("second_oeuvre_defaut", False))
            # Limites flèche (inverseur L/x)
            if "limite_fleche_inst" not in bloc and pd.notna(row.get("w_inst_inv")):
                bloc["limite_fleche_inst"] = float(row["w_inst_inv"])
            if "limite_fleche_fin" not in bloc and pd.notna(row.get("w_fin_inv")):
                bloc["limite_fleche_fin"] = float(row["w_fin_inv"])
            if "limite_fleche_2" not in bloc and pd.notna(row.get("w_2_inv")):
                bloc["limite_fleche_2"] = float(row["w_2_inv"])

        # EF-024 : double_flexion auto si Panne ET pente > 0
        if bloc.get("type_poutre") == "Panne" and float(
            bloc.get("pente_deg", 0) if not isinstance(bloc.get("pente_deg"), list)
            else bloc["pente_deg"][0]
        ) > 0:
            bloc.setdefault("double_flexion", True)

        try:
            cfg = ConfigCalcul(**bloc)
        except Exception as e:
            logger.error(f"Config de calcul invalide (id={bloc.get('id_config_calcul', '?')}) : {e}")
            sys.exit(1)

        configs.append(cfg)

    return configs


def charger_filtres(chemin: Path) -> list[ConfigFiltre]:
    """Charge configs_filtre.toml — liste de [[filtre]].

    Fichier absent → avertissement stderr + liste vide (pas d'erreur fatale).
    Noms dupliqués → erreur code 1.
    """
    if not chemin.exists():
        logger.warning(
            f"Fichier de configuration des filtres introuvable : {chemin} "
            "— aucun filtre appliqué."
        )
        return []

    with open(chemin, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Erreur de lecture configs_filtre.toml : {e}")
            sys.exit(1)

    blocs = data.get("filtre", [])
    filtres: list[ConfigFiltre] = []
    noms_vus: set[str] = set()

    for bloc in blocs:
        nom = bloc.get("nom", "")
        if nom in noms_vus:
            logger.error(f"Nom de filtre dupliqué : '{nom}' — les noms doivent être uniques.")
            sys.exit(1)
        noms_vus.add(nom)

        # Conversion des règles TOML en objets pydantic
        regles_raw = bloc.get("regles", [])
        regles = []
        for r in regles_raw:
            t = r.get("type")
            if t == "egal":
                regles.append(RegleEgal(**r))
            elif t == "plage":
                regles.append(ReglePlage(**r))
            elif t == "liste":
                regles.append(RegleListe(**r))
            elif t == "non_nul":
                regles.append(RegleNonNul(**r))
            else:
                logger.error(f"Type de règle inconnu '{t}' dans le filtre '{nom}'.")
                sys.exit(1)

        try:
            filtre = ConfigFiltre(
                nom=nom,
                sortie=bloc["sortie"],
                description=bloc.get("description", ""),
                regles=regles,
            )
        except Exception as e:
            logger.error(f"Filtre invalide (nom={nom}) : {e}")
            sys.exit(1)

        filtres.append(filtre)

    return filtres


# ---------------------------------------------------------------------------
# Expansion cartésienne EF-005c
# ---------------------------------------------------------------------------

# ABBREV fixes pour les IDs enfants
_ABBREV: dict[str, str] = {
    "g_k_kNm2": "G",
    "q_k_kNm2": "Q",
    "s_k_kNm2": "S",
    "w_k_kNm2": "W",
    "pente_deg": "P",
    "entraxe_m": "E",
    "L_min_m": "Lmin",
    "pas_longueur_m": "pas",
    "longueur_appui_mm": "La",
    "k_c90": "kc90",
    "classe_service": "CS",
}

_CHAMPS_SCALAIRES = {
    "id_config_calcul", "type_poutre", "usage", "categorie_q",
    "type_toiture_vent", "second_oeuvre", "double_flexion",
    "entraxe_antideversement_mm", "marge_securite", "taux_cible_appui",
    "limite_fleche_inst", "limite_fleche_fin", "limite_fleche_2",
    "pas_longueur_m",
}


def expandre_configs(parent: ConfigCalcul) -> list[ConfigCalcul]:
    """Génère le produit cartésien des paramètres multivalués (EF-005c).

    Paramètres multivalués (float | list[float]) → sous-configs avec IDs dérivés.
    Avertissement stderr si > 200 sous-configs.
    Erreur code 1 en cas de collision d'ID.
    """
    champs_multivalues = [
        c for c in _ABBREV
        if isinstance(getattr(parent, c, None), list)
    ]

    if not champs_multivalues:
        return [parent]

    # Construire les listes de valeurs pour le produit cartésien
    listes: list[list] = []
    for champ in champs_multivalues:
        vals = getattr(parent, champ)
        listes.append(vals if isinstance(vals, list) else [vals])

    produit = list(itertools.product(*listes))
    if len(produit) > 200:
        logger.warning(
            f"Config '{parent.id_config_calcul}' : expansion cartésienne = {len(produit)} sous-configs "
            "(> 200) — le calcul peut être long."
        )

    ids_vus: set[str] = set()
    résultats: list[ConfigCalcul] = []

    parent_dict = parent.model_dump()

    for combo in produit:
        enfant_dict = parent_dict.copy()
        suffix_parts: list[str] = []

        for champ, val in zip(champs_multivalues, combo):
            enfant_dict[champ] = val
            abbrev = _ABBREV[champ]
            # Format : entier si pas de décimales
            val_str = str(int(val)) if isinstance(val, float) and val == int(val) else str(val)
            suffix_parts.append(f"{abbrev}{val_str}")

        id_enfant = f"{parent.id_config_calcul}_{'_'.join(suffix_parts)}"
        if id_enfant in ids_vus:
            logger.error(
                f"Collision d'ID détectée lors de l'expansion : '{id_enfant}'"
            )
            sys.exit(1)
        ids_vus.add(id_enfant)
        enfant_dict["id_config_calcul"] = id_enfant

        try:
            résultats.append(ConfigCalcul(**enfant_dict))
        except Exception as e:
            logger.error(f"Sous-config invalide (id={id_enfant}) : {e}")
            sys.exit(1)

    return résultats
