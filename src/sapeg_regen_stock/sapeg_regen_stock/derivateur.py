"""Dérivation ConfigMatériau + hash SHA-256 id_config_materiau (EF-004).

Fonctions exportées :
    hash_id_materiau(b_mm, h_mm, classe_resistance, L_max_m) -> str
    deriver_config_materiau(produit, proprietes) -> ConfigMatériau
    extraire_classe_resistance(libelle, mots_cles) -> str | None
"""
from __future__ import annotations

import hashlib
import re

from sapeg_regen_stock.modeles import ConfigMatériau, ProduitValide

# Regex de classes de résistance EN 338 / EN 14080
_RE_CLASSE = re.compile(
    r"\b(C1[6-9]|C2[0-9]|C3[0-5]|C40|D1[8-9]|D2[0-4]|D3[0-9]|D[4-7]\d|"
    r"GL2[4-9][hc]|GL3[0-6][hc]|GT1[8-9]|GT2[0-4])\b",
    re.IGNORECASE,
)

# Préfixe des IDs matériau
_PREFIXE = "MAT_"
_LONGUEUR_HEX = 8  # 8 caractères hexadécimaux


def hash_id_materiau(
    b_mm: float,
    h_mm: float,
    classe_resistance: str,
    L_max_m: float,
) -> str:
    """Calcule l'id_config_materiau par hash SHA-256.

    Sérialisation canonique : "b_mm|h_mm|classe|L_max_m" (arrondi 3 décimales).
    Retourne : "MAT_" + 8 premiers caractères hexadécimaux du hash.
    """
    clé = f"{round(b_mm, 3)}|{round(h_mm, 3)}|{classe_resistance.upper()}|{round(L_max_m, 3)}"
    digest = hashlib.sha256(clé.encode("utf-8")).hexdigest()
    return f"{_PREFIXE}{digest[:_LONGUEUR_HEX]}"


def deriver_config_materiau(
    produit: ProduitValide,
    proprietes: dict,
    section: dict,
) -> ConfigMatériau:
    """Dérive un ConfigMatériau depuis un ProduitValide et ses propriétés mécaniques.

    Paramètres :
        produit     : produit validé
        proprietes  : dict depuis ec5.proprietes.get_proprietes()
        section     : dict depuis ec5.proprietes.calculer_section()

    Retourne :
        ConfigMatériau avec tous les champs calculés.
    """
    return ConfigMatériau(
        id_config_materiau=produit.id_config_materiau,
        b_mm=produit.b_mm,
        h_mm=produit.h_mm,
        classe_resistance=produit.classe_resistance,
        L_max_m=produit.L_max_m,
        A_cm2=section["A_cm2"],
        I_cm4=section["I_cm4"],
        W_cm3=section["W_cm3"],
        I_z_cm4=section["I_z_cm4"],
        W_z_cm3=section["W_z_cm3"],
        E_0_05_MPa=proprietes["E_0_05_MPa"],
        E_0_mean_MPa=proprietes["E_0_mean_MPa"],
        poids_propre_kNm=section["poids_propre_kNm"],
        f_m_k_MPa=proprietes["f_m_k_MPa"],
        f_v_k_MPa=proprietes["f_v_k_MPa"],
        f_c90_k_MPa=proprietes["f_c90_k_MPa"],
        rho_k_kgm3=proprietes["rho_k_kgm3"],
    )


def extraire_classe_resistance(libelle: str, mots_cles: str) -> str | None:
    """Extrait la classe de résistance depuis un libellé ou mots-clés.

    Cherche d'abord dans mots_cles, puis dans libelle.
    Retourne None si aucune classe reconnue n'est trouvée.
    """
    for texte in [mots_cles, libelle]:
        m = _RE_CLASSE.search(str(texte))
        if m:
            classe = m.group(0).upper()
            # GL/GT : suffixe h/c obligatoirement en minuscules (EN 14080)
            if classe.startswith(("GL", "GT")):
                classe = classe[:-1] + classe[-1].lower()
            return classe
    return None


def enrichir_produit(produit_stock, _id_config_materiau: str) -> ProduitValide:
    """Convertit un ProduitStock en ProduitValide avec l'id_config_materiau calculé."""
    return ProduitValide(
        id_produit=produit_stock.id_produit,
        libelle=produit_stock.libelle,
        b_mm=produit_stock.b_mm,
        h_mm=produit_stock.h_mm,
        L_max_m=produit_stock.L_max_m,
        classe_resistance=produit_stock.classe_resistance,
        famille=produit_stock.famille,
        disponible=produit_stock.disponible,
        fournisseur=produit_stock.fournisseur,
        id_config_materiau=_id_config_materiau,
        classe_dans_libelle=produit_stock.classe_dans_libelle,
        ligne_csv_source=produit_stock.ligne_csv_source,
    )
