# Résumé des fonctions — `abac_charpente_vectoriser`

## Workflow global

```
cli()
 └─ run()
     ├─ _configurer_loguru()
     ├─ _lire_toml()                          ← configs_calcul_vect.toml
     ├─ _regenerer_stock()
     │   ├─ _charger_filtres_sapeg()
     │   └─ sapeg_regen_stock.run()
     ├─ charger_depuis_csv()                  ← stock_enrichi.csv / stock filtré
     │   ├─ _charger_materiaux_bois()
     │   └─ _k_cr()
     └─ ── boucle [[config_calcul]] ──
         ├─ appliquer_filtres()
         ├─ _developper_produit_cartesien()
         └─ ── boucle combos scalaires ──
             ├─ generer_combinaisons()         p0 → EC0
             │   └─ _charger_psi()
             ├─ calculer_charges_caracteristiques()   p1
             │   ├─ charge_neige_kNm()
             │   └─ charge_vent_kNm()
             ├─ construire_espace()            p2
             │   ├─ calculer_kmod_CM()
             │   ├─ calculer_kdef_arr()
             │   ├─ calculer_gamma_m_arr()
             │   ├─ calculer_resistances_CM()
             │   ├─ calculer_k_crit_LM()
             │   └─ calculer_k_c_LM()
             ├─ verifier_elu()                 p3 → VERIFICATIONS_ELU[*].calculer()
             ├─ verifier_els()                 p4 → VERIFICATIONS_ELS[*].calculer()
             ├─ synthetiser()                  p5
             ├─ construire_df_complet()
             └─ exporter_abaque_complet()
                 └─ appliquer_vues_depuis_toml()
```

---

## 1. Orchestration — `moteur_vect.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `cli` | fonction | Point d'entrée CLI `abac-vect` (argparse). Parse les arguments et délègue à `run()`. | `--toml-calcul`, `--source`, `--stock`, `--filtres`, `--sortie`, `--tenseurs`, `--verbose` | — | terminal / setuptools | `_configurer_loguru`, `run` |
| `run` | fonction | Orchestre le pipeline EC5 complet : stock → chargement → boucle configs → export. | `chemin_toml`, `chemin_source`, `chemin_stock`, `chemin_sortie`, `sauvegarder_tenseurs` | `list[ResultatPortee]` | `cli`, usage Python direct | `_regenerer_stock`, `_lire_toml`, `charger_depuis_csv`, `appliquer_filtres`, `_developper_produit_cartesien`, `generer_combinaisons`, `calculer_charges_caracteristiques`, `construire_espace`, `verifier_elu`, `verifier_els`, `synthetiser`, `construire_df_complet`, `exporter_abaque_complet`, `appliquer_vues_depuis_toml` |
| `_configurer_loguru` | fonction | Configure loguru : INFO par défaut, DEBUG si `verbose=True`. | `verbose: bool` | — | `cli` | loguru |
| `_lire_toml` | fonction | Lit un fichier TOML et retourne un dict (compatible Python 3.10 via tomli). | `chemin_toml: Path` | `dict` | `run`, `_charger_filtres_sapeg` | tomllib / tomli |
| `_developper_produit_cartesien` | fonction | Développe les champs multi-valués (listes) en produit cartésien de dicts scalaires. | `config_dict: dict` | `list[dict]` | `run` | itertools.product |
| `_charger_filtres_sapeg` | fonction | Charge la liste `ConfigFiltre` depuis `configs_filtre_regen.toml`. | `chemin_filtres: Path` | `list[ConfigFiltre]` | `_regenerer_stock` | `_lire_toml`, sapeg_regen_stock.modeles |
| `_regenerer_stock` | fonction | Appelle `sapeg_regen_stock.run()` pour générer le CSV stock filtré. | `chemin_source`, `chemin_sortie`, `chemin_filtres`, `nom_filtre` | `Path` (CSV stock) | `run` | `_charger_filtres_sapeg`, `sapeg_regen_stock.run` |

---

## 2. Modèles — `modeles/`

