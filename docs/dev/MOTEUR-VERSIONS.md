# Versions du moteur de conseil

Le moteur de conseil (`custom_components/hestia_comfort/advisor/`) a son propre numéro, à part de celui de l'intégration : `VERSION` dans `advisor/__init__.py`.

Il est écrit dans chaque instantané, dans le journal des conseils, dans les avis « Ce conseil ne va pas » et dans le rapport de chaque nuit. Le panneau l'affiche dans « Versions et liens ». On sait ainsi, conseil par conseil, quelle version l'a donné, et on peut comparer avant et après une amélioration.

## La règle

- **Majeur** : une nouvelle génération du moteur ; les jumeaux appris ne sont pas repris, ils sont réappris.
- **Mineur** : un geste, une règle ou une façon de décider qui change des conseils.
- **Correctif** : une correction qui ne change que le conseil qui était faux.

Chaque changement du moteur monte son numéro et ajoute une ligne ci-dessous, la plus récente en haut.

Chaque version a aussi sa ligne en mots simples dans [CHANGELOG-MOTEUR.md](../../CHANGELOG-MOTEUR.md), le changelog du moteur publié avec Confort (règle dans [RELEASES.md](../../RELEASES.md)). Ici, le détail technique ; là-bas, ce que la famille voit changer.

## Historique

### 3.2.0 — 4 novembre 2026

