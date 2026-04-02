"""Orchestrateur du calcul EC5 (EF-008, EF-010, EF-017, EF-026).

Boucle : mat × calc × L × combis + marge_securite.
Déduplication par id_config_materiau (EF-004).
Recalcul incrémental via RegistreCalcul (EF-006, EF-007).
Application marge_securite EF-026 : taux_effectif = taux × (1 + marge_securite).
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from loguru import logger

if TYPE_CHECKING:
    from abac_charpente.config import AppConfig
    from sapeg_regen_stock.modeles import ConfigFiltre

from sapeg_regen_stock.modeles import ConfigMatériau, ProduitValide
from abac_charpente.modeles.config_calcul import ConfigCalcul
from abac_charpente.modeles.resultat_portee import RésultatPortée
from abac_charpente.ec5.types_poutre import instancier
from abac_charpente.ec5.proprietes import get_proprietes, calculer_section, get_famille
from abac_charpente.ec5.elu import verifier_elu
from abac_charpente.ec5.els import verifier_els
from abac_charpente.ec0.combinaisons import generer_combinaisons
from abac_charpente.sortie import ecrire_sortie, COLONNES_SORTIE
from abac_charpente.derivateur_local import deriver_materiau


def lancer_calcul(
    app_config: "AppConfig",
    filtres: list["ConfigFiltre"],
    stock_override: Path | None = None,
    recalcul_complet: bool = False,
    verbose: bool = False,
) -> None:
    """Lance le calcul complet de portées admissibles.

    Étapes :
        1. Appel pipeline sapeg_regen_stock.run()
        2. Lecture CSV cible (selon filtre_calcul ou stock_enrichi)
        3. Groupement par id_config_materiau
        4. Boucle mat × calc (avec registre incrémental)
        5. Application marge_securite EF-026
        6. Sélection top-10 combinaisons / longueur
        7. Construction RésultatPortée + réplication par produit
        8. Écriture CSV de sortie
    """
    import sapeg_regen_stock

    # 1. Pipeline stock
    source = stock_override or Path(app_config.stock.repertoire)
    stock_enrichi_path = Path(app_config.sortie.stock_enrichi)

    try:
        dict_filtres = sapeg_regen_stock.run(source, filtres, stock_enrichi_path)
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Erreur pipeline stock : {e}")
        sys.exit(1)

    # 2. Lecture CSV cible
    filtre_calcul = app_config.stock.filtre_calcul
    if filtre_calcul:
        if filtre_calcul not in dict_filtres:
            logger.error(
                f"filtre_calcul='{filtre_calcul}' introuvable dans les filtres générés "
                f"({list(dict_filtres.keys())}). Vérifier configs_filtre.toml."
            )
            sys.exit(1)
        chemin_stock_calcul = dict_filtres[filtre_calcul]
    else:
        chemin_stock_calcul = stock_enrichi_path

    produits_valides = _lire_produits_csv(chemin_stock_calcul)
    if not produits_valides:
        logger.error("Aucun produit après filtrage — calcul annulé.")
        sys.exit(3)

    logger.info(f"{len(produits_valides)} produits chargés pour le calcul.")

    # 3. Groupement par id_config_materiau
    groupes: dict[str, list[ProduitValide]] = {}
    for p in produits_valides:
        groupes.setdefault(p.id_config_materiau, []).append(p)

    # 4. Registre de calcul
    from abac_charpente.registre import RegistreCalcul
    chemin_registre = Path(app_config.sortie.registre)
    registre = RegistreCalcul()
    registre.charger(chemin_registre)

    if recalcul_complet:
        registre._force_recalcul = True

    chemin_sortie = Path(app_config.sortie.fichier_csv)
    horodatage = datetime.now().isoformat(timespec="seconds")

    tous_résultats: list[RésultatPortée] = []

    # 5. Boucle mat × calc
    for id_mat, produits_groupe in groupes.items():
        # Représentant du groupe (premier produit)
        p_rep = produits_groupe[0]

        # Dérivation ConfigMatériau
        try:
            materiau = deriver_materiau(p_rep)
        except Exception as e:
            logger.warning(f"AVERTISSEMENT [{p_rep.id_produit}] : dérivation matériau impossible — {e}")
            continue

        for config in app_config.configs_calcul:
            id_calc = config.id_config_calcul

            if not registre._force_recalcul and registre.est_calcule(id_mat, id_calc):
                if verbose:
                    logger.info(f"Résultats existants pour ({id_mat}, {id_calc}) — ignoré.")
                continue

            # Génération des longueurs
            L_min = float(config.L_min_m if isinstance(config.L_min_m, (int, float)) else config.L_min_m[0])
            pas = float(config.pas_longueur_m)
            L_max = p_rep.L_max_m
            longueurs_m = np.arange(L_min, L_max + pas / 2, pas)
            if len(longueurs_m) == 0:
                continue

            # Combinaisons EC0
            combinaisons = generer_combinaisons(config)
            type_poutre = instancier(config.type_poutre)

            # Vérifications ELU + ELS
            try:
                résultats_elu = verifier_elu(materiau, config, type_poutre, longueurs_m, combinaisons)
                résultats_els = verifier_els(materiau, config, type_poutre, longueurs_m, combinaisons)
            except Exception as e:
                logger.warning(
                    f"AVERTISSEMENT [{id_mat}/{id_calc}] : erreur calcul — {e} — ignoré."
                )
                continue

            # Double flexion (EF-024)
            if config.double_flexion:
                try:
                    from abac_charpente.ec5.double_flexion import verifier_double_flexion
                    from abac_charpente.ec5.proprietes import get_kmod, get_gamma_m
                    # Prendre la combinaison la plus défavorable ELU pour df
                    combi_elu = [c for c in combinaisons if c.type_combinaison == "ELU_STR"]
                    if combi_elu:
                        combi_df = combi_elu[0]
                        charges_df = type_poutre.charges_lineaires(config, materiau, longueurs_m, combi_df)
                        q_y = charges_df.get("q_y_kNm", charges_df["q_d_kNm"])
                        q_z = charges_df.get("q_z_kNm", np.zeros_like(q_y))
                        famille = get_famille(materiau.classe_resistance)
                        cs = int(config.classe_service if isinstance(config.classe_service, int) else config.classe_service[0])
                        k_mod = get_kmod(famille, cs, combi_df.duree_charge)
                        gamma_M = get_gamma_m(famille)
                        résultats_df = verifier_double_flexion(
                            materiau, config, longueurs_m, q_y, q_z, k_mod, gamma_M
                        )
                    else:
                        résultats_df = []
                except Exception as e:
                    logger.warning(f"AVERTISSEMENT [{id_mat}/{id_calc}] : double flexion — {e}")
                    résultats_df = []
            else:
                résultats_df = []

            # Application marge_securite EF-026
            marge = config.marge_securite
            résultats_elu = _appliquer_marge(résultats_elu, marge)
            résultats_els = _appliquer_marge(résultats_els, marge)

            # Construction et réplication RésultatPortée
            résultats_groupe = _construire_résultats(
                horodatage=horodatage,
                produits_groupe=produits_groupe,
                materiau=materiau,
                config=config,
                résultats_elu=résultats_elu,
                résultats_els=résultats_els,
                résultats_df=résultats_df,
            )

            tous_résultats.extend(résultats_groupe)
            registre.enregistrer(id_mat, id_calc, "calcule")

    # 6. Écriture CSV de sortie
    if tous_résultats:
        ecrire_sortie(tous_résultats, chemin_sortie)
        logger.info(f"Calcul terminé : {len(tous_résultats)} lignes écrites dans {chemin_sortie}")
    else:
        logger.info("Aucun nouveau résultat à écrire.")

    # 7. Reconstruction registre si recalcul_complet
    if recalcul_complet:
        registre.reconstruire(registre._df)


def _lire_produits_csv(chemin: Path) -> list[ProduitValide]:
    """Lit un CSV de produits enrichis et retourne une liste de ProduitValide."""
    if not chemin.exists():
        logger.error(f"CSV stock introuvable : {chemin}")
        sys.exit(1)
    try:
        df = pd.read_csv(chemin, sep=";", dtype=str)
    except Exception as e:
        logger.error(f"Erreur lecture CSV stock : {e}")
        sys.exit(1)

    produits: list[ProduitValide] = []
    for _, row in df.iterrows():
        if str(row.get("statut_ingestion", "valide")).strip() not in ("valide", "retenu", ""):
            continue
        try:
            produits.append(ProduitValide(
                id_produit=str(row["id_produit"]),
                libelle=str(row.get("libelle", "")),
                b_mm=float(row["b_mm"]),
                h_mm=float(row["h_mm"]),
                L_max_m=float(row["L_max_m"]),
                classe_resistance=str(row["classe_resistance"]),
                famille=str(row.get("famille", "bois_massif")),
                disponible=str(row.get("disponible", "True")).lower() in ("true", "1", "oui"),
                fournisseur=str(row.get("fournisseur", "")),
                id_config_materiau=str(row["id_config_materiau"]),
            ))
        except (KeyError, ValueError) as e:
            logger.warning(f"Ligne ignorée ({row.get('id_produit', '?')}) : {e}")

    return produits


def _appliquer_marge(résultats: list[dict], marge: float) -> list[dict]:
    """Applique taux_effectif = taux × (1 + marge_securite) sur tous les taux (EF-026)."""
    if marge == 0.0:
        return résultats
    champs_taux = [k for k in (résultats[0].keys() if résultats else []) if "taux" in k]
    for r in résultats:
        for k in champs_taux:
            v = r.get(k)
            if v is not None and isinstance(v, float):
                r[k] = v * (1.0 + marge)
    return résultats


def _construire_résultats(
    horodatage: str,
    produits_groupe: list[ProduitValide],
    materiau: ConfigMatériau,
    config: ConfigCalcul,
    résultats_elu: list[dict],
    résultats_els: list[dict],
    résultats_df: list[dict],
) -> list[RésultatPortée]:
    """Construit et réplique les RésultatPortée pour chaque produit du groupe."""
    # Grouper ELS par (longueur_m, id_combinaison)
    els_index: dict[tuple, dict] = {}
    for r in résultats_els:
        key = (round(r["longueur_m"], 3), r["id_combinaison"])
        els_index[key] = r

    df_index: dict[float, dict] = {}
    for r in résultats_df:
        df_index[round(r["longueur_m"], 3)] = r

    résultats_base: list[RésultatPortée] = []

    for elu in résultats_elu:
        L_m = round(elu["longueur_m"], 3)
        id_combi = elu["id_combinaison"]

        # ELS associé (même longueur, combinaison ELS_CAR si dispo)
        els_key_car = (L_m, "ELS_CAR_Q") if config.q_k_kNm2 else (L_m, "ELS_CAR_G")
        els = els_index.get(els_key_car) or els_index.get((L_m, "ELS_CAR_G"), {})
        df_res = df_index.get(L_m, {})

        # Taux déterminant
        taux_elu = max(
            elu.get("taux_flexion_ELU", 0) or 0,
            elu.get("taux_cisaillement_ELU", 0) or 0,
            elu.get("taux_appui_ELU", 0) or 0,
            elu.get("taux_deversement_ELU", 0) or 0,
        )
        taux_els = max(
            els.get("taux_ELS_inst", 0) or 0,
            els.get("taux_ELS_fin", 0) or 0,
            els.get("taux_ELS_2", 0) or 0,
        )
        if df_res:
            taux_elu = max(taux_elu,
                           df_res.get("taux_biaxial_1_ELU", 0) or 0,
                           df_res.get("taux_biaxial_2_ELU", 0) or 0)

        taux_determinant = max(taux_elu, taux_els)

        # Statut
        statut_usage = els.get("statut_usage", "ok")
        if statut_usage == "rejeté_usage":
            statut = "rejeté_usage"
        elif taux_determinant <= 1.0:
            statut = "admis"
        else:
            statut = "refusé"

        r = RésultatPortée(
            horodatage_iso=horodatage,
            id_produit=produits_groupe[0].id_produit,
            id_config_materiau=materiau.id_config_materiau,
            id_config_calcul=config.id_config_calcul,
            type_poutre=config.type_poutre,
            usage=config.usage,
            second_oeuvre=config.second_oeuvre,
            double_flexion=config.double_flexion,
            entraxe_antideversement_mm=config.entraxe_antideversement_mm,
            longueur_m=float(elu["longueur_m"]),
            longueur_projetee_m=elu.get("longueur_projetee_m"),
            id_combinaison=id_combi,
            type_combinaison=elu["type_combinaison"],
            b_mm=materiau.b_mm,
            h_mm=materiau.h_mm,
            classe_resistance=materiau.classe_resistance,
            L_max_m=materiau.L_max_m,
            A_cm2=materiau.A_cm2,
            I_cm4=materiau.I_cm4,
            W_cm3=materiau.W_cm3,
            I_z_cm4=materiau.I_z_cm4 if config.double_flexion else None,
            W_z_cm3=materiau.W_z_cm3 if config.double_flexion else None,
            poids_propre_kNm=materiau.poids_propre_kNm,
            f_m_k_MPa=materiau.f_m_k_MPa,
            f_v_k_MPa=materiau.f_v_k_MPa,
            k_mod=elu.get("k_mod", 0.0),
            gamma_M=elu.get("gamma_M", 1.3),
            f_m_d_MPa=elu.get("f_m_d_MPa", 0.0),
            f_v_d_MPa=elu.get("f_v_d_MPa", 0.0),
            q_G_kNm=elu.get("q_G_kNm", 0.0),
            q_Q_kNm=elu.get("q_Q_kNm", 0.0),
            q_S_kNm=elu.get("q_S_kNm", 0.0),
            q_W_kNm=elu.get("q_W_kNm", 0.0),
            gamma_G=elu.get("gamma_G", 1.35),
            charge_principale=elu.get("charge_principale", "G"),
            gamma_Q1=elu.get("gamma_Q1", 0.0),
            psi_0_Q2=elu.get("psi_0_Q2", 0.0),
            psi_0_Q3=elu.get("psi_0_Q3", 0.0),
            q_combinee_kNm=elu.get("q_combinee_kNm", 0.0),
            M_max_kNm=elu.get("M_max_kNm", 0.0),
            V_max_kN=elu.get("V_max_kN", 0.0),
            M_z_kNm=elu.get("M_z_kNm") if config.double_flexion else None,
            sigma_m_MPa=elu.get("sigma_m_MPa", 0.0),
            taux_flexion_ELU=elu.get("taux_flexion_ELU", 0.0),
            tau_MPa=elu.get("tau_MPa", 0.0),
            taux_cisaillement_ELU=elu.get("taux_cisaillement_ELU", 0.0),
            f_c90_k_MPa=elu.get("f_c90_k_MPa", 0.0),
            f_c90_d_MPa=elu.get("f_c90_d_MPa", 0.0),
            sigma_c90_MPa=elu.get("sigma_c90_MPa", 0.0),
            k_c90=elu.get("k_c90", 1.0),
            longueur_appui_mm=elu.get("longueur_appui_mm", 50.0),
            taux_cible_appui=elu.get("taux_cible_appui", 0.8),
            longueur_appui_min_mm=elu.get("longueur_appui_min_mm", 0.0),
            taux_appui_ELU=elu.get("taux_appui_ELU", 0.0),
            k_crit=elu.get("k_crit", 1.0),
            L_deversement_m=elu.get("L_deversement_m") if config.double_flexion else None,
            taux_deversement_ELU=elu.get("taux_deversement_ELU", 0.0),
            sigma_m_y_MPa=df_res.get("sigma_m_y_MPa") if df_res else None,
            sigma_m_z_MPa=df_res.get("sigma_m_z_MPa") if df_res else None,
            k_m=df_res.get("k_m") if df_res else None,
            taux_biaxial_1_ELU=df_res.get("taux_biaxial_1_ELU") if df_res else None,
            taux_biaxial_2_ELU=df_res.get("taux_biaxial_2_ELU") if df_res else None,
            w_inst_mm=els.get("w_inst_mm", 0.0),
            limite_inst_mm=els.get("limite_inst_mm", 0.0),
            taux_ELS_inst=els.get("taux_ELS_inst", 0.0),
            w_creep_mm=els.get("w_creep_mm", 0.0),
            w_fin_mm=els.get("w_fin_mm", 0.0),
            limite_fin_mm=els.get("limite_fin_mm", 0.0),
            taux_ELS_fin=els.get("taux_ELS_fin", 0.0),
            w_2_mm=els.get("w_2_mm"),
            limite_2_mm=els.get("limite_2_mm"),
            taux_ELS_2=els.get("taux_ELS_2"),
            w_y_inst_mm=df_res.get("w_y_inst_mm") if df_res else None,
            w_z_inst_mm=df_res.get("w_z_inst_mm") if df_res else None,
            w_res_inst_mm=df_res.get("w_res_inst_mm") if df_res else None,
            w_y_fin_mm=df_res.get("w_y_fin_mm") if df_res else None,
            w_z_fin_mm=df_res.get("w_z_fin_mm") if df_res else None,
            w_res_fin_mm=df_res.get("w_res_fin_mm") if df_res else None,
            w_vert_inst_mm=els.get("w_vert_inst_mm"),
            w_vert_fin_mm=els.get("w_vert_fin_mm"),
            taux_determinant=taux_determinant,
            verification_determinante=_trouver_verification_determinante(elu, els, df_res, taux_determinant),
            clause_EC5=_clause_ec5(elu, els, df_res, taux_determinant),
            statut=statut,
            marge_securite=config.marge_securite,
        )
        résultats_base.append(r)

    # Réplication pour chaque produit du groupe (EF-004)
    tous: list[RésultatPortée] = []
    for r_base in résultats_base:
        for produit in produits_groupe:
            from dataclasses import replace
            r_produit = replace(r_base, id_produit=produit.id_produit)
            tous.append(r_produit)

    return tous


def _trouver_verification_determinante(
    elu: dict, els: dict, df: dict, taux_max: float
) -> str:
    candidates = {
        "flexion_ELU": elu.get("taux_flexion_ELU", 0),
        "cisaillement_ELU": elu.get("taux_cisaillement_ELU", 0),
        "appui_ELU": elu.get("taux_appui_ELU", 0),
        "deversement_ELU": elu.get("taux_deversement_ELU", 0),
        "fleche_inst": els.get("taux_ELS_inst", 0),
        "fleche_fin": els.get("taux_ELS_fin", 0),
    }
    if df:
        candidates["biaxial_1_ELU"] = df.get("taux_biaxial_1_ELU", 0)
        candidates["biaxial_2_ELU"] = df.get("taux_biaxial_2_ELU", 0)
    return max(candidates, key=lambda k: candidates[k] or 0)


def _clause_ec5(elu: dict, els: dict, df: dict, taux_max: float) -> str:
    verif = _trouver_verification_determinante(elu, els, df, taux_max)
    mapping = {
        "flexion_ELU": "§6.1.6",
        "cisaillement_ELU": "§6.1.7",
        "appui_ELU": "§6.1.5",
        "deversement_ELU": "§6.3.3",
        "fleche_inst": "§7.2",
        "fleche_fin": "§7.2",
        "biaxial_1_ELU": "§6.1.6",
        "biaxial_2_ELU": "§6.1.6",
    }
    return mapping.get(verif, "§?")
