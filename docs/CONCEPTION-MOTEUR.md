# Conception technique — Moteur de conseil de Hestia Confort 3.0

Version 0.1 — 31 octobre 2026. Accompagne le [cahier du moteur](CAHIER-MOTEUR.md) : le cahier dit **quoi**, ce document dit **comment**.

## 1. Ce que le test du jumeau actuel a appris

Avant de concevoir, on a vérifié le socle : le jumeau actuel (`engine/twin.py`), entraîné sur 7 jours réels de la maison (21–28 octobre), puis testé sur les 3 jours suivants, sans rien savoir de l'avenir sauf la météo et les fenêtres réelles.

| Pièce | Jumeau, 3 h | « Rien ne change », 3 h | Demi-heures fenêtre ouverte vues (7 j) | Fenêtre ouverte : erreur à 1 h |
|---|---|---|---|---|
| Chambre P | 0,54 °C | 0,67 °C | 31 | 0,21 °C (2 cas) |
| Chambre A | 0,21 °C | 0,39 °C | 4 | aucun cas pour vérifier |
| Chambre M | 0,42 °C | 0,78 °C | 2 | aucun cas pour vérifier |
| Chambre AL | 0,42 °C | **0,37 °C** | 20 | 0,52 °C, prévue trop froide de 0,36 °C |
| Salon | 0,41 °C | 0,52 °C | 55 | 0,23 °C |

Script : [`banc/jumeau_test.py`](../banc/jumeau_test.py), à lancer depuis `custom_components/hestia_comfort` avec un historique téléchargé de Home Assistant. En service, le jumeau garde jusqu'à 30 jours : il fait un peu mieux que ce test, mais les conclusions tiennent.

