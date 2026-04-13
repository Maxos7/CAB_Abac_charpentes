# CAB_Logiciels_BE_Charpentes

WiP (Work in Progress)

# Installation

Ce progrmma s'execute sous un environement python gérer via UV
Si vous ne disposée pas de UV, vous pouvez l'installer via la commande suivante :
```
winget install --id=astral-sh.uv  -e
```
Ou suivez les instruction de l'editeur
https://docs.astral.sh/uv/getting-started/installation/#pypi

Une fois cela ffait, UV ce chargeras de l'instalation des dépendance lors du premier lancement d'un des programmes.

# Configuration

## Configuration "regene stock"

Le sous programme de filtre et régeneration des information du stock est paramétrable.
Un fichier stock_enrichi est crée par défaux dans le dossier résultats.

### Configuration du régénerateur

WiP

### Configuration du filtre

 Pour tout filtre remplis dans le fichier "comfig_regen_stock.toml" un autre fichier filtée est crée suivant les régle de filtre.

```
[[filtre]]

# nom du filte
nom = "charpente"

# position et nomage du fichier de sortie à la racine
sortie = "résultats/stock_charpente.csv"

# Information sur lusage du fichier filtée
description = "Produits charpente bois pour usages structurels"

# régle de filtre selon liste d'argument
  [[filtre.regles]]
  type = "liste"
  champ = "classe_resistance"
  valeurs = ["C24", "GL24H", "GT24"]

# régle de filtre selon plage numérique (min, max)
  [[filtre.regles]]
  type = "plage"
  champ = "b_mm"
  min = 45.0

# régle de filtre selon egalitée d'argument
  [[filtre.regles]]
  type = "egal"
  champ = "classe_resistance"
  valeur = "C24"
  ```

## Configuration "calcul abac"

Les calcule son cycliser à partire de configuration de calcul renségnier dans "comfig_calcul.toml".
Chaque configuration donne lieu à un calcul combinatoir.

```
[[config_calcul]]

# Non de la config associer aux résultats
id_config_calcul = "PANNE_TOITURE_INACC" 

# Typologie de poutre (panne; solive; ...)
type_poutre = "Panne" 

# Zone d'usage de la pièce
usage = "TOITURE_INACC" 

# Valeur Min pour le dépar du calcule de portée incrémental
L_min_m = 2.0 

# Pas d'incrémentation de la portée
pas_longueur_m = 0.5 

# Pente de la zone de chargement (float; list[float])
pente_deg = [4, 15, 30, 35, 40, 45] 

# Entraxe de la zone de chargement (float; list[float])
entraxe_m = [1.2, 1.7] 

# Classe de service (1, 2, 3)
classe_service = 1 

# Valeur permanente de chargement (float; list[float])
g_k_kNm2 = [0.4, 0.5, 0.6, 0.7, 0.8] 

# Valeur permanente fragile de chargement (float)
# Non foncionel pour l'instant
# g2_k_pcent

# Valeur exploitation de chargement (float; list[float])
q_k_kNm2 = 0.0 

categorie_q = "H"

# Valeur neige de chargement (float; list[float])
s_k_kNm2 = 0.36 

# Valeur vent de chargement (float; list[float])
w_k_kNm2 = 0.0 

# typologie de toitur pour le vent
type_toiture_vent = "1_pan" 

# Prise en compte du second oeuvre (boolean)
second_oeuvre = false 

# Prise en compte de l'orientation de la pièce pour la décomposition des charges (boolean)
double_flexion = true 

# Valeur d'entraxe pour entidéversement (portée maxe de déversement)
entraxe_antideversement_mm = 0 

# coeficient de conservation des résultas (0.0->1.0) ex: pour 0.8, 80% les resultas inferieur ou égale a 80% de taux d'usage déterminent son admis.
marge_securite = 0 
```

# Execution

## Lancer le calcul de l'abaque

Ce programme séxecute en deux phase :
- Dabort un lacement automatique de "sapeg_regen_stock" afin d'avoire une base a jour.
- Puit une execution de "abac_charpente"

Pour ce faire executer la commande "lancer_calcul_abac.bat" voulue ou executer la commande "uv run"

Si la source est à la racine
```
uv run abac calculer --config "config.toml"
```
Si la source est dans un autre répertoire est est de forme "ALL_PRODUIT_*.csv"
```
uv run abac calculer --stock "C:\" --config "config.toml"
```
Si la source est exacte chemin\votrefichier.csv
```
uv run abac calculer --stock "C:\votreficher.csv" --config "config.toml"
```

## Lancer la régéneration du stock

Ce programme peut étre lancée de magniére indépendante.
````
uv run sapeg-regen-stock regenerer --source "." --filtres "configs_filtre.toml" --stock-enrichi "resultats\stock_enrichi.csv"
````

## Lancer la génération des abaque visuel

Ce programme génère les abaques graphiques à partir du fichier `portees_admissibles.csv`.
```
uv run abac-visuel generer --donnees "resultats/portees_admissibles.csv" --configs "configs_calcul.toml" --sortie "resultats/graphiques"
```
Par défaut les graphiques sont enregistrés au format PNG. Pour obtenir des fichiers PDF :
```
uv run abac-visuel generer --format pdf
```

## Lancer le calcul vectorisé (abac-vect)