| Nom | Type | Définition | Champs principaux | Utilisé dans |
|-----|------|------------|-------------------|-------------|
| `ConfigCalculVect` | dataclass Pydantic | Configuration complète d'un calcul EC5 (une section `[[config_calcul]]` du TOML). | `id_config_calcul`, `type_poutre`, `L_min_m`, `L_max_m`, `pente_deg`, `entraxe_m`, `classe_service`, `g_k_kNm2`, `q_k_kNm2`, `s_k_kNm2`, `w_k_kNm2`, `filtres` | `run`, toutes les étapes pipeline |
| `RegleFiltre` | dataclass Pydantic | Règle de filtrage des matériaux dans la config calcul. | `champ`, `valeur` | `ConfigCalculVect.filtres`, `appliquer_filtres` |
| `ConfigMatériauVect` | dataclass | Configuration matériau avec toutes propriétés mécaniques et de section. `id_config_materiau` auto-généré en `__post_init__`. | `classe_resistance`, `famille`, `b_mm`, `h_mm`, `f_m_k_MPa`, `f_v_k_MPa`, `E_0_mean_MPa`, `rho_k_kgm3`, `A_cm2`, `I_y_cm4`, `W_y_cm3`, `type_section` | `charger_depuis_csv`, toutes les étapes pipeline |
| `CombinaisonEC0Vect` | dataclass | Coefficients EC0 pour une combinaison (ELU/ELS). | `id_combinaison`, `type_etat_limite`, `duree_charge`, `gamma_G`, `gamma_Q1`, `gamma_G2`, `psi_Q`, `psi_S`, `psi_W`, `type_charge_principale` | `generer_combinaisons`, `construire_espace`, `verifier_elu`, `verifier_els` |
| `TypeSection` | Enum | Type de section transversale. | `RECTANGULAIRE`, `RONDE`, `PERSONNALISEE` | `charger_depuis_csv`, `ConfigMatériauVect`, vérifications EC5 |

---

## 3. Chargeur — `chargeur/`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `charger_depuis_csv` | fonction | Charge et construit les `ConfigMatériauVect` depuis le CSV stock. Gère mappage colonnes, filtrage, calcul des propriétés de section (rect / rond / custom). | `chemin_stock`, `mappage_colonnes`, `filtrage_colonne`, `filtrage_valeur`, `section_colonne_forme`, `section_colonne_diametre` | `list[ConfigMatériauVect]` | `run` | `_charger_materiaux_bois`, `_k_cr`, pandas, numpy |
| `_charger_materiaux_bois` | fonction (cache) | Charge la table des propriétés mécaniques normatives depuis `donnees/materiaux_bois.csv`. | — | `pd.DataFrame` | `charger_depuis_csv` | pandas |
| `_k_cr` | fonction (cache) | Lit le facteur k_cr (section efficace cisaillement) depuis `params_ec5.csv` — EC5 §6.1.7. | — | `float` | `charger_depuis_csv` | pandas |
| `appliquer_filtres` | fonction | Applique les règles `RegleFiltre` (logique AND) sur la liste des matériaux. | `materiaux: list[ConfigMatériauVect]`, `regles: list[RegleFiltre]` | `list[ConfigMatériauVect]` | `run` | `_satisfait_toutes`, `_satisfait_regle` |
| `_satisfait_toutes` | fonction | Vérifie qu'un matériau satisfait toutes les règles (AND). | `mat`, `regles` | `bool` | `appliquer_filtres` | `_satisfait_regle` |
| `_satisfait_regle` | fonction | Vérifie si un matériau satisfait une seule règle `RegleFiltre`. | `mat`, `regle` | `bool` | `_satisfait_toutes` | getattr |

---

## 4. EC0 — Combinaisons — `ec0/combinaisons.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `generer_combinaisons` | fonction | Génère toutes les combinaisons EC0 pertinentes (ELU_STR + ELS_CAR/FREQ/QPERM) selon les charges actives dans la config. | `config: ConfigCalculVect` | `list[CombinaisonEC0Vect]` | `run` | `_charger_psi`, `_charge_active`, `_scalaire` |
| `_charger_psi` | fonction | Charge les coefficients ψ₀, ψ₁, ψ₂ depuis `donnees/psi_coefficients.csv` selon la catégorie de charge. | `categorie_q`, `categorie_s` | `dict[str, dict[str, float]]` | `generer_combinaisons` | pandas |
| `_scalaire` | fonction | Retourne une valeur scalaire ou le premier élément d'une liste. | `v` | `float` | `generer_combinaisons` | — |
| `_charge_active` | fonction | Vérifie si une charge variable est active (valeur > 0) dans la config. | `config`, `champ` | `bool` | `generer_combinaisons` | `_scalaire` |

