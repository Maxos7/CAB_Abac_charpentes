# Modèles de configuration

# `configs_regen.toml` — Ingestion stock SAPEG

## `[ingestion]`

| Paramètre | Type | Obligatoire | Défaut | Notes |
|-----------|------|:-----------:|--------|-------|
| `encodage` | str | Non | `"latin-1"` | Tout encodage Python valide |
| `separateur` | str | Non | `"\|"` | Délimiteur de colonnes CSV |
| `pattern_fichier` | str | Non | `"ALL_PRODUIT_*.csv"` | Glob — fichier le plus récent sélectionné |

## `[mappage_colonnes]`

Convention : `nom_interne = "nom_réel_dans_le_csv"`. Les clés omises sont auto-détectées.

| Clé interne | Obligatoire dans CSV | Description |
|-------------|:--------------------:|-------------|
| `code_article` | **Oui** | Identifiant unique du produit |
| `designation` | Non | Libellé commercial |
| `famille` | Non | Famille produit |
| `disponibilite` | Non | Disponibilité/commandabilité |
| `longueur` | Non | Longueur commerciale max (converti en m) |
| `largeur` | Non | Largeur b (converti en mm) |
| `hauteur` | Non | Hauteur h (converti en mm) |
| `classe` | Non | Classe de résistance EN 338 / EN 14080 |
| `fournisseur` | Non | Nom du fournisseur |

```toml
[ingestion]
encodage        = "latin-1"
separateur      = "|"
pattern_fichier = "ALL_PRODUIT_*.csv"

[mappage_colonnes]
code_article  = "produit_code_article"
designation   = "produit_libelle"
famille       = "Famille"
disponibilite = "produit_commandable"
longueur      = "produit_longueur"
largeur       = "produit_epaisseur"
hauteur       = "produit_largeur"
classe        = "produit_mots_cles"
fournisseur   = "produit_nom_fournisseur"
```

---

# `configs_filtre_regen.toml` — Filtres stock

## `[[filtre]]`

| Paramètre | Type | Obligatoire | Défaut | Notes |
|-----------|------|:-----------:|--------|-------|
| `nom` | str | **Oui** | — | Identifiant unique |
| `sortie` | str | **Oui** | — | Chemin du CSV filtré en sortie |
| `description` | str | Non | `""` | Texte libre |

---

## `[[filtre.regles]]`

Toutes les règles sont combinées en ET logique. Discriminées par `type`.

### `type = "egal"`

| Paramètre | Type | Obligatoire | Notes |
|-----------|------|:-----------:|-------|
| `champ` | str | **Oui** | Nom de colonne CSV |
| `valeur` | str \| float \| int | **Oui** | Comparaison insensible à la casse pour str |

### `type = "plage"`

| Paramètre | Type | Obligatoire | Notes |
|-----------|------|:-----------:|-------|
| `champ` | str | **Oui** | Colonne numérique |
| `min` | float | Non* | Borne inférieure inclusive |
| `max` | float | Non* | Borne supérieure inclusive |

*Au moins `min` ou `max` doit être défini.

### `type = "liste"`

| Paramètre | Type | Obligatoire | Notes |
|-----------|------|:-----------:|-------|
| `champ` | str | **Oui** | Colonne à tester |
| `valeurs` | list[str \| float \| int] | **Oui** | Appartenance à la liste |

### `type = "non_nul"`

| Paramètre | Type | Obligatoire | Notes |
|-----------|------|:-----------:|-------|
| `champ` | str | **Oui** | Rejette : `None`, `""`, `NaN` |

```toml
[[filtre]]
nom         = "charpente"
sortie      = "resultats/stock_charpente.csv"
description = "Produits charpente bois massif"

  [[filtre.regles]]
  type    = "liste"
  champ   = "classe_resistance"
  valeurs = ["C24", "GL24H"]

  [[filtre.regles]]
  type  = "plage"
  champ = "b_mm"
  min   = 45.0

  [[filtre.regles]]
  type  = "plage"
  champ = "h_mm"
  min   = 100.0
```

# `configs_entree_vect.toml` — Ingestion CSV stock pour le calcul

## `[filtrage]` — entree_vect

| Paramètre | Type | Obligatoire | Notes |
|-----------|------|:-----------:|-------|
| `colonne` | str | Non | Nom de colonne après mappage. Si absente : repli sur `classe_resistance` non nulle |
| `valeur` | str | Non | Valeur qui rend une ligne valide |

---