- Planning du chauffage lu dans ha-chauffage (issue #42, `engine/schedule.py`, `schedule_link.py`) : « Prochain changement » (`…_next_change`, armellarcier/ha-chauffage#82) s'il existe, sinon « Préréglage prévu » (`next_start`, `next_preset`, `temperatures`), et la fin de la dérogation quand elle est en cours (le créneau annoncé peut alors ne jamais venir). À défaut, Scheduler (issue #46) : les plannings en marche qui pilotent le thermostat (`entities`), l'action du prochain créneau qui change quelque chose (`actions`, `next_slot`, `next_trigger`), la température du préréglage lue dans le Versatile Thermostat ; le plus proche de plusieurs plannings. Ses conditions (jour ouvré, présence) ne sont pas prévues.
- `Thermostat.then` / `Thermostat.at` : la consigne du créneau suivant et dans combien de minutes ; `scheduled(minutes)` la donne à chaque pas de chaque scénario, aussi pour « Rallumez » et « Remettez le chauffage à … » (la consigne donnée à la main ne tient que jusqu'au créneau suivant). `heating_back` en tient compte de lui-même.
- Note « Chauffage prévu à {at} : {temperature} °C visés » (`knowing.heating_planned`) quand le créneau suivant relève la consigne dans les 6 h, jamais pendant le sommeil ; un plan, donc prouvé.

### 3.1.1 — 4 novembre 2026

- « À essayer » tient comme le bandeau : l'essai affiché reste tant qu'il est presque aussi bon que le meilleur (même marge), et il traverse une rafale qui l'interdit un instant. Chambre AL, 4 novembre, rejeu de 14 h 18 à 16 h 53 : 6 changements de geste au lieu de 12 (30 changements de texte depuis 21 h la veille).
- L'heure annoncée pour l'humidité est arrondie au quart d'heure. Pour une fenêtre laissée ouverte, c'est l'heure de fin de la prévision (« 58 % d'humidité à 18 h au lieu de 70 % ») : elle n'avance plus de 5 minutes à chaque calcul.
- Une règle de sécurité qui fait refermer (pluie, rafales) ne fait plus échouer le conseil d'une pièce dont la fenêtre vient d'être vue ouverte (Salon · Cuisine, 4 novembre à 6 h 26).

### 3.1.0 — 4 novembre 2026

- Une note pour chaque geste (CAHIER-MOTEUR.md § 15.1, proposé par Frank, `advisor/notes.py`). Une aération, une marche de la VMC rapide ou du purificateur est jugée **1 h après sa fin**, contre le jumeau **sans le geste** : effet annoncé (avec − sans) et effet mesuré (mesuré − sans). Note + (de la moitié au double, ou plus), 0 (moins de la moitié), − (l'inverse).
- Rien n'est noté si autre chose a agi pendant le geste ou l'heure qui suit : fenêtre rouverte, VMC ou purificateur qui change, source d'humidité (douche, cuisine). Un geste écarté le jour (`ecartes`) l'est aussi la nuit.
- La nuit corrige chaque catégorie (pièce × geste × sujet) vers la médiane de ses notes récentes (poids divisé par 2 en 15 jours, 3 notes au moins), au plus ×2 ou ÷2 par nuit, gardée si la dernière journée n'est pas prévue plus de 5 % moins bien. Pour la chaleur, elle remplace l'ancienne correction des fenêtres ; pour l'humidité, le CO₂, les COV et les particules, elle est nouvelle ; la part du débit de la VMC (`boost_scale`) et du purificateur (`purifier_scale`, nouveau) en viennent aussi.
- Preuves : « appris » si la médiane des 10 dernières notes est entre la moitié et le double ; « démenti » dès que les 2 dernières sont à 0 ou −, quoi qu'il y ait eu avant.
- « Ce que Hestia sait » reçoit pour chaque effet ses dernières notes (« 0 0 − ») et la correction de la nuit.

### 3.0.6 — 3 novembre 2026

- L'humidité se dit une heure après la fermeture de la fenêtre, et non au plus bas de l'aération : les murs et la literie rechargent l'air en quelques minutes (Chambre P, 3 novembre : 66 % fenêtre ouverte, 69 % dix minutes après l'avoir refermée). Si rien ne reste, la carte dit « l'humidité baisse pendant l'aération, puis revient ».
- Un effet démenti par les gestes redescend à « supposé » : deux aérations au moins dont l'effet mesuré fait moins de la moitié du prévu, ou va dans l'autre sens (`proof.belied`). Le geste passe en « À essayer » au lieu du bandeau, même si l'air de dehors est plus sec. Avant, une preuve ne pouvait que monter.
- L'aération qui se termine est notée tout de suite comme geste vu (prévu, mesuré), sans attendre la nuit (`opening.closed_cases`). La nuit ne l'efface plus si un trou de l'historique l'empêche de la relire.

### 3.0.5 — 3 novembre 2026

- La fenêtre ouverte est regardée au travail (`advisor/opening.py`). Au premier pas où elle est vue ouverte, le moteur garde ce que le jumeau lui prête. Dix minutes plus tard, il compare à la mesure : la température d'abord, l'eau de l'air si la température bouge trop peu. Le reste de l'aération est jugé avec la part réellement faite (0 à 1,5 fois la prévision). Chambre P, 3 novembre, un battant entrouvert : 12 % de la prévision. « Laissez ouvert encore 10 min · 13,6 points d'humidité en moins » devient « Rien à faire », avec en « Bon à savoir » : « Ouverte depuis 19 h 19 : 18,2 → 18,1 °C, 67 → 69 % : elle renouvelle peu l'air ». La part est notée dans le journal (`part_fenetre`).

### 3.0.4 — 3 novembre 2026

- « Cette nuit, pensez à ouvrir » seulement si le foyer ouvre la nuit (« Ouvrir une fenêtre la nuit », éteint par défaut). Avant, le conseil du soir oubliait ce réglage : la Chambre P le disait le 3 novembre, quand personne n'ouvre la nuit.
- Nouveau « Bon à savoir » quand l'humidité est en jeu (fenêtre ouverte, humidité au-dessus de son repère, geste ou essai pour elle) : l'air de dehors dit en eau, pas en %. Par exemple « Dehors 78 % à 9,9 °C, mais moins d'eau qu'ici : 7,3 g par m³ contre 10,7 ». Sinon « plus d'eau qu'ici, aérer fait monter l'humidité » ou « autant d'eau qu'ici ». Sans lui, le % de dehors semblait contredire le conseil.
- Le soir, l'humidité se dit en valeur (« 62 % d'humidité au lieu de 70 % ») et non plus en points. La carte ne répète plus « Cette nuit, pensez à… » dans « Bon à savoir ».

### 3.0.3 — 3 novembre 2026