---

## 5. EC1 — Charges climatiques

### `ec1/neige.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `charge_neige_kNm` | fonction | Charge linéique caractéristique de neige (EN 1991-1-3) : s_k × μ₁(pente) × entraxe. | `s_k_kNm2`, `pente_deg`, `entraxe_m` | `float` (kN/m) | `calculer_charges_caracteristiques` | `mu1` |
| `mu1` | fonction | Coefficient de forme μ₁ selon la pente du toit — EN 1991-1-3 §5.3. | `pente_deg: float` | `float` | `charge_neige_kNm` | `_charger_mu1_table`, numpy interpolation |
| `_charger_mu1_table` | fonction (cache) | Charge les points d'interpolation μ₁ depuis `donnees/mu1_neige.csv`. | — | `pd.DataFrame` | `mu1` | pandas |

### `ec1/vent.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `charge_vent_kNm` | fonction | Charge linéique caractéristique de vent : w_k × c_pe(type_toiture) × entraxe. | `w_k_kNm2`, `type_toiture`, `entraxe_m` | `float` (kN/m) | `calculer_charges_caracteristiques` | `c_pe` |
| `c_pe` | fonction | Coefficient de pression extérieure c_pe selon le type de toiture. | `type_toiture: str` | `float` | `charge_vent_kNm` | `_charger_cpe_table` |
| `_charger_cpe_table` | fonction (cache) | Charge les coefficients c_pe depuis `donnees/cpe_vent.csv`. | — | `pd.DataFrame` | `c_pe` | pandas |

---

## 6. EC5 — Propriétés de calcul — `ec5/proprietes.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `calculer_kmod_CM` | fonction | Matrice k_mod `(n_C, n_M)` — EC5 §2.4.3, Table 3.1. Facteur de modification pour durée de charge et classe de service. | `combinaisons`, `materiaux`, `classe_service` | `ndarray (n_C, n_M)` | `construire_espace` | `_charger_kmod` |
| `calculer_kdef_arr` | fonction | Vecteur k_def `(n_M,)` — EC5 Table 3.2. Facteur de déformation différée. | `materiaux`, `classe_service` | `ndarray (n_M,)` | `construire_espace` | `_charger_kdef` |
| `calculer_gamma_m_arr` | fonction | Vecteur γ_M `(n_M,)` — AN France. Coefficient partiel de résistance du matériau. | `materiaux` | `ndarray (n_M,)` | `construire_espace` | `_charger_gamma_m` |
| `calculer_resistances_CM` | fonction | Matrice des résistances de calcul `(n_C, n_M)` pour chaque type (flexion, cisaillement, etc.) — EC5 §2.4.1. | `combinaisons`, `materiaux`, `classe_service` | `dict[str, ndarray (n_C, n_M)]` | `construire_espace` | `calculer_kmod_CM`, `calculer_gamma_m_arr` |
| `calculer_k_crit_LM` | fonction | Facteur de déversement k_crit `(n_L, n_M)` — EC5 §6.3.3. Dépend de la longueur de déversement fournie par le type de poutre. | `longueurs_m`, `materiaux`, `type_poutre`, `config` | `ndarray (n_L, n_M)` | `construire_espace` | `_charger_params_ec5`, numpy |
| `calculer_k_c_LM` | fonction | Facteurs de flambement k_c,y et k_c,z `(n_L, n_M)` — EC5 §6.3.2. | `longueurs_m`, `materiaux`, `type_poutre`, `config` | `tuple[ndarray, ndarray]` chacun `(n_L, n_M)` | `construire_espace` | `_charger_params_ec5`, numpy |
| `_charger_kmod` | fonction (cache) | Charge la table k_mod depuis `donnees/kmod.csv`. | — | `pd.DataFrame` | `calculer_kmod_CM` | pandas |
| `_charger_kdef` | fonction (cache) | Charge la table k_def depuis `donnees/kdef.csv`. | — | `pd.DataFrame` | `calculer_kdef_arr` | pandas |
| `_charger_gamma_m` | fonction (cache) | Charge la table γ_M depuis `donnees/gamma_m.csv`. | — | `pd.DataFrame` | `calculer_gamma_m_arr` | pandas |
| `_charger_params_ec5` | fonction (cache) | Charge les paramètres scalaires EC5 (k_cr, k_m, seuils k_crit) depuis `donnees/params_ec5.csv`. | — | `dict[str, float]` | `calculer_k_crit_LM`, `calculer_k_c_LM` | pandas |