## `[section]` — entree_vect

| Paramètre | Type | Obligatoire | Notes |
|-----------|------|:-----------:|-------|
| `colonne_forme` | str | Non | Colonne CSV : `"rectangle"` (défaut) \| `"rond"` \| `"custom"` |
| `colonne_diametre` | str | Non | Diamètre [mm] pour forme `"rond"` |

---

## `[mappage_colonnes]` — entree_vect

| Clé interne | Obligatoire dans CSV | Description |
|-------------|:--------------------:|-------------|
| `b_mm` | **Oui** | Largeur de section [mm] |
| `h_mm` | **Oui** | Hauteur de section [mm] |
| `classe_resistance` | **Oui** | Classe EN 338 / EN 14080 |
| `id_produit` | Non | Code article SAPEG — propagé en sortie |
| `libelle` | Non | Désignation commerciale — propagée en sortie |
| `statut_filtre` | Non | Colonne statut (valeur attendue : `"retenu"`) |
| `statut_ingestion` | Non | Alternative statut (valeur attendue : `"valide"`) |
| `L_max_m` | Non | Longueur commerciale max [m] |
| `forme_section` | Non | Forme : `"rectangle"` \| `"rond"` \| `"custom"` |
| `d_mm` | Non | Diamètre [mm] — forme `"rond"` |
| `A_cm2` | Non | Aire [cm²] — forme `"custom"` |
| `I_y_cm4` | Non | Moment quadratique axe fort [cm⁴] — forme `"custom"` |
| `I_z_cm4` | Non | Moment quadratique axe faible [cm⁴] — forme `"custom"` |
| `W_y_cm3` | Non | Module résistant axe fort [cm³] — forme `"custom"` |
| `W_z_cm3` | Non | Module résistant axe faible [cm³] — forme `"custom"` |
| `A_eff_cisaillement_cm2` | Non | Section efficace cisaillement [cm²] — forme `"custom"` |
| *toute autre clé* | Non | Renommage de colonnes parasites (ex: `famille_stock = "famille"`) |

> `id_config_materiau` n'est jamais lu depuis le CSV — généré automatiquement par le moteur.


```toml
[filtrage]
colonne = "statut_filtre"   # ou "statut_ingestion"
valeur  = "retenu"          # ou "valide"

[section]
colonne_forme    = "forme_section"   # "rectangle" | "rond" | "custom"
colonne_diametre = "d_mm"

[mappage_colonnes]
# — Obligatoires —
b_mm              = "b_mm"
h_mm              = "h_mm"
classe_resistance = "classe_resistance"
# — Optionnelles sortie —
id_produit        = "id_produit"
libelle           = "libelle"
# — Optionnelles filtrage —
statut_filtre     = "statut_filtre"
# statut_ingestion = "statut_ingestion"
# — Optionnelle enrichissement —
L_max_m           = "L_max_m"
# — Anti-conflit (colonne "famille" du CSV → renommée) —
famille_stock     = "famille"
```

---

# `configs_calcul_vect.toml` — Configurations de calcul EC5


## `[[config_calcul]]`

Les champs marqués **multi-val.** acceptent un scalaire ou une liste → produit cartésien automatique.

