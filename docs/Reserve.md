# Document de Réserve — ABAC-Charpente (abac_charpente_vectoriser)

> Ce document définit le périmètre fonctionnel du logiciel, les problèmes inhérents à sa constitution, et distingue explicitement ce pour quoi il est conçu de ce pour quoi il ne l'est pas.
> **Dernière mise à jour** : 2026-04-20

---

## 1. Périmètre — Ce pour quoi le logiciel est fait

`abac_charpente_vectoriser` est un moteur de calcul vectorisé produisant des **abaques de portées admissibles** pour des éléments de charpente bois, conformément à l'Eurocode 5 (EN 1995-1-1) et à l'annexe nationale française.

### 1.1 Fonction principale

Le logiciel calcule, pour un ensemble de configurations matériau et de configurations de calcul, la **portée maximale admissible** d'un élément de charpente en simple appui. Le résultat est un fichier CSV (`abaque_complet_global.csv`) exploitable comme abaque paramétrique.

### 1.2 Types d'éléments supportés

| Type | Orientation | Double flexion | Déversement |
|---|---|---|---|
| PanneDeversée | Inclinée, normale au rampant | Optionnelle | Oui (k_crit) |
| PanneAplomb | Inclinée, verticale | Intrinsèque | Oui (k_crit) |
| Chevron | Inclinée, dans l'axe du rampant | Non | Non |
| Solive | Horizontale | Non | Oui (si l_antidéversement renseigné) |
| Sommier | Horizontale | Non | Oui (si l_antidéversement renseigné) |

### 1.3 Matériaux supportés

| Famille | Norme | Classes |
|---|---|---|
| Bois massif résineux | EN 338:2016 | C16, C18, C22, C24, C27, C30, C35, C40 |
| Bois massif feuillus | EN 338:2016 | D18, D24, D30, D35, D40, D50, D60, D70 |
| Lamellé-collé homogène/combiné | EN 14080:2013 | GL24h/c, GL28h/c, GL32h/c, GL36h/c |
| Reconstitué | — | GT18, GT24 |

### 1.4 Formes de section

- **RECTANGULAIRE** — section pleine b × h (cas courant, entièrement validée)
- **RONDE** — section pleine circulaire depuis d_mm ; k_crit = 1,0 (section doublement symétrique, pas de déversement)
- **PERSONNALISEE** — propriétés A, I_y, I_z, W_y, W_z lues directement depuis le CSV stock

### 1.5 Vérifications réalisées

**ELU (États Limites Ultimes)**

| Vérification | Référence normative |
|---|---|
| Flexion axe fort / axe faible | EC5 §6.1.6 |
| Double flexion (k_m = 0,7) | EC5 §6.1.6 |
| Cisaillement (k_cr = 0,67) | EC5 §6.1.7 + AN France |
| Déversement (λ_rel,m → k_crit) | EC5 §6.3.3 |
| Flambement (λ_rel,c → k_c, β_c) | EC5 §6.3.2 + AN France |
| Effort normal (traction / compression) | EC5 §6.1.2 |
| Compression oblique (Hankinson) | EC5 §6.2.2 |
| Appui (σ_c,90, longueur minimale) | EC5 §6.1.5 |

**ELS (États Limites de Service)**

| Vérification | Référence normative |
|---|---|
| Flèche instantanée (sous Q seul — AN France) | EC5 §7.2 |
| Flèche finale (fluage G × (1 + k_def) + Q) | EC5 §7.2 |
| Flèche second-œuvre (limite L/500 — CODIFAB N°1951) | EC5 §7.2 |
| Composante verticale de flèche pour éléments inclinés | AN France |

### 1.6 Base normative

