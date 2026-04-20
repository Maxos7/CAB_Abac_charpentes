# CAB_Abac_Charpentes

## `sapeg-regen-stock` — Régénération du stock SAPEG

Lit le fichier d'export SAPEG (`ALL_PRODUIT_*.csv`), enrichit chaque ligne (propriétés mécaniques EC5) et produit des CSV filtrés prêts pour le pipeline de calcul.

## `abac-vect` — Pipeline EC5 vectorisé

Génère des abaques de portées admissibles pour les pièces de charpente (pannes, solives, chevrons) selon l'Eurocode 5. Toutes les portées, combinaisons EC0 et matériaux sont traités en une seule passe NumPy.

Vérifications : flexion (§6.1.6), effort tranchant (§6.1.7), flambement (§6.3.2), déversement (§6.3.3), compression oblique (Hankinson), flexion composée, ELS flèches (instantanée, finale, second œuvre).

---

# Installation

Nécessite [UV](https://docs.astral.sh/uv/getting-started/installation/) :
```
winget install --id=astral-sh.uv -e
```
Les dépendances Python sont installées automatiquement par UV au premier lancement.

| Paquet | Usage |
|--------|-------|
| `numpy` | Calcul vectorisé |
| `pandas` | Lecture/écriture CSV |
| `pydantic` | Validation des configs TOML |
| `loguru` | Journalisation |
| `duckdb` | Stockage optionnel des tenseurs |

---

# Configuration

Référence complète des paramètres : **[modeles_config.md](modeles_config.md)**

| Fichier | Rôle |
|---------|------|
| `configs_regen.toml` | Ingestion du fichier SAPEG (encodage, séparateur, mappage colonnes) |
| `configs_filtre_regen.toml` | Filtres appliqués au stock (classes, plages de dimensions…) |
| `configs_entree_vect.toml` | Mappage CSV stock → noms internes du moteur EC5 |
| `configs_calcul_vect.toml` | Configurations de calcul EC5 (charges, géométrie, type poutre) |
| `configs_sortie_vect.toml` | Exports CSV dérivés depuis `abaque_complet_global.csv` |

---

# Exécution

## `abac-vect`

Stock détecté automatiquement (`ALL_PRODUIT_*.csv` dans le répertoire courant) :
```
uv run abac-vect --toml-calcul configs_calcul_vect.toml
```
Avec fichier d'entrée CSV personnalisé :
```
uv run abac-vect --toml-calcul configs_calcul_vect.toml --toml-entree configs_entree_vect.toml
```
Source dans un autre répertoire :
```
uv run abac-vect --toml-calcul configs_calcul_vect.toml --source "C:\SAPEG\exports"
```
Stock déjà régénéré :
```
uv run abac-vect --toml-calcul configs_calcul_vect.toml --stock "resultats/stock_charpente.csv"
```
Sauvegarder les tenseurs de taux (analyses avancées) :
```
uv run abac-vect --toml-calcul configs_calcul_vect.toml --tenseurs
```
Afficher le détail des calculs :
```
uv run abac-vect --toml-calcul configs_calcul_vect.toml --verbose
```

## `sapeg-regen-stock`

```
uv run sapeg-regen-stock regenerer --source "." --filtres "configs_filtre_regen.toml" --stock-enrichi "resultats/stock_enrichi.csv"
```

---

# Licence

Distribué sous licence **[EUPL v1.2](LICENSE)**.
Copyright (c) 2024-2026 Josselin SCHULER — CAB Abac Charpentes
