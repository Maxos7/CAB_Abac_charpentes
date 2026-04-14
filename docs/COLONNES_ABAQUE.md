# Récapitulatif des colonnes — `abaque_complet_global.csv`

> **Référence normative** : EN 1995-1-1 (EC5) + EN 1990 (EC0) + Annexe Nationale France.
> Toutes les vérifications retournent un **taux d'utilisation** $\eta \in [0, +\infty[$  
> La section est vérifiée si $\eta \leq 1{,}0$.

---

## 1. Colonnes d'identification

| Colonne | Description |
|---|---|
| `id_config_calcul` | Identifiant unique de la configuration de calcul (type de poutre + paramètres) |
| `id_produit` | Code produit SAPEG |
| `libelle` | Libellé commercial |
| `id_config_materiau` | Hash de la combinaison (classe × b × h) |
| `classe_resistance` | Classe de résistance EC5 (C18, C24, GL24h…) |
| `b_mm` | Largeur de section $b$ [mm] |
| `h_mm` | Hauteur de section $h$ [mm] |
| `longueur_m` | Portée $L$ [m] |

---

## 2. Résistances de calcul — bases communes

Toutes les résistances de calcul sont de la forme :

$$f_d = \frac{k_{mod} \cdot f_k}{\gamma_M}$$

| Paramètre | Source | Valeur type |
|---|---|---|
| $k_{mod}$ | EC5 Table 3.1 — classe de service × durée de charge | 0,60 … 1,10 |
| $\gamma_M$ | AN France — 1,30 (massif), 1,25 (LVL/GL) | — |
| $f_k$ | Propriété caractéristique du matériau (CSV stock) | — |

Les combinaisons `*_combo` (ex. `elu_FlexionAxeFort_combo`) indiquent l'identifiant EC0 dont le $k_{mod}$ (via la durée de charge) a produit le taux maximal.

---

## 3. Vérifications ELU

### 3.1 Flexion axe fort — `elu_FlexionAxeFort`

**EC5 §6.1.6 Éq. (6.11)** — toujours active

$$\eta = \frac{\sigma_{m,y,d}}{k_{crit} \cdot f_{m,d}} \leq 1{,}0$$

$$\sigma_{m,y,d} = \frac{M_{y,d}}{W_y} \quad \text{[MPa]}$$

- $M_{y,d}$ : moment fléchissant sur l'axe fort. En flexion simple : $M_{y,d} = M_d$ (moment total). En double flexion : $M_{y,d}$ est la composante perpendiculaire au plan du rampant.  
- $W_y = b\,h^2/6$ : module de flexion axe fort.  
- $k_{crit}$ : facteur de réduction au déversement (EC5 §6.3.3, voir §3.8).

---

### 3.2 Flexion axe faible — `elu_FlexionAxeFaible`

**EC5 §6.1.6 Éq. (6.12)** — active uniquement si double flexion

$$\eta = \frac{\sigma_{m,z,d}}{f_{m,d}} \leq 1{,}0$$

$$\sigma_{m,z,d} = \frac{M_{z,d}}{W_z} \quad [MPa]$$

- $M_{z,d}$ : composante du moment dans le plan du rampant (flexion latérale).  
- $W_z = b^2\,h/6$ : module de flexion axe faible.  
- Pas de réduction $k_{crit}$ sur l'axe faible.

---

### 3.3 Double flexion — axe fort déterminant — `elu_DoubleFlexionForte`

**EC5 §6.1.6 Éq. (6.19)** — active uniquement si double flexion

$$\eta = \frac{\sigma_{m,y,d}}{k_{crit} \cdot f_{m,d}} + k_m \cdot \frac{\sigma_{m,z,d}}{f_{m,d}} \leq 1{,}0$$

- $k_m = 0{,}7$ pour section rectangulaire (EC5 §6.1.6(2)).

---

### 3.4 Double flexion — axe faible déterminant — `elu_DoubleFlexionFaible`

**EC5 §6.1.6 Éq. (6.20)** — active uniquement si double flexion

$$\eta = k_m \cdot \frac{\sigma_{m,y,d}}{k_{crit} \cdot f_{m,d}} + \frac{\sigma_{m,z,d}}{f_{m,d}} \leq 1{,}0$$

---

### 3.5 Cisaillement — `elu_Cisaillement`

**EC5 §6.1.7** — toujours active

$$\eta = \frac{\tau_d}{f_{v,d}} \leq 1{,}0$$

$$\tau_d = \frac{3}{2} \cdot \frac{V_d}{A_{eff}} \quad [MPa]$$