---

## 7. Pipeline p0 → p5

### p0 — `pipeline/p0_proprietes.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `extraire_vecteurs_materiaux` | fonction | Extrait les propriétés matériau en vecteurs numpy `(n_M,)` prêts pour le broadcast tenseur. | `materiaux: list[ConfigMatériauVect]` | `dict[str, ndarray]` : A_eff_cis, W_y, W_z, I_y, I_z, E_mean, rho_k, A | `construire_espace` | numpy |

### p1 — `pipeline/p1_charges.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `calculer_charges_caracteristiques` | fonction | Convertit les charges surfaciques (kN/m²) en charges linéiques (kN/m) par matériau. Poids propre variable selon A et ρ_k. | `config`, `materiaux`, `type_poutre` | `dict[str, float \| ndarray]` : g_pp_kNm `(n_M,)`, g_kNm, g2_kNm, q_kNm, s_kNm, w_kNm | `run` | `charge_neige_kNm`, `charge_vent_kNm`, `type_poutre.poids_propre_kNm` |

### p2 — `pipeline/p2_combinaison.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `construire_espace` | fonction | Assemble charges + coefficients EC0 en tenseur `(n_L, n_C, n_M)` de sollicitations (M_d, V_d, N_d, M_y, M_z, flèches). Contient toutes les résistances de calcul. | `longueurs_m`, `combinaisons`, `materiaux`, `config`, `type_poutre`, `charges_k` | `EspaceCombinaisonTenseur` | `run` | `extraire_vecteurs_materiaux`, `calculer_kmod_CM`, `calculer_kdef_arr`, `calculer_gamma_m_arr`, `calculer_resistances_CM`, `calculer_k_crit_LM`, `calculer_k_c_LM`, `type_poutre.decomposer_charges`, `_charger_limites_fleche` |
| `_charger_limites_fleche` | fonction | Lit les limites de flèche ELS (w_inst, w_fin, w_fin_brut, w_2) selon l'usage depuis `donnees/limites_fleche_ec5.csv`. | `usage: str` | `dict[str, float \| None]` | `construire_espace` | pandas |

### p3 — `pipeline/p3_elu.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `verifier_elu` | fonction | Itère sur `VERIFICATIONS_ELU`, calcule les taux ELU, retourne le max par `(n_L, n_M)` et la combinaison déterminante. | `espace: EspaceCombinaisonTenseur` | `tuple[dict taux, dict combo, dict valeur]` chacun `{id: ndarray (n_L, n_M)}` | `run` | `VERIFICATIONS_ELU[*].calculer` |

### p4 — `pipeline/p4_els.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `verifier_els` | fonction | Itère sur `VERIFICATIONS_ELS`, calcule les taux ELS, retourne le max par `(n_L, n_M)` et la combinaison déterminante (flèche en mm). | `espace: EspaceCombinaisonTenseur` | `tuple[dict taux, dict combo, dict valeur]` chacun `{id: ndarray (n_L, n_M)}` | `run` | `VERIFICATIONS_ELS[*].calculer` |

### p5 — `pipeline/p5_synthese.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `ResultatPortee` | dataclass | Résultat par couple (matériau × config) : longueur max admissible, taux déterminant, vérification déterminante. | `id_config_materiau`, `id_config_calcul`, `longueur_max_admissible_m`, `taux_determinant`, `verif_determinante`, `taux_par_verif` | — | `synthetiser`, `run` | — |
| `synthetiser` | fonction | Agrège les taux ELU/ELS par matériau → `ResultatPortee`. Détermine la longueur maximale admissible (premier L où taux global > 1.0). | `longueurs_m`, `taux_elu`, `taux_els`, `materiaux`, `config`, `combo_elu`, `combo_els` | `list[ResultatPortee]` | `run` | numpy |

---

## 8. Protocoles et types de poutres

### `protocoles/type_poutre.py`

