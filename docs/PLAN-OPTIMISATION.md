# Plan d'optimisation de Hestia Confort

Version 0.5 du 6 novembre 2026. **Lots 1 à 4 validés par Frank et faits au labo** (voir « Résultats »), non commités,
non publiés. Tous les points décidés sont faits (le point 14 est laissé de côté, voir le lot 3).

Même méthode que Weather (`niak-weather-integration/docs/PLAN-OPTIMISATION.md`) et que le hub
(`hestia-ecosysteme/docs/PLAN-OPTIMISATION-HUB.md`) : mesurer au labo, corriger par lots, remesurer de la même façon.

## Pourquoi

Le 5 novembre, un utilisateur sur la box HA Green (4 petits cœurs ARM, 2 à 3 fois plus lente que le NAS du labo) a dû
retirer Confort et Weather : tableau de bord lent, boutons en retard de 1 à 5 s. Weather et le hub sont faits. Confort
pèse le plus : au labo, sur 4 minutes après un redémarrage, 13,8 s de calcul contre 1,1 s pour Weather.

## Ce qu'on a mesuré au labo (6 nov., fin de matinée)

Labo 192.168.0.4:8124 (Celeron J4125, 7 849 entités), code de la branche `moteur-conseil-3` (moteur 3.9), 8 pièces et
« Mon logement ». Profileur par fenêtres courtes, asyncio debug pour ce qui fige Home Assistant, un banc navigateur avec les
vraies vues du labo. **Sur une HA Green, compter 2 à 3 fois plus.**

### 1. En temps normal, sans carte ouverte (4 min)

- Confort : **3,8 s de calcul** (Weather 0,46 s).
- **127 calculs de pièce en 4 minutes**, soit environ 4 par pièce et par minute. **56 viennent de Weather** : chaque fois que
  Weather se met à jour (une fois par minute), les 8 pièces recalculent tout, même si rien de ce que Confort lit dans Weather
  n'a changé. Le reste : le tic de chaque minute, les capteurs, le conseil 3.0.
- Un calcul de pièce coûte environ 45 ms (sous profileur). Les deux tiers partent dans deux simulations :
  « Cette nuit » (30 h, `engine/night.py`) et « Prochaines heures » (24 h, `engine/horizon.py`), refaites à chaque calcul
  alors que leurs demi-heures ne changent que toutes les 30 minutes. Dedans, **la position du soleil est recalculée
  59 000 fois** en 4 minutes (`engine/twin.py` `sun_position`).
- Ce qui fige Home Assistant (asyncio debug) :
  - **chaque minute, 0,12 à 0,19 s** (une fois 0,9 s) : les 8 pièces recalculées d'affilée dans la mise à jour de Weather ;
    **0,33 à 0,4 s** dans les minutes qui suivent un démarrage ;
  - **toutes les 5 minutes, 4 à 8 blocages de 0,13 à 0,38 s** : le conseil 3.0 décide pour chaque pièce sur la boucle
    (`advisor_home.py` `tick`).
- Petits balayages de toute la maison à chaque calcul : l'alarme est cherchée dans les 7 849 entités du registre (2 fois),
  les plannings dans tous les interrupteurs, le type de chauffage dans toutes les pièces. 0,2 à 0,4 s en 4 min.

### 2. Avec des cartes ouvertes

Onglet Confort du tableau Labo : 26 cartes de pièce, « Mon logement », le bilan. Mesuré avec 24 abonnements de pièce et
celui de « Mon logement » pendant 3 min 35 :

- **8,4 Mo envoyés**. « Mon logement » reçoit **93 ko à chaque fois** (37 fois, 3,4 Mo) : toutes les pièces, dès qu'une
  seule change. Une pièce : 8 à 21 ko, 14 à 24 fois.
- **Presque chaque calcul repart vers les cartes** : les pentes des courbes de tendance sont recalées sur « maintenant », la
  puissance du chauffage porte l'heure du calcul, le soleil moyen bouge d'un dixième. La vue « change » donc toujours.