- $V_d$ : effort tranchant maximal en appui $= q_d \cdot L/2$.  
- $A_{eff} = A \cdot k_{cr}$ : section efficace (EC5 §6.1.7(2)) — $k_{cr} = 0{,}67$ (bois massif).

---

### 3.6 Appui — compression perpendiculaire au fil — `elu_Appui`

**EC5 §6.1.5** — toujours active

$$\eta = \frac{\sigma_{c,90,d}}{k_{c,90} \cdot f_{c,90,d}} \leq 1{,}0$$

$$\sigma_{c,90,d} = \frac{R_d}{b \cdot \ell_{appui}} \quad [MPa]$$

- $R_d = V_d$ : réaction d'appui.  
- $\ell_{appui}$ : longueur d'appui [mm] (paramètre TOML `longueur_appui_mm`).  
- $k_{c,90}$ : facteur de distribution (paramètre TOML, typiquement 1,0 … 1,75).

---

### 3.7 Compression oblique — formule de Hankinson — `elu_CompressionOblique`

**EC5 §6.2.2** — active uniquement si l'élément est incliné ($\alpha > 0$)

$$f_{c,\alpha,d} = \frac{f_{c,0,d} \cdot f_{c,90,d}}{f_{c,0,d} \sin^2\!\alpha + f_{c,90,d} \cos^2\!\alpha}$$

$$\eta = \frac{\sigma_{c,\alpha,d}}{k_{c,90} \cdot f_{c,\alpha,d}} \leq 1{,}0 \qquad \sigma_{c,\alpha,d} = \frac{V_d}{b \cdot \ell_{appui}} \quad [MPa]$$

- $\alpha$ : angle entre le fil du bois et la direction de la réaction (= pente du rampant).  
- Cas dégénéré $\alpha = 0$ : compression parallèle → vérification non active.  
- Cas dégénéré $\alpha = 90°$ : dégénère en §6.1.5 (Appui).

---

### 3.8 Déversement — indicateur — `elu_Deversement`

**EC5 §6.3.3** — toujours actif (indicateur, pas une vérification autonome)

$$\eta_{devers.} = 1 - k_{crit}$$

Le facteur $k_{crit}$ est calculé via l'élancement relatif de déversement :

$$\sigma_{m,crit} = \frac{0{,}78\,b^2\,E_{0,05}}{h\,\ell_{ef}} \qquad \bar{\lambda}_{rel,m} = \sqrt{\frac{f_{m,k}}{\sigma_{m,crit}}}$$

$$k_{crit} = \begin{cases}
1{,}0 & \bar{\lambda}_{rel,m} \leq 0{,}75 \\
1{,}56 - 0{,}75\,\bar{\lambda}_{rel,m} & 0{,}75 < \bar{\lambda}_{rel,m} \leq 1{,}40 \\
1/\bar{\lambda}_{rel,m}^2 & \bar{\lambda}_{rel,m} > 1{,}40
\end{cases}$$

- $\ell_{ef}$ : longueur effective de déversement (portée ou distance inter-contreventements).  
- Taux = 0 si pas de déversement ($k_{crit} = 1$) ; Taux = 1 si instabilité totale.

---

### 3.9 Traction parallèle au fil — `elu_Traction`

**EC5 §6.1.2** — active si $N_d > 0$

$$\eta = \frac{\sigma_{t,0,d}}{f_{t,0,d}} \leq 1{,}0 \qquad \sigma_{t,0,d} = \frac{N_d}{A} \quad [MPa]$$

---

### 3.10 Traction transversale (perpendiculaire au fil) — `elu_TractionTransversale`

**EC5 §6.1.3** — active si $N_d > 0$ et élément incliné

$$\eta = \frac{\sigma_{t,90,d}}{f_{t,90,d}} \leq 1{,}0 \qquad \sigma_{t,90,d} = \frac{N_d \cdot \sin\alpha}{A} \quad [MPa]$$

- La composante transversale de la traction axiale crée une traction perpendiculaire au fil.

---

### 3.11 Compression parallèle au fil — `elu_Compression`

**EC5 §6.1.4** — active si $N_d < 0$, **sans** réduction de flambement

$$\eta = \frac{\sigma_{c,0,d}}{f_{c,0,d}} \leq 1{,}0 \qquad \sigma_{c,0,d} = \frac{|N_d|}{A} \quad [MPa]$$

---

### 3.12 Flambement axe fort — `elu_FlambementAxeFort`

**EC5 §6.3.2** — active si $N_d < 0$