| Paramètre | Type | Oblig. | Défaut | Multi-val. | Valeurs / Notes |
|-----------|------|:------:|--------|:----------:|-----------------|
| `id_config_calcul` | str | **Oui** | — | Non | Identifiant unique |
| `type_poutre` | str | **Oui** | — | Non | `"Panne"`, `"PanneDeversee"`, `"PanneAplomb"`, `"Solive"`, `"Chevron"` |
| `usage` | str | **Oui** | — | Non | Clé dans `limites_fleche_ec5.csv` (ex: `"panne_standard"`, `"plancher_courant"`) |
| `L_min_m` | float | Non | `1.0` | Oui | Longueur minimale [m] |
| `L_max_m` | float | Non | `8.0` | Oui | Longueur maximale [m] |
| `pas_longueur_m` | float | Non | `0.10` | Non | Pas de discrétisation [m] |
| `pente_deg` | float | Non | `0.0` | Oui | Pente rampant [°] |
| `entraxe_m` | float | Non | `0.60` | Oui | Entraxe entre poutres [m] |
| `classe_service` | int | Non | `1` | Oui | **1**, 2 ou 3 |
| `g_k_kNm2` | float | Non | `0.0` | Oui | Charges permanentes G [kN/m²] |
| `g2_k_kNm2` | float | Non | `0.0` | Oui | Charges permanentes fragiles G2 [kN/m²] |
| `q_k_kNm2` | float | Non | `0.0` | Oui | Charges variables Q [kN/m²] |
| `categorie_q` | str | Non | `"H"` | Non | `"H"`, `"A"` à `"G"` — lookup ψ EC5 |
| `s_k_kNm2` | float | Non | `0.0` | Oui | Charges neige S [kN/m²] (projection horizontale) |
| `w_k_kNm2` | float | Non | `0.0` | Oui | Pression vent W [kN/m²] |
| `type_toiture_vent` | str | Non | `"1_pan"` | Non | `"1_pan"`, `"2_pans"`, `"terrasse"` |
| `double_flexion` | bool | Non | `false` | Non | Active vérifications double flexion ELU §6.1.6 |
| `fleches_double` | bool | Non | `false` | Non | Active calcul bi-axe ELS flèche (forcé `true` si `double_flexion=true`) |
| `contre_fleche_mm` | float | Non | `0.0` | Non | Pré-cambrure soustraite de w_fin et w_2 [mm] |
| `second_oeuvre` | bool | Non | `false` | Non | Active ELS flèche second-œuvre (w_2) |
| `limite_fleche_inst` | float | Non | — | Non | Override limite ELS instantanée [L/x] |
| `limite_fleche_fin` | float | Non | — | Non | Override limite ELS finale [L/x] |
| `limite_fleche_2` | float | Non | — | Non | Override limite ELS second-œuvre [L/x] |
| `longueur_appui_mm` | float | Non | `50.0` | Oui | Longueur d'appui EC5 §6.1.5 [mm] |
| `k_c90` | float | Non | `1.0` | Oui | Facteur appui k_c90 EC5 §6.1.5(4) |
| `entraxe_antideversement_mm` | float | Non | `0.0` | Non | 0 = longueur complète [mm] |

---

## `[[config_calcul.filtres]]`

| Paramètre | Type | Obligatoire | Valeurs possibles |
|-----------|------|:-----------:|-------------------|
| `champ` | str | **Oui** | Attribut de `ConfigMatériauVect` : `"classe_resistance"`, `"b_mm"`, `"h_mm"`, `"famille"`… |
| `operateur` | str | **Oui** | `"=="`, `"!="`, `">="`, `"<="`, `">"`, `"<"`, `"in"` |
| `valeur` | str \| float \| int \| list | **Oui** | Liste si `operateur = "in"`, scalaire sinon |

### Modèle Panne déversée

```toml
[[config_calcul]]
id_config_calcul = "PANNE_DEVERSEE"
type_poutre       = "PanneDeversee"
usage             = "panne_standard"

L_min_m           = 2.0
L_max_m           = 12.0
pas_longueur_m    = 0.25

pente_deg         = [40]
entraxe_m         = [1.2]
classe_service    = 1

g_k_kNm2          = [0.40]
g2_k_kNm2         = [0.17]   # second œuvre/fragile (si second_oeuvre = true)
q_k_kNm2          = 0.0
categorie_q       = "H"
s_k_kNm2          = 0.36
w_k_kNm2          = 0.0

double_flexion             = true
fleches_double             = true
contre_fleche_mm           = 0.0
second_oeuvre              = true
entraxe_antideversement_mm = 0.0
longueur_appui_mm          = 50.0
```

### Modèle Panne aplomb

```toml
[[config_calcul]]
id_config_calcul = "PANNE_APLOMB"
type_poutre       = "PanneAplomb"
usage             = "panne_standard"

L_min_m           = 2.0
L_max_m           = 8.0
pas_longueur_m    = 0.25

pente_deg         = [30, 45]
entraxe_m         = [1.2]
classe_service    = 1

g_k_kNm2          = 0.40
q_k_kNm2          = 0.0
categorie_q       = "H"
s_k_kNm2          = 0.36
w_k_kNm2          = 0.0

entraxe_antideversement_mm = 0.0
longueur_appui_mm          = 60.0
```

### Modèle Solive de plancher

```toml
[[config_calcul]]
id_config_calcul = "SOLIVE_PLANCHER"
type_poutre       = "Solive"
usage             = "plancher_courant"

L_min_m           = 2.0
L_max_m           = 6.0
pas_longueur_m    = 0.25

pente_deg         = 0.0
entraxe_m         = [0.60]
classe_service    = 1

g_k_kNm2          = 0.60
g2_k_kNm2         = 0.17
q_k_kNm2          = 1.50
categorie_q       = "A"
s_k_kNm2          = 0.0
w_k_kNm2          = 0.0

second_oeuvre              = true
longueur_appui_mm          = 50.0
entraxe_antideversement_mm = 0.0
```