Ce programme est une version vectorisée du calcul EC5. Il traite toutes les portées et combinaisons de paramètres en une seule passe numpy, ce qui le rend significativement plus rapide pour les gros abaques paramétriques.

Il séxecute en deux phase :
- Dabort un lancement automatique de "sapeg_regen_stock" afin d'avoire une base a jour (sauf si un stock est fournie directement).
- Puit une execution vectorisée du pipeline EC5.

Résolution du stock (par ordre de priorité) :

Si la source est dans le répertoire courant (ALL_PRODUIT_*.csv détecté automatiquement)
```
uv run abac-vect --toml-calcul "configs_calcul_vect.toml"
```
Si la source est dans un autre répertoire
```
uv run abac-vect --toml-calcul "configs_calcul_vect.toml" --source "C:\SAPEG\exports"
```
Si le stock est déja régénéré et disponible directement
```
uv run abac-vect --toml-calcul "configs_calcul_vect.toml" --stock "resultats/stock_enrichi.csv"
```
Pour sauvegarder les tenseurs de taux dans une base DuckDB (analyses avancées)
```
uv run abac-vect --toml-calcul "configs_calcul_vect.toml" --tenseurs
```
Pour afficher le détail des calculs par combinaison (charges, taux ELU/ELS)
```
uv run abac-vect --toml-calcul "configs_calcul_vect.toml" --verbose
```

# Configuration (suite)

## Configuration "calcul abac vectorisé"

Les calculs sont définis dans `configs_calcul_vect.toml`. Chaque `[[config_calcul]]` est indépendante. Les champs acceptant une liste génèrent le produit cartésien automatiquement.

```
[[config_calcul]]

# Identifiant de la configuration (apparait dans les CSV de sortie)
id_config_calcul = "PANNE_STD"

# Typologie de poutre : Panne | PanneAplomb | PanneDeversee | Chevron | Solive | Sommier
type_poutre = "Panne"

# Zone d'usage de la pièce
usage = "panne_standard"

# Portée minimum de début de calcul (m)
L_min_m = 2.0

# Portée maximum de fin de calcul (m)
L_max_m = 8.0

# Pas d'incrémentation de la portée (m)
pas_longueur_m = 0.25

# Pente de la zone de chargement (float ou list[float]) → produit cartésien si liste
pente_deg = [15, 30, 45]

# Entraxe de la zone de chargement (float ou list[float])
entraxe_m = [1.0, 1.2, 1.7]

# Classe de service (1, 2 ou 3)
classe_service = 1

# Charge permanente hors poids propre (kN/m²) (float ou list[float])
g_k_kNm2 = 0.40

# Charge d'exploitation (kN/m²)
q_k_kNm2 = 0.0

# Catégorie d'exploitation EN 1990 (A, B, C, D, E, F, G, H)
categorie_q = "H"

# Charge de neige (kN/m²)
s_k_kNm2 = 0.36

# Charge de vent (kN/m²)
w_k_kNm2 = 0.0

# Double flexion (décomposition des charges selon les deux axes)
double_flexion = true

# Entraxe anti-déversement (mm) — 0 = pas de risque de déversement
entraxe_antideversement_mm = 0.0

# Longueur d'appui (mm)
longueur_appui_mm = 60.0

# Filtres sur les matériaux du stock (optionnel — peut être répété)
  [[config_calcul.filtres]]
  champ     = "classe_resistance"
  operateur = "in"
  valeur    = ["C24", "C30", "GL24H"]

  [[config_calcul.filtres]]
  champ     = "h_mm"
  operateur = ">="
  valeur    = 120
```

Opérateurs de filtre disponibles : `egal`, `different`, `inferieur`, `superieur`, `inferieur_egal`, `superieur_egal`, `contient`, `in`.

## Configuration des vues de sortie vectorisées

Le fichier `configs_sortie_vect.toml` permet de définir des exports CSV dérivés depuis le fichier global `abaque_complet_global.csv`. Si le fichier est absent, seul `abaque_complet_global.csv` est produit.

```
[[vue]]

# Identifiant de la vue
nom = "synthetique"

# Description (informatif)
description = "Longueur max admissible par couple (matériau × config)"

# Nom du fichier de sortie dans le dossier résultats
fichier_sortie = "abaque_synthetique_global.csv"

# Type de vue : agregation (portée max par groupe) ou filtre (lignes brutes)
type = "agregation"

# Colonnes de regroupement pour l'agrégation
groupby = ["id_config_materiau", "id_config_calcul"]

# Colonnes à conserver dans le fichier de sortie (vide = toutes)
colonnes = [
    "id_config_materiau",
    "id_config_calcul",
    "classe_resistance",
    "b_mm",
    "h_mm",
    "longueur_max_admissible_m",
    "taux_determinant",
    "verif_determinante",
]

# Tri du fichier de sortie
trier_par = ["id_config_calcul", "classe_resistance", "b_mm", "h_mm"]

# Filtre optionnel sur les lignes (peut être répété)
  [[vue.filtres]]
  champ     = "classe_resistance"
  operateur = "contient"
  valeur    = "C"
```

Colonnes calculées automatiquement par l'agrégation :
- `longueur_max_admissible_m` — portée maximale vérifiée (taux global ≤ 1.0)
- `verif_determinante` — vérification au taux le plus élevé (§6.1.6, §6.1.7, §7.2…)
- `taux_determinant` — valeur de ce taux