| Norme | Objet |
|---|---|
| EN 1990:2002 | Combinaisons d'actions (ELU fondamentale, ELS caractéristique, quasi-permanente) |
| EN 1991-1-3 | Charges de neige — coefficient de forme µ₁(α) |
| EN 1991-1-4 | Pression de vent — coefficients c_pe (toitures courantes) |
| EN 1995-1-1:2004/A1:2008 | Dimensionnement des structures en bois |
| EN 338:2016 | Bois massif — classes de résistance |
| EN 14080:2013 | Bois lamellé-collé — propriétés mécaniques |
| AN France (NF EN 1995-1-1/NA) | Valeurs nationales : k_cr, β_c, ψ₂ = 0, limites de flèche, composante verticale |
| CODIFAB N°1951 | Interprétation AN : limite second-œuvre L/500 (cloisons, chapes) |

### 1.7 Paramètres de configuration

Toute la configuration est déclarative via des fichiers TOML :

- `configs_entree_vect.toml` — mappage colonnes du CSV stock, filtrage, forme de section
- `configs_calcul_vect.toml` — types de poutre, portées, charges, classe de service, géométrie

Un paramètre de type liste génère automatiquement le produit cartésien des configurations (ex. `pente_deg = [30, 40, 50]` × `entraxe_m = [0.6, 1.2]` → 6 variantes).

---

## 2. Ce pour quoi le logiciel n'est pas fait

### 2.1 Types d'éléments hors périmètre

Les types suivants ne sont **pas implémentés** :

- **Arbaletrier** — compression + flexion combinées ; vérifications spécifiques EC5 §6.2.4 non réalisées
- **Entrait** — traction + flexion combinées
- **Faîtière** — chargement symétrique bi-portée
- **Poutre continue** — schéma statique multi-appuis ; le pipeline suppose un **simple appui** dans tous les cas

### 2.2 Sections hors périmètre

- Sections composées, en I, en T, en caisson, ou tout profilé non plein
- Pour la section PERSONNALISEE : si les colonnes A/I/W sont absentes du CSV, le logiciel applique un **fallback silencieux** sur les formules rectangulaires ; aucune erreur n'est levée

### 2.3 Domaines de vérification non couverts

- **Assemblages et connexions** — aucune vérification EC5 §8 (chevilles, boulons, encoches, etc.)
- **Justification incendie** — pas de calcul de vitesse de carbonisation EC5 §4
- **Vibrations et dynamique** — pas d'analyse fréquentielle EC5 §7.3, pas d'amplification dynamique
- **Effets du temps au-delà du fluage** — k_def est appliqué ; k_ser et effets rhéologiques avancés ne le sont pas
- **Concentrations de contraintes locales** — le pipeline suppose des sections prismatiques sans entailles ni perçages

### 2.4 Charges non couvertes

- Charges d'exploitation variable Q de type autre que valeur scalaire uniforme (pas de charges roulantes, pas de charges mobiles)
- Profils de vent personnalisés — la table c_pe est fixe pour des toitures courantes ; les géométries atypiques ne sont pas couvertes
- Neige pour pentes supérieures à 60° — µ₁(α) est défini jusqu'à 60° ; au-delà, le comportement n'est pas garanti

### 2.5 Portée réglementaire

- Le logiciel produit des **taux de vérification** et des **portées admissibles** à titre d'outil de prédimensionnement
- Il **ne constitue pas une note de calcul** au sens réglementaire et ne remplace pas la vérification et la signature d'un ingénieur structure habilité
- Les résultats sont valables dans le cadre réglementaire **français uniquement** (AN France). Une adaptation des coefficients nationaux est nécessaire pour tout autre pays membre

---

## 3. Problèmes sous-jacents à la constitution du logiciel

### 3.1 Absence de suite de tests automatisés

Il n'existe pas de suite de tests unitaires ou d'intégration. La validation repose sur la revue manuelle des sorties par un ingénieur. Toute modification du moteur de calcul (formules EC5, combinaisons EC0, facteurs AN) ne bénéficie d'aucun filet de régression automatique.

**Conséquence** : un changement de logique peut introduire silencieusement une erreur de calcul sans qu'elle soit détectée avant l'usage des résultats.

