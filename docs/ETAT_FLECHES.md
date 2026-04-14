# État des vérifications ELS Flèches — Pipeline `abac_charpente_vectoriser`

> Synthèse du rapport CODIFAB N°1951 (rev4, 10/03/2022) et des conventions du pipeline.
> Source principale : `docs/1951-etude-critere-de-service-rapport-final-rev4-1-2022-03-10.pdf`

---

## 1. Définitions EC5 §7.2 + AN française

| Symbole | Nom | Définition |
|---|---|---|
| $w_{inst}$ | Flèche instantanée (EN) | Flèche sous charges totales G+Q (valeur EN de référence) |
| $W_{inst}(Q)$ | Flèche instantanée (AN française) | Flèche sous **charges variables seules** (Q+S) — critère de confort |
| $w_{fin}$ | Flèche finale | $w_G \cdot (1+k_{def}) + w_Q \cdot (1+\psi_2 \cdot k_{def})$ — EC5 §7.2(2) eq.(7.3) |
| $W_{net,fin}$ | Flèche nette finale | $w_{fin} - w_c$ où $w_c$ est la contre-flèche |
| $W_{tot,2}$ | Flèche second-œuvre | $w_Q + k_{def} \cdot (w_G + w_{G2})$ — flèche après pose du second-œuvre |

**Rappel AN française (§2.3.1 CODIFAB N°1951) :**
> « L'AN française apporte deux modifications supplémentaires en introduisant la flèche
> instantanée sous actions variables seules $W_{inst}(Q)$ en lieu et place de $W_{inst}$. »

---

## 2. Tableau des limites retenues — CODIFAB N°1951 Tableau 10

Valeurs rationalisées pour bâtiments courants (reproduites dans `donnees/limites_fleche_ec5.csv`) :

| Ouvrage | Élément | $W_{inst}(Q)$ | $W_{net,fin}$ | $W_{tot,2}$ |
|---|---|---|---|---|
| Couverture | Éléments structuraux (pannes, arbalétriers) | $L/300$ | $L/200$ | — |
| Couverture | Chevrons | $L/300$ | $L/150$ | — |
| Couverture | Liteaux, volige, planches | — | — | $L/300$ |
| Étanchéité | Éléments structuraux (pente ≥ 1,6 %) | $L/300$ | $L/250$ | $L/250$ |
| Plancher | Éléments struct. — cloisons/plafonds fragiles | $L/300$ | $L/250$ | $L/500$ *(L ≤ 5 m)* |
| Plancher | Éléments struct. — cloisons/plafonds non fragiles | $L/300$ | $L/250$ | $L/350$ |

---

## 3. Incohérences identifiées et état de correction

| # | Vérification | Problème identifié | État | Correction appliquée |
|---|---|---|---|---|
| **1** | `FlecheSecondOeuvre` — limite | CSV : `w_2 = L/300` pour `panne_standard` | ✅ **CORRIGÉE** | `L/500` (CODIFAB Tableau 10, 2nd-œuvre fragile) |
| **2** | `FlecheInst` | Utilise G+Q total au lieu de Q seul (AN française) | ✅ **CORRIGÉE** | `q_Q = q_d − q_G` → seules les charges variables |
| **3** | `FlecheSecondOeuvre` — double flexion | Calcul axe fort uniquement pour les pannes déversées | ✅ **CORRIGÉE** | Décomposition G/Q/G2 par axe y et z, composante verticale |
| **4** | Tous (double flexion) | Résultante vectorielle $\sqrt{w_y^2+w_z^2}$ ≠ flèche verticale | ✅ **CORRIGÉE** | Composante verticale $w_{vert} = w_y \cos\alpha + w_z \sin\alpha$ |
| **5** | `FlecheFin` | $w_{fin} = (w_G+w_Q)(1+k_{def})$ — k_def appliqué à Q | ✅ **CORRIGÉE** | Formule EC5 exacte $\psi_2=0$ : $w_{fin} = w_G(1+k_{def}) + w_Q$ |

---

## 4. Détail des incohérences

### Incohérence 1 — Limite FlecheSecondOeuvre (CSV)

**Avant :** `panne_standard;250;200;300` → $W_{tot,2} \leq L/300$

**Après :** `panne_standard;300;200;500` → $W_{tot,2} \leq L/500$ (CODIFAB Tableau 10)

Impact : le taux `els_FlecheSecondOeuvre` est sous-estimé de **+67 %** avec l'ancienne limite.

---

### Incohérence 2 — FlecheInst : G+Q → Q seul (AN française)

**Avant :** $W_{inst} = f(G+Q)$

**Après (AN française) :** $W_{inst}(Q) = f(Q) = f(q_d - q_G)$

