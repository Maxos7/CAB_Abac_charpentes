# CAB_Abac_charpentes
Code de calcule d'abac pour une série d'hypotése pour l'enssemble des piéces en stock.

# Instalation

104780	MAT_748238e9


# Configuration

## Configuration regene stock



## Configuration calcul abac

# Execution
## Lancer le calcule de l'abaque
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



## Lancer la génération des abaque visuel


