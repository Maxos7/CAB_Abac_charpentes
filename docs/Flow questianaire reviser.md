## Diagramme du questionnaire sur Type Forme :
````mermaid
---
title : Flow questionnaire Type Forms
---
flowchart TB
Start ---> Type_poutre
Type_poutre{Type de poutre ?}
    Type_poutre --> panne
    Type_poutre --> solive

subgraph panne [Pannes]
    direction TB
Usage1[Usage: 
= Toiture Inaccessible - valeur par défaut]

Usage1 --->  Pente{{Pente:
    -4°
    -15°
    -30°
    -35°
    -40°
    -45°}}
Pente --->Couverture{{ Couverture :
    - Ardoises naturelles -> 25
    - Tuiles -> 45
    - Zinc -> 6 
    - Bac acier -> 8
    - Bac acier isolé -> 12}}
Couverture --> SupportC{{Support de couverture :
    - Volige résineuse ép. 18mm -> 12
    - Volige résineuse ép. 15mm -> 10
    - Liteaux résineux -> 4
    - Panneaux OSB 18mm -> 12
    - Vide -> 0}}
SupportC ---> Couche_p1{{Couche 1 :
    - Chevrons courants 4*6 -> 2.8
    - Autre -> 0
    - Vide -> 0}}
Couche_p1 ---> Couche_p2{{Couche 2:
    - Laine de verre ép 200mm -> 3.45
    - Laine de verre ép 300mm -> 5
    - Autre -> 0
    - Vide -> 0}}
end

subgraph solive [Solive]
    direction TB
Usage2{{Usage :
    - Habitation
    - Autre}}

Usage2 ---> Plancher{{ Plancher :
    - Parquet Stratifier -> 12
    - Carrelage -> 25
    - Autre -> 0}}
Plancher --> SupportP{{Support de plancher :
    - Dalle OSB 22mm -> 
    - Autre -> 0}}
SupportP ---> Couche_s1{{Couche :
    - Laine de verre ép 200mm -> 3.45
    - Laine de verre ép 300mm -> 5
    - Autre -> 0
    - Vide -> 0}}
end

panne ---> Finition
solive ---> Finition
Finition{{Finition :
    - Placo plâtre Ba13 -> 17
    -Lambris -> 8}}
Finition  ---> A@{ shape: subproc, label: "Somme des valeurs de charge + ajout de 5daN de marge"} ---> Entraxe
Entraxe{{Entraxe :
    -1.2
    -1.7}}
Entraxe ---> Portée(Portée -> valeur libre de 2 à 10 m)
Portée ---> Essence{{Essence :
    - Épicéa
    - Douglas
    - Chêne}}
Essence ---> End
````