| Nom | Type | Définition | Méthodes abstraites / clés | Utilisé dans |
|-----|------|------------|---------------------------|-------------|
| `TypePoutreVect` | ABC | Interface abstraite de tous les types de poutres. Convention d'axes : `(n_L, n_C, n_M)`. | `decomposer_charges(q_d) → (q_y, q_z)`, `poids_propre_kNm(materiaux)`, `longueur_deversement_m(L)`, `effort_normal_kN(L, C, M)`, `longueur_flambement_y_m(L)`, `longueur_flambement_z_m(L)` | toutes les étapes pipeline |
| `TypePoutreInclineeVect` | ABC (hérite TypePoutreVect) | Base pour poutres inclinées. Implémente la projection des charges ⊥ et ∥ au rampant. | — | ChevronVect, PanneDeverseeVect, PanneAplombVect |
| `PoutreHorizontaleVect` | ABC (hérite TypePoutreVect) | Base pour poutres horizontales (charges verticales, pas de déversement). | — | SoliveVect, SommierVect |

### `types_poutre/horizontales.py`

| Nom | Type | Définition | Comportement spécifique |
|-----|------|------------|------------------------|
| `SoliveVect` | classe (hérite PoutreHorizontaleVect) | Solive de plancher — bi-appui, portée horizontale. Pas de déversement, pas de double flexion. | Poids propre vertical, longueur de flambement = L |
| `SommierVect` | classe (hérite PoutreHorizontaleVect) | Poutre principale / sommier — même comportement que Solive mais usage distinct. | Identique à SoliveVect |

### `types_poutre/inclinees.py`

| Nom | Type | Définition | Comportement spécifique |
|-----|------|------------|------------------------|
| `ChevronVect` | classe (hérite TypePoutreInclineeVect) | Chevron de toiture incliné, charge ⊥ rampant uniquement. Pas de double flexion. | Décomposition q_d → composante ⊥ rampant seulement |
| `PanneDeverseeVect` | classe (hérite TypePoutreInclineeVect) | Panne déversée — charges décomposées selon y et z. Double flexion + vérification déversement. | `decomposer_charges` → `(q×cos(α), q×sin(α))`, longueur déversement = L |
| `PanneAplombVect` | classe (hérite TypePoutreInclineeVect) | Panne à l'aplomb — charges verticales décomposées selon axes de la section inclinée. Double flexion + déversement. | Décomposition biaxiale, effort normal nul |

---

## 9. Vérifications ELU — `verifications/ec5/`

Toutes les classes héritent de `VerificationELU` (ABC, `protocoles/verification.py`).  
Interface : `id_verification: str`, `calculer(espace) → ResultatVerification`.

### Flexion — `elu_flexion.py`

| Nom | Vérification EC5 | Taux calculé |
|-----|-----------------|-------------|
| `FlexionAxeFort` | §6.1.6 flexion axe fort | σ_m,y,d / f_m,d |
| `FlexionAxeFaible` | §6.1.6 flexion axe faible | σ_m,z,d / f_m,d |
| `DoubleFlexionForte` | §6.1.6 double flexion (composante forte) | σ_m,y,d/f_m,d + k_m × σ_m,z,d/f_m,d |
| `DoubleFlexionFaible` | §6.1.6 double flexion (composante faible) | k_m × σ_m,y,d/f_m,d + σ_m,z,d/f_m,d |

### Effort tranchant et appui — `elu_effort_tranchant.py`

| Nom | Vérification EC5 | Taux calculé |
|-----|-----------------|-------------|
| `Cisaillement` | §6.1.7 effort tranchant | τ_d / f_v,d |
| `Appui` | §6.1.5 compression ⊥ fil à l'appui | σ_c90,d / (k_c90 × f_c90,d) |

### Effort normal — `elu_effort_normal.py`

| Nom | Vérification EC5 | Taux calculé |
|-----|-----------------|-------------|
| `Traction` | §6.1.2 traction // fil | σ_t0,d / f_t0,d |
| `TractionTransversale` | §6.1.4 traction ⊥ fil | σ_t90,d / f_t90,d |
| `Compression` | §6.1.4 compression // fil | σ_c0,d / f_c0,d |

### Flambement — `elu_flambement.py`

| Nom | Vérification EC5 | Taux calculé |
|-----|-----------------|-------------|
| `FlambementAxeFort` | §6.3.2 flambement axe fort | σ_c0,d / (k_c,y × f_c0,d) |
| `FlambementAxeFaible` | §6.3.2 flambement axe faible | σ_c0,d / (k_c,z × f_c0,d) |

