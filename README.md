# CAB_Logiciel_BE_Charpentes

WiP (Work in Progress)

# Installation

Si vous ne disposée pas de UV, vous pouvez l'installer via la commande suivante :
```
winget install --id=astral-sh.uv  -e
```
Ou suivez lzs instruction de l'editeur
https://docs.astral.sh/uv/getting-started/installation/#pypi

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

WiP