- L'humidité se dit en valeur, à l'heure où le geste fait le plus : « Vers 19 h 35 : 56 % d'humidité au lieu de 67 % ». Avant : « 13,6 points d'humidité en moins », une différence à recalculer soi-même (Frank : « c'est vraiment difficile à comprendre »).
- La carte n'affiche « Optimisé par l'apprentissage » que pour un effet avéré dans la pièce. Avant, elle l'affichait aussi pour un effet seulement probable : la Chambre P le portait pour une fenêtre jamais vue ouverte.

### 3.0.2 — 3 novembre 2026

- « Plus tard » seulement pour ce que le dehors apporte (plus frais, plus sec, le soleil parti). Le moment tardif est rejoué avec le dehors figé : si la pièce seule explique qu'il batte la même aération maintenant, il est écarté. Avant, le CO₂ qui remonte d'ici la fin de la prévision (3 h) faisait paraître tout moment tardif meilleur, et le moment reculait sans jamais venir (Salon · Cuisine, 15 h à 18 h). « Aérez » vient quand aérer maintenant en vaut la peine.
- « Laissez ouvert encore 10 min » se dit face à « Refermez maintenant », et non face à la fenêtre laissée ouverte trois heures : la Chambre P, ouverte pour l'humidité, disait « 2,4 kWh de chauffage économisés » ; elle dit « 11 points d'humidité en moins ».
- Avant sa première nuit, une pièce reçoit 5 % du poêle, celle où il se trouve 60 % (au lieu de 20 % partout) : au labo, la Chambre M prévoyait 30 °C à 20 h à l'allumage du poêle et disait « Ouvrez ». Appris ensuite : 74 % au Salon · Cuisine, 0 à 27 % ailleurs.
- Une surface déclarée après coup garde la chaleur déjà apprise : seuls les jumeaux de l'air sont refaits.
- L'apprentissage de nuit fouille les 7 derniers jours (les gestes restent comptés sur tout l'historique) et ne refait plus deux fois la même prévision d'une heure : 4 jours en 3,5 s au lieu de 5,2 par pièce sur le banc, 12 jours en 7 s au lieu de 19, et un historique de 60 jours ne coûte plus que 7 jours. Même résultat qu'avant jusqu'à 7 jours.

### 3.0.1 — 3 novembre 2026

- Un « plus tard » annoncé ne recule plus à chaque calcul : « Aérez 5 min vers 17 h 15 » reste 17 h 15 tant qu'aucun autre moment ne fait nettement mieux. Avant, le moment annoncé n'était jamais comparé (les moments comparés sont espacés d'un quart d'heure à partir de maintenant), et le Salon · Cuisine a dit « dans une heure » de 15 h à 18 h.
- Un « même air » a le volume de toutes ses pièces : les surfaces déclarées du Salon et de la Cuisine s'additionnent. Avant, seule la pièce qui conseille comptait.
- Une surface déclarée après coup refait les jumeaux à la bonne taille (les effets observés sont gardés, la nuit réapprend le reste). Avant, ils gardaient pour toujours les 40 m³ d'une pièce ordinaire : au labo, le CO₂ du Salon · Cuisine montait presque trois fois trop vite.
- « À propos » le dit « 3.0.x bêta » tant que la génération 3.0 n'a pas fait ses bêtas dans de vraies maisons (`BETA` dans `advisor/__init__.py`). Le numéro écrit dans les instantanés et le journal reste nu.

### 3.0.0 — 3 novembre 2026

Le moteur entre dans l'intégration (étape C de `PASSAGE-CONFORT-3.md`). Il reprend tout ce qui a été mis au point au labo depuis le 31 octobre :

- conseils par comparaison de gestes simulés sur les jumeaux de chaque pièce (chaleur, humidité, CO₂, particules, COV) ;
- interdits de sécurité : pluie, rafales, vigilance, absence, gel ;
- la plage suit le thermostat, le poêle simulé, « Coupez le poêle » quand la consigne est dépassée trop longtemps ;
- durées de 5 en 5 min, « Laissez ouvert encore N min », source du moment, air traversant ;
- conseil gardé au moins 30 min tant qu'il aide, pas d'appareil conseillé la nuit ;
- « Bon à savoir » : le soleil en une ligne, seulement quand il compte ;
- apprentissage de chaque nuit, avec les fenêtres recalées sur les vraies ouvertures ;
- un geste « plus tard » dit son heure (« Aérez 15 min vers 13 h 50 »).