### Déversement — `elu_deversement.py`

| Nom | Vérification EC5 | Taux calculé |
|-----|-----------------|-------------|
| `Deversement` | §6.3.3 déversement (flambement latéral) | σ_m,d / (k_crit × f_m,d) |

### Compression oblique — `elu_compression_oblique.py`

| Nom | Vérification EC5 | Taux calculé |
|-----|-----------------|-------------|
| `CompressionOblique` | §6.2.2 compression à angle (Hankinson) | formule Hankinson f_c,α,d |

### Combinées — `elu_combines.py`

| Nom | Vérification EC5 | Taux calculé |
|-----|-----------------|-------------|
| `FlexionTraction` | §6.2.3 flexion + traction | σ_t/f_t + σ_m,y/f_m + k_m × σ_m,z/f_m |
| `FlexionCompressionForte` | §6.2.4 flexion + compression (axe fort) | (σ_c/f_c)² + σ_m,y/f_m + k_m × σ_m,z/f_m |
| `FlexionCompressionFaible` | §6.2.4 flexion + compression (axe faible) | (σ_c/f_c)² + k_m × σ_m,y/f_m + σ_m,z/f_m |
| `FlexionDevComprimeeForte` | §6.3.2+6.3.3 déversement + compression fort | σ_c/(k_c,y×f_c) + σ_m/(k_crit×f_m) |
| `FlexionDevComprimeeFaible` | §6.3.2+6.3.3 déversement + compression faible | σ_c/(k_c,z×f_c) + σ_m/(k_crit×f_m) |

---

## 10. Vérifications ELS — `verifications/ec5/els_fleche.py`

Toutes les classes héritent de `VerificationELS` (ABC).  
Les taux sont : flèche calculée / limite réglementaire (ex. L/300).

| Nom | Définition | Composante |
|-----|-----------|-----------|
| `FlecheInst` | Flèche instantanée totale (y + z) | w_inst,Q / lim_inst |
| `FlecheInstY` | Flèche instantanée axe fort y | w_inst,Q,y / lim_inst |
| `FlecheInstZ` | Flèche instantanée axe faible z | w_inst,Q,z / lim_inst |
| `FlecheFinBrute` | Flèche finale brute totale (G + Q + déformation diff.) | w_fin,brut / lim_fin_brut |
| `FlecheFinBruteY` | Flèche finale brute axe y | w_fin,brut,y / lim_fin_brut |
| `FlecheFinBruteZ` | Flèche finale brute axe z | w_fin,brut,z / lim_fin_brut |
| `FlecheFin` | Flèche finale nette totale (déduite des prédéformations) | w_fin / lim_fin |
| `FlecheFinY` | Flèche finale nette axe y | w_fin,y / lim_fin |
| `FlecheFinZ` | Flèche finale nette axe z | w_fin,z / lim_fin |
| `FlecheSecondOeuvre` | Flèche post-second œuvre totale | w_2 / lim_w2 |
| `FlecheSecondOeuvreY` | Flèche post-second œuvre axe y | w_2,y / lim_w2 |
| `FlecheSecondOeuvreZ` | Flèche post-second œuvre axe z | w_2,z / lim_w2 |

Fonctions internes (`els_fleche.py`) :

| Nom | Définition |
|-----|-----------|
| `_fleche_bi_appui` | Formule BI appui : w = 5qL⁴/(384EI) |
| `_ratios_moment_yz` | Rapports My/M et Mz/M pour pondération biaxiale |
| `_decomposer_G_Q` | Décompose les charges en composantes G (permanente) et Q (variable) |
| `_composante_verticale` | Extrait la composante verticale depuis les charges 3D |
| `_w_inst_composantes` | Calcule les composantes de flèche instantanée |
| `_w_fin_composantes` | Calcule les composantes de flèche finale |
| `_w2_composantes` | Calcule les composantes de flèche second œuvre |

---

## 11. Sortie — `sortie/`

