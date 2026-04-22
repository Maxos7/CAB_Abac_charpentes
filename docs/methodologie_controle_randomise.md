# Méthodologie — Contrôle randomisé des sorties ABAC

Document méthodologique du projet **CAB_Abac_Charpentes**. Décrit la démarche de Vérification & Validation (V&V) des sorties du pipeline `abac-vect` par comparaison à un corpus de valeurs de référence tabulées, avec échantillonnage randomisé conforme aux normes internationales.

---

## 1. Contexte

Le pipeline `abac-vect` produit [abaque_complet_global.csv](../resultats/abaque_complet_global.csv) — environ 11 584 lignes × 105 colonnes — rassemblant l'ensemble des vérifications Eurocode 5 vectorisées :

- **ELU** : flexion §6.1.6, cisaillement §6.1.7, flambement §6.3.2, déversement §6.3.3, compression oblique (Hankinson), flexion composée.
- **ELS** : flèches instantanée, finale, nette de fluage, court terme.
- **Statut global** : `taux_global`, `verifie` (booléen), `verifie_raison`.

Le contrôle qualité s'appuie sur des **valeurs de référence tabulées**, saisies manuellement dans une feuille du classeur [Comparatif.xlsx](../resultats/comparatif/Comparatif.xlsx). Chaque ligne de la table de référence porte :
- un jeu complet d'entrées (type de poutre, classe, charges, géométrie),
- les valeurs attendues en sortie (taux EC5, flèches, statut) issues d'une **source reconnue** : calcul EC5 à la main, logiciel métier, publication technique, note de calcul d'ingénieur.

---

## 2. Problème méthodologique

Un contrôle statistique strict au sens ISO 2859 / ISO 3951 suppose un **lot** à inspecter et un **oracle** capable de trancher pour chaque élément tiré. Ici :

- **Lot** = 11 584 lignes de l'abaque.
- **Oracle** = table de référence tabulée, nécessairement plus petite que le lot.

Il est donc impossible de tirer aléatoirement 200 lignes de l'abaque et d'obtenir une vérité de terrain pour chacune. La démarche doit combiner deux contrôles complémentaires de nature différente :

- **Contrôle A** — validation déterministe sur le sous-ensemble du lot pour lequel on dispose d'une référence (« validation » au sens ASME V&V 10).
- **Contrôle B** — vérification randomisée sur l'ensemble du lot via des **propriétés physiques invariantes** connues *a priori* (« verification » au sens ASME V&V 10, technique du *metamorphic testing*).

---

## 3. Cadre normatif

### 3.1 Norme pilier

> **Norme pilier — ASME V&V 10-2019** *Standard for Verification and Validation in Computational Solid Mechanics*
>
> Unique standard international dédié à la V&V des codes de calcul en mécanique des solides. Pose le vocabulaire et la séparation :
> - **Verification** (« solving the equations right ») — le code résout-il correctement les équations posées ?
> - **Validation** (« solving the right equations ») — les équations posées représentent-elles correctement le phénomène réel ?
> - **Uncertainty Quantification** — comment les variations d'entrées se propagent-elles aux sorties ?

### 3.2 Normes de soutien

> **Norme — ASME V&V 10.1 / V&V 10.3**
>
> Sous-parties dédiées aux exemples (10.1) et aux **métriques de comparaison** (10.3 : biais, erreur relative, régression, Bland-Altman). Base du Contrôle A.

> **Norme — EN 1990 Annexe D** *Basis of structural design — Design assisted by testing*
>
> Annexe informative de l'Eurocode 0 (EN 1990) encadrant l'évaluation statistique des données d'essai et la dérivation de valeurs caractéristiques. Sections D5 (dérivation des valeurs de calcul), D6 (principes généraux d'évaluation statistique), D7 (propriété unique), D8 (modèles de résistance). Référence réglementaire pertinente côté Eurocode.

> **Norme — ISO 2859-1:1999** *Sampling procedures for inspection by attributes — Sampling schemes indexed by AQL*
>
> Plan d'échantillonnage par attributs (conforme / non conforme). Utilisée pour le drapeau binaire `verifie` et les flags `OK` / `VIOLATION` des propriétés invariantes.

> **Norme — ISO 3951-1:2022** *Sampling procedures for inspection by variables — Part 1: single sampling plans indexed by AQL*
>
> Plan d'échantillonnage par variables (grandeurs continues). Utilisée pour `taux_global`, taux partiels et flèches.

