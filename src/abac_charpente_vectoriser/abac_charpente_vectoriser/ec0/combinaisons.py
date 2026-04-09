"""
ec0.combinaisons
================
Génération des combinaisons EC0 (EN 1990) adaptées au pipeline vectorisé EC5.

Les coefficients ψ sont lus depuis ``donnees/psi_coefficients.csv``
(aucune valeur normative hardcodée).

Combinaisons générées pour chaque config :
  ELU :
    - STR G+Q (Q principale)
    - STR G+S (S principale) — si s_k > 0
    - STR G+W (W principale) — si w_k > 0
  ELS :
    - CAR  (Q principale)
    - CAR  (S principale) — si s_k > 0
    - FREQ (Q principale)
    - QPERM (Q quasi-permanente)

La charge variable principale porte gamma_Q1 = 1.5 (ELU) ou 1.0 (ELS_CAR).
Les charges variables d'accompagnement sont pondérées par psi_0 (ELU) ou psi_1/psi_2 (ELS).

Durées de charge associées (EC5 Table 3.1) :
    G  → permanent
    Q (cat. H, A–E) → moyen_terme (AN France)
    S  → court_terme
    W  → instantane
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pandas as pd

from ..modeles.combinaison import CombinaisonEC0Vect
from ..modeles.config_calcul import ConfigCalculVect

# Durée de charge par type de charge variable (EC5 AN France)
_DUREE_CHARGE: dict[str, str] = {
    "Q": "moyen_terme",
    "S": "court_terme",
    "W": "instantane",
}


def _charger_psi(categorie_q: str, categorie_s: str = "neige") -> dict[str, dict[str, float]]:
    """Charge les coefficients ψ depuis donnees/psi_coefficients.csv.

    Parameters
    ----------
    categorie_q:
        Catégorie de charge variable d'exploitation (ex: "H", "A", "B").
    categorie_s:
        Catégorie pour la neige (ex: "neige", "neige_altitude").

    Returns
    -------
    dict[str, dict[str, float]]
        Dictionnaire ``{type_charge: {"psi_0": ..., "psi_1": ..., "psi_2": ...}}``.
    """
    chemin_csv = files("abac_charpente_vectoriser.donnees").joinpath("psi_coefficients.csv")
    df = pd.read_csv(str(chemin_csv), sep=";", comment="#")
    df = df.set_index("categorie")

    def _psi(cat: str) -> dict[str, float]:
        row = df.loc[cat]
        return {"psi_0": float(row["psi_0"]), "psi_1": float(row["psi_1"]), "psi_2": float(row["psi_2"])}

    return {
        "Q": _psi(categorie_q),
        "S": _psi(categorie_s),
        "W": _psi("vent"),
    }


def generer_combinaisons(config: ConfigCalculVect) -> list[CombinaisonEC0Vect]:
    """Génère toutes les combinaisons EC0 pertinentes pour une configuration de calcul.

    Produit les combinaisons ELU_STR et ELS (CAR, FREQ, QPERM) selon les charges
    actives dans ``config``. Une charge est active si sa valeur caractéristique > 0.

    Parameters
    ----------
    config:
        Configuration de calcul. Les valeurs multi-valuées ne sont pas développées ici —
        la fonction prend les scalaires issus du produit cartésien (appelée par le moteur).

    Returns
    -------
    list[CombinaisonEC0Vect]
        Liste des combinaisons EC0, ordonnée ELU puis ELS.
    """
    psi = _charger_psi(config.categorie_q)

    # Résolution des charges scalaires (en cas de multi-valeurs, le moteur passe des scalaires)
    q_actif = _scalaire(config.q_k_kNm2) > 0
    s_actif = _scalaire(config.s_k_kNm2) > 0
    w_actif = _scalaire(config.w_k_kNm2) > 0

    combinaisons: list[CombinaisonEC0Vect] = []

    # ── ELU STR ──────────────────────────────────────────────────────────────────
    charges_principales_elu: list[str] = []
    if q_actif:
        charges_principales_elu.append("Q")
    if s_actif:
        charges_principales_elu.append("S")
    if w_actif:
        charges_principales_elu.append("W")

    for ch_princ in charges_principales_elu:
        # Charges d'accompagnement : toutes les charges variables sauf la principale
        psi_0_accomp = max(
            (psi[ch]["psi_0"] for ch in ("Q", "S", "W") if ch != ch_princ and _charge_active(ch, config)),
            default=0.0,
        )
        combinaisons.append(CombinaisonEC0Vect(
            id_combinaison=f"ELU_STR_G+{ch_princ}",
            type_etat_limite="ELU",
            type_combinaison="STR",
            gamma_G=1.35,
            gamma_G2=1.35,
            gamma_Q1=1.50,
            gamma_Q_accomp=1.50 * psi_0_accomp,
            type_charge_principale=ch_princ,
            duree_charge=_DUREE_CHARGE[ch_princ],
        ))

    # Cas G seul si aucune charge variable (ou toujours ajouté pour robustesse)
    if not charges_principales_elu:
        combinaisons.append(CombinaisonEC0Vect(
            id_combinaison="ELU_STR_G",
            type_etat_limite="ELU",
            type_combinaison="STR",
            gamma_G=1.35,
            gamma_G2=1.35,
            gamma_Q1=0.0,
            gamma_Q_accomp=0.0,
            type_charge_principale="Q",
            duree_charge="permanent",
        ))

    # ── ELS CAR ──────────────────────────────────────────────────────────────────
    for ch_princ in charges_principales_elu or ["Q"]:
        psi_1_accomp = max(
            (psi[ch]["psi_1"] for ch in ("Q", "S", "W") if ch != ch_princ and _charge_active(ch, config)),
            default=0.0,
        )
        combinaisons.append(CombinaisonEC0Vect(
            id_combinaison=f"ELS_CAR_G+{ch_princ}",
            type_etat_limite="ELS",
            type_combinaison="CAR",
            gamma_G=1.0,
            gamma_G2=1.0,
            gamma_Q1=1.0,
            gamma_Q_accomp=psi_1_accomp,
            type_charge_principale=ch_princ,
            duree_charge=_DUREE_CHARGE[ch_princ],
        ))

    # ── ELS FREQ (Q principale uniquement) ───────────────────────────────────────
    if q_actif:
        psi_1_q = psi["Q"]["psi_1"]
        psi_2_s = psi["S"]["psi_2"] if s_actif else 0.0
        psi_2_w = psi["W"]["psi_2"] if w_actif else 0.0
        combinaisons.append(CombinaisonEC0Vect(
            id_combinaison="ELS_FREQ_G+Q",
            type_etat_limite="ELS",
            type_combinaison="FREQ",
            gamma_G=1.0,
            gamma_G2=1.0,
            gamma_Q1=psi_1_q,
            gamma_Q_accomp=max(psi_2_s, psi_2_w),
            type_charge_principale="Q",
            duree_charge=_DUREE_CHARGE["Q"],
        ))

    # ── ELS QPERM (quasi-permanente) ─────────────────────────────────────────────
    psi_2_q = psi["Q"]["psi_2"] if q_actif else 0.0
    psi_2_s = psi["S"]["psi_2"] if s_actif else 0.0
    combinaisons.append(CombinaisonEC0Vect(
        id_combinaison="ELS_QPERM",
        type_etat_limite="ELS",
        type_combinaison="QPERM",
        gamma_G=1.0,
        gamma_G2=1.0,
        gamma_Q1=psi_2_q,
        gamma_Q_accomp=psi_2_s,
        type_charge_principale="Q",
        duree_charge="permanent",
    ))

    return combinaisons


def _scalaire(v: float | list[float]) -> float:
    """Retourne la valeur scalaire ou le premier élément d'une liste."""
    return v[0] if isinstance(v, list) else v


def _charge_active(type_charge: str, config: ConfigCalculVect) -> bool:
    """Vérifie si une charge variable est active dans la configuration."""
    mapping = {"Q": config.q_k_kNm2, "S": config.s_k_kNm2, "W": config.w_k_kNm2}
    return _scalaire(mapping[type_charge]) > 0