**Ce qu'on en tire :**
1. **Le jumeau bat à peine l'immobilité**, et pas partout. « Moins de 0,5 °C à 3 h » n'est pas un bon objectif : ne rien prévoir du tout l'atteint déjà dans quatre pièces sur cinq. L'objectif doit être **relatif** (battre l'immobilité) et porter **sur les gestes**.
2. **On n'apprend pas l'effet d'un geste rare par simple régression.** Deux ouvertures en une semaine ne suffisent pas. Or c'est précisément ce que le moteur doit comparer.
3. **La demi-heure est trop grossière** pour une aération de 10 minutes.
4. **La masse des murs n'est pas identifiée** (coefficient nul dans quatre pièces sur cinq) : la régression ne la voit pas sans aide.
5. **Le chauffage est lu en « marche / arrêt »**, alors que le Versatile Thermostat donne sa puissance en pour cent, minute par minute.

**Décision de conception qui en découle : un jumeau « physique d'abord ».** Ses paramètres ont un sens physique (volume, vitrage, isolation, débit d'air d'une fenêtre). Ils partent de valeurs plausibles tirées des déclarations et des lois connues, et l'apprentissage les **ajuste** au lieu de les **deviner**. Une pièce qui n'a jamais ouvert sa fenêtre sait quand même, à peu près, ce qu'une ouverture lui ferait.

### 1 bis. Premier jumeau physique (31 octobre, étape 2 en cours)

Ajusté sur 7 jours, testé sur les 3 suivants, sans aucune déclaration (volumes, tailles de fenêtres, puissances inconnus), soleil d'Open-Meteo. Commande : `python -m advisor.bench.twin_check historique.json 7 open-meteo.json`.

| Pièce | Physique, 3 h | 2.1, 3 h | Rien ne change | Gain | Fenêtre ouverte, 1 h |
|---|---|---|---|---|---|
| Chambre P | 0,52 °C | 0,54 | 0,75 | 31 % | aucun cas |
| Chambre A | 0,22 °C | 0,22 | 0,39 | 42 % | aucun cas |
| Chambre M | 0,38 °C | 0,43 | 0,77 | 50 % | aucun cas |
| Chambre AL | 0,37 °C | 0,42 | 0,36 | **0 %** | 0,42 °C, biais −0,26 (2.1 : 0,52, −0,37) |
| Salon | 0,37 °C | 0,43 | 0,52 | 28 % | 0,29 °C, biais +0,02 (2.1 : 0,23, 0,00) |

**Où on en est** : à 3 h, le jumeau physique fait mieux que le 2.1 en moyenne (0,37 contre 0,41 °C) et que « rien ne change » dans quatre pièces sur cinq. **L'objectif n'est pas encore atteint** : la Chambre AL ne gagne rien, le 2.1 reste meilleur à 1 h, et certaines valeurs ajustées ne sont pas plausibles (chauffage de 5 kW dans la Chambre A, qui n'a chauffé qu'une heure en 10 jours). Pistes, dans l'ordre :
1. **les déclarations** (surface, tailles des fenêtres, puissance des radiateurs) pour fixer ce que 10 jours d'automne ne montrent pas ;
2. **30 jours** d'apprentissage au lieu de 7 ;
3. **le soleil par façade** (exposition des fenêtres) au lieu du soleil horizontal ;
4. **l'échange avec les pièces voisines** (portes de chambre ouvertes sur le palier).

**Avec les déclarations de Frank** (surfaces du plan, tailles des fenêtres, puissances lues dans Versatile, tenues presque fixes) : Chambre P mieux (0,46 °C à 3 h au lieu de 0,51), Chambres A et M à peu près pareil, **Salon (0,42) et Chambre AL (0,39) moins bien**. Lecture : avec la vraie puissance du poêle (8,5 kW), le Salon seul ne peut pas absorber toute cette chaleur ; elle monte par le hall et l'escalier vers l'étage, et la Chambre AL en reçoit sans que le jumeau le sache. **Prochaine pièce du modèle : les échanges entre pièces** (hall et escalier, portes des chambres), puis 30 jours d'historique. Les déclarations n'ont pas rendu le jumeau meilleur partout, mais elles ont rendu ses valeurs plausibles, ce qui a fait apparaître ce qui manque.

**Avec le poêle en chauffage de maison** (sa chaleur répartie entre toutes les pièces, part apprise) : séjour 0,36 °C à 3 h (au lieu de 0,42), Chambre M 0,36 (au lieu de 0,41), Chambres A et AL à peu près pareil, Chambre P 0,55 (au lieu de 0,46). Moyenne 0,38 °C, contre 0,41 pour le jumeau 2.1. **La Chambre AL ne bat toujours pas « rien ne change »**, et sur trois jours de test, des écarts de quelques centièmes ne sont pas significatifs : il faut des semaines de test. Les états des fenêtres et du chauffage ne sont gardés que 10 jours par Home Assistant ; seul le moteur en coulisses, en enregistrant ce dont il a besoin, permettra un banc sur un mois ou une saison.

**Sur une année, statistiques horaires de Home Assistant** (`advisor/bench/season_check.py`, 31 octobre) : ajusté sur l'hiver 2025-26 (19 déc. – 31 mars), testé au printemps, en été et cet automne, sans fenêtres (absentes des statistiques). Erreur à 3 h, et « rien ne change » :

| Pièce | Hiver (appris) | Printemps | Été | Automne |
|---|---|---|---|---|
| Chambre P | 0,59 (0,77) | 0,64 (0,66) | **1,11 (0,56)** | 0,71 (0,41) |
| Chambre A | 0,68 (0,80) | 0,35 (0,34) | 0,42 (0,54) | 0,19 (0,28) |
| Chambre M | 0,81 (1,10) | 0,52 (0,58) | 0,66 (0,72) | 0,36 (0,52) |
| Chambre AL | 0,77 (0,88) | 0,49 (0,49) | 0,47 (0,61) | 0,50 (0,43) |
| Salon | 0,77 (1,09) | 0,46 (0,56) | 0,51 (0,52) | 0,44 (0,34) |

Lecture :
1. **En hiver, le jumeau bat « rien ne change » de 12 à 29 %** : le chauffage et le poêle sont bien appris (puissances retrouvées à 3 % près, part du poêle au séjour 23 %).
2. **Ce qui est appris l'hiver ne vaut pas l'été** : la Chambre P (volet piloté par Adaptive Cover Pro) est deux fois pire que « rien ne change » en été. Les fenêtres ouvertes la nuit et les volets, absents des données, font la saison. **Un jumeau sans fenêtres ni volets ne peut pas être juste toute l'année.**
3. **À 1 h, le jumeau fait moins bien que « rien ne change » partout** : sur des moyennes horaires lissées, et comme sur le banc de 10 jours, il prend du retard sur les variations rapides. Piste : corriger chaque prévision par l'écart constaté la dernière heure (l'erreur d'un jumeau persiste d'heure en heure).
4. **Ce que le moteur doit vraiment bien prévoir, c'est la différence entre deux gestes** (ouvert / fermé, volet baissé / levé), pas la température exacte : une erreur commune aux deux scénarios s'annule dans la comparaison. Le prochain banc mesurera cela, sur les fenêtres et volets que le HA de test enregistre depuis le 31 octobre.

**Correction par l'écart récent** (31 octobre, 10 jours détaillés, appris 7 jours, testé 3) : l'écart de la dernière heure entre prévu et mesuré est ajouté à la prévision suivante, en s'estompant sur 2 h (`fit.py`, `DEFAULT_RECENT = "offset"`).

| Pièce | 1 h sans → avec | « Rien ne change », 1 h | 3 h sans → avec | Fenêtre ouverte, 1 h, sans → avec |
|---|---|---|---|---|
| Chambre P | 0,38 → 0,34 | 0,35 | 0,55 → 0,57 | — |
| Chambre A | 0,13 → 0,13 | 0,16 | 0,24 → 0,27 | — |
| Chambre M | 0,24 → 0,22 | 0,29 | 0,36 → 0,38 | — |
| Chambre AL | 0,23 → **0,15** | 0,15 | 0,37 → 0,35 | 0,42 → **0,29** (biais −0,26 → −0,14) |
| Salon | 0,29 → **0,20** | 0,27 | 0,36 → 0,34 | 0,26 → **0,18** (le jumeau 2.1 : 0,23) |

