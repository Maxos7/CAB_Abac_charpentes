"""
chargeur.depuis_csv
===================
Chargement des matériaux depuis un fichier CSV stock (format SAPEG ou compatible).

Le CSV doit au minimum contenir les colonnes ``b_mm``, ``h_mm`` et ``classe_resistance``.
Les propriétés mécaniques sont récupérées dans ``donnees/materiaux_bois.csv``
par jointure sur ``classe_resistance``.

Les propriétés de section (A, I, W) sont calculées par le derivateur pour les sections
rectangulaires. Pour les sections personnalisées, utiliser ``depuis_dict.py``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..modeles.config_materiau import ConfigMatériauVect
from .derivateur import deriver_section_rect
from importlib.resources import files


def _charger_materiaux_bois() -> pd.DataFrame:
    """Charge la table des propriétés mécaniques depuis donnees/materiaux_bois.csv."""
    chemin: str = str(files("abac_charpente_vectoriser.donnees").joinpath("materiaux_bois.csv"))
    return pd.read_csv(chemin, sep=";", comment="#")


def charger_depuis_csv(
    chemin_stock: Path,
    separateur: str = ";",
) -> list[ConfigMatériauVect]:
    """Charge une liste de configurations matériau depuis un CSV stock.

    Le CSV stock doit contenir au minimum les colonnes :
    - ``b_mm``              : largeur de la section en mm
    - ``h_mm``              : hauteur de la section en mm
    - ``classe_resistance`` : classe EN 338 / EN 14080 (ex: "C24", "GL28h")

    Une colonne optionnelle ``id_config_materiau`` peut fournir un identifiant
    personnalisé. Sinon, l'identifiant est généré automatiquement (``classe_b×h``).

    Parameters
    ----------
    chemin_stock:
        Chemin vers le fichier CSV stock.
    separateur:
        Séparateur de colonnes (défaut ``";"``) .

    Returns
    -------
    list[ConfigMatériauVect]
        Liste de configurations matériau, une par ligne du CSV stock.

    Raises
    ------
    ValueError
        Si une classe de résistance du CSV stock n'est pas dans la table normative.
    """
    df_stock: pd.DataFrame = pd.read_csv(chemin_stock, sep=separateur, comment="#")

    # Exclure les lignes sans classe_resistance valide (produits exclus du filtrage SAPEG)
    if "statut_filtre" in df_stock.columns:
        df_stock = df_stock[df_stock["statut_filtre"] == "retenu"].reset_index(drop=True)
    elif "statut_ingestion" in df_stock.columns:
        df_stock = df_stock[df_stock["statut_ingestion"] == "valide"].reset_index(drop=True)
    else:
        df_stock = df_stock[df_stock["classe_resistance"].notna()].reset_index(drop=True)

    df_mat: pd.DataFrame = _charger_materiaux_bois().set_index("classe")

    configs: list[ConfigMatériauVect] = []
    for _, ligne in df_stock.iterrows():
        classe: str = str(ligne["classe_resistance"])
        if classe not in df_mat.index:
            raise ValueError(
                f"Classe '{classe}' non trouvée dans materiaux_bois.csv. "
                f"Classes disponibles : {list(df_mat.index)}"
            )
        b_mm: float = float(ligne["b_mm"])
        h_mm: float = float(ligne["h_mm"])
        props_mat: pd.Series = df_mat.loc[classe]
        props_section: dict[str, float] = deriver_section_rect(b_mm, h_mm)

        if "id_config_materiau" in df_stock.columns and not pd.isna(ligne["id_config_materiau"]):
            id_mat: str = str(ligne["id_config_materiau"])
        else:
            id_mat = f"{classe}_{int(b_mm)}x{int(h_mm)}"

        id_produit: str = (
            str(int(ligne["id_produit"]))
            if "id_produit" in df_stock.columns and not pd.isna(ligne["id_produit"])
            else ""
        )
        libelle: str = (
            str(ligne["libelle"])
            if "libelle" in df_stock.columns and not pd.isna(ligne["libelle"])
            else ""
        )

        configs.append(ConfigMatériauVect(
            id_config_materiau=id_mat,
            classe_resistance=classe,
            famille=str(props_mat["famille"]),
            id_produit=id_produit,
            libelle=libelle,
            b_mm=b_mm,
            h_mm=h_mm,
            A_cm2=props_section["A_cm2"],
            I_y_cm4=props_section["I_y_cm4"],
            I_z_cm4=props_section["I_z_cm4"],
            W_y_cm3=props_section["W_y_cm3"],
            W_z_cm3=props_section["W_z_cm3"],
            A_eff_cisaillement_cm2=props_section["A_eff_cisaillement_cm2"],
            f_m_k_MPa=float(props_mat["f_m_k_MPa"]),
            f_v_k_MPa=float(props_mat["f_v_k_MPa"]),
            f_c90_k_MPa=float(props_mat["f_c90_k_MPa"]),
            f_t0_k_MPa=float(props_mat["f_t0_k_MPa"]),
            f_c0_k_MPa=float(props_mat["f_c0_k_MPa"]),
            E_0_mean_MPa=float(props_mat["E_0_mean_MPa"]),
            E_0_05_MPa=float(props_mat["E_0_05_MPa"]),
            rho_k_kgm3=float(props_mat["rho_k_kgm3"]),
        ))

    return configs
