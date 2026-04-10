"""
sortie.tenseur_duck
===================
Stockage des tenseurs de taux EC5 dans DuckDB (import paresseux).

Remplace le store zarr par une base SQL fichier, queryable directement.
DuckDB supporte nativement les colonnes ``FLOAT[]`` (listes), ce qui permet
de stocker les vecteurs de taux par matériau sans sérialisation binaire externe.

Schéma
------
``taux``
    Une ligne par triplet (id_combo, verif_id, longueur_m).
    La colonne ``taux`` est un vecteur ``FLOAT[]`` de longueur n_M (un taux
    par matériau). Requêtes utiles :

    .. code-block:: sql

        -- Max taux par vérification pour un combo donné
        SELECT verif_id, MAX(list_max(taux)) AS taux_max
        FROM taux
        WHERE id_combo = 'PANNE_APLOMB_P30_E1.2'
          AND type_verif = 'ELU'
        GROUP BY verif_id
        ORDER BY taux_max DESC;

        -- Taux d'un matériau précis à une portée donnée
        SELECT taux[position + 1] AS taux_mat
        FROM taux
        JOIN materiaux_combo USING (id_combo)
        WHERE taux.id_combo = 'PANNE_APLOMB_P30_E1.2'
          AND verif_id = 'FlexionSimple'
          AND longueur_m = 4.0
          AND id_config_materiau = 'MAT_748238e9';

``materiaux_combo``
    Référentiel des matériaux par combo — joint avec ``taux`` sur ``id_combo``.
    La colonne ``position`` est l'index 0-based dans le vecteur ``taux``.

Usage
-----
    from abac_charpente_vectoriser.sortie.tenseur_duck import TenseurDuck

    with TenseurDuck(Path("resultats/tenseurs.duckdb")) as store:
        store.sauvegarder(id_combo, longueurs_m, taux_elu, taux_els, materiaux)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..modeles.config_materiau import ConfigMatériauVect


_DDL_TAUX = """
CREATE TABLE IF NOT EXISTS taux (
    id_combo    VARCHAR  NOT NULL,
    type_verif  VARCHAR  NOT NULL,
    verif_id    VARCHAR  NOT NULL,
    longueur_m  FLOAT    NOT NULL,
    taux        FLOAT[]  NOT NULL,
    horodatage  TIMESTAMP NOT NULL,
    PRIMARY KEY (id_combo, verif_id, longueur_m)
)
"""

_DDL_MATERIAUX = """
CREATE TABLE IF NOT EXISTS materiaux_combo (
    id_combo           VARCHAR  NOT NULL,
    position           INTEGER  NOT NULL,
    id_config_materiau VARCHAR  NOT NULL,
    id_produit         VARCHAR,
    libelle            VARCHAR,
    classe_resistance  VARCHAR,
    b_mm               FLOAT,
    h_mm               FLOAT,
    PRIMARY KEY (id_combo, position)
)
"""


class TenseurDuck:
    """Store DuckDB pour les tenseurs de taux EC5.

    Ouvre ou crée le fichier DuckDB et initialise les tables au premier appel.

    Parameters
    ----------
    chemin_db:
        Chemin vers le fichier DuckDB (ex: ``resultats/tenseurs.duckdb``).
        Utiliser ``":memory:"`` pour un store volatile (tests).
    """

    def __init__(self, chemin_db: Path | str = ":memory:") -> None:
        import duckdb  # lazy import

        chemin_str: str = str(chemin_db)
        if chemin_str != ":memory:":
            Path(chemin_str).parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(chemin_str)
        self._conn.execute(_DDL_TAUX)
        self._conn.execute(_DDL_MATERIAUX)

    def sauvegarder(
        self,
        id_combo: str,
        longueurs_m: np.ndarray,
        taux_elu: dict[str, np.ndarray],
        taux_els: dict[str, np.ndarray],
        materiaux: list[ConfigMatériauVect],
    ) -> None:
        """Sauvegarde les tenseurs de taux d'un combo dans DuckDB.

        Chaque vérification (ELU ou ELS) génère ``n_L`` lignes dans la table
        ``taux``. Le vecteur ``taux`` de chaque ligne contient les ``n_M`` taux
        correspondant aux matériaux (même ordre que ``materiaux``).

        Si le combo existe déjà (PRIMARY KEY), les lignes sont remplacées.

        Parameters
        ----------
        id_combo:
            Identifiant unique du combo (ex: ``"PANNE_APLOMB_P30_E1.2"``).
        longueurs_m:
            Vecteur de portées ``(n_L,)``.
        taux_elu:
            Résultats ELU ``{verif_id: (n_L, n_M)}``.
        taux_els:
            Résultats ELS ``{verif_id: (n_L, n_M)}``.
        materiaux:
            Liste des configurations matériau ``(n_M,)``.
        """
        horodatage: datetime = datetime.now(timezone.utc)

        # Suppression des données existantes pour ce combo (idempotent)
        self._conn.execute("DELETE FROM taux WHERE id_combo = ?", [id_combo])
        self._conn.execute("DELETE FROM materiaux_combo WHERE id_combo = ?", [id_combo])

        # Référentiel matériaux
        mat_rows: list[tuple] = [
            (
                id_combo,
                idx,
                mat.id_config_materiau,
                mat.id_produit or None,
                mat.libelle or None,
                mat.classe_resistance,
                mat.b_mm,
                mat.h_mm,
            )
            for idx, mat in enumerate(materiaux)
        ]
        self._conn.executemany(
            "INSERT INTO materiaux_combo VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            mat_rows,
        )

        # Tenseurs taux — une ligne par (verif, longueur)
        taux_rows: list[tuple] = []
        for verif_id, arr in taux_elu.items():
            for l_idx, L in enumerate(longueurs_m):
                taux_rows.append((
                    id_combo, "ELU", verif_id, float(L),
                    arr[l_idx].tolist(), horodatage,
                ))
        for verif_id, arr in taux_els.items():
            for l_idx, L in enumerate(longueurs_m):
                taux_rows.append((
                    id_combo, "ELS", verif_id, float(L),
                    arr[l_idx].tolist(), horodatage,
                ))

        self._conn.executemany(
            "INSERT INTO taux VALUES (?, ?, ?, ?, ?, ?)",
            taux_rows,
        )

    def fermer(self) -> None:
        """Ferme la connexion DuckDB."""
        self._conn.close()

    def __enter__(self) -> "TenseurDuck":
        return self

    def __exit__(self, *_) -> None:
        self.fermer()