À 1 h, le jumeau rattrape ou dépasse « rien ne change » dans toutes les pièces sauf la Chambre P (volet piloté, position pas encore utilisée), et fait **mieux que le jumeau 2.1 avec une fenêtre ouverte au séjour**. À 3 h, l'effet est neutre. La variante « pente » (l'écart pris comme une dérive) fait à peu près pareil à 1 h, moins bien avec une fenêtre ouverte : écartée. Pas encore testé sur l'année entière (statistiques horaires).

**Effet des gestes et volet de la Chambre P** (31 octobre, 10 jours détaillés, `fit.gestures`) :

| Pièce | Gestes | Mesuré en 1 h | Prévu en 1 h | Effet propre du geste selon le jumeau |
|---|---|---|---|---|
| Salon, fenêtres | 33 | −0,13 °C | −0,25 °C | −0,17 °C |
| Chambre P, fenêtre | 7 | −0,26 °C | −0,17 °C | −0,18 °C |
| Chambre AL, fenêtre | 4 | −0,15 °C | −0,22 °C | −0,20 °C |
| Chambre A, fenêtre | 2 | −0,18 °C | −0,54 °C | −0,13 °C |
| Chambre M, fenêtre | 1 | −0,20 °C | −0,49 °C | −0,11 °C |
| Chambre P, volet relié | 50 | +0,13 °C | −0,10 °C | 0,00 °C |

