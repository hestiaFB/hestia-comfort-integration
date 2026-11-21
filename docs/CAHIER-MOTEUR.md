# Cahier des charges — Moteur de conseil de Hestia Confort

Version 0.18 — 4 novembre 2026. Brouillon à valider par Frank.

Ce document remplace le § 8 du [cahier des charges de Confort](CAHIER-DES-CHARGES.md) (« Le moteur : reprise du template ») et en concrétise le § 13. L'état des lieux qui a mené à cette refonte est dans [MOTEUR-DE-CONSEIL.md](MOTEUR-DE-CONSEIL.md).

Règles d'évolution (reprises du § 0 du cahier de Confort, cette fois tenues) :
- toute décision est écrite ici **avant** d'être codée ;
- chaque version est datée, avec ce qui change (§ 24) ;
- ce document fait référence pour Frank, Claude et Codex ;
- un comportement du moteur qui n'est pas décrit ici est un défaut, pas une fonction.

---

## 1. Objet

Construire un moteur de conseil **fiable, intelligent, proactif, qui apprend de ses erreurs**, **gratuit** et **transparent**, qui fonctionne dans **toutes les maisons**, du logement équipé d'une seule sonde par pièce jusqu'à la maison très équipée.

Le moteur répond à une seule question, pour chaque pièce et pour le logement :

> **Que dois-je faire, maintenant ou bientôt, et qu'est-ce que j'y gagne ?**

## 2. Pourquoi repartir de zéro