> **Norme — ISO 3951-2:2013** *Variables — independent quality characteristics*
>
> Extension multi-caractéristiques, applicable ici car plusieurs grandeurs continues sont contrôlées simultanément (flexion, cisaillement, flèches…).

> **Norme — ISO 5725** (série) *Accuracy (trueness and precision) of measurement methods and results*
>
> Cadre pour séparer **biais systématique** (trueness) et **dispersion aléatoire** (precision). Définit répétabilité et reproductibilité, utiles à l'interprétation des écarts ABAC / référence.

> **Norme — ISO/IEC 25010:2011** *Systems and software Quality Requirements and Evaluation (SQuaRE)*
>
> Cadre général qualité logicielle. Caractéristique pertinente ici : **functional correctness** (§8.2.1) — rattachement général du dispositif à la démarche qualité logicielle.

---

## 4. Trame méthodologique en deux contrôles

### 4.1 Contrôle A — Validation nominale sur valeurs de référence tabulées

**Correspondance normative** : ASME V&V 10 *Validation*.

**Objectif** : sur les configurations documentées dans la table de référence, ABAC doit restituer les mêmes sorties, à une tolérance définie.

**Nature** : déterministe, non randomisé. Chaque ligne de la table de référence est rapprochée de la ligne correspondante de [abaque_complet_global.csv](../resultats/abaque_complet_global.csv) par jointure sur les variables d'entrée.

**Métriques par ligne** (ASME V&V 10.3) :

| Grandeur | Métrique | Critère proposé |
|---|---|---|
| Taux ELU (flexion, cisaillement, flambement, déversement, Hankinson) | erreur relative `ε = (τ_abac − τ_ref) / τ_ref` | `\|ε\| ≤ 5 %` |
| Flèches ELS (instantanée, finale, nette de fluage) | erreur relative | `\|ε\| ≤ 5 %` |
| `taux_global` | erreur relative | `\|ε\| ≤ 5 %` |
| Statut `verifie` | égalité stricte | 100 % concordance |

**Justification du seuil 5 %** : ordre de grandeur classique des écarts inter-logiciels EC5 (arrondis de coefficients, interpolations linéaires, ε machine). Seuil à confirmer sur un run pilote.