Lecture : le jumeau donne **le bon ordre de grandeur** de l'effet propre d'une aération (−0,1 à −0,2 °C en 1 h pour ces aérations courtes d'automne doux, mesuré −0,13 à −0,26 °C). Mais ces effets sont petits devant le reste de l'erreur (0,3 à 0,4 °C pendant un geste) : avec si peu de gestes et une saison douce, on ne peut pas encore valider l'objectif « à 30 % près ». Le volet de la Chambre P ne change rien fin octobre : le soleil y entre peu à cette saison (part de soleil apprise faible), son effet viendra au printemps et en été. **Les données d'hiver et d'été du HA de test**, avec des aérations plus longues et des écarts de température plus grands, sont nécessaires pour juger l'effet des gestes.

**Jumeaux de l'eau (humidité) et de l'air (CO₂)** (31 octobre, `advisor/physics/water.py`, `air.py`, banc `advisor/bench/air_check.py` ; appris 7 jours, testés 3, avec la correction par l'écart récent) :

| Pièce | Humidité 1 h | Humidité 3 h | Aérations : mesuré / prévu en 1 h |
|---|---|---|---|
| Chambre P | 2,1 (2,6) | **3,1 (5,0)** | aucune dans les jours de test |
| Chambre A | 0,7 (0,7) | 1,4 (1,4) | aucune |
| Chambre M | 0,7 (0,8) | 1,5 (1,8) | aucune |
| Chambre AL | 0,9 (0,9) | 1,9 (1,8) | 1 : −1,8 / −1,6 points |
| Salon | **1,0 (1,5)** | **1,7 (2,4)** | **12 : −3,0 / −2,8 points** |
| Salon, CO₂ | 76 (76) ppm | **94 (115) ppm** | **12 : −171 / −139 ppm** |

(en points d'humidité ou en ppm ; « rien ne change » entre parenthèses)

Lecture :
1. **Sur l'effet des aérations, l'indicateur principal, l'humidité et le CO₂ tiennent l'objectif** au séjour : −2,8 prévus pour −3,0 mesurés (à 7 % près), −139 pour −171 ppm (à 19 % près). C'est mieux que la chaleur, dont l'effet d'automne est noyé dans le reste.
2. Le jumeau de l'humidité bat « rien ne change » de 17 à 38 % à 3 h dans trois pièces sur cinq, et fait jeu égal dans les deux autres (chambres A et AL, très stables).
3. **La loi des fenêtres surestime le débit** : multiplicateurs appris de 0,02 à 0,4 (fenêtres entrouvertes ou oscillo-battantes, capteur loin de la fenêtre, aérations brèves). Le séjour donne ×0,38 par l'humidité, ×0,11 par le CO₂, ×0,73 par la chaleur. **Essai d'un débit unique, appris par le CO₂ et prêté aux autres** (`air_check --debit-partage`) : l'humidité se dégrade (aérations prévues −1,6 point au lieu de −3,0 mesurés ; avec son propre débit, −2,8), la chaleur ne change presque pas. Dans un séjour de 44 m², les capteurs ne sont pas au même endroit et ne voient pas le même courant d'air ; l'humidité baisse aussi par la réserve d'eau des murs. **Décision : chaque jumeau apprend l'effet des fenêtres tel que son capteur le voit** (principe 13, rester simple).
4. Le premier passage avait laissé les réglages à leur valeur de départ : la recherche partait avec des pas trop petits. Corrigé (pas de départ explicites, logarithmes bornés).

**Jumeau des particules fines (PM2.5)** (31 octobre, `air.particles_step`, séjour, capteur IKEA ; valeurs à 999 écartées comme pannes) : erreur à 1 h **5,2 µg/m³** (« rien ne change » 7,2), à 3 h **4,1** (7,2) ; **11 aérations : −43,9 µg/m³ mesurés, −48,0 prévus en 1 h (à 9 % près)**. Les aérations du séjour suivent souvent la cuisine : le jumeau voit bien l'air du dehors chasser les particules. Le purificateur n'a pas d'historique sur ces 10 jours (le HA de test l'enregistre désormais) : son effet n'est pas encore appris.

**Première décision** (31 octobre, `advisor/decide.py`, 7 tests) : gestes possibles, simulation sur les jumeaux de la chaleur, de l'eau, du CO₂ et des particules, coût terme par terme, gain minimal, une seule hystérésis sur le coût, interdits de sécurité. La nuit du 30 octobre (séjour à 20,6 °C, porte-fenêtre ouverte, 1 h, 12,8 °C dehors) donne **« Refermez »** : ouverte jusqu'à 7 h, 16,4 °C et 6,3 kWh de chaleur perdue ; fermée, 19,3 °C. À 21,5 °C, même conseil : plus de falaise. **Pas encore simulé** : la réponse du chauffage (régulation de Versatile, § 7 du cahier, couche 5) — le scénario « fermé » montre la pièce sans chauffage.

Le banc a aussi confirmé le défaut de la station (§ 7.3 du cahier) : par ciel dégagé, elle ne voit que 20 à 30 % du soleil d'Open-Meteo en début de matinée et en fin d'après-midi, et 65 à 70 % au mieux vers 13 h.

**Tendance, soleil par la fenêtre ouverte, énergie** (31 octobre au soir, après les premiers conseils du HA de test) :

1. **La tendance mesurée** : quand l'état des fenêtres n'a pas changé depuis une heure, l'écart de la dernière heure entre le jumeau et la mesure se prolonge. Reporté comme un décalage qui s'estompe sur 2 h, il réduit l'erreur à 1 h d'un cinquième à deux cinquièmes (fermée : Chambre P 0,43 → 0,34, Salon 0,30 → 0,19 ; ouverte : Chambre AL 0,38 → 0,29, Salon 0,23 → 0,13). Reporté comme une pente, il ne fait pas mieux. **Décision : `Now.missed`, porté par tous les scénarios** ; le HA de test garde la dernière heure de chaque pièce pour le mesurer (attribut `ecart_1h`).
2. **Le soleil de chaque scénario** : un scénario « fermé » prend le soleil derrière la vitre, un scénario « tout ouvert » le soleil par l'ouvrant (`Inputs.facade_shut`, `facade_all`). Essai de compter en entier le soleil d'un ouvrant, sans la part apprise de la vitre : la Chambre P du 31 octobre (fenêtre ouest ouverte de 13 h 52 à 16 h 07, +1,4 °C en 2 h, le jumeau en voyait 0,9 de moins) aurait été suivie deux fois mieux, mais sur 10 jours la Chambre AL fenêtre ouverte se dégrade (0,29 → 0,37 °C à 1 h) et rien ne s'améliore ailleurs. **Écarté pour l'instant** : trop peu d'après-midi ensoleillés fenêtre ouverte pour trancher ; le HA de test les enregistre, l'indicateur des gestes jugera.
3. **L'énergie d'un geste** est ce que le chauffage simulé dépense (`Path.spent`) : la chaleur qu'une fenêtre laisse sortir d'une pièce que le thermostat ne chaufferait pas ne coûte rien. Elle rendait « significatif » un « Refermez, vous gardez 0,6 °C ». Un geste gagné sur l'énergie seule le dit en kWh.
4. **« Rien à faire » dit vrai** : « la pièce restera dans votre plage » seulement si c'est le cas ; sinon « Ouverte ou fermée : 19,5 °C à 18 h » ou « Aucun geste ne ferait vraiment mieux : 18,9 °C à 17 h ».

**Niveaux de preuve et « Bon à savoir »** (cahier v0.12, § 4.1 et § 6.2 bis ; `advisor/proof.py`, `advisor/knowing.py`) : sur les 10 jours, l'effet d'une aération est **avéré** pour la chaleur et l'humidité dans la Chambre P (7 gestes : −0,25 °C prévu, −0,26 mesuré), la Chambre AL (4) et le salon (33, avec le CO₂ et les particules) ; **supposé** dans les chambres A (2 gestes) et M (1). Le soleil de chaque fenêtre est calculé (heures où il la frappe à moins de 75° et au-dessus de 5°), remplacé par les heures d'Adaptive Cover Pro quand il pilote la fenêtre (Chambre P : 12 h 50 – 16 h 35 le 31 octobre, calcul 13 h 15 – 17 h). En passant, la même faille que l'énergie : sans thermostat simulé, la chaleur perdue par une fenêtre se voit déjà dans le refroidissement de la pièce ; l'énergie n'est plus un sujet que là où le chauffage est simulé.

**Apprentissage de chaque nuit** (`advisor/nightly.py`, 31 octobre) : chaque jumeau réapprend sa pièce sur les jours enregistrés (3 au moins, 60 au plus), **en partant de lui-même** (une nuit retouche, elle ne recommence pas), et ne garde le nouveau que s'il prévoit mieux les dernières 24 h, tenues à l'écart de la recherche. Les gestes vus sont datés et gardés 60 jours pour les niveaux de preuve. Pas de SciPy dans Home Assistant : la simulation de l'humidité, du CO₂ et des particules est sortie du banc (`physics/airfit.py`) et cherche avec la méthode du jumeau de la chaleur. Rejoué sur les 10 jours de la maison : 5 minutes pour les 5 pièces ; seules les chaleurs des chambres P (erreur à 3 h 0,370 → 0,358 °C) et M sont gardées, les autres jumeaux ne font pas mieux que ceux déjà appris sur ces jours — c'est attendu. Dans le HA de test : à 3 h 30, et 10 minutes après un démarrage si le dernier apprentissage a plus d'un jour ; sauvegarde des 7 derniers jumeaux, compte rendu dans `apprentissage.jsonl` et `sensor.conseil_3_apprentissage`.

Rejeu de la Chambre P le 31 octobre après-midi (météo réelle) : le moteur dit « Rien à faire, ouverte ou fermée » tout l'après-midi, au lieu du « Refermez, 0,5 °C » du HA de test à 15 h 24. Il sous-estime encore ce que la fenêtre ouverte au soleil apporte à cette chambre (+0,1 °C prévu à l'ouverture, +1,4 °C mesuré) : c'est ce que l'apprentissage de chaque nuit devra corriger.

## 2. Organisation du code

Un nouveau paquet, **sans aucune dépendance à Home Assistant**, pour être testé et rejoué hors de la maison :

```
custom_components/hestia_comfort/advisor/
  observe.py      couche 1  Observation : valeur, unité, heure, origine, fiabilité ; anti-rebond unique
  quality.py      couche 2  fiabilité des capteurs des pièces
  house.py        couche 3  Maison : pièces, volumes d'air, liens, façades ; grandeurs dérivées
  physics/
    thermal.py    couche 4  chaleur : air + murs
    water.py                eau : air + réserve des matériaux
    air.py                  CO₂ et COV
    vents.py                débit d'air d'une fenêtre, d'un air traversant, de la VMC
    fit.py                  ajustement sur la prévision à 1 h et 3 h (§ 6.5)
  inputs.py       couche 5  chronologie des prochaines heures : météo, occupation, consignes
  gestures.py     couche 6  catalogue des gestes, interdits de sécurité
  simulate.py     couche 7  simulation d'un scénario
  cost.py                   coût d'un scénario
  decide.py       couche 8  choix, stabilité, séances, nuit, vacances, plan du logement
  words/          couche 9  phrases fr, en, de
  journal.py      couche 10 journal des décisions, situations signalées
  bench/                    rejeu d'un historique, propriétés, trois maisons
```

`coordinator.py` reste l'adaptateur Home Assistant : il lit les entités, appelle `advisor`, publie les entités et la vue de la carte. Pendant la phase en coulisses, il appelle **les deux moteurs** et ne publie que l'ancien.

## 3. Couche 1 — Observations

```python
@dataclass(frozen=True)
class Observation:
    value: float | bool | None
    unit: str | None
    at: datetime            # heure de la mesure
    origin: str             # measured | weather | declared | computed | learned | estimated
    reliability: float      # 0 à 1, fixé par la couche 2
    source: str | None      # entité Home Assistant
```

- Reprend `engine/sources.py` (pas de valeur de remplacement, expiration des seules mesures).
- **L'anti-rebond est fait ici, une seule fois.** La carte reçoit l'état des fenêtres **de cette couche**, jamais du contact brut. Plus de « deux cerveaux ».

## 4. Couche 2 — Fiabilité des capteurs des pièces

Une note de 0 à 1 par capteur, à partir de :
- **figé** : aucune variation pendant que les voisins bougent ;
- **sauts** : variation impossible physiquement en une minute ;
- **voisins** : écart persistant avec les autres pièces du même air ;
- **causes apprises** : pic qui suit le soleil sur la façade ou la chauffe (capteur mal placé) ;
- **jumeau** : écart persistant entre prévu et mesuré, sans cause connue.

Le dehors arrive de Weather avec sa propre note (Weather 3.x). En attendant, Confort applique au dehors les mêmes contrôles simples (figé, sauts) et garde l'ombre de la station apprise par `sunlight.py`.

Une mesure sous 0,5 est remplacée par la prévision du jumeau, marquée « estimé ».

## 5. Couche 3 — La maison

```python
@dataclass
class Room:
    id: str; name: str
    floor: int | None
    volume_m3: float            # déclaré, sinon 2,5 m × surface, sinon 40 m³
    envelope: Envelope          # murs dehors, vitrages, isolation (déclarés ou ordinaires)
    openings: list[Opening]     # exposition, taille, type, abri, volet, masques
    devices: Devices            # thermostat, VMC, ventilateur, purificateur, volets reliés
    uses: set[str]              # chambre, cuisine, salle de bain, dormeurs…

@dataclass
class House:
    rooms: dict[str, Room]
    volumes: list[set[str]]     # pièces de même air (Salon · Cuisine)
    links: list[Link]           # portes intérieures, escalier : coefficient d'échange appris
```

Grandeurs dérivées, calculées une fois ici : humidité absolue, point de rosée, coin de mur le plus froid (facteur 0,7, comme aujourd'hui), buée sur le vitrage, soleil par fenêtre (`on_facades` repris, avec masques).

## 6. Couche 4 — Le jumeau physique

### 6.1 Chaleur : deux réservoirs par pièce

```
Ca · dTa/dt = H_env·(Te − Ta) + H_am·(Tm − Ta) + H_v·(Te − Ta) + Σ H_ij·(Tj − Ta) + P_chauffe + P_soleil,air + P_occupants
Cm · dTm/dt = H_am·(Ta − Tm) + P_soleil,murs
```

| Symbole | Sens | Valeur de départ |
|---|---|---|
| Ca | chaleur de l'air et des meubles | 1,2 × volume × 3 (kJ/K) |
| Cm | chaleur des murs | selon murs lourds / légers déclarés × surface |
| H_env | pertes par les murs et vitrages | selon vitrage, isolation, surfaces donnant dehors |
| H_am | échange air / murs | ~8 W/m²K × surface intérieure |
| H_v | air qui entre | 0,34 × débit (m³/h) : fuites + fenêtres + VMC (§ 6.4) |
| H_ij | échange avec une pièce voisine | appris, départ selon le lien déclaré |
| P_chauffe | chauffage de la pièce | `power_percent` du Versatile Thermostat × `device_power` |
| part × P_maison | chauffage de maison (poêle, cheminée) | sa puissance réelle × la part qui arrive dans cette pièce, apprise (cahier § 6.7 bis) |
| P_soleil | soleil par fenêtre | facteur de vitrage × surface vitrée × W/m² sur la façade, partagé entre air et murs |
| P_occupants | personnes | ~80 W par personne présente |

### 6.2 Eau : l'air et la réserve des matériaux

```
V · dW/dt = Q·(We − W) + G_sources + k_b·(W_b − W)
dW_b/dt = k_b'·(W − W_b)
```
La **réserve** (murs, tissus, meubles) explique le « rebond » après une aération : l'air sèche vite, puis les matériaux rendent leur eau. C'est ce que `learning.py` modélise aujourd'hui à part ; ici, c'est dans le jumeau. Sources : ~40 g/h par dormeur, douche, cuisson (déduites des équipements, § 6.6 du cahier).

### 6.3 Air : CO₂ et COV
```
V · dC/dt = Q·(Ce − C) + n_personnes × 18 L/h
```
**Le CO₂ mesure le débit d'air.** Chaque aération dans une pièce équipée (le Salon) donne une mesure directe du débit Q de ses fenêtres. Ce débit se transpose aux autres pièces par la loi du § 6.4, proportionnellement à la taille de leurs fenêtres.

### 6.4 Débit d'air d'une fenêtre (`vents.py`)
Formules classiques de ventilation naturelle :
- **tirage thermique** (une seule façade) : Q = Cd · A/3 · √(g · H · |ΔT| / T) ;
- **vent** : Q = 0,025 · A · v ;
- **air traversant** (façades opposées) : bien plus fort, selon la différence de pression au vent / sous le vent ;
- **effet cheminée** entre étages : hauteur entre ouvertures basses et hautes.

A et H viennent des déclarations (taille, type : un vasistas compte peu), sinon de valeurs ordinaires par type. Un **multiplicateur appris par fenêtre** corrige la formule (rideau, ouverture partielle, oscillo-battant).

### 6.5 Apprentissage (`fit.py`)
- **Ajustement sur la prévision** : sur les jours passés, depuis chaque demi-heure, le jumeau prévoit 1 h et 3 h avec la météo, le chauffage et les fenêtres réels ; les paramètres sont déplacés jusqu'à ce que ces prévisions collent au mieux à ce qui a été mesuré (recherche de Nelder-Mead, sans bibliothèque). Les murs sont suivis à partir de l'air mesuré.
- **Le filtre de Kalman a été essayé et écarté** (banc du 31 octobre) : appris à 5 minutes sur des capteurs qui avancent par pas de 0,1 °C, il apprend surtout le bruit, et prévoit moins bien à 3 h que « rien ne change ».
- **Rappel vers les valeurs ordinaires** : un paramètre que les jours n'ont pas montré (un chauffage qui a peu tourné, une fenêtre jamais ouverte) reste plausible.
- **Quand** : une fois par nuit, en tâche de fond, sur les 30 derniers jours (environ une minute pour cinq pièces sur un PC, quelques minutes sur un Raspberry Pi).
- **Confiance** : l'erreur mesurée de chaque pièce, à 1 h et 3 h, pendant et hors des gestes (banc). Elle remplace l'incertitude du filtre.
- **Emprunt à la maison** : une pièce peu observée garde des paramètres proches de ceux de la maison (même isolation, même vitrage), avec une incertitude plus large.
- **Démarrage** : à l'installation, le filtre est rejoué sur l'historique déjà présent dans Home Assistant (10 jours détaillés).
- **Pas de calcul** : 5 minutes. Coût : quelques dizaines d'opérations par pièce, négligeable.

Le jumeau actuel (`twin.py`) reste pendant la phase en coulisses, pour comparaison et pour la reprise de ses données.

## 7. Couche 5 — Les prochaines heures (`inputs.py`)

Une chronologie au pas de 5 minutes, jusqu'à demain midi :
- **météo** : prévisions horaires de Weather (température, humidité, vent, nuages), interpolées ; soleil par façade ;
- **occupation** : présence, sommeil et absences appris (alarme, téléphones, lumières), heure de lever et de coucher ;
- **chauffage et climatisation** : simulés comme le Versatile Thermostat les pilote (consigne, préréglage, régulation proportionnelle) ;
- **séances en cours** : une aération commencée et sa fin prévue.

## 8. Couche 6 — Gestes et interdits (`gestures.py`)

```python
@dataclass(frozen=True)
class Gesture:
    kind: str                 # nothing | close | open | open_until | cross | shutter | vmc | fan | purifier | heat | cool | pause_heating
    targets: tuple[str, ...]  # entités ou ouvrants concernés
    minutes: int | None       # durée, pour une ouverture
    until: datetime | None
```

- On n'énumère que les gestes possibles dans la pièce ou le volume.
- Les **interdits de sécurité** (§ 9.3 du cahier) retirent des gestes, ou en imposent un. Ils sont repris de `assessment.py`, testés, et sont la seule partie en règles.

## 9. Couche 7 — Simulation et coût

### 9.1 Simulation
Pour chaque geste : on applique le geste à la chronologie (fenêtre ouverte 10 min, volet baissé…), on fait tourner le jumeau sur l'horizon, et on obtient les courbes de température, d'humidité, de CO₂, ainsi que l'énergie de chauffe ou de froid.

Budget : 10 à 15 gestes × 6 volumes × 120 pas (10 h de nuit) ≈ 20 000 pas, soit quelques millisecondes.

### 9.2 Coût
```
coût = Σ_t [ w_T · écart_plage(t) + w_H · excès_humidité(t) + w_M · risque_moisissure(t) + w_C · excès_CO₂(t) ] · Δt
     + w_E · kWh + dérangement(geste, nuit)
```
- Chaque terme a son unité affichable (°C·h, points·h, heures, kWh).
- Les poids viennent des trois curseurs du cahier (§ 10.3), dans des bornes.
- **Prudence** : on calcule aussi le coût avec la fourchette défavorable du jumeau. Un geste n'est conseillé que s'il gagne **aussi** dans ce cas : un jumeau incertain conseille moins.

## 10. Couche 8 — Décision (`decide.py`)

```python
@dataclass
class Decision:
    zone: str                        # pièce ou volume
    gesture: Gesture
    subject: str                     # heat | cool | humidity | air | sun | safety
    moment: str | datetime           # now | before | tonight | heure
    gain: Gain                       # valeur, unité, comparé à « rien »
    confidence: str                  # measured | estimated
    scenarios: list[ScenarioSummary] # 2 ou 3, pour « Pourquoi ? »
    session: Session | None
    night_notes: list[Note]          # « Cette nuit, pensez à… »
    trace: Trace                     # débogage (cahier § 16 bis) : mesures, jumeau, gestes retirés,
                                     # coûts terme par terme, règle appliquée, ce qui ferait changer d'avis
```

Chaque décision s'exporte en instantané JSON (`Snapshot` : entrées, état et paramètres du jumeau, préférences, version). `bench` le rejoue et doit retrouver la même décision : aucune source de hasard, aucune lecture de l'heure système dans `advisor/` (l'heure est une entrée).

Règles, dans l'ordre :
1. **Sécurité** : un geste imposé par un interdit passe avant tout.
2. **Séance en cours** : on la termine (« Refermez dans 3 min »), sauf sécurité.
3. **Meilleur geste** : plus faible coût, et gain sur « rien » au-dessus du seuil, y compris en cas défavorable.
4. **Stabilité** : on garde le conseil affiché tant que le nouveau ne le bat pas d'une marge (20 % du coût, réglable en interne).
5. **Nuit** : seuls passent les gestes importants ; le reste devient une note de « Cette nuit » la veille, ou attend le matin.
6. **Vacances** : seuls la sécurité, l'humidité, la moisissure et le hors-gel.
7. **Logement** : on cherche d'abord le meilleur geste de chaque volume, puis on teste les combinaisons utiles (air traversant entre deux pièces, une seule pièce à la fois quand c'est mieux). Un seul plan, sans contradiction sur un même air.

## 11. Couche 9 — Rédaction (`words/`)

- Une fonction par sujet et geste, qui reçoit la `Decision` et rend : titre du bandeau, ligne d'explication, lignes de « À savoir », « Pourquoi ? ».
- Le gain s'écrit en mots simples : « vous gardez 2 °C d'ici 7 h », « 10 points d'humidité en moins ».
- La confiance change la tournure (indicatif / conditionnel).
- Fichiers par langue : `fr.py`, `en.py`, `de.py`, mêmes clés, testés pour qu'aucune phrase ne manque.

## 12. Couche 10 — Journal (`journal.py`)

- Stockage Home Assistant (`Store`), une entrée par décision qui change : heure, entrées résumées, scénarios, prévision.
- Résultat mesuré ajouté deux heures après ; avis « Ce conseil ne va pas » ajouté s'il est donné.
- 60 jours glissants ; situations signalées gardées à part, sans limite, exportables (téléchargement des diagnostics) pour devenir des tests du banc.

## 13. Vue envoyée à la carte et entités

- La carte reçoit `Decision` + les observations de la couche 1 + les courbes prévues. **Elle ne décide et ne rédige plus rien.**
- Les entités du cahier (§ 20 et § 20.1) sont calculées à partir de la `Decision`. Elles changent donc en même temps que la carte, avec la même stabilité.
- Évènement `hestia_comfort_advice` à chaque nouvelle décision.

## 14. Banc d'essai (`bench/`)

- **Rejeu** : télécharge un historique Home Assistant (comme `jumeau_test.py`), reconstitue la chronologie, fait tourner le moteur toutes les 5 minutes, et compare à l'ancien moteur.
- **Trois maisons** : la tienne (historique réel), une minimale et une très équipée (dérivées de la tienne en retirant ou ajoutant des capteurs).
- **Propriétés** (§ 18.2 du cahier), sur des milliers de situations tirées au hasard autour des situations réelles.
- **Jumeau** : erreur à 1 h et 3 h, comparée à l'immobilité, **séparément pendant les gestes**.

## 15. Ordre de construction

| Étape | Contenu | Vérifié par |
|---|---|---|
| 1 | `observe`, `house`, banc de rejeu | rejeu de 10 jours sans erreur |
| 2 | Jumeau physique : chaleur, puis eau, puis CO₂, puis débits de fenêtre | bat l'immobilité dans **toutes** les pièces, et bat le jumeau actuel pendant les ouvertures |
| 3 | `inputs` (météo de Weather, occupation, thermostat simulé) | prévision à 3 h avec la vraie météo prévue |
| 4 | `gestures`, `simulate`, `cost`, `decide` | propriétés du cahier ; la nuit du 30 au 31 octobre donne « Refermez » |
| 5 | `words`, vue de la carte, entités, journal | parité carte / entités, trois langues |
| 6 | Confort 3.0 en développement dans le HA de test (`~/niak-ha-test`, qui recopie la maison), à côté du moteur 2.1 de la maison ; journal des désaccords | revue avec Frank |

Périmètre de chaque étape : cahier § 3 bis (la 3.0 fait la chaleur, les fenêtres et volets reliés, le chauffage ; l'eau, le CO₂ et les déductions viennent après). Prochaine action à l'étape 2 : la correction par l'écart récent, puis la mesure de l'effet des gestes sur les fenêtres et volets que le HA de test enregistre.

L'étape 2 est la plus risquée. Si le jumeau physique ne bat pas nettement l'immobilité **pendant les gestes**, on s'arrête et on revoit la méthode avant d'aller plus loin.

## 16. Historique
- **v0.1 — 31 octobre 2026** : première version, après le test du jumeau actuel sur 10 jours réels.
- **v0.7 — 31 octobre 2026, nuit** : plage de chaque pièce lue dans Confort ; « Cette nuit, pensez à… » ; rejeu 2.1 contre 3.0 refait (`niak-comfort/banc/rejeu-2-1-contre-3-0-soir.md`) et règle de signification révisée (l'écart épargné pendant 2 h, le moins coûteux des gestes significatifs) ; jumeau du COV (indice Sensirion, loi des particules : 3 h 54 contre 89 points) ; VMC rapide et purificateur, gestes et preuves par appareil ; le logement : moisissure (coin de mur EN ISO 13788, 80 %), buée, gel, mode vacances.
- **v0.6 — 31 octobre 2026 au soir** : apprentissage de chaque nuit (`nightly.py`, `physics/airfit.py`), branché dans le HA de test.
- **v0.5 — 31 octobre 2026 au soir** : instantané rejouable et trace en sept couches (`advisor/snapshot.py`, `python -m advisor.bench.replay instantane.json [--dehors +1.5] [--poids heat=2]`) ; « ce qui ferait changer d'avis » cherche le plus petit écart de température dehors qui retourne le conseil ; le HA de test garde le dernier instantané de chaque pièce et chaque changement de conseil, 10 jours.
- **v0.4 — 31 octobre 2026 au soir** : niveaux de preuve (`proof.py`), « Bon à savoir » par fournisseurs (`knowing.py`) : soleil sur les fenêtres, « Laissez ouvert » constaté ; intégration Soleil et Adaptive Cover Pro dans le HA de test.
- **v0.3 — 31 octobre 2026 au soir** : tendance mesurée (`Now.missed`), soleil par scénario, énergie dépensée par le chauffage simulé, « Rien à faire » vrai hors plage ; soleil entier par l'ouvrant essayé puis écarté (§ 1 bis).
- **v0.2 — 31 octobre 2026** : étapes 1 et 2 commencées (`advisor/observe.py`, `house.py`, `physics/vents.py`, `thermal.py`, `fit.py`, `bench/`, 12 tests). Filtre de Kalman écarté au profit de l'ajustement sur la prévision ; rythme de la journée ajouté ; premiers résultats (§ 1 bis).