- Côté Home Assistant, chaque envoi recopie toute la vue puis la convertit en texte trié, **une fois par carte**, sur la
  boucle (`websocket.py` `_stable` + `json.dumps`) : **0,4 s par minute** de plus avec 25 cartes.
- La vue d'une pièce qui partage l'air (Salon) contient aussi toute celle de son partenaire (5,7 ko sur 21), et la carte
  s'abonne en plus au partenaire.

### 3. L'apprentissage de nuit du conseil 3.0 (3 h 30, et 10 min après un démarrage s'il date de plus d'un jour)

Relancé à la demande (`hestia_comfort/relearn`) :

- **8,1 s d'un seul bloc où Home Assistant est figé** : les 60 jours d'historique sont lus bruts, avec tous les
  attributs, puis convertis sur la boucle (`advisor_home.py` `learn`). Le labo n'a que 6 jours d'historique
  (112 000 lignes) : avec 10 jours (réglage par défaut de HA) ce serait environ 13 s, **30 à 40 s sur une HA Green**.
- La mémoire suit : tout l'historique, attributs compris, est en mémoire en même temps. Avec 60 jours : environ 1,1 million
  d'états.
- Puis **environ 90 s de calcul** (ajustement des jumeaux : `advisor/physics/airfit.py` 36 s, `thermal.py` 32 s,
  `water.py` 11 s). 3 min 36 relancé, **7 minutes cette nuit au labo**. Il tourne dans un fil à part, mais Python n'en
  fait avancer qu'un à la fois : pendant ce temps HA se fige souvent 1,2 à 1,8 s d'un coup.

### 4. Au démarrage

- Mise en place : 2,2 s (Weather 2,7 s), sans figer HA.
- 30 à 300 s après, **l'apprentissage 2.1 de chaque pièce fige HA 0,5 à 0,8 s** (8 fois, puis toutes les 6 heures) :
  la conversion des 10 jours d'historique et l'ombre de la station se font sur la boucle (`room/learning.py` `_points`,
  `_sun_history`, 259 000 positions du soleil).
- Total : 13,2 s de calcul de Confort sur les 5 premières minutes.

### 5. Dans le navigateur

Banc local : la vraie carte, les vraies vues du labo, les 28 cartes de l'onglet Confort, processeur ralenti 4 fois
(téléphone moyen).

- Les 28 cartes ouvrent **45 abonnements** (chaque carte d'une pièce qui partage l'air s'abonne aussi au partenaire).
- Premier affichage : 0,9 s.
- Une vague de mises à jour de toutes les cartes : 200 ms (6 complètes 72 ms, 17 cartes à la pièce 85 ms, 3 tuiles 25 ms,
  Mon logement 15 ms). Les mises à jour arrivent environ 4 fois par minute et par pièce.
- **Au repos : environ 1 %**. Les animations se mettent déjà en pause hors de l'écran. Le verre dépoli ne se mesure pas
  sur le banc (carte graphique) : pas de changement sans mesure sur un vrai appareil, comme pour Weather.
- Fichiers : carte **465 ko servis sans compression** (138 ko compressée) ; la carte charge les polices **TTF**
  (4 × 95 ko + la variable) alors que les woff2 sont déjà dans le dossier.

### 6. Le disque

- Instantanés du conseil 3.0 : 1 457 fichiers, 57 Mo en 3 jours (gardés 10 jours) ; le « dernier » de chaque pièce est
  réécrit toutes les 5 minutes. Une HA Green écrit sur une mémoire eMMC.
- Les fichiers d'une pièce supprimée restent dans `.storage` (deux anciennes pièces au labo).

### En résumé

| Ce qui pèse | Au labo | Sur HA Green (×2 à 3) |
|---|---|---|
| Apprentissage de nuit, d'un bloc | **8,1 s figé** (6 jours d'historique) | **30 à 40 s** avec 10 jours |
| Apprentissage de nuit, le calcul | 90 s, 3 à 7 min, HA ralenti | 4 à 20 min |
| Apprentissage 2.1 des pièces (démarrage, toutes les 6 h) | 8 × 0,5-0,8 s | 8 × 1-2,4 s |
| Réaction aux mises à jour de Weather | 0,12-0,4 s par minute | 0,3-1,2 s par minute |
| Conseil 3.0, toutes les 5 min | 4-8 × 0,13-0,38 s | 4-8 × 0,3-1,1 s |
| Envoi aux cartes (25 cartes) | 0,4 s par minute | 0,8-1,2 s par minute |
| Données envoyées (onglet Confort) | 2,4 Mo par minute | idem, plus lent à lire |