**Métriques agrégées** (sur l'ensemble des paires référence / ABAC) :
- **Biais moyen** `B = mean(ε)` — attendu ≈ 0 (pas d'erreur systématique).
- **Écart-type** `S = std(ε)` — quantifie la dispersion.
- **Régression y = a·x + b** sur les couples (ref, abac) — attendu `a ∈ [0,98 ; 1,02]`, `b ≈ 0`, `R² ≥ 0,99`.
- **Bland-Altman** — nuage `ε` vs `moyenne(ref, abac)` — 95 % des points dans les limites d'agrément ±1,96·S.

### 4.2 Contrôle B — Robustesse randomisée par propriétés invariantes

**Correspondance normative** : ASME V&V 10 *Verification* ; échantillonnage ISO 2859-1 par attributs sur les flags de violation.

**Objectif** : sur les ≈ 99 % de lignes qui n'ont pas de référence tabulée, détecter toute incohérence interne via des **propriétés physiques invariantes** (monotonies, bornes, lois de conservation) connues *a priori*. Technique du *metamorphic testing*, standard en QC des logiciels scientifiques quand l'oracle direct manque.

**Propriétés invariantes**

| # | Propriété | Formulation testable |
|---|---|---|
| P1 | Monotonie portée | À entrée constante, `taux_global` croît avec `longueur_m` |
| P2 | Monotonie charge | À géométrie constante, `taux_global` croît avec `q_k`, `s_k`, `w_k` |
| P3 | Monotonie classe mécanique | À section / charge constantes, `taux_global` décroît C24 → GL24h |
| P4 | Monotonie section | À charge / portée constantes, `taux_global` décroît avec `h_mm` |
| P5 | Effet classe de service | `w_fin_brut` croît avec `classe_service` (fluage ↑) |
| P6 | Cohérence binaire | `verifie = True` ⇔ tous les taux partiels ≤ 1 |
| P7 | Domaine déversement | `k_crit ∈ [0 ; 1]` et ne dépasse jamais 1 |
| P8 | Hankinson aux bornes | `pente_deg = 0` ⇒ `σ_c_alpha = σ_c0` ; `= 90°` ⇒ `σ_c90` |

**Plan d'échantillonnage randomisé**

Espace d'entrée à ≈ 12 dimensions mixtes :
- Catégorielles : `type_poutre` (3), `usage`, `classe_service` (1/2/3), `essence`, `classe_resistance`.
- Discrètes : `b_mm`, `h_mm`.
- Continues : `pente_deg`, `entraxe_m`, `longueur_m`, `g_k`, `q_k`, `s_k`, `w_k`.

**Méthode recommandée : séquence de Sobol (quasi-Monte-Carlo, low-discrepancy)** — justification :

1. **Convergence en O(1/N)** contre O(1/√N) pour Monte-Carlo pseudo-aléatoire.
2. **Remplissage d'espace supérieur** en dimension ≥ 5, comparé à Latin Hypercube Sampling.
3. **Reproductibilité** : séquence déterministe fondée sur un seed → rejeu identique, traçable en audit.
4. **Scrambling possible** (Owen 1997) pour obtenir des réalisations randomisées avec intervalles de confiance valides.

**Alternative acceptable — LHS** : plus simple à mettre en œuvre. Un LHS N = 400 atteint la précision d'un Monte-Carlo N = 6 000.

**Monte-Carlo pseudo-aléatoire pur — non recommandé** : clusters et lacunes, convergence lente.

**Stratification obligatoire sur les catégorielles** avant le tirage Sobol : au moins un tirage par combinaison critique `type_poutre × classe_service × classe_resistance`. Principe issu d'ISO 2859-1 §1.2 et du Design of Experiments classique.

**Taille d'échantillon**

| Référentiel | Paramètres | n recommandé |
|---|---|---|
| ISO 3951-1 niveau II, AQL 1,0 % | variable continue, lot 10 k-35 k | ≈ 125 |
| ISO 2859-1 niveau II, AQL 1,0 % | attribut, lot 10 001-35 000, code lettre M | n = 200, Ac = 5, Re = 6 |
| Sobol space-filling dim 12 | minimum pour remplissage correct | n ≥ 256 (= 2⁸) |

**Recommandation finale : n = 256 tirages** (puissance de 2, optimal pour Sobol, enveloppe les deux plans ISO).

**Décision d'acceptation** : pour chaque propriété P1–P8, taux de violation ≤ **AQL 1,0 %** ⇒ lot accepté. Sur 256 tirages : tolérance ≤ 2 violations par propriété avant investigation.

### 4.3 Synoptique d'ensemble

```
                    ┌──────────────────────────────────────┐
                    │  abaque_complet_global.csv           │
                    │  (11 584 lignes × 105 colonnes)      │
                    └──────────────────────────────────────┘
                                    │
                ┌───────────────────┴───────────────────┐
                ▼                                       ▼
      ┌──────────────────────┐              ┌──────────────────────┐
      │ Contrôle A           │              │ Contrôle B           │
      │ Validation nominale  │              │ Vérif. robustesse    │
      │ (ASME V&V — Valid.)  │              │ (ASME V&V — Verif.)  │
      ├──────────────────────┤              ├──────────────────────┤
      │ Oracle : table       │              │ Oracle : propriétés  │
      │ référence tabulée    │              │ physiques invariantes│
      │ Méthode : déterm.    │              │ Sampling : Sobol 256 │
      │ Seuil : |ε| ≤ 5 %    │              │ Décision : ISO 2859  │
      │ Métriques ASME 10.3  │              │ Tolérance ≤ 2 viol.  │
      └──────────────────────┘              └──────────────────────┘
                │                                       │
                └───────────────────┬───────────────────┘
                                    ▼
                        ┌──────────────────────────┐
                        │ Rapport de validation    │
                        │ (ISO/IEC 25010 §8.2.1    │
                        │ functional correctness)  │
                        └──────────────────────────┘
```

---

## 5. Limites assumées

À acter dans tout rapport produit :

1. **Corpus de référence tabulé limité** : le Contrôle A ne couvre que les configurations documentées. Hors de ces points, la garantie repose uniquement sur le Contrôle B (propriétés invariantes).
2. **Les valeurs tabulées ne sont pas une vérité absolue** mais une référence technique. Un écart significatif ABAC / référence ne tranche pas « qui a raison » ; il déclenche une analyse croisée (recalcul EC5 manuel sur le sous-cas).
3. **Les propriétés invariantes ne garantissent pas la justesse absolue** : elles détectent les incohérences internes et les ruptures de monotonie, pas une erreur systématique présente depuis l'origine du code.
4. **Extension souhaitée dans le temps** : l'enrichissement régulier de la table de référence (objectif ≥ 30 lignes) est le principal levier pour renforcer le Contrôle A et rendre le plan ISO 3951 statistiquement valide sur oracle réel.

---

## 6. Exemple de mise en place dans `Comparatif.xlsx`

État actuel du classeur [Comparatif.xlsx](../resultats/comparatif/Comparatif.xlsx) — 4 feuilles, miroir statique des CSV produits :

| Feuille actuelle | Contenu |
|---|---|
| `abaque_complet_global` | 11 006 × 105 — copie du CSV résultats |
| `abaque_questionnaire` | 2 218 × 13 — copie du CSV simplifié |
| `ALL_PRODUIT_2026-02-12_06_01_04` | 17 713 × 82 — export SAPEG brut |
| `stock_charpente` | 159 × 12 — stock filtré |

Ces feuilles sont aujourd'hui des **copies figées**. Pour opérationnaliser la méthodologie, les remplacer / compléter par la structure suivante.

### 6.1 Architecture cible du classeur

| # | Feuille | Rôle |
|---|---|---|
| 0 | `0_README` | Note de garde : normes suivies, périmètre, seuils, date MAJ |
| 1 | `1_abaque_import` | Import Power Query dynamique de `abaque_complet_global.csv` |
| 2 | `2_references_tabulees` | Table de référence saisie à la main |
| 3 | `3_comparaison_A` | Contrôle A (validation nominale, formules d'écart) |
| 4 | `4_plan_sobol` | Plan d'échantillonnage Sobol 256 points (import statique) |
| 5 | `5_comparaison_B` | Contrôle B (propriétés invariantes, flags violation) |
| 6 | `6_rapport_synthese` | Verdict consolidé une page |
| 7 | `7_historique` | Journal des verdicts successifs (dérive temporelle) |

### 6.2 Feuille `1_abaque_import` — import dynamique du CSV résultats

Au lieu de coller les valeurs, importer le CSV via **Données → Obtenir des données → À partir d'un fichier texte/CSV** (Power Query) :

- Source : `../abaque_complet_global.csv` (chemin relatif au classeur, stable après déplacement du repo)
- Séparateur : `;`
- Encodage : `UTF-8`
- Promotion des entêtes
- Actualisation : manuelle via `Ctrl+Alt+F5` ou bouton « Actualiser tout »

**Avantage** : la feuille reste synchronisée à chaque régénération de l'abaque sans re-coller, évitant les oublis de MAJ.

### 6.3 Feuille `2_references_tabulees` — table de référence (saisie manuelle)

Format : une ligne par cas de référence. Colonnes d'entrée **identiques** à celles de `1_abaque_import`, suivies de colonnes `*_ref` pour les sorties attendues.

Colonnes suggérées (ordre) :

```
id_ref | source_ref | date_saisie | auteur |
type_poutre | usage | pente_deg | entraxe_m | classe_service |
g_k_kNm2 | g2_k_kNm2 | q_k_kNm2 | s_k_kNm2 | w_k_kNm2 |
essence | classe_resistance | b_mm | h_mm | longueur_m |
--- oracle ---
eta_m_y_ref | eta_m_z_ref | tau_d_ref | k_crit_ref |
w_inst_ref_mm | w_fin_brut_ref_mm | w_net_fin_ref_mm |
taux_global_ref | verifie_ref
```

Chaque ligne porte sa **provenance** (`source_ref` = calcul manuel EC5 / logiciel tiers / publication / note de calcul) et un identifiant unique (ex. `REF_SOL_001`).

### 6.4 Feuille `3_comparaison_A` — contrôle A (validation nominale)

Pour chaque ligne de `2_references_tabulees`, remonter la ligne correspondante dans `1_abaque_import` par `RECHERCHEX` / `INDEX+EQUIV` sur une clé composite des variables d'entrée.

Exemple de formule (colonne `taux_global_abac`) :

```excel
=RECHERCHEX(
   [@type_poutre] & [@classe_service] & [@classe_resistance] & [@b_mm] & [@h_mm]
   & [@longueur_m] & [@entraxe_m] & [@pente_deg] & [@g_k_kNm2] & [@q_k_kNm2]
   & [@s_k_kNm2] & [@w_k_kNm2];
   '1_abaque_import'[type_poutre] & '1_abaque_import'[classe_service] & ... & '1_abaque_import'[w_k_kNm2];
   '1_abaque_import'[taux_global];
   "NON TROUVE"; 0)
```

Colonnes calculées par ligne :

| Colonne | Formule-type | Commentaire |
|---|---|---|
| `taux_global_abac` | `RECHERCHEX(...)` ci-dessus | Valeur ABAC récupérée |
| `epsilon_taux_global` | `= ([taux_global_abac] - [taux_global_ref]) / [taux_global_ref]` | Erreur relative |
| `verdict_taux` | `= SI(ABS([epsilon_taux_global]) <= 5%; "OK"; "ECART")` | Verdict ligne |
| `verifie_abac` | `RECHERCHEX(...)` sur `verifie` | Statut ABAC |
| `verdict_verifie` | `= SI([verifie_abac] = [verifie_ref]; "OK"; "KO")` | Accord binaire |

Répéter pour chaque grandeur : `eta_m_y`, `tau_d`, `k_crit`, `w_inst`, `w_fin_brut`, `w_net_fin`.

**Mise en forme conditionnelle** : vert si `|ε| ≤ 5 %`, orange si `5 % < |ε| ≤ 10 %`, rouge si `> 10 %` ou `KO`.

**Ligne de synthèse** en haut de feuille (figée) :

```
Biais moyen taux_global : =MOYENNE(Tableau[epsilon_taux_global])
Ecart-type taux_global  : =ECARTYPE.PECH(Tableau[epsilon_taux_global])
% cas conformes         : =NB.SI(Tableau[verdict_taux];"OK") / NBVAL(Tableau[verdict_taux])
Accord binaire (%)      : =NB.SI(Tableau[verdict_verifie];"OK") / NBVAL(Tableau[verdict_verifie])
```

### 6.5 Feuille `4_plan_sobol` — plan d'échantillonnage randomisé

256 lignes tirées **hors Excel** (Python `scipy.stats.qmc.Sobol`, R `randtoolbox::sobol`, ou générateur en ligne) produisant un CSV intermédiaire. Import par Power Query.

Colonnes = toutes les entrées ABAC.

Feuille **scellée** : le seed Sobol et la date de tirage sont inscrits en entête pour garantir la reproductibilité du plan en audit (ASME V&V 10 exige traçabilité des plans d'essai).

### 6.6 Feuille `5_comparaison_B` — contrôle B (propriétés invariantes)

Pour chaque ligne Sobol, récupérer la sortie ABAC par `RECHERCHEX` sur `1_abaque_import`. Puis pour chaque propriété P1–P8, comparer avec des tirages voisins du plan Sobol.

Exemple — **P1 (monotonie portée)** : grouper les tirages à entrées identiques sauf `longueur_m`, trier par portée croissante, vérifier que `taux_global` croît bien. Formule schématique par bloc trié :

```excel
=SI([@taux_global_abac] >= [@[-1]taux_global_abac]; "OK"; "VIOLATION")
```

(syntaxe simplifiée — `DECALER` ou tableaux structurés selon préférence).

Colonne finale `P1_flag` à `P8_flag` : `OK` / `VIOLATION`.

**Synthèse** en haut de feuille :

```
Nb tirages Sobol  : 256
Violations P1     : =NB.SI(Tableau[P1_flag]; "VIOLATION")
Violations P2     : =NB.SI(Tableau[P2_flag]; "VIOLATION")
...
Seuil AQL 1,0 %   : 2,56  (soit tolérance pratique = 2)
Verdict P1        : =SI(NB.SI(Tableau[P1_flag];"VIOLATION") <= 2; "ACCEPTE"; "REJETE")
```

### 6.7 Feuille `6_rapport_synthese`

Tableau final une page :

| Item | Valeur | Verdict |
|---|---|---|
| Norme référence | ASME V&V 10-2019 | — |
| Date de génération abaque | formule `=...` | — |
| Nb lignes abaque | `=NBVAL('1_abaque_import'[taux_global])` | — |
| Nb cas de référence (A) | `=NBVAL('2_references_tabulees'[id_ref])` | — |
| Biais moyen `taux_global` (A) | `=...` | ≤ 2 % |
| Accord binaire `verifie` (A) | `=...` | 100 % |
| Violations P1..P8 (B) | `=...` | ≤ 2 / prop. |
| **Verdict global** | formule `ET(...)` | **ACCEPTE** / **REJETE** |

### 6.8 Feuille `7_historique`

Journal simple : une ligne par exécution — date / auteur / nombre de cas ref / biais / nombre total de violations / verdict global. Permet de détecter toute **dérive temporelle** entre deux générations successives de l'abaque.

### 6.9 Flux de travail recommandé

1. Régénérer les CSV : `uv run abac-vect --toml-calcul configs_calcul_vect.toml`
2. Ouvrir `Comparatif.xlsx` → **Données → Actualiser tout** (Power Query rafraîchit `1_abaque_import`).
3. Compléter si besoin la feuille `2_references_tabulees` (nouveaux cas).
4. Les feuilles 3, 5, 6 se recalculent automatiquement.
5. Lire la feuille `6_rapport_synthese` : verdict immédiat.
6. En cas d'écart : inspecter `3_comparaison_A` ou `5_comparaison_B` pour *root cause analysis*.
7. Reporter la ligne dans `7_historique`.

### 6.10 Hygiène du classeur

- **Verrouiller** les feuilles `1_abaque_import` et `4_plan_sobol` (lecture seule) : ce sont des données, pas du calcul.
- **Protéger par mot de passe** la structure pour éviter la modification accidentelle d'une formule de contrôle.
- **Versionner** le classeur dans git. Format `.xlsx` (suivi grossier) ; envisager un export `.csv` parallèle des feuilles 3, 5, 6 pour un diff lisible.
- **Historiser** les verdicts successifs (feuille 7) : principal détecteur d'une régression silencieuse.

---

## 7. Sources documentaires

### Normes citées

- [ASME V&V 10-2019 — Verification and Validation in Computational Solid Mechanics](https://webstore.ansi.org/standards/asme/asme102019)
- [ASME V&V 10 — présentation (ASME.org)](https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics)
- [ASME VVUQ — Verification, Validation & Uncertainty Quantification](https://www.asme.org/codes-standards/publications-information/verification-validation-uncertainty)
- [ISO 2859-1:1999 — Sampling procedures for inspection by attributes (AQL)](https://www.iso.org/standard/1141.html)
- [ISO 3951-1:2022 — Sampling procedures for inspection by variables (AQL)](https://www.iso.org/standard/74706.html)
- [ISO 3951-2:2013 — Variables, independent quality characteristics](https://www.iso.org/standard/57491.html)
- [EN 1990 Annexe D — Basis of structural design, Design assisted by testing](https://www.phd.eng.br/wp-content/uploads/2015/12/en.1990.2002.pdf)
- [EN 1990 — document JRC complémentaire](https://eurocodes.jrc.ec.europa.eu/sites/default/files/2022-06/EN1990_2_Gulvanessian.pdf)

### Méthodes d'échantillonnage

- [Comparative Study of Latin Hypercube Sampling and Monte Carlo Method in Structural Reliability Analysis (HSET)](https://drpress.org/ojs/index.php/HSET/article/view/4061)
- [On Latin hypercube sampling for structural reliability analysis (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0167473002000395)
- [Sampling based on Sobol' sequences for Monte Carlo techniques applied to building simulations (ResearchGate)](https://www.researchgate.net/publication/257139589_Sampling_based_on_Sobol'_sequences_for_Monte_Carlo_techniques_applied_to_building_simulations)
- [Quasi-Monte Carlo method — Wikipedia](https://en.wikipedia.org/wiki/Quasi-Monte_Carlo_method)
- [Latin hypercube sampling — Wikipedia](https://en.wikipedia.org/wiki/Latin_hypercube_sampling)
- [Sampling based on Sobol' sequences — IBPSA/BS2011](https://publications.ibpsa.org/conference/paper/?id=bs2011_1590)
- [Latin Hypercube vs Monte Carlo — Analytica](https://analytica.com/blog/latin-hypercube-vs-monte-carlo-sampling/)

### Application AQL / échantillonnage industriel

- [ISO 2859-1 — tables de taille d'échantillon (QC Advisor)](https://www.qcadvisor.com/wp-content/uploads/2023/05/AQL-QCADVISOR.pdf)
- [Inspection Levels ISO 2859-1 (QualityInspection.org)](https://qualityinspection.org/inspection-level/)