### `sortie/abaque_complet.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `construire_df_complet` | fonction | Construit le DataFrame complet (une ligne par matériau × longueur) avec tous les taux ELU/ELS, combinaisons déterminantes et colonnes de contexte. | `longueurs_m`, `taux_elu`, `taux_els`, `materiaux`, `config`, `combo_elu`, `combo_els`, `valeur_elu`, `valeur_els` | `pd.DataFrame` | `run` | pandas, `renommer_cols_elu_els` |
| `renommer_cols_elu_els` | fonction | Renomme les colonnes taux ELU/ELS pour l'export CSV (préfixe ELU_ / ELS_). | `df: pd.DataFrame` | `pd.DataFrame` | `construire_df_complet` | pandas |
| `calculer_indice_de_classement` | fonction | Calcule un indice de classement pondéré des matériaux depuis la config TOML de sortie. | `df`, `config_indice: dict` | `pd.Series` | `run` | pandas, numpy |
| `exporter_abaque_complet` | fonction | Exporte le DataFrame global vers `abaque_complet_global.csv` (UTF-8, sep=`;`). | `df`, `chemin: Path` | — | `run` | pandas |

### `sortie/tenseur_duck.py`

| Nom | Type | Définition | Méthodes clés | Utilisé dans |
|-----|------|------------|--------------|-------------|
| `TenseurDuck` | classe | Store DuckDB pour sauvegarder les tenseurs de taux `(n_L, n_M)` par vérification. Colonnes `FLOAT[]` indexées par `id_config_calcul`. | `sauvegarder(id, longueurs, taux_elu, taux_els, materiaux, ...)`, `fermer()` | `run` (si `--tenseurs`) |

### `sortie/vues.py`

| Nom | Type | Définition | Paramètres clés | Retour | Appelé par | Appelle |
|-----|------|------------|-----------------|--------|-----------|---------|
| `appliquer_vues_depuis_toml` | fonction | Lit `configs_sortie_vect.toml` et produit les CSV de vues dérivées (filtres, agrégations). | `df`, `chemin_toml`, `chemin_sortie` | — | `run` | `_lire_toml`, `_produire_filtre`, `_produire_agregation` |
| `_produire_filtre` | fonction | Produit un CSV filtré selon une section `[[filtre]]` du TOML de sortie. | `df`, `config_filtre: dict`, `chemin_sortie` | — | `appliquer_vues_depuis_toml` | `_appliquer_filtres`, pandas |
| `_produire_agregation` | fonction | Produit un CSV agrégé (groupby + agg) selon une section `[[agregation]]` du TOML de sortie. | `df`, `config_agg: dict`, `chemin_sortie` | — | `appliquer_vues_depuis_toml` | pandas |
| `_appliquer_filtres` | fonction | Applique une liste de filtres TOML sur le DataFrame. | `df`, `filtres: list[dict]` | `pd.DataFrame` | `_produire_filtre` | `_coerce_vers_dtype_col` |
| `_coerce_vers_dtype_col` | fonction | Coerce une valeur vers le dtype de la colonne cible (int, float, str, bool). | `df`, `col`, `val` | valeur coercée | `_appliquer_filtres` | pandas dtypes |

---

## 12. Protocoles — `protocoles/verification.py`

| Nom | Type | Définition | Interface |
|-----|------|------------|----------|
| `ResultatVerification` | dataclass | Résultat d'une vérification : taux `(n_L, n_C, n_M)` + valeur intermédiaire optionnelle. | `taux_LCM: ndarray`, `valeur_intermediaire: ndarray \| None` |
| `VerificationELU` | ABC | Classe de base de toutes les vérifications ELU. | `id_verification: str`, `calculer(espace) → ResultatVerification` |
| `VerificationELS` | ABC | Classe de base de toutes les vérifications ELS. | `id_verification: str`, `calculer(espace) → ResultatVerification` |

### `pipeline/espace.py`

| Nom | Type | Définition | Champs clés |
|-----|------|------------|------------|
| `EspaceCombinaisonTenseur` | dataclass | Structure centrale du pipeline : contient tous les tenseurs `(n_L, n_C, n_M)` de sollicitations et résistances. Passée à chaque vérification. | `M_d_kNm`, `V_d_kN`, `N_d_kN`, `M_y_d_kNm`, `M_z_d_kNm`, `f_m_d_CM`, `f_v_d_CM`, `f_c0_d_CM`, `k_crit_LM`, `k_c_y_LM`, `k_c_z_LM`, `kdef_M`, `combinaisons`, `config`, `type_poutre`, `limites_fleche` |
