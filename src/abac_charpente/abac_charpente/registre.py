"""Registre de calcul incrémental (EF-006, EF-007).

Persistance CSV : id_config_materiau;id_config_calcul;statut;horodatage_iso
Lookup O(1) via ensemble frozenset en mémoire.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger


_COLONNES = ["id_config_materiau", "id_config_calcul", "statut", "horodatage_iso"]


class RegistreCalcul:
    """Registre persistant des couples (id_config_materiau, id_config_calcul) calculés.

    Usage :
        registre = RegistreCalcul()
        registre.charger(Path("registre.csv"))
        if not registre.est_calcule(id_mat, id_calc):
            # ... calcul ...
            registre.enregistrer(id_mat, id_calc, "calcule")
    """

    def __init__(self) -> None:
        self._calcules: set[tuple[str, str]] = set()
        self._df: pd.DataFrame = pd.DataFrame(columns=_COLONNES)
        self._chemin: Path | None = None
        self._force_recalcul: bool = False

    def charger(self, chemin: Path) -> None:
        """Charge le registre depuis un CSV existant ou crée un registre vide."""
        self._chemin = chemin
        if not chemin.exists():
            logger.info(f"Registre absent — créé à {chemin}. Calcul complet.")
            self._df = pd.DataFrame(columns=_COLONNES)
            self._calcules = set()
            return

        try:
            df = pd.read_csv(chemin, sep=";", dtype=str)
            # Vérification colonnes minimales
            if not {"id_config_materiau", "id_config_calcul"}.issubset(df.columns):
                raise ValueError("Colonnes obligatoires manquantes.")
            self._df = df
            self._calcules = {
                (str(row["id_config_materiau"]), str(row["id_config_calcul"]))
                for _, row in df.iterrows()
            }
            logger.info(f"Registre chargé : {len(self._calcules)} entrées depuis {chemin}")
        except Exception as e:
            logger.warning(
                f"AVERTISSEMENT : Registre illisible ({e}) — recalcul complet forcé."
            )
            self._df = pd.DataFrame(columns=_COLONNES)
            self._calcules = set()
            self._force_recalcul = True

    def est_calcule(self, id_mat: str, id_calc: str) -> bool:
        """Retourne True si ce couple a déjà été calculé."""
        if self._force_recalcul:
            return False
        return (id_mat, id_calc) in self._calcules

    def enregistrer(self, id_mat: str, id_calc: str, statut: str = "calcule") -> None:
        """Enregistre un couple et flushte immédiatement sur disque."""
        if (id_mat, id_calc) in self._calcules:
            return  # déjà présent — pas de doublon

        self._calcules.add((id_mat, id_calc))
        nouvelle_ligne = {
            "id_config_materiau": id_mat,
            "id_config_calcul": id_calc,
            "statut": statut,
            "horodatage_iso": datetime.now().isoformat(timespec="seconds"),
        }
        self._df = pd.concat(
            [self._df, pd.DataFrame([nouvelle_ligne])], ignore_index=True
        )

        if self._chemin is not None:
            self._flush()

    def reconstruire(self, df: pd.DataFrame) -> None:
        """Réécrit le registre complet (utilisé après recalcul_complet)."""
        self._df = df
        if self._chemin is not None:
            self._flush()

    def _flush(self) -> None:
        """Écrit le registre sur disque (création répertoire si nécessaire)."""
        if self._chemin is None:
            return
        try:
            self._chemin.parent.mkdir(parents=True, exist_ok=True)
            self._df.to_csv(self._chemin, sep=";", encoding="utf-8", index=False)
        except Exception as e:
            logger.warning(f"AVERTISSEMENT : Impossible d'écrire le registre ({e}).")