### Modèle Chevron

```toml
[[config_calcul]]
id_config_calcul = "CHEVRON"
type_poutre       = "Chevron"
usage             = "chevron"

L_min_m           = 1.0
L_max_m           = 5.0
pas_longueur_m    = 0.25

pente_deg         = [30, 45]
entraxe_m         = [0.5, 0.6, 0.7]
classe_service    = 1

g_k_kNm2          = 0.30
q_k_kNm2          = 0.0
categorie_q       = "H"
s_k_kNm2          = 0.36
w_k_kNm2          = 0.0

longueur_appui_mm = 40.0
```

### Filtre sur articles (optionnel dans `[[config_calcul]]`)

```toml
  [[config_calcul.filtres]]
  champ     = "classe_resistance"
  operateur = "in"
  valeur    = ["C24", "GL24h"]

  [[config_calcul.filtres]]
  champ     = "h_mm"
  operateur = ">="
  valeur    = 160
```

---

# `configs_sortie_vect.toml` — Exports CSV

### `[indice_de_classement]`

| Paramètre | Type | Obligatoire | Défaut | Notes |
|-----------|------|:-----------:|--------|-------|
| `actif` | bool | Non | `true` | `false` supprime la colonne de tous les exports |
| `poids_section` | float | Non | `1.0` | Critère section fine (b×h minimal) — `0` désactive |
| `poids_longueur` | float | Non | `1.0` | Critère longueur proche (L_max_article − L_m minimal) — `0` désactive |
| `poids_classe` | float | Non | `1.0` | Critère classe faible — `0` désactive |
| `ordre_classes_resistance` | list[str] | Non | — | Du plus économique au plus résistant ; classes absentes traitées comme pire cas |

---

## `[[vue]]`

| Paramètre | Type | Obligatoire | Défaut | Notes |
|-----------|------|:-----------:|--------|-------|
| `nom` | str | **Oui** | — | Identifiant unique |
| `description` | str | Non | — | Texte libre |
| `fichier_sortie` | str | Non | `"{nom}.csv"` | Chemin relatif au répertoire de sortie |
| `type` | str | **Oui** | — | `"agregation"` \| `"filtre"` |
| `colonnes` | list[str] | Non | `[]` | Colonnes à retenir ; `[]` = toutes |
| `trier_par` | list[str] | Non | `[]` | Ordre de tri après filtrage/agrégation |
| `groupby` | list[str] | Si `type="agregation"` | — | Colonnes de regroupement |
| `cles_groupe` | list[str] | Non | — | `type="filtre"` uniquement — colonnes définissant un groupe |
| `limite_par_groupe` | int | Non | — | `type="filtre"` uniquement — nb max articles retenus par groupe (après tri) |

**Colonnes auto-générées par `type = "agregation"` :**

| Colonne | Description |
|---------|-------------|
| `longueur_max_admissible_m` | Portée max vérifiée (taux_global ≤ 1.0) par groupe |
| `verif_determinante` | Vérification au taux le plus élevé |
| `taux_determinant` | Valeur de ce taux |

---

## `[[vue.filtres]]`

| Paramètre | Type | Obligatoire | Notes |
|-----------|------|:-----------:|-------|
| `champ` | str | **Oui** | Nom de colonne du DataFrame |
| `operateur` | str | **Oui** | `"egal"`, `"different"`, `"inferieur"`, `"superieur"`, `"inferieur_egal"`, `"superieur_egal"`, `"contient"`, `"in"` |
| `valeur` | str \| float \| int \| bool \| list | **Oui** | Liste si `operateur = "in"`, scalaire sinon ; `"contient"` insensible à la casse |

---



### Indice de classement

```toml
[indice_de_classement]
actif           = true
poids_section   = 1.0
poids_longueur  = 1.0
poids_classe    = 1.0

ordre_classes_resistance = [
    "C18", "C24", "C27", "C30", "C35", "C40",
    "GL24h", "GL24c", "GL28h", "GL28c", "GL32h", "GL32c"
]
```

### Vue `filtre`

