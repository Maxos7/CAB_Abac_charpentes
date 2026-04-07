# Foncionement Sys d'Abaque

````mermaid
---
title : Fonctionnement
---
flowchart LR
Questionaire[Questionaire ADH]@{ shape: manual-input} --->|Rèponse|Boite_d'envoi
Boite_d'envoi --->|Via boite email BE| Mail_ADH@{shape: curv-trap}
Boite_d'envoi <--->|Comparaison valeurs| Base_simple
Reglages@{ shape: lean-r}--->|.toml|logiciels
Execution@{shape: procs}--->|automatique mensuel|logiciels
subgraph logiciels [Logiciels BE charpente]
    direction TB
    Abac_charpente
    Regene_stock
    Abac_view
    Autre[Autre logiciel à venir]
end
Abac_charpente--->|Ecriture|Base_simple@{shape: cyl}
Abac_charpente--->|Ecriture|Base@{shape: cyl}
Regene_stock--->|Ecriture|Base@{shape: cyl}
Abac_view--->|Generation|abac[Feuille graphique pour le BE]@{shape: doc}
````

# Logiciel de calcul de portée
## Info d'entrée

Voir le README du projet

## Info de sortie
Donnée a extraire du logicielle de calcul de portée : 

- Code Sapeg
- ID MAT
- ID config
- Essence
- Portée
- Indice de classement

# Formulaire
## Diagrame du questionaire sur Type Forme :
````mermaid
---
title : Flow questionaire Type Forms
---
flowchart TB
Start ---> Type_poutre
Type_poutre{Type de poutre ?}
    Type_poutre --> panne
    Type_poutre --> solive

subgraph panne [Pannes]
    direction TB
Pente{{Pente:
    -15°
    -30°
    -35°
    -40°
    -45°}}
Pente --->Couverture{{ Couverture :
    - Ardoise naturelles -> 25
    - Tuiles -> 45
    - Zinc -> 6 
    - Bac acier -> 8
    - Bac acier isolé -> 12}}
Couverture --> SupportC{{Support de couverture :
    - Volige résineux ép. 18mm -> 12
    - Volige résineux ép. 15mm -> 10
    - Liteaux résineux -> 4
    - Panneaux OSB 18mm -> 12
    - Vide -> 0}}
SupportC ---> Couche_p1{{Couche 1 :
    - Chevrons courant 4*6 -> 2.8
    - Vide -> 0}}
Couche_p1 ---> Couche_p2{{Couche 2:
    - Laine de verre ép 200mm -> 3.45
    - Laine de verre ép 300mm -> 5
    - Laine de roche ép _ -> 
    - Laine de bois ép _ -> 
    - Vide -> 0}}
end

subgraph solive [Solive]
    direction TB
Plancher{{ Palancher :
    -  -> }}
Plancher --> SupportP{{Support de plancher :
    - Lambris résineux ép.  -> 
    - Dalle OSB 22mm -> 
    - Vide -> 0}}
SupportP ---> Couche_s1{{Couche :
    - Laine de verre ép 200mm -> 3.45
    - Laine de verre ép 300mm -> 5
    - Laine de roche ép _ -> 
    - Laine de bois ép _ -> 
    - Vide -> 0}}
end

panne ---> Finition
solive ---> Finition
Finition{{Finition
    - Palaco platre Ba13 -> 17
    -Lambris -> 8}}
Finition  ---> Entraxe
Entraxe{{Entraxe :
    -1.2
    -1.7}}
Entraxe ---> Portée(Portée -> valeur libre de 2 à 10 m)
Portée ---> Essence{{Essence :
    - Epicea
    - Douglas
    - Chene}}
Essence ---> End
````

# Boite d'envoi
## Réponce à l'aderent :

Réponce par e-mail

### Réuissite

````
De : etudes.chapente@cab56.com
A : {Email_aderant}
Objet : 

Bonjour,
Pour les données suivantes fournies dans le formulaire :

Une {Type de pièce} de {portée_m} m de portée avec {entraxe_m} m d'entraxe en {essence}.

Nous ne trouvons pas d'article répondant à votre demande dans notre base.
Merci de revenir vers nous pour une évaluation plus prècise.

Attention:
- Ces valeurs sont  calculées en fonction des règles de construction en vigeur (Eurocodes 5, Eurocode 0 et Eurocode 1). 
- La présence d'éléments fragiles (comme le placo) est prise en compte dans ces calculs. 
- Nous attirons l'attention sur le fait qu'ils sont réalisés dans notre zone géographique, à savoir une zone de neige A1  et une zone de vent 3".
- Il s'agit d'une aide au chiffrage et en aucun cas une note de calculs précises pour la mise en œuvre.

Pour toutes questions, nous restons à votre disposition en retoure de cet e-mail.
Cordialement,
L'équipe du bureau d'étude charpente,
````

### Echeque

````
De : etudes.chapente@cab56.com
A : {Email_aderant}
Objet : 

Bonjour,
Pour les données suivantes fournies dans le formulaire :

Une {Type de pièce} de {portée_m} m de portée avec {entraxe_m} m d'entraxe en {essence}.

Nous ne trouvons pas d'article répondant à votre demande dans notre base.
Merci de revenir vers nous pour une evaluation plus prècise.

Pour toutes questions, nous restons à votre disposition en retoure de cet e-mail.
Cordialement,
L'équipe du bureau d'étude charpente,
````