$$\eta = \frac{\sigma_{c,0,d}}{k_{c,y} \cdot f_{c,0,d}} \leq 1{,}0$$

Le facteur $k_{c,y}$ est calculé depuis l'élancement relatif axe fort :

$$\lambda_y = \frac{L_0}{i_y} \quad i_y = \sqrt{\frac{I_y}{A}} \qquad \bar{\lambda}_{rel,y} = \frac{\lambda_y}{\pi}\sqrt{\frac{f_{c,0,k}}{E_{0,05}}}$$

$$k_y = 0{,}5\!\left[1 + \beta_c(\bar{\lambda}_{rel,y} - 0{,}3) + \bar{\lambda}_{rel,y}^2\right]$$

$$k_{c,y} = \begin{cases}
1{,}0 & \bar{\lambda}_{rel,y} \leq 0{,}3 \\
\dfrac{1}{k_y + \sqrt{k_y^2 - \bar{\lambda}_{rel,y}^2}} & \bar{\lambda}_{rel,y} > 0{,}3
\end{cases}$$

- $\beta_c = 0{,}20$ (bois massif) ou $0{,}10$ (lamellé-collé).  
- $L_0 = L$ (bi-appui simple, longueur de flambement = portée).

---

### 3.13 Flambement axe faible — `elu_FlambementAxeFaible`

**EC5 §6.3.2** — active si $N_d < 0$

$$\eta = \frac{\sigma_{c,0,d}}{k_{c,z} \cdot f_{c,0,d}} \leq 1{,}0$$

Idem §3.12 avec $i_z = \sqrt{I_z/A}$ et $\bar{\lambda}_{rel,z}$. Généralement déterminant pour les sections élancées ($h \gg b$).

---

### 3.14 Flexion + traction — `elu_FlexionTraction`

**EC5 §6.2.3** — active si $N_d > 0$

$$\eta = \frac{\sigma_{t,0,d}}{f_{t,0,d}} + \frac{\sigma_{m,d}}{f_{m,d}} \leq 1{,}0$$

---

### 3.15 Flexion + compression — axe fort — `elu_FlexionCompressionForte`

**EC5 §6.2.4 Éq. (6.23)** — active si $N_d < 0$

$$\eta = \left(\frac{\sigma_{c,0,d}}{f_{c,0,d}}\right)^{\!2} + \frac{\sigma_{m,y,d}}{k_{crit} \cdot f_{m,d}} \leq 1{,}0$$

---

### 3.16 Flexion + compression — axe faible — `elu_FlexionCompressionFaible`

**EC5 §6.2.4 Éq. (6.24)** — active si $N_d < 0$

$$\eta = \left(\frac{\sigma_{c,0,d}}{f_{c,0,d}}\right)^{\!2} + k_m \cdot \frac{\sigma_{m,y,d}}{k_{crit} \cdot f_{m,d}} \leq 1{,}0$$

---

### 3.17 Double flexion + compression + flambement — axe fort — `elu_FlexionDevComprimeeForte`

**EC5 §6.3.2 Éq. (6.23)** — active si $N_d < 0$ et double flexion

$$\eta = \frac{\sigma_{c,0,d}}{k_{c,y} \cdot f_{c,0,d}} + \frac{\sigma_{m,y,d}}{f_{m,d}} + k_m \cdot \frac{\sigma_{m,z,d}}{f_{m,d}} \leq 1{,}0$$

> Note : l'instabilité est gérée par $k_{c,y}$ et non par $k_{crit}$ (EC5 §6.3.2(3)).

---

### 3.18 Double flexion + compression + flambement — axe faible — `elu_FlexionDevComprimeeFaible`

**EC5 §6.3.2 Éq. (6.24)** — active si $N_d < 0$ et double flexion

$$\eta = \frac{\sigma_{c,0,d}}{k_{c,z} \cdot f_{c,0,d}} + k_m \cdot \frac{\sigma_{m,y,d}}{f_{m,d}} + \frac{\sigma_{m,z,d}}{f_{m,d}} \leq 1{,}0$$

---

## 4. Vérifications ELS

La flèche bi-appui sous charge uniformément répartie est :

$$w_{inst} = \frac{5\,q\,L^4}{384\,E_{mean}\,I} \quad [mm]$$

Pour les éléments inclinés (chevrons), la flèche dans le plan du rampant est convertie en flèche **verticale** :

$$w_{vert} = \frac{w_{rampant}}{\cos\alpha}$$

La référence de longueur est alors la longueur projetée horizontale $L_{proj}$.

---