```toml
[[vue]]
nom            = "ma_vue"
description    = "Description"
fichier_sortie = "abaque_ma_vue.csv"
type           = "filtre"
colonnes       = ["col1", "col2"]
trier_par      = ["col1"]
# cles_groupe       = ["col1", "col2"]   # limite par groupe
# limite_par_groupe = 10

  [[vue.filtres]]
  champ     = "verifie"
  operateur = "egal"
  valeur    = "True"
```

### Vue `agregation`

```toml
[[vue]]
nom            = "ma_vue_agreg"
description    = "Longueur max admissible par groupe"
fichier_sortie = "abaque_agreg.csv"
type           = "agregation"
groupby        = ["id_config_materiau", "id_config_calcul"]
colonnes       = ["classe_resistance", "b_mm", "h_mm",
                  "longueur_max_admissible_m", "verif_determinante", "taux_determinant"]
trier_par      = ["classe_resistance", "b_mm", "h_mm"]

  [[vue.filtres]]
  champ     = "classe_resistance"
  operateur = "contient"
  valeur    = "C"
```

### Vue `verifie` — export brut lignes vérifiées

```toml
[[vue]]
nom            = "verifie"
description    = "Toutes les lignes vérifiées (taux_global ≤ 1.0) — export brut"
fichier_sortie = "abaque_verifie.csv"
type           = "filtre"
colonnes       = ["id_config_calcul", "id_config_materiau", "classe_resistance",
                  "b_mm", "h_mm", "longueur_m", "taux_global"]
trier_par      = ["id_config_calcul", "classe_resistance", "b_mm", "h_mm", "longueur_m"]

  [[vue.filtres]]
  champ     = "verifie"
  operateur = "egal"
  valeur    = true
```

### Vue `massif` — bois massif C, longueur max admissible

```toml
[[vue]]
nom            = "massif"
description    = "Bois massif C uniquement — longueur max admissible"
fichier_sortie = "abaque_massif_global.csv"
type           = "agregation"
groupby        = ["id_config_materiau", "id_config_calcul"]
colonnes       = ["classe_resistance", "b_mm", "h_mm", "id_config_calcul",
                  "longueur_max_admissible_m", "verif_determinante", "taux_determinant"]
trier_par      = ["classe_resistance", "b_mm", "h_mm"]

  [[vue.filtres]]
  champ     = "classe_resistance"
  operateur = "contient"
  valeur    = "C"
```

### Vue `GL` — lamellé-collé, longueur max admissible

```toml
[[vue]]
nom            = "GL"
description    = "Bois lamellé-collé GL uniquement — longueur max admissible"
fichier_sortie = "abaque_GL_global.csv"
type           = "agregation"
groupby        = ["id_config_materiau", "id_config_calcul"]
colonnes       = ["classe_resistance", "b_mm", "h_mm", "id_config_calcul",
                  "longueur_max_admissible_m", "verif_determinante", "taux_determinant"]
trier_par      = ["classe_resistance", "b_mm", "h_mm"]

  [[vue.filtres]]
  champ     = "classe_resistance"
  operateur = "contient"
  valeur    = "GL"
```

### Vue `detail_P30` — détail complet d'une config

```toml
[[vue]]
nom            = "detail_P30"
description    = "Détail complet config pente 30° — tous les taux ELU/ELS"
fichier_sortie = "abaque_detail_P30.csv"
type           = "filtre"
colonnes       = []    # vide = toutes les colonnes
trier_par      = ["id_config_materiau", "longueur_m"]

  [[vue.filtres]]
  champ     = "id_config_calcul"
  operateur = "contient"
  valeur    = "_P30_"
```

### Vue `grandes_sections` — export métreur

```toml
[[vue]]
nom            = "grandes_sections"
description    = "Sections b≥100 et h≥200 — longueur max admissible"
fichier_sortie = "abaque_grandes_sections.csv"
type           = "agregation"
groupby        = ["id_config_materiau", "id_config_calcul"]
colonnes       = ["classe_resistance", "b_mm", "h_mm", "id_config_calcul",
                  "longueur_max_admissible_m", "verif_determinante", "taux_determinant"]
trier_par      = ["b_mm", "h_mm"]

  [[vue.filtres]]
  champ     = "b_mm"
  operateur = "superieur_egal"
  valeur    = 100.0

  [[vue.filtres]]
  champ     = "h_mm"
  operateur = "superieur_egal"
  valeur    = 200.0
```

**Opérateurs disponibles :** `egal`, `different`, `inferieur`, `superieur`, `inferieur_egal`, `superieur_egal`, `contient`, `in`