### 3.2 Risque de dérive numérique

Les vérifications ELU et ELS sont réalisées sur des tenseurs NumPy de forme (n_L × n_C × n_M). Les opérations broadcast-compatibles accumulent des erreurs d'arrondi flottant (IEEE 754 float64). Aucune borne explicite sur l'erreur numérique n'est définie ni vérifiée.

**Cas sensibles identifiés** : calcul de k_crit lorsque λ_rel,m → 0 (division potentielle par une valeur très faible) ; calcul du taux de cisaillement pour des portées très courtes.

### 3.3 Dépendances à risque de rupture de compatibilité

| Dépendance | Version cible | Risque |
|---|---|---|
| Python | 3.11+ | Rupture de syntaxe (match/case, f-strings) lors d'une régression de version |
| NumPy | 2.x | Changements de comportement sur `np.where`, `np.newaxis`, types float |
| Pandas | — | Évolution des APIs `DataFrame.itertuples`, lecture CSV |
| Pydantic | 2.x | Incompatibilité avec modèles Pydantic v1 si upgrade majeur |

Un gel de version explicite (fichier `pyproject.toml` avec bornes supérieures) est la seule mitigation fiable.

### 3.4 Registre de déduplication sans détection de collision

Le registre `registre_calcul.csv` utilise `id_config_materiau` (hash de propriétés) pour éviter de recalculer des paires déjà traitées. En cas de **collision de hash** (probabilité très faible mais non nulle), un matériau différent pourrait être ignoré sans avertissement.

De plus, si les paramètres de calcul changent sans que le hash change (modification d'une dimension non incluse dans le hash), le registre doit être purgé manuellement.

### 3.5 Corrections ELS flèche — impact rétrospectif

Cinq corrections substantielles ont été apportées au module de calcul des flèches ELS (détaillées dans `docs/ETAT_FLECHES.md`) :

1. Limite second-œuvre corrigée de L/300 à **L/500** (CODIFAB N°1951)
2. Base de la flèche instantanée corrigée de G+Q à **Q seul** (AN France)
3. Double flexion ELS étendue aux composantes G/Q/G2 séparées
4. Direction de la flèche corrigée de la résultante vectorielle à la **composante verticale**
5. Formule de flèche finale corrigée : w_fin = w_G(1 + k_def) + w_Q (k_def non appliqué à Q)

Ces corrections ont un impact direct sur les portées admissibles calculées. Tout abaque produit avant ces corrections est **obsolète et ne doit pas être utilisé**.

### 3.6 Responsabilité d'interprétation des sorties

Le fichier de sortie indique un `taux_global` et un indicateur `verifie` (booléen). La décision de retenir une portée, d'en modifier les conditions aux limites, ou d'adapter les charges relève de la **responsabilité exclusive de l'ingénieur** qui utilise les abaques.

Le logiciel ne valide pas la cohérence physique des configurations d'entrée (ex. portée minimale > portée maximale, charge nulle avec classe de service 3) : certaines configurations invalides peuvent produire des résultats sans erreur apparente.

---

## 4. Aspects légaux et licences

### 4.1 Licences des dépendances

| Dépendance | Licence |
|---|---|
| NumPy | BSD 3-Clause |
| Pandas | BSD 3-Clause |
| Loguru | MIT |
| Pydantic | MIT |
| Click | BSD 3-Clause |

- BSD 3-Clause : https://opensource.org/license/bsd-3-clause
- MIT : https://opensource.org/license/mit

### 4.2 Données normatives intégrées

Les tables de données intégrées (`donnees/materiaux_bois.csv`, `donnees/kmod.csv`, etc.) sont des retranscriptions de valeurs publiées dans les normes EN 338, EN 14080, EN 1995-1-1 et leurs annexes nationales françaises. Leur utilisation est soumise aux droits de reproduction des organismes de normalisation (AFNOR, CEN).