### 4.1 Flèche instantanée — `els_FlecheInst`

**EC5 §7.2** — toujours active

$$\eta = \frac{w_{inst}}{L\,/\,\text{lim}_{inst}} \leq 1{,}0$$

- $w_{inst}$ : flèche sous la combinaison ELS caractéristique (CAR).  
- En double flexion : $w_{inst} = \sqrt{w_y^2 + w_z^2}$.  
- Limite $\text{lim}_{inst}$ : paramètre TOML (ex. 300 pour $L/300$).

---

### 4.2 Flèche finale avec fluage — `els_FlecheFin`

**EC5 §7.2** — toujours active

$$\eta = \frac{w_{fin}}{L\,/\,\text{lim}_{fin}} \leq 1{,}0 \qquad w_{fin} = w_{inst} \cdot (1 + k_{def})$$

- $k_{def}$ : facteur de fluage EC5 Table 3.2 (classe de service × type de matériau).  
  Exemples : $k_{def} = 0{,}60$ (C×, CS1), $k_{def} = 0{,}80$ (C×, CS2), $k_{def} = 2{,}00$ (C×, CS3).

---

### 4.3 Flèche nette second-œuvre — `els_FlecheSecondOeuvre`

**EC5 §7.2** — active uniquement si `limite_fleche_2` est défini dans le TOML

$$\eta = \frac{w_2}{L\,/\,\text{lim}_2} \leq 1{,}0$$

$$w_2 = w_{Q,fin} + k_{def}\,(w_G + w_{G2})$$

- $w_{Q,fin}$ : flèche due aux charges variables (quasi-permanente) ≈ $w_{total} - w_G$.  
- $w_G$ : flèche due aux charges permanentes ordinaires (poids propre + $G$ hors second-œuvre).  
- $w_{G2}$ : flèche due aux charges permanentes fragiles (carrelage, chape) — calculée séparément car $G_2 \subset G$ dans les charges caractéristiques.  
- Le second-œuvre amplifie uniquement la part permanente qui s'installe après la construction ($G_2$).

---

## 5. Colonnes de combinaison EC0

Pour chaque colonne de taux `elu_<verif>` et `els_<verif>`, une colonne jumelle `elu_<verif>_combo` / `els_<verif>_combo` indique l'identifiant normatif de la combinaison qui a produit ce taux maximal.

### Identifiants de combinaison

| Identifiant | Type | Charge principale | $\gamma_G$ | $\gamma_{Q1}$ | $k_{mod}$ durée |
|---|---|---|---|---|---|
| `ELU_STR_G+Q` | ELU-STR | Exploitation $Q$ | 1,35 | 1,50 | moyen_terme |
| `ELU_STR_G+S` | ELU-STR | Neige $S$ | 1,35 | 1,50 | court_terme |
| `ELU_STR_G+W` | ELU-STR | Vent $W$ | 1,35 | 1,50 | instantané |
| `ELS_CAR_G+Q` | ELS-CAR | Exploitation $Q$ | 1,00 | 1,00 | moyen_terme |
| `ELS_CAR_G+S` | ELS-CAR | Neige $S$ | 1,00 | 1,00 | court_terme |
| `ELS_FREQ_G+Q` | ELS-FREQ | Exploitation $Q$ | 1,00 | $\psi_1$ | moyen_terme |
| `ELS_QPERM_G+Q` | ELS-QPERM | — | 1,00 | 0 | permanent |

---

## 6. Colonnes globales

| Colonne | Calcul |
|---|---|
| `taux_global` | $\eta_{global} = \max\!\left(\text{tous les taux ELU et ELS}\right)$ |
| `verif_globale` | Identifiant de la vérification qui produit $\eta_{global}$ |
| `combo_global` | Identifiant EC0 de la combinaison qui produit $\eta_{global}$ |
| `verifie` | `True` si $\eta_{global} \leq 1{,}0$, `False` sinon |

---

## 7. Colonnes dérivées (fichiers de sortie agrégés)

Dans les vues de type `agregation` (définies dans `configs_sortie_vect.toml`) :

| Colonne | Calcul |
|---|---|
| `longueur_max_admissible_m` | Plus grande portée $L$ où `verifie = True` pour ce groupe |
| `verif_determinante` | Vérification au taux le plus élevé à $L_{max}$ |
| `taux_determinant` | Valeur de ce taux |
| `combo_determinante` | Combinaison EC0 correspondante (= `combo_global` de la ligne retenue) |

---

*Généré le 2026-04-10 — pipeline abac-vect v0.x*