Le moteur 2.1 décide par une cascade de règles (28 branches, 8 retouches, 32 raisons, 23 seuils écrits en dur). Il en résulte, mesuré le 31 octobre :
- **des falaises** : fenêtre ouverte, 12,8 °C dehors, 1 h du matin, le conseil passe de « Refermez » (21,0 °C) à « cela ne change rien » (21,1 °C) puis « Laissez ouvert » (21,5 °C) ;
- **deux cerveaux** : la carte et le moteur ne voient pas la même maison (anti-rebond de 30 s d'un côté seulement) ;
- **aucune notion de coût** : le moteur se demande si un geste aide, jamais ce qu'il coûte ;
- **pas d'anticipation**, **pas d'apprentissage des erreurs**, et un jumeau qui sait prévoir mais ne décide rien ;
- **57 corrections en deux semaines**, chacune ajoutant une exception.

On garde ce qui est sain (§ 21) ; on refait la décision, la rédaction et la logique de la carte.

## 3. Principes

1. **Une valeur absente reste inconnue.** Une estimation est toujours nommée comme telle.
2. **Ne parler que de ce qu'on sait, et dire à quel point on le sait.** Mesuré : le moteur affirme. Estimé : il nuance. Inconnu : il se tait sur la carte et le dit dans le panneau.
3. **Un seul cerveau.** Le moteur décide **et** rédige. La carte, les entités et les LED affichent la même décision, sans rien recalculer.
4. **Comparer plutôt que trancher.** Le confort se décide en comparant des scénarios simulés. Seule la sécurité reste en règles fixes.
5. **Un conseil se justifie par un gain chiffré.** Sans gain net, c'est « Rien à faire », et c'est démontré.
6. **La continuité.** Une petite variation d'une mesure ne retourne jamais le conseil.
7. **Le dehors appartient à Weather.** Confort emprunte, ne recalcule pas.
8. **Toutes les maisons.** Un même moteur ; chaque capteur ajouté précise, aucun n'est obligatoire hors la température de la pièce.
9. **Apprendre, mais rester lisible.** Tout ce qui est appris se lit en mots et en chiffres dans le panneau. Pas d'IA générative, ni dans la décision ni dans la rédaction.
10. **Observer, conseiller, ne jamais commander.** Le moteur ne pilote aucun équipement.
11. **Gratuit et local.** Aucun abonnement, aucune clé. Seule la position (arrondie) part vers Open-Meteo, par Weather.
12. **Le confort d'abord.** Par défaut, le moteur penche vers le confort. Il calcule quand même l'énergie de chaque geste, pour la brique Énergie.
13. **Rester simple : chaque capteur enrichit, rien de compliqué n'est deviné.** Le moteur suit le tableau du § 6.7 : avec peu de capteurs, des conseils simples et sûrs ; chaque capteur ajouté débloque des conseils de plus. Ce qui n'est pas mesuré (volet manuel, porte intérieure) reste une habitude déclarée ou une incertitude dite, pas une déduction fragile. Les déductions fines sont des améliorations pour plus tard (§ 23.2), jamais une condition (remarque de Frank, 31 octobre).

## 3 bis. Ce qui entre dans la 3.0, et ce qui vient après

Le principe 13 tranche : la 3.0 fait peu, mais juste. Tout le reste de ce cahier reste valable comme cap, et chaque section dit à quelle étape elle appartient.

| Dans la 3.0 | Après la 3.0 |
|---|---|
| **Tous les sujets du confort que la pièce mesure** (tableau du § 6.7) : chaleur, humidité, air (CO₂, COV, particules), lumière | Ce qu'aucun capteur ne mesure, deviné (CO₂ ou humidité sans capteur, § 6.6) |
| Jumeaux de la **chaleur** (air + murs), de l'**eau** (humidité) et de l'**air** (CO₂), chacun validé au banc sur ses propres gestes ; lumière calculée (soleil) ou lue (capteur) | Jumeaux plus fins (lumière apprise pièce par pièce, réserve d'eau des murs affinée) |
| Données **mesurées**, **empruntées à Weather**, **déclarées**, **calculées** par la physique, **apprises** par le jumeau | Données **déduites** : fenêtre ou chauffage virtuels, CO₂ ou humidité estimés sans capteur, volets et portes devinés (§ 6.6, § 23.2) |
| Contrôles simples des capteurs : figé, saut impossible, hors plage ; ombre de la station (déjà apprise) | Contrôle complet avec Open-Meteo et page « Fiabilité » (avec Weather 3.x, § 7) |
| Gestes : fermer, ouvrir N min, volet relié, VMC, chauffage, climatisation par Versatile | Combinaisons entre pièces du plan du logement (air traversant entre deux pièces, § 12) |
| Coût, décision stable, séances, nuit, vacances, « Cette nuit, pensez à… » | Poids qui s'ajustent tout seuls avec les avis (§ 10.3) |
| Trace, instantané rejouable, journal, bouton « Ce conseil ne va pas » | Page « Atelier » complète avec « Et si… ? », capteur le plus utile (§ 16) |
| Entités, évènement, LED | Notifications sur téléphone (§ 13) |

## 4. Ce qu'est un conseil

Un conseil a toujours **quatre parties** :

| Partie | Exemple |
|---|---|
| **Geste** | Refermer la porte-fenêtre SG |
| **Moment** | Maintenant · avant 14 h · ce soir vers 22 h · cette nuit |
| **Gain** | « vous gardez 2 °C d'ici 7 h » |
| **Preuve** | Avéré · renforcé (dit au conditionnel) · supposé (§ 4.1) |

Il porte aussi un **sujet** (chaleur, humidité, air, lumière, sécurité) et, en interne, les scénarios comparés qui le justifient.

**Le confort des personnes, sur tous ses sujets** (remarques de Frank, 31 octobre). Le moteur ne pense pas qu'en degrés : un volet ouvert l'hiver change peu la température, mais il apporte la lumière du jour ; un volet fermé l'été garde la fraîcheur mais assombrit. Le coût (§ 10.2) compte chaque sujet que la pièce mesure. Le moteur s'occupe des personnes **et du logement où elles vivent** (remarque de Frank) : moisissure, condensation et buée sur les vitres, murs humides, risque de gel, logement préservé pendant une absence. Ni plantes, ni animaux.

**Deux sortes de conseils** :
- **les gestes** (bandeau) : quelque chose à faire, maintenant ou bientôt ;
- **les conseils passifs** (« Bon à savoir », § 14) : rien à faire, un repère utile sur la pièce, par exemple « la chambre P a le soleil du matin de 9 h à 12 h ».

« Rien à faire » est un conseil comme les autres : il dit pourquoi (« Fermée : 20,4 °C à 7 h. Ouverte : 17,5 °C »).

Les 32 raisons actuelles disparaissent. Elles sont remplacées par la combinaison geste × sujet × moment.

### 4.1 Trois niveaux de preuve (proposé par Frank, 31 octobre)

Chaque **effet** que le moteur prête à un geste dans une pièce — l'aération sur la chaleur, sur l'humidité, sur le CO₂, sur les particules ; le soleil par la vitre, le soleil par la fenêtre ouverte ; le volet relié ; le chauffage de la pièce, le poêle — a un niveau de preuve :

| Niveau | D'où il vient | Ce qu'il permet |
|---|---|---|
| **Supposé** | la géométrie et les déclarations seules : orientation de la fenêtre, position du soleil, saison, valeurs ordinaires du jumeau | un conseil passif seulement, dans « Bon à savoir » : « Soleil sur la fenêtre ouest de 14 h à 17 h 20 » |
| **Renforcé** | les mesures et prévisions du moment le confirment : rayonnement prévu, écart dedans-dehors, air du dehors plus sec | un conseil passif au conditionnel ; **un geste seulement s'il est très net** (deux fois le seuil du § 10.2 bis, sans se cumuler avec la nuit), dit au conditionnel |
| **Avéré** | la pièce l'a montré : **appris** (au moins 3 gestes où le jumeau a prévu le bon sens et le bon ordre de grandeur, entre la moitié et le double de l'effet mesuré, § 18.3), ou **constaté sur le moment** (le geste est en cours et la mesure suit le sens prévu, d'au moins la moitié du seuil) | un geste dès qu'il est significatif (§ 10.2 bis), dit à l'affirmatif |

Les règles de sécurité (§ 9.3) ne dépendent d'aucun niveau. Le niveau monte avec les gestes observés et redescend si le jumeau se met à se tromper : c'est la boucle « le modèle s'est trompé » du § 15, rendue visible. Un effet qui n'est jamais conseillé n'est jamais observé : le conseil passif invite à essayer, et les gestes faits de soi-même comptent autant que les gestes conseillés.

Exemple, la Chambre P le 31 octobre : le soleil sur la fenêtre ouest est **supposé** par l'orientation, **renforcé** par le grand soleil prévu, puis **avéré sur le moment** quand la chambre gagne 1,4 °C en deux heures fenêtre ouverte, alors que le jumeau n'en prévoyait que 0,1. Le passif « Soleil sur la fenêtre ouest jusqu'à 17 h 20 » devient alors « Laissez ouvert, le soleil réchauffe la chambre ».

## 5. Architecture en couches

Chaque couche a une seule responsabilité, se teste seule, et ne connaît que la précédente.

| # | Couche | Rôle |
|---|---|---|
| 1 | **Mesures** | Lire les capteurs, leur fraîcheur, appliquer l'anti-rebond **une seule fois** |
| 2 | **Contrôle des mesures** | Noter la fiabilité de chaque mesure, corriger ou remplacer (§ 7) |
| 3 | **État de la maison** | Grandeurs dérivées (humidité absolue, point de rosée, mur froid…), données virtuelles (§ 6) |
| 4 | **Modèle** | Le jumeau de chaque pièce et du logement (§ 8) |
| 5 | **Prévisions** | Météo de Weather, horaires de vie appris, consignes de chauffage |
| 6 | **Gestes possibles** | Ce que chaque pièce permet vraiment ; interdits de sécurité (§ 9) |
| 7 | **Évaluation** | Simuler chaque geste, calculer son coût (§ 10) |
| 8 | **Décision** | Choisir, stabiliser, regrouper, suivre les séances (§ 11) |
| 9 | **Rédaction** | Transformer la décision en phrases, en français, anglais, allemand (§ 14) |
| 10 | **Journal** | Garder chaque décision, sa prévision, son résultat, l'avis donné (§ 15) |

## 6. Les données

### 6.1 Cinq origines, toujours affichées

| Origine | Exemple | Sur la carte |
|---|---|---|
| **Mesurée** | Température du Salon | valeur seule |
| **Empruntée à Weather** | Soleil prévu sur la façade ouest | « prévu » |
| **Déclarée** dans le panneau | Exposition d'un ouvrant, type de vitrage | — (sert au calcul) |
| **Calculée** | Point de rosée, coin de mur froid | « calculé » |
| **Apprise ou estimée** | Inertie de la pièce, humidité d'une chambre sans capteur | « appris » · « estimé » |

### 6.2 Ce qu'on emprunte à Weather

Weather fournit tout ce qui vient du dehors, déjà contrôlé (§ 7) :
- **soleil** : position, rayonnement mesuré ou estimé à l'ombre, couverture nuageuse, et **le soleil prévu heure par heure sur une façade donnée** (nouvelle interface de Weather) ;
- **prévisions horaires** : température, humidité, vent ; minimale de la nuit, maximale de demain ;
- **pluie** : en cours, dans l'heure à la minute ;
- **vent** : vitesse, rafales, direction ;
- **air et pollens**, **saison** et moyennes des 7 derniers jours ;
- **orage, éclairs, vigilance** ;
- la **fiabilité** de chacune de ces valeurs.

### 6.2 bis Le soleil : chaque source pour ce qu'elle sait (décidé avec Frank, 31 octobre)

| Source | Ce qu'on en prend | Pourquoi |
|---|---|---|
| **Le calcul du moteur** (formules de la 2.1, `sunlight.py`) | la position du soleil, maintenant et pour toutes les heures à venir | une seule source pour toute la courbe, sans saut entre « maintenant » et « dans 5 minutes » ; juste à 0,2° près de Home Assistant (vérifié le 31 octobre) ; marche sans aucune intégration |
| **L'intégration Soleil de Home Assistant** (ses capteurs, retrouvés par l'intégration et non par leur nom) | les heures du lever, du coucher, de l'aube, du crépuscule ; et un **contrôle** : si sa position s'écarte du calcul, la position de la maison est mal réglée dans Home Assistant (page Fiabilité, § 16.1) | ce qu'elle sait en propre ; ses capteurs gardent des statistiques à long terme, utiles au banc. Sans elle, le moteur calcule ces heures |
| **Adaptive Cover Pro** (s'il pilote le volet de la fenêtre) | le soleil devant cette fenêtre maintenant (`sun_infront`) et ses heures de début et de fin (`start_sun`, `end_sun`) | il connaît l'angle exact de la fenêtre et son champ de vision : il prime sur le calcul pour cette fenêtre |
| **Le rayonnement prévu** (Open-Meteo, recoupé par la station de Weather) | combien de soleil, maintenant et prévu | ce qui fait passer le soleil d'une fenêtre de **supposé** à **renforcé** (§ 4.1) ; le jumeau thermique en a besoin heure par heure |

`sun.sun` et ses attributs ne sont plus lus. L'intégration Soleil donne la position, jamais la quantité : elle ne voit pas les nuages.

**Le soleil prévu, recoupé par la station** (décidé avec Frank, 31 octobre). Weather ne prévoit pas de rayonnement : Open-Meteo le prévoit, nuages compris. Quand Weather a une station avec un capteur de rayonnement, le moteur s'en sert pour le corriger :
1. **L'ombre de la station** : par ciel clair, la part du soleil prévu qu'elle reçoit, apprise par position du soleil (cases de 10° d'azimut × 5° de hauteur). Une case non revue est gardée : le soleil bas de l'hiver s'apprend l'hiver et sert encore au printemps. Apprise chaque nuit, à 3 h 30.
2. **Les nuages manqués** : là où la station voit le soleil (part ≥ 60 %), le rapport mesuré / attendu des deux dernières heures corrige l'heure en cours, puis de moins en moins sur les suivantes (effacement sur 4 h). À l'ombre, soleil trop bas ou trop faible : la prévision est gardée telle quelle.
3. Sans station, ou sans capteur de rayonnement : Open-Meteo seul.

Banc du 31 octobre (un an de la GW2000A, ombre apprise jusqu'à fin août, jugée sur septembre–octobre) : écart moyen au rayonnement mesuré 64 → 46 W/m² pour l'heure en cours, 70 → 57 à 2 h, 74 → 64 à 3 h, rien gagné à 6 h. La station de la maison est à l'ombre sous 25° de soleil presque toute l'année : l'hiver, la correction sert peu. Par ciel clair et soleil haut, Open-Meteo tombe juste (part 0,95 à 1,0) : sa prévision par ciel clair n'est pas biaisée.

Au passage : le rayonnement d'Open-Meteo à une heure donnée est la moyenne de l'heure **qui s'achève** ; le moteur l'utilisait une heure trop tard pour la prévision (pas pour l'apprentissage). Corrigé.

### 6.3 Données déclarées (encart « Pour aller plus loin », § 16.2)

Toutes facultatives. Une donnée non déclarée prend la valeur de la maison, sinon une valeur ordinaire.
- **Pièce** : surface, hauteur sous plafond, murs donnant dehors ou mitoyens, murs lourds ou légers, étage, usage (chambre, cuisine, salle de bain…).
- **Ouvrants** : exposition ou angle exact, type, taille, vitrage (simple, double, triple), débord de toit, abri, volet, masques (arbre, immeuble) par direction.
- **Occupation** : nombre de personnes qui y dorment, porte habituellement fermée.
- **Liens** : pièces voisines, portes intérieures, escalier ouvert, « même air ».
- **Chauffage** : type (poêle, radiateurs, plancher), pièce chauffée par une autre.
- **Équipements** : douche, plaque de cuisson, sèche-linge, et l'entité qui montre qu'ils sont en marche.

### 6.4 Données calculées
Soleil par fenêtre (W/m², maintenant et prévu, avec ombre et masques) · heures de soleil direct par fenêtre · apports solaires prévus par pièce · air traversant et effet cheminée · pluie battante par façade · humidité absolue · point de rosée · coin de mur le plus froid · buée sur le vitrage.

### 6.5 Données apprises
Constante de temps de chaque pièce · température d'équilibre · chaleur des murs · renouvellement d'air de chaque fenêtre · séchage · efficacité de la VMC · déperditions de la maison · heures de lever et de coucher.

### 6.6 Données déduites d'autres appareils
**Dans la 3.0, seulement ce qui se lit directement** : présence de la pièce (Versatile, capteur de présence), sommeil et absence (alarme en mode nuit, absent, vacances). **Le reste vient après la 3.0** (§ 3 bis) :
présence plus fine (téléphones, lumières, télévision) · sources d'humidité (cuisson, douche, chauffe-eau, sèche-linge) · CO₂ estimé d'une chambre sans capteur · **fenêtre virtuelle** (pièce qui refroidit trop vite) · **chauffage virtuel** (le poêle vu à la montée de température).

### 6.7 Ce que chaque équipement débloque

Socle de toute pièce, sans capteur de plus : Weather, la maison (présence, sommeil, apprentissage des autres pièces) et les déclarations.

| La pièce a | Mesuré (affirmé) | Emprunté ou estimé (nuancé) | Ce que le moteur peut dire |
|---|---|---|---|
| **Température seule** | Température | Soleil par fenêtre prévu ; inertie (de la maison puis la sienne) ; température d'équilibre ; heure de sortie de la plage | Trop frais, trop chaud, garder la fraîcheur ; « si le volet est ouvert, baissez-le avant 14 h » ; « Cette nuit, fermez les volets » |
| **+ humidité** | Humidité, eau dans l'air, point de rosée | Coin de mur froid, buée ; sources d'humidité ; séchage appris | Assécher ou attendre, VMC, moisissure ; « c'est la douche, ça retombera seul » |
| **+ contacts** | Fenêtres ouvertes, depuis quand | Renouvellement d'air appris ; air traversant ; pluie battante ; kWh perdus | « Refermez », « Refermez dans 4 min », « celle-ci, pas celle-là » |
| **+ CO₂, COV ou particules fines (PM2.5)** | Qualité de l'air : CO₂ (air confiné), COV (produits, cuisson), PM2.5 (cuisson, poêle, air du dehors) | Occupation confirmée ; moment choisi avec l'air et les pollens du dehors ; purificateur appris | Air à renouveler, au bon moment ; « l'air du dehors en apporte, refermez » ; « lancez le purificateur » pour les particules (aérer ne les enlève pas si le dehors en est chargé) |
| *(sans CO₂, après la 3.0)* | — | CO₂ estimé (dormeurs, sommeil, porte) | « Si la chambre sent le renfermé, aérez au lever » |
| **+ thermostat** | Consigne, chauffe réelle | Déperditions ; chaleur des murs ; coût en kWh | Chauffage, pause pendant l'aération, « Chauffez un peu plus » pour les murs |
| **+ volets, VMC, purificateur** | Leur état | Ombre sur chaque volet ; efficacité apprise | Des gestes en plus, comparés aux autres |
| **+ orientation des fenêtres** (facultative, déclarée dans le panneau ; angle exact par Adaptive Cover Pro) | — | Soleil sur chaque fenêtre, heure par heure, avec `sun.sun` et la façade (calcul repris de Confort 2.1) ; sans elle, le soleil global appris par pièce | Soleil bas qui entre en fin de journée, « laissez ouvert, le soleil chauffe la chambre », « baissez le volet ouest avant 15 h » |
| *(lumière, sans capteur)* | — | Soleil qui entre naturellement : soleil sur les fenêtres (Weather + exposition déclarée), volet relié | Conseils passifs, en « Bon à savoir » : « la chambre P a le soleil du matin de 9 h à 12 h » |
| **+ capteur de luminosité** (dédié, ou celui d'un détecteur de mouvement) | Lumière réelle de la pièce (lx) | — | Conseils précis : « il fait sombre alors que le soleil est dehors, ouvrez le volet » ; « la lumière du jour suffit, éteignez » |
| **+ éclairage relié** (lampes de la pièce dans Home Assistant) | Lampes allumées, leur puissance si connue | Lumière du jour disponible au même moment | Bénéfice chiffré : « la lumière du jour suffit, éteignez : 0,1 kWh d'économisé ce matin » ; en « Bon à savoir » : le temps d'éclairage évité par le soleil de la semaine |

### 6.7 bis Chauffage de pièce, chauffage de maison

Deux sortes de chauffage, interprétées différemment (remarque de Frank, 31 octobre) :
- **Chauffage de pièce** (radiateur électrique, convecteur, plancher d'une pièce) : il chauffe sa pièce. C'est le cas le plus courant ; chez Frank, les radiateurs à fil pilote.
- **Chauffage de maison** (poêle, cheminée, insert, climatisation réversible du séjour) : il est posé dans une pièce, le plus souvent le séjour, mais sa chaleur se répand dans toute la maison, par les portes, les couloirs et, s'il y en a, l'escalier.

Le jumeau de **chaque pièce** reçoit la chaleur des chauffages de maison et **apprend la part qui lui arrive**. Au départ : la moitié dans la pièce où il est posé, un peu ailleurs. Rien ne suppose un étage : dans une maison de plain-pied, les portes et le couloir font le même travail que l'escalier, et chaque pièce apprend simplement sa part.

Dans le panneau, à l'onglet Chauffage : « Ce chauffage chauffe : **cette pièce** · **toute la maison** ». Proposé d'office « toute la maison » pour un poêle ou une cheminée reconnus ; modifiable. La carte « Mon logement » peut alors dire où va la chaleur (« le poêle chauffe surtout le séjour et la chambre P »).

**Portes intérieures.** La part qui arrive dans une pièce dépend de sa porte, mais personne ne met de capteur sur une porte intérieure (remarque de Frank). Simple (principe 13) : la **part apprise** par chaque pièce contient déjà son habitude de porte. Chez Frank, sans rien savoir de la porte, le jumeau de la chambre d'Alice a appris qu'il ne lui arrive rien du poêle (0 %) : sa porte est souvent fermée, ce que Frank a confirmé. Un contact de porte qui existe déjà est lu ; il n'est jamais demandé. Deviner la porte heure par heure est une piste pour plus tard (§ 23.2).

Mesuré chez Frank (banc du 31 octobre) : le poêle traité en chauffage de maison améliore nettement la prévision du séjour (0,36 °C à 3 h au lieu de 0,42). Parts apprises : séjour 55 %, chambres de 0 à 15 %.

**Type de chauffage** (idée de Frank, 5 novembre ; moteur 3.9.5). Chaque chauffage a un type, réglé dans l'onglet Chauffage ; sans réponse, c'est un convecteur. Le type dit ce que fait le chauffage quand son thermostat l'arrête ou le relance :

| Type | Chaleur après l'arrêt | Fenêtre ouverte | Courant |
|---|---|---|---|
| Convecteur ou soufflant (défaut) | aucune | le coupe | 1 kWh = 1 kWh de chaleur |
| Panneau rayonnant | aucune (le Ressenti change) | le coupe | idem |
| Radiateur à inertie ou à eau | environ 30 min | le coupe | idem |
| Plancher chauffant | environ 3 h | le coupe, sans grand effet | idem |
| Poêle à bois ou insert | environ 1 h | ne le coupe pas | bois |
| Poêle à granulés | environ 20 min | le coupe | granulés |
| Climatisation réversible | aucune | la coupe | 1 kWh = 3 kWh de chaleur |

Le jumeau garde la chaleur que le chauffage rend encore après l'arrêt et le temps qu'il met à repartir. Une aération pendant la chauffe coûte donc plus avec l'inertie ou un plancher ; « Aérez avant que le chauffage démarre » sort des scénarios « plus tard » quand l'écart est net, sans règle à part. Le délai est une valeur par type ; l'apprendre pièce par pièce est une piste. Mesuré sur Chambre P, 5 novembre à 21 h 22 : « Aérez 5 min » reste à essayer avec des radiateurs (+0,36 kWh convecteur, +0,51 kWh inertie), pas avec un plancher.

### 6.7 ter Volets manuels : ni mesurés, ni devinés au hasard

Chez Frank comme chez beaucoup, les volets des chambres sont en bois et manuels, et chaque pièce a ses habitudes : celui de la chambre M n'est presque jamais fermé, celui de la chambre A l'est souvent (remarque de Frank, 31 octobre). Simple, selon le tableau du § 6.7 (principe 13) :
- **Volet relié** (moteur, Adaptive Cover Pro…) : sa position est lue, quel que soit ce qui le commande, et le moteur en tient compte.
- **Ce que le volet relié change dans le jumeau** (décidé avec Frank, 1er novembre) : le soleil qu'il laisse entrer, et **la chaleur qu'il garde fermé**. Pour la chaleur, le moteur prend la norme EN ISO 10077-1, annexe G : un volet roulant ajoute 0,15 m²K/W à sa fenêtre. Pour la Chambre P (1,3 m² de vitre), une nuit à 5 °C dehors, cela fait **environ 0,2 à 0,3 °C de plus au réveil**. L'apprentissage de nuit tient compte de la position du volet, comme le jumeau.
- **Ses gestes** : « Baissez le volet » et « Ouvrez le volet » entrent dans la comparaison des scénarios (§ 10), avec les mêmes seuils que les autres gestes.
  - L'effet n'est que **supposé** tant que les nuits volet fermé et volet ouvert n'ont pas été comparées (§ 4.1). Un geste de volet passe donc d'abord en « À essayer ».
  - Le jour : ouvrir le volet au soleil d'hiver ne compte que si le gain atteint 1,5 °C. Il faut environ 5 h de grand soleil sur la fenêtre ; avec 3 h, la pièce ne gagne qu'environ 1 °C, et le moteur ne dit rien.
  - La nuit, 0,2 à 0,3 °C n'atteint jamais le seuil d'un geste. Le volet fermé pour la nuit est donc un conseil passif : « **Baissez le volet ce soir : environ 0,2 °C de plus au réveil** », ou en kWh de chauffage économisés quand un thermostat tient la pièce.
  - Ce conseil paraît en « Bon à savoir », le soir seulement (jamais une fois le foyer couché). Il faut que la pièce se réveillerait sous sa plage et que le gain atteigne 0,1 °C ou 0,05 kWh.
- **Volet piloté par une automatisation** (pilotage automatique d'Adaptive Cover Pro activé) : le moteur tient compte de sa position, mais ne propose aucun geste sur lui, pour ne pas contredire l'automatisation.
- **Volet manuel** : l'habitude de la pièce, apprise par le jumeau (le soleil qui y entre en moyenne) ou déclarée dans « Pour aller plus loin » (« volet le plus souvent ouvert / fermé »). Un conseil qui en dépend reste conditionnel : « si le volet est ouvert, fermez-le avant 14 h ».

Déduire chaque jour la position d'un volet manuel en comparant deux pièces de même exposition est possible (vérifié sur l'été 2026 : entre les chambres M et A, plein sud, l'écart de chauffe va de −2,4 à +2,8 °C d'un jour de soleil à l'autre), mais c'est une amélioration pour plus tard (§ 23.2).

### 6.7 quater La lumière

Deux sources, comme le reste du tableau du § 6.7 (principe 13) :
- **Le soleil qui entre naturellement**, calculé sans capteur : soleil sur chaque fenêtre (Weather, exposition déclarée, volet relié). Il donne des **conseils passifs**, dans « Bon à savoir » : les heures de soleil de la pièce, la pièce la plus lumineuse le matin, etc.
- **Le capteur de luminosité**, s'il y en a un (dédié, ou celui d'un détecteur de mouvement) : la lumière réelle de la pièce. Il permet des **conseils précis**, parfois des gestes : « il fait sombre alors que le soleil est dehors, ouvrez le volet », « la lumière du jour suffit ».

Repères : moins de 100 lx, une pièce sombre ; 300 lx et plus, assez pour lire. Le volet se juge ainsi sur la lumière autant que sur la chaleur.

**Ce que la lumière du jour apporte** (les bénéfices que le moteur met en avant) :
- **le bien-être** : une pièce claire le jour, la lumière du matin pour bien se réveiller, la pénombre le soir pour bien dormir ;
- **la chaleur gratuite l'hiver** : un volet ouvert au soleil chauffe la pièce sans rien coûter (relié au jumeau de la chaleur) ;
- **l'éclairage évité** : quand le jour suffit, les lampes peuvent rester éteintes, chiffré en kWh et en € si l'éclairage est relié ;
- **et ses excès, à éviter** : l'été, le soleil direct qui surchauffe ; l'éblouissement sur un écran ou un bureau.

Ces bénéfices entrent dans le coût (§ 10.2) et dans le gain annoncé d'un geste : « ouvrez le volet : plus de lumière, et 1 °C gagné d'ici midi ».

### 6.8 Ce qu'on lit dans Versatile Thermostat (rien à déclarer)

Les attributs de chaque thermostat Versatile (`climate.*`) contiennent beaucoup de ce que le moteur cherche. Lu chez Frank le 31 octobre :

| Attribut | Ce qu'il dit | Ce que le moteur en fait |
|---|---|---|
| `power_manager.device_power` | Puissance déclarée du chauffage (W) | Puissance du jumeau, tenue fixe ; kWh de chaque geste pour la brique Énergie. **Plus besoin de la demander** |
| `power_percent`, `on_percent` | Chauffe réelle, en %, minute par minute | Entrée du jumeau (au lieu de « marche / arrêt ») |
| `preset_temperatures` (frost, eco, comfort, boost, et leurs versions « absent ») | Les consignes de chaque mode | Plage de la pièce ; prévoir la chauffe des prochaines heures |
| `current_state`, `requested_state` (mode, consigne, préréglage) | Ce que le thermostat vise maintenant | Simuler le chauffage dans les scénarios |
| `timed_preset_manager` | Un préréglage temporaire en cours (boost) et sa fin | Prévoir quand la consigne redescend |
| `vtherm_over_switch.tpi_coef_int`, `tpi_coef_ext`, `configuration.cycle_min` | La régulation du thermostat | Simuler sa réponse exacte dans les scénarios (« si vous ouvrez, il chauffera 20 min ensuite ») |
| `configuration.ac_mode` | Climatisation (mode froid) | Geste « climatisation » (§ 9.2) |
| `window_manager` (`window_sensor_entity_id`, `window_action`, `window_delay_sec`) | La fenêtre suivie, et ce que fait le thermostat quand elle s'ouvre (chez Frank : il coupe après 30 s) | Ne pas conseiller « baissez le chauffage pendant l'aération » : c'est déjà fait. Contrôle croisé du contact de fenêtre |
| `presence_manager` (capteur et état) | Présence dans la pièce (ex. `binary_sensor.presence_marylou`) | Occupation de la pièce, sans capteur à déclarer |
| `humidity_manager.humidity_sensor_entity_id` | Le capteur d'humidité de la pièce | Détection automatique des capteurs de la pièce |
| `specific_states.hvac_off_reason`, `is_sleeping`, `safety_state` | Pourquoi le chauffage est arrêté | Ne pas dire « Rallumez » quand l'arrêt est voulu (fenêtre, sécurité, mode central) |
| `ema_temp`, `temperature_slope` | Température lissée et tendance | Contrôle croisé du capteur ; tendance quand le jumeau débute |

**La plage suit le thermostat** (repris de Confort 2.1, rappelé par Frank le 1er novembre) : quand la pièce a un thermostat, en marche ou éteint (son préréglage reste le choix du foyer), sa consigne du moment devient le minimum de la plage, sauf si la pièce dit le contraire (`thermostat_reference`, oui par défaut).
- **Éco compris :** l'éco baisse la consigne exprès, et la pièce est alors attendue plus fraîche.
- **En hors-gel**, qui est une protection et non un confort, c'est la température « confort » du thermostat qui compte.
- **La consigne n'est retenue** qu'entre 5 °C et le maximum de la plage.
- **Le thermostat principal de la pièce** : une pièce peut nommer le thermostat que sa plage suit (`thermostat_plage`), quand ce n'est pas le sien. Par exemple, chez Frank, le Salon suit le poêle, qui est son chauffage principal ; son thermostat électrique ne sert que de tampon pour que la pièce ne descende pas trop (Frank, 1er novembre). Confort 2.1 le règle déjà ainsi : sa source de chauffage pour le Salon est le poêle.
- **Quand ce thermostat principal est un chauffage de la maison** (le poêle), le moteur le simule comme un thermostat dans les scénarios de la pièce : il repart quand la pièce refroidit. Avant, il gardait sa puissance du moment pour toute la prévision : le 1er novembre, la pièce était à 22 °C et le poêle en pause sur sa consigne, et le moteur prévoyait 19,4 °C à 16 h. Les autres chauffages de la maison restent tels quels.
- **Tant que ce thermostat principal est en marche**, « Chauffage éteint : le rallumer… » ne parle jamais du chauffage d'appoint, même quand le poêle fait une pause.

**Le poêle qui ne s'arrête pas seul** (Frank, 1er novembre) : son thermostat baisse la flamme jusqu'au minimum, mais le poêle brûle encore (`hvac_action` reste « heating » à 0 %).
- **Conseil passif** quand le poêle tourne au minimum et que la pièce a atteint sa consigne :
  - « Le poêle tourne au minimum : sans lui, la pièce reste au-dessus de 20 °C jusqu'à 18 h », si le jumeau, poêle arrêté, garde la pièce dans sa plage au moins **3 h** (réglage du foyer `poele_tient_h` : un rallumage coûte des granulés et de l'usure) ;
  - sinon « Le poêle tourne au minimum et la pièce monte encore : 0,6 °C de plus en 30 min », mesuré sur la dernière demi-heure (dès 0,3 °C).
- **Geste « Coupez le poêle »** quand la pièce reste au-dessus de la consigne du poêle de **1 °C** (`depassement`) depuis **30 min** (`depassement_min`) : « 22,7 °C pour 21,5 °C visés, depuis 35 min ». C'est une mesure, pas une prévision : pas besoin de preuve. Il passe avant les gestes du jumeau, jamais la nuit ni avant un interdit. Suivi : fait quand le poêle ne chauffe plus.
- Le jumeau voit encore le poêle au minimum comme éteint (0 %) : la « montée » vient donc de la mesure, pas de la prévision.

**Un thermostat coupé par sa fenêtre** (`hvac_off_reason` = `hvac_off_window_detection`) reste le thermostat de la pièce : dans les scénarios, il repart dès que la fenêtre est refermée. Avant, le moteur le comptait comme arrêté par le système, donc la pièce fermée ne chauffait plus non plus (Chambre AL, 1er novembre : 3 h ouverte, « Ouverte ou fermée » pendant que la pièce passait de 20 à 17,7 °C). Ce cas ne donne toujours pas « Rallumez ».

**Les murs gardés d'un redémarrage à l'autre** : le moteur note la température de ses murs à chaque passage. Après un redémarrage de moins d'une heure, il la reprend ; au-delà, il part de la moyenne de l'air des 6 dernières heures, jamais de l'air du moment. Le 1er novembre, un redémarrage juste après le poêle avait pris 22,3 °C pour les murs du Salon : la prévision à 1 h a été trop chaude de 1,5 °C pendant cinq heures.

**« Le chauffage ramène la pièce à 17 °C vers 12 h 30 »** (demande de Frank, 1er novembre) : quand une pièce est sous sa plage et que son thermostat l'y ramène, le jumeau dit quand, en « Bon à savoir ». Rien n'est à faire, et le foyer sait à quelle heure la pièce sera revenue.
| `specific_states.total_energy` | Énergie consommée | Contrôle du jumeau (énergie prévue / mesurée) ; données pour Énergie |
| `underlying_entities` | Les appareils commandés (fil pilote, poêle) | Savoir qu'une pièce a plusieurs chauffages (Salon : poêle + radiateurs) |
| `auto_tpi_learning` | L'apprentissage propre au thermostat, s'il est actif | À reprendre plus tard : Versatile apprend déjà l'inertie de chauffe |

Sans intérêt pour le conseil : verrou, sécurité détaillée, réglages de délai minimal.

**Sans Versatile Thermostat** : un thermostat ordinaire (`climate`) ne dit que s'il chauffe (`hvac_action`). Le moteur lit alors « marche / arrêt », et la puissance s'apprend (ou se déclare dans « Pour aller plus loin »), avec une confiance plus faible sur les gestes de chauffage.

## 7. Contrôle des mesures et fiabilité

### 7.1 Principe
Avant le moteur, chaque mesure reçoit une **note de fiabilité**, en la comparant à trois références :
1. **la physique** (ex. rayonnement par ciel clair, calculé localement) ;
2. **une source classique gratuite** : Open-Meteo (sans clé), Météo-France ;
3. **les voisins et l'historique** : autres capteurs de la maison, le capteur lui-même les jours sans défaut.

Le système apprend **dans quelles conditions** un capteur se trompe : position du soleil, direction du vent, heure, chauffage en marche.

### 7.2 Ce qu'il en fait
- **Fiable** : utilisée telle quelle.
- **Douteuse dans un cas appris** : remplacée par l'estimation, marquée « estimé ».
- **Dérive sans cause apprise** : signalée dans le panneau (« un nouvel obstacle depuis le 3 novembre ? »).

### 7.3 Cas connus

Dans la 3.0 : l'ombre de la station (déjà apprise par Confort, reprise par Weather) et, pour tous les capteurs, les contrôles simples (figé, saut impossible, hors plage). Les autres lignes viennent avec Weather 3.x et la page « Fiabilité » (§ 3 bis).

| Capteur | Piège | Repérage |
|---|---|---|
| Rayonnement (station de Frank, mât à l'est) | Ombre de la maison l'après-midi | Masque d'ombre appris par position du soleil, par temps clair |
| Température extérieure | Abri chauffé par le soleil | Écart à Open-Meteo qui suit le rayonnement |
| Rafales | Abri par certaines directions | Rapport station / Open-Meteo par direction |
| Pluviomètre | Bouché, abrité | Pluie annoncée ou au radar, station à zéro |
| Humidité | Dérive lente | Écart permanent par temps calme |
| Température intérieure | Soleil, radiateur, poêle | Pics liés au soleil sur la façade ou au chauffage |
| CO₂ | Dérive du réglage automatique | Minimum après longue aération comparé à 420 ppm |
| Tout capteur | Figé, pile faible | Aucune variation pendant que les voisins bougent |

**Les contrôles simples des pièces** (1er novembre, HA de test, `advisor/checks.py`) :

| Mesure | Plage possible | Saut impossible (en 5 min) | Figée depuis |
|---|---|---|---|
| Température | −10 à 45 °C | plus de 4 °C | 12 h |
| Humidité | 1 à 100 % | plus de 30 points | 12 h |
| CO₂ | 350 à 10 000 ppm | plus de 2 000 ppm | 12 h |
| Particules | 0 à 500 µg/m³ | aucun (la cuisson fait des bonds) | 48 h |
| COV (indice) | 1 à 500 | aucun | 48 h |

- **Un saut** est mis de côté une seule fois : si la mesure suivante confirme la nouvelle valeur, elle est reprise ; un pic isolé disparaît.
- **« Figée »** se lit sur le dernier changement de valeur. Après un redémarrage, ce compteur repart de zéro : une mesure figée ne se voit qu'au bout des 12 ou 48 h.
- **Une mesure douteuse est laissée de côté**, jamais conseillée. La carte le dit, par exemple « Mesure douteuse, laissée de côté : CO₂ (0 ppm : valeur impossible) ».
- **Si c'est la température de la pièce** qui est douteuse, la carte ne donne aucun conseil, en gris : « La température semble fausse (figée depuis 9 h 40) : pas de conseil tant qu'elle l'est ».
- **La page Fiabilité** montre chaque mesure de chaque pièce : sa valeur, fiable ou douteuse, et pourquoi.
- **Ce que ces contrôles remplacent :** les seuils écrits en dur (CO₂ sous 300 ppm, particules au-dessus de 500, COV hors 0 à 500).

**La prévision aussi se contrôle** (31 octobre, HA de test) : Open-Meteo, à la position arrondie, était 2,5 à 4 °C trop froid toute la journée chez Frank, et la station avait raison (une chambre a gagné 1 °C fenêtre ouverte). Le moteur recale donc la prévision sur la station et garde cet écart des heures durant ; Weather 3.x devra l'apprendre heure par heure et le fournir corrigé.

### 7.4 Partage des rôles
- **Weather** contrôle le dehors (masque d'ombre repris de `sunlight.py` de Confort, Open-Meteo élargi : rayonnement, nuages, température, humidité, vent ; un appel par heure gardé en mémoire).
- **Confort** contrôle les capteurs des pièces.
- Chaque valeur échangée porte **sa fiabilité et son origine**.
- **Confort ne dépend pas d'Open-Meteo** : sans lui, il garde la physique, Météo-France et l'historique, et la page Fiabilité le dit.

## 8. Le modèle : le jumeau

**Physique d'abord** : ses paramètres ont un sens (volume, vitrage, isolation, débit d'une fenêtre), partent de valeurs plausibles et sont ajustés par l'apprentissage. Le jumeau 2.1, appris par simple régression, bat à peine la prévision « rien ne change » et ne sait rien d'un geste rare (test du 31 octobre, [conception](CONCEPTION-MOTEUR.md) § 1).

- **Chaleur** : air et murs (deux réservoirs : l'air réagit vite, les murs rendent lentement). Entrées : dehors, soleil par fenêtre, chauffage, fenêtres ouvertes, pièces voisines.
- **Eau** : échange avec le dehors (fuites, fenêtres, VMC), sources (sommeil, douche, cuisson), pièces voisines.
- **CO₂** : occupants, renouvellement d'air.
- **Départ** : les déclarations (§ 6.3) donnent des valeurs physiques plausibles dès le premier jour. À l'installation, le jumeau s'entraîne sur l'historique déjà présent dans Home Assistant (10 jours détaillés, statistiques à long terme).
- **Emprunt à la maison** : une pièce peu mesurée part de ce que les autres ont appris (isolation, soleil, enveloppe), puis s'en écarte avec ses propres mesures.
- **Confiance** : la précision mesurée de chaque pièce (erreur à 1 h et 3 h, pendant et hors des gestes, § 18.3). Une pièce mal prévue fait parler au conditionnel, ou taire.
- **Apprentissage** : chaque nuit, les paramètres sont ajustés pour que les prévisions à 1 h et 3 h des jours passés soient les plus justes possibles ; une valeur déclarée ou lue (la puissance d'un radiateur) est tenue presque fixe ([conception](CONCEPTION-MOTEUR.md) § 6.5). Le filtre de Kalman, essayé, a été écarté.
- **Correction par l'écart récent** : l'erreur d'un jumeau persiste d'heure en heure ; chaque prévision est corrigée par l'écart constaté la dernière heure, qui s'estompe ensuite. C'est ce qui manque au jumeau à 1 h (banc du 31 octobre).
- **Saisons** : ce qui est appris l'hiver (chauffage, poêle) ne suffit pas l'été (fenêtres la nuit, volets, soleil) ; le jumeau continue d'apprendre toute l'année et garde ce qu'il sait de chaque saison.
- **Tous les sujets dans la 3.0** : chaleur, eau et CO₂ ont chacun leur jumeau, construits et validés l'un après l'autre avant la préversion ; la lumière est calculée (soleil) ou lue (capteur). La température n'est que la première ligne du tableau du § 6.7 (remarque de Frank).

## 9. Gestes possibles et interdits

### 9.1 Catalogue
Ne rien faire · fermer (une fenêtre précise ou toutes) · ouvrir 5, 10 ou 20 min · ouvrir jusqu'à une heure · ouvrir ici et là (air traversant) · fermer ou ouvrir un volet · lancer ou arrêter la VMC · lancer le purificateur · chauffer d'un degré · baisser le chauffage pendant l'aération · lancer, régler ou arrêter la climatisation · lancer un ventilateur.

Un geste n'est proposé que si la pièce a de quoi le faire (déclaré ou détecté).

### 9.1 bis Le chauffage (décidé avec Frank, 1er novembre)

Deux gestes, pour une pièce qui a son propre thermostat (Versatile Thermostat) :
- **« Rallumez le chauffage », en conseil passif seulement** (décidé avec Frank le 1er novembre) : le thermostat est éteint, la pièce passe sous sa consigne (donc sous sa plage), et rallumer apporterait un vrai plus.
  - Il ne monte jamais dans le bandeau. Il paraît en « Bon à savoir » : « Chauffage éteint : le rallumer donnerait 1,5 °C de plus d'ici 15 h ». Une pièce chauffée par autre chose, comme le Salon par le poêle, n'est ainsi jamais poussée à rallumer.
  - Le moteur simule le thermostat rallumé sur sa consigne du moment. En hors-gel, c'est sa température « confort », comme pour la plage (§ 6.8).
  - Un arrêt à la main (`hvac_off_manual`) ne bloque pas ce conseil. Un arrêt imposé par le système (fenêtre, sécurité, mode central…) le bloque.
  - Le conseil n'est pas donné pendant le sommeil, et seulement si le gain serait signalé pour un geste (§ 10.2 bis).
- **« Remettez le chauffage à 19 °C »** : le thermostat chauffe, mais sur une consigne plus basse que le minimum de la pièce.
  - Avec la plage qui suit le thermostat, ça n'arrive qu'en hors-gel, ou pour une pièce qui ne suit pas son thermostat (`thermostat_reference` à non).
  - Une pièce qui remonte seule vers sa consigne n'a pas de geste. Elle a son « Bon à savoir » : « Le chauffage ramène la pièce à 17 °C vers 12 h 30 » (§ 6.8).

**Ces gestes sont jugés comme les autres** (§ 10) : le confort gagné contre les kWh que le chauffage dépense, avec les mêmes seuils pour être signalés.
- **Pas de geste de chauffage pendant le sommeil**, comme pour l'aération : personne ne se lève pour ça.
- **L'effet est tenu pour avéré** dès que le jumeau de chaleur de la pièce est appris. La puissance du radiateur et sa réponse sont justement ce que l'apprentissage de nuit mesure chaque jour, sur la chauffe réelle (`power_percent`).
- **Le suivi** (§ 15) voit le geste fait quand le thermostat repasse en chauffe, ou quand sa consigne atteint celle conseillée.

### 9.1 ter Durées, fenêtre ouverte, source du moment, air traversant (décidé avec Frank, 1er novembre)
- **La durée la plus courte qui suffit**, de 5 en 5 min, jusqu'à la limite du foyer (§ 10.3) : il faut 6 min, le moteur ne dit plus « Aérez 10 min » mais compare 5, 10, 15… et garde la plus courte dont le coût reste à 10 % du meilleur. Pareil pour la VMC rapide et le purificateur. Les gestes « plus tard » vont de quart d'heure en quart d'heure ; jamais la nuit.
- **Fenêtre ouverte, dire quand refermer** : « Laissez ouvert encore 10 min », puis « encore 5 min », puis « Refermez ». Le geste gardé d'un passage à l'autre est décompté du temps écoulé, et la carte décompte la minute entre deux passages (`refermer_a`). Au-delà d'une heure : « Refermez vers 16 h ». La lumière qui change au moment de refermer viendra avec l'intégration.
- **La source du moment**, pour le CO₂, le COV, les particules et l'humidité : le jumeau rejoue la dernière demi-heure avec ce qui a vraiment agi ; si la mesure reste au-dessus de sa prévision (60 ppm, 20 points de COV, 4 µg/m³, 0,4 g/m³ d'eau), une source tourne encore — cuisson, douche, invités. Son débit est trouvé avec la dilution de la pièce, puis porté dans tous les scénarios en s'éteignant (1 h 30 pour le CO₂, 45 min pour le COV, 30 min pour les particules et l'eau ; à apprendre). Une cuisson qui continue fenêtre ouverte ne donne plus « Refermez » : fermé, le COV remonterait. Rien n'est déduit si une fenêtre ou un appareil a changé entre-temps.
- **L'air traversant** : des fenêtres ouvertes sur deux côtés (60° d'écart au moins) laissent passer deux fois l'air de chacune seule (CIBSE AM10 : deux à trois fois par vent moyen). L'apprentissage de la nuit le compte aussi, pour que l'effet appris d'une fenêtre reste celui d'un seul côté. Une fenêtre ouverte d'un côté propose « Ouvrez aussi les fenêtres sud 5 min : l'air redevient sain en 5 min au lieu de 15 ». L'effet est supposé tant que la pièce ne l'a pas montré : il sort d'abord en « À essayer ».
- **Après la 3.0** : prévoir une source habituelle (« Il est 19 h, entrouvrez avant de cuisiner »).

**Apprentissage de la nuit, ajouts du 2 novembre** :
- **L'effet des fenêtres recalé sur les ouvertures elles-mêmes** : l'ajustement sur toute la journée pèse à peine quelques heures d'ouverture. Après lui, l'effet de la fenêtre est corrigé pour que le jumeau reproduise ce que les ouvertures ont vraiment fait (médiane, au moins 2 ouvertures nettes, au plus ×2 ou ÷2 par nuit). Une ouverture ne compte que si son propre effet dépasse ce que la pièce aurait fait sans elle (le poêle qui s'arrête, le soleil le cachent sinon). Gardé si la dernière journée n'est pas prévue plus de 5 % moins bien.
- **Le débit réel de la VMC rapide** : on connaît rarement son débit. La nuit essaie de 5 % à 130 % du débit déclaré et garde la part qui prévoit le mieux l'humidité (au moins 1 h de vitesse rapide vue). Chambre P : 5 %, la VMC rapide ne change presque rien.
- **La part de la chaleur du poêle reçue par une pièce n'est jamais négative.**
- **Le labo apprend sur l'historique de la maison** tant qu'il a moins de 10 jours à lui (lecture seule).

**Le soleil dans « Bon à savoir »** (Frank, 3 novembre) : une seule ligne pour la pièce, ses façades dans l'ordre où le soleil passe (« Soleil sur les fenêtres est, sud et ouest jusqu'à 17 h : +0,8 °C dans la pièce »), et seulement quand il réchauffe la pièce d'au moins 0,5 °C dans les heures qui viennent (le jumeau avec et sans soleil). Les jours où il ne change rien, la ligne disparaît.

### 9.2 Climatisation et ventilateurs
- **Climatisation** : lue par le Versatile Thermostat déjà présent (mode froid, consigne, marche réelle). Elle est comparée aux gestes gratuits : volets, air de la nuit, air traversant. Elle n'est conseillée que s'ils ne suffisent pas, et son coût en kWh est compté. Pendant une aération, le moteur conseille de la couper, comme pour le chauffage.
- **Ventilateur** : deux cas, comme pour la VMC.
  - **Déclaré** dans « Équipements » sans être relié : conseil simple (« Lancez le ventilateur »), sans suivi de son état.
  - **Relié** (entité `fan`) : son état est lu, le conseil suit s'il tourne.
- **Un ventilateur ne refroidit pas l'air**, il rafraîchit la peau. Quand il tourne, le coût d'inconfort se calcule sur la **température ressentie** (environ 2 °C de moins), pas sur la température de la pièce.

### 9.3 Interdits de sécurité (règles fixes, reprises et testées)
Pluie sur un ouvrant exposé · pluie dans l'heure · rafales au-dessus du seuil · orage et vigilance (sauf si la station mesure calme et sec, comme aujourd'hui) · air extérieur pollué · alarme armée (absent, ou nuit sauf fenêtre voulue) · gel pour une ouverture longue.

Un interdit retire des gestes ; il peut aussi en imposer un (« Fermez, il pleut »).

## 10. Évaluation

### 10.1 Horizon
- Le jour : les 3 prochaines heures.
- Le soir et la nuit : jusqu'au réveil appris.
- Pour « À venir » et « Cette nuit » : jusqu'à demain midi, avec les prévisions.

### 10.2 Coût d'un scénario
| Terme | Unité affichée |
|---|---|
| Inconfort | degrés hors de la plage × heures |
| Humidité | points au-dessus du seuil × heures ; heures de risque de moisissure sur mur froid |
| Air | ppm au-dessus du repère × heures (CO₂, COV) |
| Lumière | heures de jour, pièce occupée, sous le repère de lumière (lx), si un capteur la mesure ; en moins, l'éclairage évité (kWh) quand l'éclairage est relié |
| Énergie | kWh de chaleur perdue (que le chauffage devra rendre) |
| Dérangement | coût fixe d'un geste, plus élevé la nuit |

Les plages et repères restent ceux de [SEUILS.md](../../niak-comfort-integration/docs/SEUILS.md), réglables par pièce.

### 10.2 bis Un geste doit être significatif (décidé avec Frank, 31 octobre)

Un geste n'est conseillé que s'il est **significatif** sur au moins un sujet, c'est-à-dire :
- **A. il épargne à la pièce l'écart minimal ci-dessous pendant deux heures**, en cumulé sur l'horizon : degrés hors de la plage, points au-dessus du premier repère (1,5 °C pendant 2 h, 50 points de COV pendant 2 h…). Une chambre gardée 2,5 °C plus chaude toute la nuit compte, même sous sa plage dans les deux cas ; un COV de cuisine gardé sous son repère pendant l'heure qui suit la cuisson aussi ; « Refermez, vous gardez 0,5 °C » pour une pièce juste sous sa plage (1,5 °C·h) non. *(Révisé le 31 octobre au soir : la première version, « une heure de plus dans la plage avec la moitié de l'écart à la fin », taisait ces deux cas, révélés par le rejeu de 10 jours.)*
- **B. ou il apporte un écart qu'on perçoit**, à la fin de l'horizon :

| Sujet | Écart minimal | Repères (condition A) |
|---|---|---|
| Température | **1,5 °C** | bornes de la plage de la pièce |
| Humidité | **5 points** | 60 %, 70 % |
| CO₂ | **200 ppm** | 1 000, 1 500 ppm |
| COV | **50 points d'indice**, ou **150 ppb** selon le capteur | indice 150, 250 ; 300 et 1 000 ppb |
| Particules fines (PM2.5) | **5 µg/m³** | 15, 25 µg/m³ |
| Lumière | **200 lx** | 100, 300 lx |
| Moisissure | **5 points d'humidité au coin de mur le plus froid**, comptés au-dessus de 80 % (EN ISO 13788), sans falaise ; pas doublé la nuit | 80 % au coin de mur |
| Énergie seule | **0,5 kWh**, là où le chauffage est simulé (sans thermostat, la chaleur perdue se voit déjà dans la température) | — |

- **La nuit, les écarts minimaux doublent**, sauf pour la sécurité et la moisissure.
- Un pourcentage a été écarté : il n'a pas de base commune (1 °C vaut 5 % de 20 °C ou 100 % de l'écart à la plage).
- Les écarts sont réglables ; le curseur « tolérance aux gestes » les fait monter ou descendre ensemble.
- **Parmi les gestes significatifs, le moins coûteux est conseillé**, et non le moins coûteux de tous : une aération de 10 minutes qui ne change rien de perceptible ne doit pas cacher « Ouvrez », qui change quelque chose.
- Les COV ont leur jumeau depuis le 31 octobre, sur la loi des particules : l'indice remonte avec la cuisine, baisse avec l'air du dehors, et revient de lui-même vers l'air habituel de la pièce (l'indice de Sensirion se recale sur 24 h). Au banc, à 3 h : 54 points d'erreur contre 89 pour « rien ne change » ; 33 aérations, −81 mesurés pour −154 prévus en 1 h. Un COV modéré retombe seul (pas de geste) ; après une cuisson à 450, une aération de 10 minutes. Chez Frank, deux capteurs : `sensor.ikea_sensor_voc_index` dans la cuisine (indice, volume Salon · Cuisine) et `sensor.tvoc_voc` dans le couloir de l'étage (en ppb). Un capteur de couloir ne décrit l'air d'aucune pièce : il sert de repère général de l'étage (conseils passifs, « Bon à savoir »), jamais à un geste dans une chambre.

### 10.3 Préférences (à la place des 23 seuils cachés)
Trois curseurs dans les réglages, avec leur effet expliqué :
- **Confort ou économie** — par défaut côté confort ;
- **Tolérance aux gestes** — combien de conseils par jour ;
- **La nuit** — par défaut : seulement les gestes importants.

Le reste est appris et affiché. Les poids s'ajustent avec les avis (§ 15), **dans des bornes**, jamais au-delà.

**Tout ce qui dépend du foyer et de son mode de vie est un réglage, jamais une valeur figée dans le code** (Frank, 31 octobre). Réglé pour la maison, et pour une pièce quand elle diffère (une chambre d'enfant, un travail de nuit) ; chaque réglage a une valeur par défaut. La physique et les normes (EN ISO 13788, règles de preuve du § 4.1) ne sont pas des réglages.

| Réglage du foyer | Par défaut | Ce qu'il change |
|---|---|---|
| Heures de sommeil | 22 h – 7 h ; l'alarme en mode nuit compte aussi | la nuit du moteur, son horizon jusqu'au réveil |
| Ouvrir la nuit | non | aucune ouverture conseillée pendant le sommeil ; « Refermez », VMC et purificateur restent |
| Aération la plus longue | 30 min (10 min à 1 h) | « Aérez… » : le moteur trouve la plus courte qui suffit, de 5 en 5 min |
| Gestes « plus tard », jusqu'à | 2 h (30 min à 4 h) | « Aérez 10 min vers 16 h 15 », « Refermez vers 16 h », de quart d'heure en quart d'heure |
| VMC rapide et purificateur, durée la plus longue | 1 h (15 min à 2 h) | la plus courte qui suffit, de 5 en 5 min à partir de 10 min |
| « Cette nuit, pensez à… » | 4 h avant le coucher | quand la phrase apparaît |
| Buée de la nuit | 5 h avant le coucher | quand la phrase apparaît |
| Hors-gel pendant une absence | 7 °C | le seul confort gardé en mode vacances |
| Tolérance aux gestes | 1 (plus haut : moins de gestes) | tous les écarts du § 10.2 bis |
| « Pas maintenant » | 1 h | combien de temps un geste refusé est mis de côté (§ 15) |
| Poêle : arrêt utile | 3 h | combien de temps la pièce doit tenir sans le poêle pour dire qu'on peut l'arrêter (§ 6.8) |
| Poêle : dépassement | 1 °C pendant 30 min | au-delà, « Coupez le poêle » (§ 6.8) |
| Plage de confort, repères | ceux de Confort | le coût d'inconfort |

**La plage de chaque pièce** est celle réglée dans Confort (chez Frank : Chambre P 18–24 °C, les autres pièces 19–24 °C, 26 °C l'été), avec la même règle de saison que la 2.1 : la limite haute passe de l'hiver à l'été, à mi-chemin au printemps et en automne, quand la saison de la maison est connue (Weather ou capteur Saison choisi dans Confort) ; sans saison, la plage reste telle qu'elle est réglée. Les repères d'humidité, de CO₂, de particules et de COV aussi.

## 11. Décision

1. Le moteur garde le scénario au coût le plus bas.
2. Il le conseille **seulement s'il bat « ne rien faire » d'un gain net minimal**.
3. **Stabilité** : un conseil affiché ne change que si le nouveau le bat d'une marge. Une seule hystérésis, sur le coût.
4. **Séances** : un geste suivi devient une séance avec un début et une fin (« Aérez 10 min » → « Refermez dans 3 min » → « Merci, c'est fait »). Pas de conseil contraire pendant une séance, sauf sécurité.
5. **Moments naturels** : les gestes non urgents sont regroupés au lever, au retour, au coucher.
6. **La nuit** (heures de sommeil de la pièce, un réglage, ou alarme en mode nuit) : seulement les gestes importants — fenêtre ouverte et pièce qui va sortir de sa plage, pluie, alarme. Le reste attend le matin ou passe dans « Cette nuit, pensez à… » la veille. **Jamais d'ouverture conseillée pendant le sommeil** (Frank : « en plein hiver, il y a très peu de chance que je laisse ouvert, même 20 min pour aérer en pleine nuit ») : la nuit garde « Refermez », la VMC et le purificateur ; une fenêtre pour la nuit (l'été) se décide le soir.
7. **Rythme** : un plafond de conseils par heure, sécurité exceptée.
8. **Mode vacances**, déduit de l'alarme : le mode « vacances » d'Alarmo s'il est utilisé, sinon l'alarme armée en « absent » depuis plus de 24 h. Le moteur ne garde alors que la sécurité (fenêtre restée ouverte, pluie), l'humidité et le risque de moisissure, et le hors-gel. Les conseils de confort se taisent. La carte affiche « Mode vacances ». Au retour, elle résume ce qui s'est passé pendant l'absence et dans quel état on retrouve la maison (« Chambre P à 16 °C, humidité normale »).

## 12. Le logement

- Le moteur raisonne sur **la maison entière**, vue comme des pièces reliées : volumes « même air », portes intérieures, escalier, étages, façades.
- Il produit **un seul plan** (« Ouvrez la cuisine et la chambre P 10 min, laissez le Salon fermé »). Chaque carte de pièce en montre sa part ; la carte « Mon logement » montre le plan entier.
- Le plan s'appuie d'abord sur les pièces bien mesurées ; les autres suivent avec leur confiance.
- Deux pièces ne reçoivent jamais des conseils contraires sur un même air.

## 13. Proactivité

- **À venir** : le prochain geste utile et son heure (« Vers 14 h, baissez le volet ouest »).
- **Cette nuit, pensez à…** : un encart rempli le soir à partir des prévisions et de l'état de la maison (« Fermez les volets de l'étage, 6 °C cette nuit » · « Fenêtre de la cuisine encore ouverte »). Il n'apparaît que s'il a quelque chose à dire.
- **Onglet Notifications de Confort** : c'est là que se règlent les LED (déjà fait) et, dans une version suivante, les notifications sur téléphone.
- **LED (WLED et lumières couleur)** : elles lisent directement la décision du moteur, sans passer par les entités. Elles montrent donc toujours la même chose que la carte.
- **Notifications sur téléphone** (appli Home Assistant) : **validées, mises en attente** pour une version après la 3.0. Elles seront réglées dans l'onglet Notifications, désactivées par défaut, et réservées aux gestes importants et à « Cette nuit, pensez à… ».

## 14. Rédaction et affichage

- Le moteur produit les phrases ; la carte ne compose aucune phrase de conseil.
- **Bandeau** : un seul geste, ou « Rien à faire ». Une estimation n'y monte que si elle est très sûre.
- **« À savoir »** : par importance, en trois rubriques (pour le geste · à surveiller · appris), puis **« Bon à savoir »** : une ligne qui défile, un conseil passif à la fois (soleil de la pièce, lumière, habitudes apprises), sans couleur d'alerte.
- **« Bon à savoir » reste enrichissable** (demande de Frank) : il est fait de **fournisseurs**, chacun une petite fonction qui reçoit la pièce et rend zéro, un ou plusieurs conseils passifs (texte, sujet, importance, durée de validité). Ajouter un fournisseur n'oblige à rien changer ailleurs. Les premiers : soleil de la pièce, lumière, habitudes apprises. D'autres viendront de Confort, des autres briques (Weather, Énergie) ou des extensions, sans savoir encore lesquels. Chaque fournisseur s'active ou se coupe dans les réglages.
- **« Pourquoi ? »** : les deux ou trois scénarios comparés, avec leurs chiffres.
- **Tournures selon la preuve** (§ 4.1) : affirmatif (avéré), conditionnel (renforcé) ; un effet seulement supposé ne parle que dans « Bon à savoir ».
- **Textes pour la famille** : une idée par ligne, un seul conseil par carte, kW et €, « heures pleines / creuses ».
- **Couleurs** : bleu = tout va bien, vert = bénéfice, orange = action, rouge = attention, gris = inconnu. (Le § 2.7 du cahier de Confort, qui dit « vert = tout va bien », est périmé.)
- **Langues** : français, anglais, allemand, depuis un seul module.

## 15. Apprendre de ses erreurs

Trois sortes d'erreurs, trois boucles :
1. **Le modèle s'est trompé** (prévu ≠ mesuré) : le jumeau se corrige seul.
2. **Le calcul était juste mais le choix ne convenait pas** : bouton **« Ce conseil ne va pas »** sur la carte (« faux », « inutile », « pas maintenant »). Les poids s'ajustent dans leurs bornes ; la situation complète est gardée.
3. **Il manque une donnée** (après la 3.0) : quand une pièce fait autre chose que prévu, le moteur pose une question au lieu de conseiller à l'aveugle (« La chambre refroidit vite : une fenêtre sans capteur est-elle ouverte ? »). Dans la 3.0, il baisse simplement sa confiance dans cette pièce.

**Ce que Hestia sait de votre maison** : chaque effet avec son niveau de preuve (§ 4.1), le nombre de gestes vus et l'écart entre prévu et mesuré, dans le hub (§ 16). C'est la version lisible de l'apprentissage.

Le moteur suit aussi **quels conseils sont suivis**. Un conseil jamais suivi est un échec, pas une réussite.

**Comment ça marche (1er novembre, HA de test)** :
- **Le bouton** : « Ce conseil ne va pas », en bas de la carte de la pièce. Il ouvre trois réponses et une note facultative :
  - « Faux » : le conseil se trompe ;
  - « Inutile » : il est juste, mais ne vaut pas le geste ;
  - « Pas maintenant » : je ne peux pas, redemandez plus tard. Cette réponse n'est pas proposée pour un interdit de sécurité, ni quand rien n'est demandé.
- **La situation est gardée** : à chaque réponse, le dernier instantané de la pièce est rangé avec sa trace, ce que la carte montrait, l'avis et la note. Rien n'est jamais effacé ; chaque cas se rejoue sur le banc (§ 16 bis.2).
- **« Pas maintenant »** met le geste de côté pendant un temps propre au foyer (`pas_maintenant_min`, 60 min par défaut, § 10.3). Ensuite, le moteur juge sans ce geste. La carte dit « Mis de côté jusqu'à 11 h 05 : aérer ».
  - Le geste reste fermé même si le moteur le jugerait encore utile ; seule la sécurité passe outre.
  - Si le foyer fait le geste quand même, la mise de côté s'arrête.
  - Une aération mise de côté ne rend jamais « interdites » les fenêtres déjà ouvertes : le moteur lirait ce cas comme le « Fermez » de la pluie.
- **Le suivi** : le geste affiché, ou le geste « À essayer », est noté **suivi** s'il est fait pendant qu'il est affiché. Il est noté **pas suivi** s'il est remplacé avant :
  - une fenêtre ouverte suit « Aérez » ;
  - toutes les fenêtres fermées suivent « Refermez » ;
  - un appareil démarré ou arrêté suit le conseil qui le demandait.
- **Où le lire** : la page « Atelier » montre, par pièce, la part des gestes suivis sur 30 jours, les gestes « À essayer » à part, puis les avis donnés, dont chacun ouvre sa trace.
- **Ce qui n'est pas encore fait** : les poids ne bougent pas seuls après un « Faux » ou un « Inutile ». Un seul appui ne doit pas déplacer le moteur. Les cas signalés sont d'abord relus et rejoués, puis la correction se fait au bon endroit : mesure, jumeau, poids, interdit ou phrase (§ 16 bis). Un réglage automatique dans les bornes reste à décider avec Frank, quand il y aura assez de cas.

**Journal** : chaque décision est gardée 60 jours avec ses entrées, les scénarios, la prévision, le résultat et l'avis. Les situations signalées sont gardées sans limite : elles deviennent des tests (§ 18).

### 15.1 Une note pour chaque geste (proposé par Frank, 3 novembre)

**Pourquoi.** Jusqu'ici, la nuit recalibre le jumeau sur toutes les mesures des 7 derniers jours. Une fenêtre ouverte 20 minutes sur une journée y pèse presque rien. Pour la chaleur, une correction à part regarde les ouvertures seules ; pour l'humidité, il n'y en a pas. La Chambre P, le 3 novembre, promettait encore « −13 points » alors que ses deux aérations n'avaient rien donné, et l'humidité était revenue au même niveau, voire plus haut. Le moteur savait que le geste ne marchait pas (§ 4.1), mais ses chiffres ne bougeaient pas.

**Le principe.** Chaque geste reçoit une note, rangée par catégorie. La nuit fait le bilan des notes de chaque catégorie et ajuste le jumeau.

**1. Quand on note.** **1 h après la fin du geste** : la fenêtre refermée, la VMC repassée en vitesse lente, le purificateur arrêté. Les murs et les meubles ont eu le temps de rendre l'eau et la chaleur que l'air avait perdues.

**2. Ce qu'on compare.** Le jumeau calcule deux trajets depuis le début du geste, avec ce qui a vraiment agi :
- **avec le geste**, tel qu'il a été fait (ouvert 45 min, puis fermé) ;
- **sans le geste** (tout resté fermé).

| | Calcul |
|---|---|
| **Effet annoncé** | prévu avec le geste − prévu sans |
| **Effet mesuré** | mesuré − prévu sans |
| **Rapport** | effet mesuré ÷ effet annoncé |

On compare à « sans le geste », pas à « avant ». Le soir, une chambre où l'on dort prend de l'humidité toute seule. Une aération qui la laisse au même niveau, alors qu'elle serait montée de 5 points, a réussi.

**3. La note.**

| Note | Rapport | Ce qu'elle dit |
|---|---|---|
| **+** | de 0,5 à 2 | le geste a fait ce qui était annoncé |
| **0** | de 0 à 0,5 | il a fait peu |
| **−** | moins de 0 | il a fait l'inverse |
| **+** (au-delà) | plus de 2 | il a fait bien plus : le jumeau sous-estime |

La note sert à **dire** (« vos 3 dernières aérations ont peu asséché la chambre »). Le **rapport** est gardé avec elle : c'est lui qui sert à **ajuster**.

**4. Rien n'est noté quand quelque chose d'autre a agi**, pendant le geste ou l'heure qui suit :
- une fenêtre de la pièce rouverte ;
- la VMC ou le purificateur qui change d'état ;
- une source d'humidité repérée : douche, cuisine (§ 9.1 ter).

Le chauffage ne compte pas : le jumeau le simule. Une personne qui respire non plus : son CO₂ ne fausse ni la chaleur ni l'humidité. Rouvrir pendant l'heure d'attente annule la note de la première aération, et la seconde aération est notée à part. On perd quelques gestes, mais ceux qui restent sont fiables.

Un geste trop court (moins de 10 min) ou un effet annoncé trop petit pour être lu (moins de 0,3 °C, moins de 0,5 g/m³ d'eau) n'est pas noté non plus.

**5. Les catégories : pièce × geste × sujet.**

| Exemple | Ce que la nuit ajuste |
|---|---|
| Chambre P · fenêtre · chaleur | l'effet des fenêtres sur la chaleur |
| Chambre P · fenêtre · humidité | l'effet des fenêtres sur l'eau |
| Chambre P · fenêtre · CO₂ / COV / particules | l'effet des fenêtres sur chaque air |
| Salle de bain · VMC rapide · humidité | la part du débit déclaré que la VMC donne vraiment |
| Salon · purificateur · particules | le débit d'air propre du purificateur |

Pas de catégorie selon la météo : le jumeau en tient déjà compte. Un soir doux et humide, il annonce un petit effet, et c'est à ce petit effet qu'on compare. Si une catégorie rate surtout dans un cas précis, par vent faible par exemple, on la découpera plus tard.

Les gestes faits de soi-même sont notés comme les gestes conseillés.

**6. Le bilan de la nuit**, pour chaque catégorie :
- au moins **3 notes** ;
- les plus récentes comptent davantage : une note perd la moitié de son poids en **15 jours**. Un joint changé, un meuble déplacé, et la pièce n'est plus la même ;
- on retient la **médiane** des rapports, pour qu'un cas bizarre ne fausse pas tout ;
- l'effet de la catégorie dans le jumeau est corrigé vers cette médiane, **au plus ×2 ou ÷2 par nuit**. Une médiane de 0,3 donne un effet ÷2 la première nuit, puis la suite au fil des nuits ;
- le **niveau de preuve** (§ 4.1) suit les mêmes notes : avéré, à essayer, démenti.

Le reste du jumeau (murs, soleil, chauffage) continue d'être recalibré sur toutes les mesures, comme avant (§ 8). Les deux ne se gênent pas : les notes règlent les gestes, le recalibrage règle la pièce au repos.

**7. Dans la journée.** La note est prise dès que l'heure est passée, sans attendre la nuit. Elle change tout de suite le **niveau de preuve** : 2 notes « − » ou « 0 » d'affilée, et le conseil passe en « À essayer ». Les **chiffres** du jumeau, eux, ne bougent que la nuit, en une fois et sur plusieurs notes.

La nuit recalcule chaque note avec l'historique, en suivant **la même règle** : 1 h après la fin, et rien quand quelque chose d'autre a agi. Une note écartée dans la journée ne revient pas la nuit.

**8. Où le lire.** « Ce que Hestia sait de votre maison » (§ 16.1 bis) montre, pour chaque catégorie, les dernières notes et la correction faite : « Fenêtre de la Chambre P sur l'humidité : 3 notes, 0 0 −, effet divisé par 2 cette nuit ».

**Valeurs validées par Frank le 4 novembre** : 1 h d'attente ; note + entre 0,5 et 2 ; 3 notes au moins ; poids divisé par 2 en 15 jours ; ×2 ou ÷2 au plus par nuit ; 2 notes ratées pour « À essayer ».

**Comment c'est fait (moteur 3.1.0, 4 novembre, labo)** — `advisor/notes.py` :
- **Dans la journée**, seules les aérations sont notées : la carte connaît les deux trajets du jumeau (avec et sans) dès l'ouverture. La VMC et le purificateur sont notés la nuit.
- **La nuit** recalcule les notes de tout l'historique avec le jumeau du moment. Seules ces notes recalculées corrigent les chiffres : une note plus ancienne que l'historique a été prise avec un jumeau d'avant, la réappliquer corrigerait deux fois. Elle compte encore pour la preuve.
- Une correction est gardée si la dernière journée n'est pas prévue plus de 5 % moins bien (la même règle qu'avant pour les fenêtres).
- **Preuve** : « avéré » quand la médiane des 10 dernières notes est entre la moitié et le double ; « à essayer » dès que les 2 dernières sont à 0 ou −, quoi qu'il y ait eu avant.
- **Chaleur** : une ouverture n'est notée que si son effet ressort de la dérive de la pièce (le poêle qui s'arrête, le soleil), comme avant (Salon, 1er novembre).
- Le débit réel de la VMC et du purificateur devient une part du débit déclaré (`boost_scale`, `purifier_scale`), corrigée par leurs notes.
- La commande `hestia_comfort/relearn` relance l'apprentissage à la demande (Atelier, labo).

## 16. Le panneau

Dans la 3.0 : le journal des conseils (§ 16.3), les encarts « Pour aller plus loin » (§ 16.2) et l'instantané rejouable (§ 16 bis.2). La page « Fiabilité » vient avec Weather 3.x ; la page « Atelier » complète et le capteur le plus utile, après la 3.0.

### 16.1 Page « Fiabilité des capteurs » (hub commun Weather + Confort)
- En tête : fiables · corrigés en partie · à vérifier.
- Une ligne par capteur : fiabilité, ce qui a été appris (« ombre de 14 h à 18 h »), utilisé comme (mesuré, corrigé, estimé).
- Détail : courbe mesure / référence, masque appris, date du dernier changement.
- Lien vers le bon encart « Pour aller plus loin » quand une déclaration aiderait.
- Une ligne **Position de la maison** : l'écart entre le soleil calculé et celui de l'intégration Soleil (§ 6.2 bis).
- Un encart **Soleil prévu et station** : les deux dernières heures, prévu et mesuré, la part que la station voit, et la correction appliquée ou la raison de n'en pas faire (§ 6.2 bis).

### 16.1 bis Page « Ce que Hestia sait de votre maison »
- Par pièce, chaque effet (§ 4.1) : son niveau de preuve, le nombre de gestes vus, l'effet prévu et l'effet mesuré.
- Ce qui manque pour qu'il monte d'un niveau (« encore 2 aérations par temps froid »).

### 16.2 Encart « Pour aller plus loin » dans chaque onglet de réglage
- En bas de l'onglet, replié par défaut, compteur « 2 sur 6 renseignés ».
- Chaque réglage dit ce qu'il débloque.
- Tout est facultatif.

| Onglet | Déclarations |
|---|---|
| Température et humidité | Surface, hauteur, murs dehors ou mitoyens, murs lourds ou légers |
| Fenêtres et portes | Vitrage, taille, angle exact, débord, masques |
| Air | Dormeurs, usage, porte habituellement fermée |
| Chauffage | Type, pièce chauffée par une autre |
| Équipements | Douche, cuisson, sèche-linge, ventilateur, et leur entité |
| Pièce et confort | Voisines, escalier, étage |
| Extérieur (Weather) | Hauteur et place de la station, obstacles connus |

### 16.3 Page « Journal des conseils »
Chaque conseil : quand, quoi, pourquoi, ce qui était prévu, ce qui s'est passé, l'avis donné. Filtre par pièce.

### 16.4 Le capteur le plus utile
Le panneau classe les capteurs à ajouter par utilité, avec une raison tirée de la maison (« Un capteur d'humidité dans la chambre P : la nuit, elle gagne sans doute plus de 10 points »).

## 16 bis. Débogage : trouver vite pourquoi un conseil est faux

But : devant un conseil qui ne va pas, savoir **en quelques minutes** d'où vient l'erreur, et la corriger au bon endroit (une mesure, le jumeau, un poids, un interdit, une phrase), sans ajouter d'exception.

### 16 bis.1 Chaque décision garde sa trace
Chaque décision porte une **trace** lisible, dans l'ordre des couches :
1. **Mesures** : chaque valeur avec son origine, sa fraîcheur et sa fiabilité ;
2. **Jumeau** : son état (air, murs, eau) et ses paramètres appris, avec leur incertitude ;
3. **Gestes** envisagés, et ceux retirés par un interdit (lequel, pourquoi) ;
4. **Scénarios** : pour chacun, le coût **détaillé terme par terme** (inconfort, humidité, air, kWh, dérangement) ;
5. **Règle de décision appliquée** : sécurité, séance, meilleur geste, stabilité, nuit ou vacances ;
6. **Ce qui ferait changer d'avis** : « avec 0,8 °C de plus dehors, le conseil serait “Laissez ouvert” » ;
7. **Phrase** produite et sa clé de traduction.

La trace dit ainsi **dans quelle couche** est l'erreur.

### 16 bis.2 Un instantané rejouable
- Chaque décision peut être exportée en **un seul fichier** (entrées, état du jumeau, paramètres, version du moteur).
- Ce fichier rejoué sur le banc redonne **exactement** la même décision. On peut alors modifier une entrée ou un poids et voir la nouvelle décision.
- **« Ce conseil ne va pas »** enregistre l'instantané automatiquement. Il suffit de le transmettre (à Claude ou à Codex) pour reproduire le cas.
- Le moteur est **déterministe** : mêmes entrées, même décision.

### 16 bis.3 Page « Atelier » dans le hub (mode expert)
Affichée seulement si le mode expert est activé dans les Réglages généraux :
- **Chronologie** d'une pièce : mesures, prévision du jumeau, conseils successifs, avec les moments où le conseil a changé et la raison ;
- **Ouvrir une décision** : sa trace complète (§ 16 bis.1), lisible, avec les scénarios côte à côte ;
- **Et si… ?** : modifier une mesure, un poids ou une préférence, et voir la décision qui en sortirait, sans rien enregistrer ;
- **Précision du jumeau** de chaque pièce : erreur à 1 h et 3 h, comparée à « rien ne change », pendant et hors des gestes ;
- **Bouton « Télécharger l'instantané »**.

### 16 bis.4 Côté code
- Journal Home Assistant par couche (`advisor.observe`, `advisor.physics`, `advisor.decide`…), activable séparément en mode debug.
- Les diagnostics téléchargeables de l'intégration contiennent les derniers instantanés et les situations signalées.
- Le banc a une commande unique : rejouer un instantané, ou rejouer un historique entre deux dates, et afficher les décisions qui ont changé entre deux versions du moteur.

## 17. Écosystème

| Brique | Ce que Confort reçoit | Ce que Confort donne |
|---|---|---|
| **Weather** (3.x : contrôle des mesures du dehors, Open-Meteo élargi, soleil par façade) | Le dehors contrôlé, ses prévisions, sa fiabilité | Le lien « Relié à Confort » |
| **Énergie** (après mi-novembre) | Plus tard : prix et heures pleines / creuses, pour le curseur économie | kWh perdus par geste, déperditions de la maison, journal |
| **Versatile Thermostat** | Consigne, préréglage, mode chaud ou froid (climatisation), fenêtre vue, pente | Proposition de pause du chauffage ou de la climatisation pendant l'aération (conseil seulement) |
| **Alarme (Alarmo)** | Nuit, absent, vacances | — |
| **LED** (onglet Notifications) | — | La décision du moteur, lue directement |
| **Automatisations des utilisateurs** | — | Entités stables (§ 20) |

## 18. Validation

### 18.0 Les données du banc

| Source | Profondeur | Ce qu'elle contient | Ce qu'elle permet |
|---|---|---|---|
| **HA principal, historique détaillé** | 10 jours | Tout : fenêtres, volets, chauffage minute par minute | Tests rapides de la semaine |
| **HA principal, statistiques horaires** | 11 à 24 mois | Températures, humidités, station, chauffe de chaque thermostat (pas les fenêtres ni les volets) | Apprendre le chauffage et le poêle sur un hiver entier ; tester d'une saison à l'autre |
| **HA de test** (`~/niak-ha-test`, port 8124) | 60 jours, depuis le 31 octobre 2026 | La maison recopiée en direct (Remote Home-Assistant), environ 265 entités archivées, fenêtres et volets compris | Juger le jumeau sur de vrais gestes ; faire tourner Confort 3.0 en développement sans toucher la maison |
| **Open-Meteo** | des années | Soleil, nuages, température, à la position arrondie | Remplacer le soleil de la station là où elle est à l'ombre |

Outils du banc : `niak-comfort/banc/.venv` (numpy, scipy, websockets), commandes `advisor.bench.twin_check` (10 jours) et `advisor.bench.season_check` (une année).

### 18.1 Banc de rejeu
- les jours détaillés de la vraie maison (10 jours du HA principal, jusqu'à 60 jours du HA de test), rejoués dans le moteur **et** dans la carte ;
- toutes les situations signalées par « Ce conseil ne va pas », gardées pour toujours ;
- **trois maisons** : minimale (une température par pièce), celle de Frank (inégale), très équipée ;
- des cas physiques simples (nuit froide, après-midi chaud, douche, pluie).

### 18.2 Propriétés vérifiées automatiquement
- **Continuité** : ±0,1 °C, ±1 % ou ±20 ppm ne retournent jamais le conseil, hors sécurité.
- **Bon sens** : un dehors plus froid ne rend jamais l'ouverture plus intéressante pour réchauffer ; plus chaud dehors ne la rend jamais plus intéressante pour rafraîchir.
- **Nuit** : jamais « Laissez ouvert » quand la pièce va passer sous sa plage avant le réveil.
- **Cohérence** : même phrase sur la carte, les entités et les LED.
- **Équipement** : ajouter un capteur ne retourne pas un conseil sans raison mesurée ; une pièce ne parle jamais d'un sujet qu'elle ne mesure ni n'estime.
- **Logement** : jamais deux conseils contraires sur un même air.

### 18.3 Indicateurs d'acceptation
| Indicateur | Objectif |
|---|---|
| Contradictions carte / entités | 0 |
| Changements de conseil hors sécurité | au plus 1 par pièce et par demi-heure |
| **Effet d'un geste** (ouvert / fermé, volet baissé / levé) : écart prévu entre les deux scénarios, comparé à l'écart mesuré | à 30 % près, sans biais — c'est l'indicateur principal : le moteur compare des gestes, une erreur commune aux deux scénarios ne le trompe pas |
| Jumeau à 1 h et 3 h (pièce mesurée) | bat « rien ne change » dans chaque pièce et chaque saison ; d'au moins 30 % pour les pièces dont fenêtres et volets sont connus. Une pièce à volets manuels peut faire moins bien l'été : elle parle alors au conditionnel |
| Jumeau pendant une fenêtre ouverte | bat « rien ne change » et le jumeau 2.1, sans biais |
| **Chaque sujet a son indicateur**, jugé de la même façon | humidité : erreur en points à 1 h et 3 h, et effet d'une aération ou de la VMC ; CO₂ : erreur en ppm et durée d'aération pour revenir sous le repère ; lumière : écart entre soleil calculé et lumière mesurée, par heure de jour |
| Situations signalées rejouées | 100 % respectées |
| Temps de calcul pour toute la maison | moins d'une seconde sur un Raspberry Pi 4 |

### 18.4 Dans le HA de test, pas dans la maison
Le Confort en service chez Frank ne reçoit aucun code en essai (décision du 31 octobre). Le nouveau moteur tourne d'abord dans le **HA de test**, qui reçoit la maison en direct : il conseille sur les vraies mesures, à côté du moteur 2.1 de la maison, sans rien changer chez elle. Chaque désaccord entre les deux est noté et revu avec Frank avant toute préversion.

## 19. Livraison

| Étape | Contenu | Pour les utilisateurs |
|---|---|---|
| 0 | Ce cahier validé ; HA de test relié à la maison (fait le 31 octobre) | rien |
| 1 | Jumeaux validés au banc, **chacun sur ses propres gestes** : chaleur (fait en partie), humidité et CO₂ (fenêtres, VMC), soleil calculé contre lumière mesurée (§ 18.3) | rien |
| 2 | Couches 6 à 10 (gestes, coût, décision, rédaction, journal) ; Confort 3.0 en développement dans le HA de test, à côté du moteur 2.1 de la maison ; journal des désaccords revu avec Frank | rien |
| 2 bis | Weather 3.x : contrôle du dehors, Open-Meteo élargi, soleil par façade, page Fiabilité | préversion Weather |
| 3 | Préversion Confort 3.0.0b1 : tous les sujets mesurés, gestes et conseils passifs (« Bon à savoir ») ; « Ce conseil ne va pas », « Cette nuit », journal, encarts « Pour aller plus loin » | préversion |
| 4 | Retours de la préversion, réglage des poids entre sujets | préversions 3.0.0bN |
| 5 | Retrait de l'ancien moteur et de la logique de la carte ; Confort 3.0.0 stable | stable |

Le correctif de la phrase de la carte pendant les 30 premières secondes (moteur 2.1) est laissé de côté, à la demande de Frank : le nouveau moteur le rend inutile.

Confort 3.0 est une version majeure : la décision change, les entités publiées restent (§ 20).

**Version et changelog du moteur (demandé par Frank, 4 novembre).** Le moteur a son propre numéro, à part de celui de Confort (`VERSION` dans `advisor/__init__.py`) :
- chaque changement du moteur monte son numéro : majeur pour une nouvelle génération (les jumeaux sont réappris), mineur pour une règle qui change des conseils, correctif pour un conseil qui était faux ;
- chaque version a sa ligne datée dans **CHANGELOG-MOTEUR.md**, à la racine du dépôt de Confort, en mots simples, classée Nouveautés / Améliorations / Corrections. Le détail technique va dans `docs/dev/MOTEUR-VERSIONS.md` ;
- la note de chaque version de Confort se termine par une section à part, **« Moteur de conseil 3.1.0 »**, qui résume les versions du moteur depuis la précédente version de Confort, ou dit « inchangé » ;
- le numéro est affiché dans « Versions et liens » et écrit dans chaque instantané, chaque ligne du journal, chaque avis et chaque rapport de nuit : on sait quelle version a donné quel conseil.

## 20. Compatibilité

- **Les LED ne dépendent pas des entités** : elles font partie de Confort (onglet Notifications) et lisent la décision directement.
- **Frank n'a pas d'automatisation sur ces entités**, mais d'autres utilisateurs peuvent en avoir. On garde donc les mêmes identifiants : Conseil, État, Couleur, Geste, Aération conseillée, Fenêtres à refermer, VMC conseillée, Trop humide, Humidité, Apprentissage, Chauffage observé, Couverture, et celles de « Mon logement ».
- **Raison** (diagnostic) : ses valeurs changent (geste × sujet × moment). Annoncé dans la note de version.
- **Nouvelles entités** : Moment, Gain, Confiance, Cette nuit.

### 20.1 Des entités faites pour les automatisations
Hestia ne commande rien (principe 10). Celui qui veut que le geste se fasse tout seul crée une automatisation à partir de ces entités :

| Entité (par pièce) | Type | Sert à |
|---|---|---|
| Aération conseillée | oui / non | lancer une VMC, prévenir |
| Fenêtres à refermer | oui / non, avec la liste des fenêtres | prévenir, lumière d'alerte |
| Volet à baisser · Volet à ouvrir | oui / non, avec les volets concernés (entités `cover`) | piloter les volets motorisés |
| VMC conseillée | oui / non, avec la vitesse | piloter la VMC |
| Climatisation conseillée | oui / non, avec la consigne proposée | régler le Versatile Thermostat |
| Ventilateur conseillé | oui / non | piloter un ventilateur relié |
| Chauffage à baisser pendant l'aération | oui / non | mettre le thermostat en pause |
| Conseil | texte, avec en attributs : geste, sujet, moment, gain, confiance, appareils concernés | tout le reste |
| Cette nuit | texte, avec la liste des points | notification du soir |

Pour le logement : **Mode vacances** (oui / non) et **Plan du logement** (texte, avec les gestes de chaque pièce en attributs).

**Évènement `hestia_comfort_advice`** : déclenché à chaque nouveau conseil, avec la pièce, le geste, le moment et les appareils concernés. C'est le déclencheur le plus simple pour une automatisation.

**Règles** :
- un « oui » ne change qu'avec la décision, donc avec la même stabilité que la carte (§ 11) : une automatisation ne fait pas monter et descendre un volet toutes les cinq minutes ;
- les appareils concernés sont donnés par leur identifiant Home Assistant, pour être utilisés tels quels dans une automatisation ;
- des **blueprints** d'exemple (volets, VMC, notification du soir) sont publiés sur GitHub, pas dans l'intégration.

**Données gardées au passage à la 3.0** : jumeau, apprentissage, habitudes et réponses Oui / Non, réglages des pièces.

## 21. Ce qu'on garde de l'actuel
Lecture et normalisation des capteurs (`sources.py`) · liens Weather · panneau et assistant des pièces · volumes « même air » · interdits de sécurité · ombre de la station apprise (`sunlight.py`, déplacée vers Weather) · données apprises du jumeau · habitudes · repères d'air (SEUILS.md) · tous les cas réels déjà rencontrés, convertis en tests.

## 22. Décisions

### 22.1 Prises le 31 octobre
1. **Notifications sur téléphone** : oui, dans l'onglet Notifications, **dans une version après la 3.0** (§ 13).
2. **Mode vacances** : oui, déduit de l'alarme (§ 11, point 8).
3. **Climatisation** : oui, lue par le Versatile Thermostat. **Ventilateurs** : conseil simple s'ils sont déclarés, suivis s'ils sont reliés, comme la VMC (§ 9.2).
4. **Préférences** : par pièce seulement, pas par personne.
5. **Pas de bouton « Appliquer »** : Hestia conseille seulement. À la place, des entités et un évènement pensés pour les automatisations (§ 20.1).
6. **Trois niveaux de preuve** (idée de Frank) : supposé, renforcé, avéré ; un geste ne monte au bandeau que sur un effet avéré, ou renforcé et très net (§ 4.1).
7. **Le soleil** : position calculée par le moteur ; heures et contrôle par l'intégration Soleil ; fenêtre pilotée par Adaptive Cover Pro ; `sun.sun` n'est plus lu ; quantité prévue par Open-Meteo, recoupée par la station de Weather (§ 6.2 bis).

Il ne reste aucune décision ouverte.

## 23. Relecture : ce qu'on avait oublié, ce qu'on peut améliorer… ou pas

### 23.1 Oubliés pendant nos échanges, ajoutés ici
- **Compatibilité des entités** (§ 20) : les automatisations d'autres utilisateurs peuvent dépendre des entités actuelles.
- **Démarrage à froid** (§ 8) : une nouvelle installation doit conseiller juste dès le premier jour, grâce aux déclarations et à l'historique déjà présent.
- **Puissance de calcul** (§ 18.3) : simuler une dizaine de gestes par pièce doit rester léger sur un petit boîtier.
- **Langues** (§ 14) : l'allemand arrive ; la rédaction doit être unique et traduisible.
- **Utilisateurs hors de France** : sans Météo-France ni Atmo, Open-Meteo prend le relais (via Weather).
- **Vie privée** : tout reste local ; seule la position arrondie part vers Open-Meteo.
- **Couleurs** : le cahier de Confort dit encore « vert = tout va bien », contraire à la règle actuelle.
- **Mesurer la qualité du moteur** (§ 18.3) : sans indicateurs chiffrés, « fiable » reste une impression.
- **Taille du journal** (§ 15) : 60 jours, plus les situations signalées.
- **Ajoutés à la relecture v0.8** : le périmètre de la 3.0 (§ 3 bis), qui manquait pour tenir le principe 13 ; les sources de données du banc et le HA de test (§ 18.0, § 18.4) ; un thermostat sans Versatile (§ 6.8) ; l'indicateur principal sur l'effet des gestes (§ 18.3) ; l'apprentissage par ajustement nocturne et la correction par l'écart récent (§ 8) ; le jumeau qui garde ce qu'il sait de chaque saison (§ 8).
- **Contradictions corrigées à la relecture v0.8** : numéro de version de l'en-tête ; déductions (fenêtre virtuelle, CO₂ estimé…) annoncées pour tout de suite alors que le principe 13 les reporte ; essai « en coulisses » dans la maison, refusé par Frank, remplacé par le HA de test ; objectif « 30 % dans chaque pièce » intenable pour les pièces à volets manuels en été ; pas de simulation (demi-heure / 5 minutes) ; correctif de la carte 2.1 encore prévu ; ligne « données gardées » rangée dans les règles des automatisations.

### 23.2 Améliorations possibles, plus tard
- **Reprendre l'apprentissage de Versatile** (`auto_tpi_learning`) quand il est actif : il connaît déjà l'inertie de chauffe de la pièce.
- **Apprendre d'une maison à l'autre** (avec l'accord des utilisateurs, plus tard) : des valeurs de départ par type de pièce et de bâti, tirées des jumeaux d'autres maisons.
- **Pièces témoins** : déduire jour par jour un volet manuel ou une porte intérieure en comparant deux pièces de même exposition, sur ce que leurs jumeaux n'expliquent pas (idée de Frank, vérifiée sur l'été 2026).
- **Masques solaires appris pour chaque fenêtre**, comme pour la station, à partir de la montée de température de la pièce.
- **Exposition d'un ouvrant proposée** à partir de l'heure où la pièce chauffe au soleil (piste du § 13 du cahier de Confort).
- **Bilan de saison** : « cet hiver, vos aérations ont coûté 40 kWh et évité 120 heures d'humidité ».
- **Plan sur la journée affiché** comme une frise (une fois la proactivité éprouvée).

### 23.3 À ne pas faire
- **IA générative**, écartée par Frank : non vérifiable, non rejouable, pas gratuite durablement.
- **Ajuster les poids sans bornes** : le moteur dériverait selon les humeurs ; les bornes restent visibles.
- **Multiplier les déclarations obligatoires** : tout reste facultatif, sinon on perd les débutants.
- **Simuler à la minute** : un pas de 5 minutes suffit, y compris pour une aération de 10 minutes (la demi-heure du jumeau 2.1 était trop grossière).
- **Remettre des exceptions dans la décision** pour un cas isolé : un cas qui ne va pas se règle par le modèle, le coût ou un test, jamais par une branche de plus.
- **Prévisions adaptées par la station** : abandonnées le 11 octobre ; le contrôle des mesures fait l'inverse et reste compatible avec ce choix.

## 24. Historique du document
- **v0.18 — 4 novembre 2026** : version et changelog du moteur, à part de ceux de Confort (§ 19) ; ce qui est fait des notes de gestes (§ 15.1).
- **v0.17 — 3 novembre 2026** : une note pour chaque geste, proposée par Frank (§ 15.1) : prise 1 h après la fin du geste, comparée à « sans le geste », rien de noté si autre chose a agi ; catégories pièce × geste × sujet ; bilan de la nuit par la médiane, corrige l'effet de chaque catégorie dans le jumeau, au plus ×2 ou ÷2 par nuit.
- **v0.16 — 1er novembre 2026** : « Ce conseil ne va pas » et suivi des conseils mis en œuvre dans le HA de test (§ 15). « Pas maintenant » met un geste de côté pendant un réglage du foyer, 1 h par défaut. Les situations signalées sont gardées sans limite, avec leur trace. Les poids ne bougent pas seuls : à décider plus tard. Volet relié : la chaleur qu'il garde fermé (norme EN ISO 10077-1), ses gestes comparés aux autres, « Baissez le volet ce soir » en « Bon à savoir », rien proposé quand Adaptive Cover Pro le pilote (§ 6.7 ter). Contrôles simples des capteurs des pièces — hors plage, saut, figé —, mesure douteuse laissée de côté et montrée (§ 7.3).
- **v0.15 — 31 octobre 2026** : le soleil prévu d'Open-Meteo recoupé par la station de Weather — ombre de la station apprise par position du soleil, nuages manqués des deux dernières heures (§ 6.2 bis, § 16.1) ; prévision de température lue dans Weather plutôt qu'Open-Meteo (point à 537 m).
- **v0.14 — 31 octobre 2026** : réglages du foyer (§ 10.3) — tout ce qui dépend du mode de vie est réglable, pour la maison et la pièce : sommeil, ouvrir la nuit, durées, délais, hors-gel, tolérance ; jamais d'ouverture pendant le sommeil par défaut (§ 11, point 6).
- **v0.13 — 31 octobre 2026** : règle de signification révisée après le rejeu de 10 jours (§ 10.2 bis, condition A : l'écart épargné pendant deux heures) ; le moins coûteux des gestes significatifs ; énergie seulement là où le chauffage est simulé ; jumeau du COV ; plage de chaque pièce lue dans Confort (§ 10.3).
- **v0.12 — 31 octobre 2026** : trois niveaux de preuve, supposé, renforcé, avéré, proposés par Frank (§ 4.1, § 14, § 15, § 22.1) ; le soleil, chaque source pour ce qu'elle sait : calcul, intégration Soleil, Adaptive Cover Pro, rayonnement (§ 6.2 bis).
- **v0.11 — 31 octobre 2026** : le logement compte aussi, parce qu'on y vit (§ 4) : moisissure, condensation, murs humides, gel, absence.
- **v0.10 — 31 octobre 2026** : bénéfices de la lumière (§ 6.7 quater) — bien-être, chaleur gratuite l'hiver, éclairage évité, excès à éviter — et ligne « + éclairage relié » au tableau du § 6.7, à la demande de Frank.
- **v0.9 — 31 octobre 2026** : remarques de Frank. Le moteur ne pense pas qu'en degrés : il ne s'occupe que du confort des personnes, sur tous ses sujets (chaleur, humidité, air, lumière) ; gestes et conseils passifs (« Bon à savoir », ligne qui défile, § 4, § 14) ; la lumière vient du soleil calculé (passif) ou d'un capteur (précis) (§ 6.7, § 6.7 quater) ; tous les sujets mesurés entrent dans la 3.0, chacun avec son jumeau et son indicateur (§ 3 bis, § 8, § 18.3, § 19). Les plantes, un simple exemple, ne sont pas un sujet du moteur.
- **v0.8 — 31 octobre 2026** : relecture d'ensemble demandée par Frank. Périmètre de la 3.0 (§ 3 bis) ; données et outils du banc, HA de test (§ 18.0, 18.4) ; indicateur principal sur l'effet des gestes (§ 18.3) ; apprentissage nocturne et correction par l'écart récent (§ 8) ; livraison refaite (§ 19) ; contradictions corrigées (§ 23.1).
- **v0.7 — 31 octobre 2026** : principe 13 « rester simple », à la demande de Frank : le moteur suit le tableau du § 6.7, chaque capteur enrichit ; portes intérieures et volets manuels réduits à l'habitude (apprise ou déclarée) et à des conseils conditionnels ; les déductions fines passent au § 23.2.
- **v0.6 — 31 octobre 2026** : chauffage de pièce et chauffage de maison (§ 6.7 bis), y compris les maisons de plain-pied, à la demande de Frank.
- **v0.5 — 31 octobre 2026** : ce qu'on lit dans Versatile Thermostat (§ 6.8), à la demande de Frank : la puissance du chauffage, entre autres, n'est plus à déclarer.
- **v0.4 — 31 octobre 2026** : débogage (§ 16 bis), demandé par Frank : trace par couche, instantané rejouable, page Atelier en mode expert, « Et si… ? ».
- **v0.3 — 31 octobre 2026** : jumeau « physique d'abord » (§ 8) et objectifs du jumeau relatifs à « rien ne change », mesurés aussi pendant les gestes (§ 18.3), après le test du jumeau 2.1 sur 10 jours réels. Conception technique dans [CONCEPTION-MOTEUR.md](CONCEPTION-MOTEUR.md).
- **v0.2 — 31 octobre 2026** : décisions de Frank. Notifications sur téléphone dans l'onglet Notifications, après la 3.0. Mode vacances déduit de l'alarme. Climatisation par le Versatile Thermostat, ventilateurs déclarés ou reliés, coût sur la température ressentie. Préférences par pièce seulement. Les LED lisent la décision directement ; pas d'automatisation chez Frank. Pas de bouton « Appliquer » : des entités et un évènement faits pour les automatisations (§ 20.1), avec des blueprints d'exemple sur GitHub.
- **v0.1 — 31 octobre 2026** : premier brouillon, rassemblant l'état des lieux du moteur 2.1 et les échanges du 31 octobre avec Frank (pas d'IA, repartir de zéro, confort par défaut avec kWh pour Énergie, nuit = gestes importants + « Cette nuit, pensez à… », maisons inégales, emprunts à Weather, données virtuelles, contrôle des mesures avec Open-Meteo, page Fiabilité, encart « Pour aller plus loin »).