## Le plan, du plus rentable au moins rentable

Chaque point : ce qu'on change, le gain attendu, le risque, la mesure avant/après. Les points qui touchent `advisor/`
changent le moteur : version 3.9.x et une ligne dans `CHANGELOG-MOTEUR.md`.

### Lot 1 — Home Assistant ne se fige plus (gros gain, risque faible à moyen)

**1. Apprentissage de nuit : lire l'historique en compact, hors de la boucle** (`advisor_home.py`, `advisor/nightly.py`)
Lire jour par jour et entité par entité avec la lecture compacte déjà utilisée par l'apprentissage 2.1
(`recorder_history.py` : seulement les vrais changements, seul l'attribut utile du thermostat), et convertir dans le même
fil. Jamais tout l'historique brut en mémoire.
- Gain attendu : 8,1 s figé → **moins de 0,05 s** ; mémoire de l'apprentissage divisée par 10 au moins.
- Risque : moyen. Test : mêmes jumeaux appris, pièce par pièce, sur l'historique du labo (rapport d'apprentissage avant et
  après, `advisor/bench`).
- Mesure : `relearn` sous asyncio debug (aujourd'hui 8,1 s à `advisor_home.py:605`).

**2. Apprentissage 2.1 des pièces : tout dans le fil à part** (`room/learning.py`)
`_points` et l'ombre de la station (`_sun_history`) passent dans l'exécuteur, comme le reste de l'apprentissage.
- Gain : 8 × 0,5-0,8 s figés → 0. Risque : faible. Mesure : asyncio debug au démarrage.

**3. Weather ne fait recalculer que ce qui change** (`coordinator.py:169`, `weather_link.py`)
À chaque mise à jour de Weather, comparer ce que Confort en lit (heures prévues, pluie, orage, vigilance, saison, air) à
la fois d'avant ; ne recalculer les pièces que si ça a changé, en une seule salve.
- Gain : 56 calculs sur 127 en moins ; 0,12-0,4 s par minute → presque rien. Risque : faible.
- Mesure : calculs de pièce par minute dans le profil ; asyncio debug sur la mise à jour de Weather.

**4. Une seule conversion par mise à jour, partagée par toutes les cartes** (`websocket.py`)
La vue est convertie une fois quand la pièce change, et toutes les cartes abonnées réutilisent ce texte.
- Gain : 0,4 s par minute (25 cartes) → quelques ms. Risque : faible. Mesure : profil avec le flux ouvert.

### Lot 2 — Un calcul de pièce moins cher

**5. Positions du soleil mémorisées** (`engine/twin.py`, `engine/sunlight.py`, `room/sun.py`)
Les positions et le ciel clair calculés une fois sur une grille de 5 minutes et gardés (le calcul est déjà juste à un
degré près ; en 5 minutes le soleil bouge d'un degré environ).
- Gain : 59 000 calculs en 4 min → quelques centaines ; environ un tiers d'un calcul de pièce. Risque : faible.
- Mesure : temps d'un calcul de pièce dans le profil.

**6. « Cette nuit » et « Prochaines heures » refaits seulement quand il faut** (`engine/night.py`, `engine/horizon.py`)
Les garder tant que la demi-heure est la même, que le conseil n'a pas changé et que les mesures n'ont pas bougé (0,1 °C,
1 % d'humidité, une fenêtre, une prévision).
- Gain : les deux tiers d'un calcul, la plupart du temps. Risque : moyen (le dessin doit suivre le conseil) ; test : même
  résultat que le calcul complet sur une journée rejouée.

**7. Un calcul par salve** (`coordinator.py`)
Le tic de la minute, les capteurs, Weather et le conseil 3.0 se regroupent : une pièce calcule au plus une fois par
salve ; une fenêtre ouverte reste affichée tout de suite.
- Gain : environ 4 calculs par minute et par pièce → 1 à 2. Risque : faible.

**8. Le conseil 3.0 décide hors de la boucle** (`advisor_home.py` `_tick`, `room/advice.py`)
L'instantané de la pièce est pris sur la boucle (rapide), la décision et ses simulations tournent dans l'exécuteur.
- Gain : 4-8 blocages de 0,13-0,38 s toutes les 5 min → 0. Risque : moyen (le moteur ne doit lire que l'instantané) ;
  test : mêmes décisions sur les situations gardées (`instantanes`).

**9. Plus de balayage de toute la maison à chaque calcul** (`room/presence.py`, `schedule_link.py`, `coordinator.py`)
L'alarme, les plannings du thermostat et le type de chauffage sont cherchés une fois et gardés, puis cherchés à nouveau
quand le registre ou les réglages changent.
- Gain : 0,2-0,4 s en 4 min, davantage dans une grande maison. Risque : faible.

**10. Le calcul de l'apprentissage de nuit lui-même** (`advisor/physics/`, `advisor/nightly.py`)
90 s de calcul pur Python. D'abord laisser respirer Home Assistant (une courte pause entre les pièces et entre les essais
de l'ajustement), puis regarder où l'ajustement peut faire moins d'essais sans perdre en précision.
- Gain : HA ne se fige plus pendant l'apprentissage ; durée à mesurer. Risque : moyen (précision des jumeaux) ; même test
  qu'au point 1.
- À décider après le point 1 : passer ces calculs dans un processus à part (seule façon de ne plus du tout gêner HA),
  ou les écrire avec numpy, coûterait plus cher à faire.

### Lot 3 — Moins de données vers les cartes

**11. Une vue qui ne change que quand l'écran change** (`engine/evolution.py`, `coordinator.py`)
Pentes et points des tendances sur une grille fixe et arrondis ; la puissance du chauffage garde l'heure de son dernier
changement ; le soleil moyen arrondi.
- Gain : la plupart des envois deviennent inutiles et ne partent plus. Risque : faible (à vérifier à l'œil sur les
  courbes). Mesure : messages par minute et par pièce (aujourd'hui 4 à 7).

**12. « Mon logement » ne reçoit que les pièces qui ont changé** (`websocket.py` + `card/src/home.ts`)
Comme Weather au point 8 : la carte qui le demande reçoit tout une fois, puis seulement les pièces changées. Une carte
plus ancienne, gardée en cache par l'appli mobile, reçoit toujours tout.
- Gain : 93 ko → 10 à 20 ko par envoi. Risque : moyen (format entre l'intégration et la carte).

**13. Un abonnement par pièce et par page** (`card/src/live.ts`)
Toutes les cartes d'une même pièce partagent un seul flux, comme Weather (`card/src/stream.ts`).
- Gain : 45 abonnements → 9 sur l'onglet Confort du Labo ; 5 fois moins de données et de travail. Risque : faible.

**14. Retirer de la vue ce que la carte ne lit pas**
D'abord la copie de la pièce partenaire (5,7 ko sur 21 pour le Salon), puis ce qu'un relevé des lectures de la carte montrera
inutile. Risque : moyen (la carte, les entités et le verdict doivent garder ce qu'ils lisent).

**15. Fichiers compressés et polices woff2** (`card/scripts/build_card.mjs`, `card/src/card.ts`)
Un `.gz` à côté de la carte, comme Weather et le hub ; la carte charge les woff2 déjà présents.
- Gain : 465 → 138 ko, polices 545 → environ 150 ko, au premier chargement et après chaque mise à jour. Risque : faible.

### Lot 4 — Petites choses

**16. Instantanés sur le disque** : écrire « dernier » seulement s'il a changé ; garder les instantanés datés moins
longtemps, ou seulement quand l'Atelier est utilisé. **À décider par Frank** (l'Atelier s'en sert).

**17. Ranger à la suppression d'une pièce** : ses fichiers `.storage` (jumeau, apprentissage, retours, conseil) partent avec elle.

**18. Mesure commune** : rassembler les scripts de cette mesure dans `hestia-labo/` (profil en temps normal et avec cartes,
apprentissage de nuit, démarrage, banc des cartes), pour refaire exactement les mêmes chiffres après chaque lot.

## Résultats

### Lot 1 — fait le 6 nov. après-midi, au labo, non commité

- **Point 1** : l'apprentissage de nuit lit l'historique entité par entité et jour par jour, dans le fil du recorder, en ne
  gardant que les deux attributs qu'il lit (puissance du chauffage, position du volet) et une seule fois un état répété
  (`advisor_home.py` `night_history`, `night_rows`). Vérifié sur 7 jours réels du labo : **toutes les séries lues par le
  moteur sont identiques** (températures, humidités, contacts, puissance, volets, absences), 112 875 → 72 304 lignes,
  **207 Mo → 14 Mo** de texte. Test : `tests/test_night_history.py`. Le moteur lui-même ne change pas (pas de nouvelle
  version du moteur).
- **Point 2** : l'apprentissage de chaque pièce prépare ses points, l'ombre de la station et les échantillons du jumeau dans
  le fil à part ; les unités (°F) sont lues avant, sur la boucle (`room/learning.py`).
- **Point 3** : une mise à jour de Weather ne fait recalculer une pièce que si ce qu'elle y lit a changé (prévisions,
  pluie, orage, vigilance, saison, air sans son heure de calcul, pollens), et le calcul part avec les mesures, plus dans la
  mise à jour de Weather (`weather_link.fingerprint`, `coordinator.py` `_weather_updated`). Test : `tests/test_weather_listen.py`.
- **Point 4** : une vue est convertie une fois par mise à jour, pour toutes les cartes abonnées, avec le convertisseur
  rapide de Home Assistant (`websocket.py` `_texts`). Test ajouté dans `tests/test_websocket.py`.
- Tests : 826, une seule erreur, déjà présente sur la version commitée (`test_domain_migration_ha`).

| Mesure (labo) | Avant | Après le lot 1 |
|---|---|---|
| Apprentissage de nuit : HA figé d'un bloc | **8,1 s** | **aucun blocage de Confort** |
| Apprentissage de nuit : durée (7 pièces) | 3 min 36 | 3 min 26 (avec un moteur plus lourd, voir plus bas) |
| Démarrage : apprentissage des pièces sur la boucle | 8 × 0,5-0,8 s | **0** |
| Chaque minute : réaction à Weather | 0,12-0,4 s | **0** |
| Calculs de pièce en 4 min | 127 | 93 |
| Calcul de Confort en 4 min, sans carte | 3,8 s | 2,7 s |
| Envoi aux cartes (25 abonnements, 3 min, sous profileur) | 1,2 s | 0,46 s |
| Données envoyées (25 abonnements, 3 min 35) | 8,4 Mo | 6,7 Mo |

Ce qui reste, pour le lot 2 :
- Le conseil 3.0 fige HA toutes les 5 minutes (4 à 9 fois 0,1 à 0,46 s). **Il s'est alourdi** : le moteur 3.9.6, en
  cours dans une autre session et parti au labo avec ce déploiement, appelle `decide.simulate` environ 40 fois plus
  (3 078 appels contre 75 dans les 5 minutes qui suivent un démarrage). Le point 8 (décider hors de la boucle) devient
  le plus utile du lot 2.
- Pendant le calcul de l'apprentissage de nuit, HA se fige encore par à-coups (jusqu'à 1,6 s) : point 10.

### Lot 2 (points 5, 8, 9) — fait le 6 nov. après-midi, au labo, non commité

Mesuré avec le moteur 3.9.6 commité par Frank.

- **Point 8** : le conseil 3.0 prend ses mesures sur la boucle, puis décide et simule dans le fil à part (la décision, la
  seconde décision quand un geste en cours se montre, « Cette nuit », le chauffage qui revient, le poêle, le volet du
  soir, les sources du moment) ; la pièce se met à jour ensuite sur la boucle (`room/advice.py` `advise` → `_advise`,
  `think`). Une décision à la fois par pièce : une fenêtre qui bouge attend celle en cours. Les lignes de calcul sont
  déplacées telles quelles. Vérifié au labo : pour les 8 pièces, le rejeu de l'instantané écrit par le nouveau code
  redonne exactement le conseil affiché.
- **Point 5** : les positions du soleil déjà calculées pour un instant exact sont gardées (`engine/twin.py`, 4 096
  instants) ; même résultat au chiffre près.
- **Point 9** : le panneau Alarmo est cherché dans le registre une fois toutes les 10 minutes au lieu de deux fois par
  calcul (`room/presence.py` `alarmo`). Un panneau ajouté ou désactivé est vu dans les 10 minutes. Les plannings du
  thermostat et le type de chauffage restent cherchés à chaque calcul : ils ne coûtent presque rien.
- Tests : 826, la même seule erreur qu'avant.

| Mesure (labo) | Avant | Lot 1 | Lot 2 (5, 8, 9) |
|---|---|---|---|
| Conseil 3.0, toutes les 5 min : HA figé | 4-9 × 0,1-0,46 s | idem | **aucun blocage** (2 tics observés) |
| Un calcul de pièce (sous profileur) | 46 ms | 45 ms | **25 ms** |
| Positions du soleil calculées en 4 min | 59 000 | 42 000 | **10 700** |
| Recherche de l'alarme en 4 min | 0,23 s | 0,17 s | **0** |

### Lot 2, suite (points 6, 7, 10) — validés par Frank et faits le 6 nov. après-midi, au labo, non commités

- **Point 10** : chaque pièce apprend la nuit dans un petit programme à part (`night_worker.py`), lancé par HA sans
  bloquer sa boucle, en priorité basse, qui ne charge que le moteur (jamais HA) et s'arrête ensuite. Il ne reçoit que
  l'historique de sa pièce (`advisor_home.py` `room_history`). S'il ne peut pas démarrer, l'apprentissage se fait comme
  avant, la raison écrite une fois dans le journal. Test : `tests/test_night_process.py` (même apprentissage, au chiffre
  près, que le calcul direct). Un premier essai avec le moteur de processus de Python mourait au labo dès son lancement
  et bloquait la boucle en le lançant : remplacé.
- **Point 6** : « Cette nuit » et « Prochaines heures » sont gardés tant que ce qu'ils lisent n'a pas bougé (température
  au dixième, humidité au point, prévisions, conseil, jumeau, soleil), et refaits au moins toutes les 5 minutes, pour
  que la courbe ne commence jamais plus de 5 minutes en retard (`coordinator.py`).
- **Point 7** : les mesures qui bougent tout le temps sont regroupées sur 30 s au lieu de 10 s (`room/constants.py`) ;
  une fenêtre, le chauffage, une présence ou un volet restent affichés dans la seconde.
- Tests : 827, la même seule erreur qu'avant.

| Mesure (labo) | Avant | Lot 1 | Lot 2 (5, 8, 9) | Lot 2 complet |
|---|---|---|---|---|
| Calculs de pièce en 4 min | 127 | 93 | 110 | **84** |
| Un calcul de pièce (sous profileur) | 46 ms | 45 ms | 25 ms | **14 ms** |
| « Cette nuit » simulée en 4 min | 127 | 93 | 110 | **15** |
| Apprentissage de nuit : durée (7 pièces) | 3 min 36 | 3 min 26 | — | **1 min 41** |
| Apprentissage de nuit : HA figé | 8,1 s d'un bloc, puis à-coups jusqu'à 1,6 s | à-coups jusqu'à 1,6 s | — | **rien au-dessus de 0,19 s** |

Ce qui fige encore le labo n'est plus Confort : l'ancien module `hestia_advisor_dev` (0,3 à 0,76 s toutes les 5 min,
absent chez les utilisateurs) et Remote Home-Assistant.

Reste du lot 2 (avant validation, gardé pour mémoire) :
- **Point 10** : le calcul de l'apprentissage de nuit (90 s au labo, environ 4 à 10 min sur une HA Green) fait encore
  « hoqueter » HA (jusqu'à 1,6 s). Ce n'est pas un blocage de Confort sur la boucle : Python ne fait avancer qu'un fil à
  la fois, et chaque petite lecture de HA attend alors son tour. Des pauses n'y changeraient presque rien ; seul un
  **processus à part** (comme un petit programme lancé la nuit, qui meurt ensuite) supprime le problème. Risque moyen :
  environ 100 à 150 Mo de mémoire pendant l'apprentissage, et à vérifier sur HA OS. **À décider par Frank.**
- **Point 6** (« Cette nuit » et « Prochaines heures » gardés) : environ la moitié des 25 ms qui restent. Risque moyen.
- **Point 7** (un calcul par salve) : HA reprogramme déjà le tic de la minute après chaque calcul ; 110 calculs en
  4 min pour 8 pièces (moins de 3,5 par pièce et par minute). Gagner plus voudrait dire afficher les mesures moins vite
  (10 s → 30 s) : à décider par Frank.

### Lot 3 (points 11, 12, 13, 15) — validé par Frank et fait le 6 nov. en fin d'après-midi, au labo, non commité

- **Point 13** : une seule souscription par pièce et par page, que toutes les cartes de la pièce écoutent ; une carte
  ajoutée plus tard reçoit tout de suite la dernière vue ; la dernière carte partie la ferme (`card/src/shared.ts`,
  `card/src/live.ts`). Le test de la carte qui voulait un abonnement par carte est réécrit pour le nouveau comportement.
- **Point 12** : « Mon logement » demande `changes` : toutes les pièces une fois, puis seulement celles qui ont changé,
  avec l'ordre des pièces et la synthèse (`websocket.py`, `card/src/home.ts`). Une carte plus ancienne reçoit tout comme
  avant ; une intégration plus ancienne refuse `changes` et la carte redemande sans. Test : `tests/test_websocket.py`.
- **Point 11** : tendances calculées sur une grille de 2 minutes (`engine/evolution.py`) ; heure de la puissance de
  chauffe et de l'air de Weather arrondie à 5 minutes (`coordinator.py`, `exterior.py`). Plus aucune vue ne part pour
  ses seules pentes ou heures. En journée, presque chaque vue porte encore un vrai changement (le soleil mesuré bouge à
  chaque relevé) ; la nuit, les vues cessent de partir pour rien.
- **Point 15** : la construction de la carte écrit `hestia-comfort-card.js.gz` à côté (`card/scripts/build_card.mjs`) ;
  vérifié au labo : servie compressée, **465 → 138 ko**. La carte charge les polices woff2 (`card/src/card.ts`) : 16 ko
  au lieu de 95 ko pour une graisse.
- **Point 14 laissé de côté** : la copie de la pièce partenaire est lue par la carte et par le verdict des entités, testés
  pour rester identiques ; elle ne concerne que les pièces qui partagent l'air, et le point 13 en divise déjà l'envoi.
- Tests : 828 côté intégration (la même seule erreur qu'avant), 72 sur 72 côté carte.

| Mesure | Avant le lot 3 | Après |
|---|---|---|
| Abonnements des 28 cartes de l'onglet Confort (banc) | 45 | **8** |
| Données reçues par ces cartes pour les mêmes mises à jour (banc) | 4,4 Mo | **1,1 Mo** |
| « Mon logement », 4 min au labo (même nombre d'envois) | 1 931 ko | **892 ko** |
| « Mon logement » recollé dans le navigateur (banc) | — | 8 pièces sur 8, sans erreur |
| Carte téléchargée | 465 ko | **138 ko** |
| Une graisse de police | 95 ko | **16 ko** |

Le temps de dessin d'une vague de mises à jour reste d'environ 190 ms au ralenti ×4 : chaque carte se redessine
encore ; mais une pièce n'envoie plus qu'un message pour toutes ses cartes.

### Lot 4 (points 17, 18) — fait le 6 nov. en fin de journée, non commité ; point 16 à décider

- **Point 17** : une pièce supprimée emporte ses fichiers `.storage` (apprentissage, jumeau, retours, conseil 3.0)
  (`__init__.py` `async_remove_entry`, test `tests/test_remove_room.py`). Au labo, les 6 fichiers des deux anciennes pièces
  de test sont rangés dans `config/sauvegardes/stores-orphelins-confort-2026-11-06`.
- **Point 18** : les scripts de cette mesure sont dans `hestia-labo/confort/` (profil, flux des cartes, apprentissage de
  nuit, démarrage, conseils, banc des cartes et ses données), décrits dans `hestia-labo/LISEZMOI.md`.
- **L'ancien module `hestia_advisor_dev` est retiré du labo** (voir les notes en bas).
- **Point 16, décidé par Frank le 6 nov.** : nos outils d'analyse se débranchent. Un interrupteur « Outils d'analyse »
  (`analysis` dans les réglages de la maison, **coupé par défaut**) : coupé, le conseil 3.0 n'écrit ni instantanés, ni
  journal, ni gestes suivis, ni rapport de nuit — le moteur ne les relit jamais pour décider ni pour apprendre (tout ce
  qu'il apprend est dans `.storage`). « Pas maintenant » marche toujours ; « Ce conseil ne va pas » garde la situation en
  mémoire et ne l'écrit qu'au signalement (`advisor_store.py` `signal`). Allumé : tout comme avant, pour l'Atelier.
  Gardé quand on enregistre les réglages généraux. Réglé par la commande `hestia_comfort/set_analysis` (pas encore de
  bouton dans le hub). **Allumé au labo** ; vérifié : coupé, rien n'est écrit ; allumé, les 7 pièces écrivent au tic
  suivant. Test : `tests/test_analysis_tools.py`. Gain pour une bêta publique : environ 55 Mo écrits par jour et 150 Mo
  sur le disque en moins (chiffres du labo).
- Tests : 831, la même seule erreur qu'avant.

## Comment on avance

1. Un lot à la fois : code, tests, déploiement au labo, mesure avant/après notée ici.
2. Le moteur change aux points 1, 8 et 10 : version 3.9.x et `CHANGELOG-MOTEUR.md`.
3. Le dossier est partagé avec d'autres sessions qui changent le moteur : relire le diff de chaque fichier avant de
   commiter, ou travailler dans un worktree propre.
4. Préversion seulement quand Frank le décide ; changer de numéro (la carte reste en cache 31 jours sinon).

Notes :
- L'ancien module `hestia_advisor_dev` est **retiré du labo** depuis le 6 nov. (accord de Frank) : les mesures ne voient plus
  que Confort et Weather. Les onglets techniques du tableau Labo gardent leurs cartes (`hestia-labo/cartes-techniques.js`).
- Ne touche pas au panneau Confort (`panel.py`, `socle.py`, `frontend/`), traité par le plan du hub.