La part permanente ne participe pas à la sensation de confort vibratoire. Le critère réglementaire
français évalue uniquement la flèche due aux surcharges d'exploitation.

---

### Incohérence 3 — FlecheSecondOeuvre : double flexion absente

Pour une panne déversée à angle $\alpha$ avec `double_flexion=True` :

**Avant :** calcul uniquement sur l'axe fort ($I_y$), la composante $w_z$ est ignorée.

**Après :** décomposition par ratio de moment $r_y = \frac{|M_y|}{|M_y|+|M_z|}$ :

$$q_{G,y} = q_G \cdot r_y, \quad q_{G,z} = q_G \cdot r_z$$
$$q_{G2,y} = q_{G2} \cdot r_y, \quad q_{G2,z} = q_{G2} \cdot r_z$$
$$q_{Q,y} = \max(q_{d,y} - q_{G,y}, 0), \quad q_{Q,z} = \max(q_{d,z} - q_{G,z}, 0)$$
$$W_{tot,2,y} = w_{Q,y} + k_{def}(w_{G,y} + w_{G2,y})$$
$$W_{tot,2} = W_{tot,2,y} \cos\alpha + W_{tot,2,z} \sin\alpha$$

---

### Incohérence 4 — Direction : résultante ≠ composante verticale

**Avant :** résultante vectorielle $w_{res} = \sqrt{w_y^2 + w_z^2}$

**Après :** composante verticale $w_{vert} = w_y \cos\alpha + w_z \sin\alpha$

**Justification géométrique :**
Pour une panne déversée (section ⊥ au rampant) à pente $\alpha$ :
- Axe fort $y$ ⊥ au rampant → déflexion $w_y$ a une composante verticale $w_y \cos\alpha$
- Axe faible $z$ le long du rampant → déflexion $w_z$ a une composante verticale $w_z \sin\alpha$

Le critère EC5 §7.2 porte sur les **flèches verticales** (*vertical deflections* dans la norme EN).
La résultante vectorielle n'est pas la flèche verticale.

**Quantification (cas de référence b=100mm, h=320mm, α=45°, GL28h) :**

$$\frac{w_{res}}{w_{vert}} = \frac{\sqrt{w_y^2+w_z^2}}{w_y\cos 45° + w_z\sin 45°} \approx 1{,}29$$

L'ancienne formulation était **29 % surconservatrice** sur ce cas.

---

### Incohérence 5 — FlecheFin : formule EC5 exacte

**Avant (approximation conservatrice documentée dans le code) :**

$$w_{fin} = (w_G + w_Q)(1+k_{def})$$

**Après (EC5 §7.2(2) équation (7.3)) :**

$$w_{fin} = w_G(1+k_{def}) + w_Q(1+\psi_2 \cdot k_{def})$$

Pour $\psi_2 = 0$ (neige catégorie H, toitures) :

$$w_{fin,correct} = w_G(1+k_{def}) + w_Q$$

**Excédent de l'ancienne formule :** $w_Q \cdot k_{def}$ en plus.
Pour $k_{def} = 0{,}6$ et $G = Q$ : surdimensionnement de **+23 %** sur la part variable.

---

## 5. Nouveaux paramètres TOML

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `fleches_double` | `bool` | `false` | Active le calcul bi-axe dans les 3 vérifications ELS flèche. Implicitement `true` si `double_flexion=true`. |
| `contre_fleche_mm` | `float` | `0.0` | Pré-cambrure en mm soustraite de $W_{net,fin}$ et $W_{tot,2}$. Ne s'applique pas à $W_{inst}(Q)$. |
| `limite_fleche_inst` | `float\|None` | `None` | Surcharge la limite $W_{inst}(Q)$ (L/x). `None` → valeur du CSV. |
| `limite_fleche_fin` | `float\|None` | `None` | Surcharge la limite $W_{net,fin}$ (L/x). `None` → valeur du CSV. |
| `limite_fleche_2` | `float\|None` | `None` | Surcharge la limite $W_{tot,2}$ (L/x). `None` → valeur du CSV. |

---

## 6. Cas de référence — Validation

**Configuration :** PanneDeversee, b=100 mm, h=320 mm, L=5 m, α=45°, entraxe=1,2 m, GL28h,
g=0,40 kN/m², g2=0,17 kN/m², s=0,36 kN/m², classe de service 1.

| Vérification | Logiciel référence | Pipeline (après corrections) |
|---|---|---|
| ELU FlexionDouble | 35 % ✓ | ~35 % ✓ |
| ELU Cisaillement | 6 % ✓ | ~6 % ✓ |
| ELU Déversement | 9 % ✓ | ~9 % ✓ |
| ELS FlecheSecondOeuvre | **167 % ✗** | ~167 % |

---

*Document généré le 2026-04-10. Source : CODIFAB N°1951 rev4, 10/03/2022.*
