# Versions du moteur de conseil

Le moteur de conseil (`custom_components/hestia_comfort/advisor/`) a son propre numéro, à part de celui de l'intégration : `VERSION` dans `advisor/__init__.py`.

Il est écrit dans chaque instantané, dans le journal des conseils, dans les avis « Ce conseil ne va pas » et dans le rapport de chaque nuit. Le panneau l'affiche dans « Versions et liens ». On sait ainsi, conseil par conseil, quelle version l'a donné, et on peut comparer avant et après une amélioration.

## La règle

Règle revue par Frank le 5 novembre 2026, à partir de 3.9.0 : le numéro du milieu ne monte plus à chaque ajout.

- **Majeur** (3.9.0 → 4.0.0) : une nouvelle génération du moteur ; les jumeaux appris ne sont pas repris, ils sont réappris.
- **Mineur** (3.9.0 → 3.10.0) : un changement intermédiaire : un nouveau geste, une nouvelle source ou une nouvelle série de questions, une autre façon de décider pour toutes les pièces.
- **Correctif** (3.9.0 → 3.9.1) : un petit ajout, un réglage, un calcul affiné ou une correction.

En cas de doute entre les deux derniers, c'est un correctif.

Chaque changement du moteur monte son numéro et ajoute une ligne ci-dessous, la plus récente en haut.

Chaque version a aussi sa ligne en mots simples dans [CHANGELOG-MOTEUR.md](../../CHANGELOG-MOTEUR.md), le changelog du moteur publié avec Confort (règle dans [RELEASES.md](../../RELEASES.md)). Ici, le détail technique ; là-bas, ce que la famille voit changer.

## Historique

### 3.9.0 — 5 novembre 2026

« Volets fermés quand vous partez » seulement pour une absence de 2 h ou plus (`Habits.shutters_away_after`, clé `volets_absence_apres_h`, 2 h par défaut, pas encore dans le panneau). Salon, 5 nov. : alarme en absence 24 min à midi, volets ouverts en plein soleil (FP2 165 lx), le moteur les croyait fermés.
- En direct (`room/advice.py` `_away_for`) : heures depuis le `last_changed` de l'alarme, ou depuis le début de la journée vide déclarée ; les volets comptent fermés une fois les 2 h passées.
- La nuit (`nightly._absences`, `_absence`) : durée totale de chaque absence lue dans l'historique de l'alarme (encore en cours = jusqu'à la fin de la lecture) ; une absence courte n'est jamais lue volets fermés, une longue l'est d'un bout à l'autre ; sans alarme, la durée de la journée vide déclarée.
- `Habits.shut(…, away_for=None)` : sans durée connue, l'absence compte comme avant.

### 3.8.0 — 5 novembre 2026

Confiance de Hestia Weather dans sa station (`niak-weather-integration/docs/STATION-EMPLACEMENT.md` § 4 et § 5, `api.station_trust(entry_id)`), lue par `weather_link.station_trust` ; un Weather qui ne la donne pas (ou qui échoue) = capteurs bruts, comme `station_shade`. Appliquée seulement si le capteur de Confort est celui de la station de Weather (`weather_link.from_station` : capteurs de `api.station`, ou `pluie_en_cours`).
- Température : `temperature.now` « forecast » ou « corrected » → `advisor_home._read_outdoor` prend `temperature.value` (mur ou toit au soleil : la prévision, ou la mesure moins l'écart appris) ; l'humidité suit à eau égale (`water.relative(retenue, absolute(mesurée, HR))`). `coming()` part de la valeur retenue : l'écart station − prévision dû au mur n'est plus prolongé sur douze heures. `outside()` ajoute `station_mesuree` et `retenue` (valeur, `now`, `why`).
- Vent : `wind.now` « forecast » (côté abrité) → `safety()` passe à `forbidden` la plus forte des rafales, station de Confort ou `wind.value` (km/h).
- Pluie : `rain.level` « handled » (pluviomètre sous un arbre ou un avant-toit) → `rain_believed(…, sheltered=True)` croit la pluie annoncée sans attendre de goutte (plus d'abandon au bout de `RAIN_SOON_WAIT`) ; la pluie mesurée interdit toujours.
- Pas encore : l'apprentissage de nuit lit toujours l'historique brut de la station (heures de mur au soleil comprises).
- Tests : `tests/test_station_trust.py` (10).

### 3.7.0 — 5 novembre 2026

Habitudes du foyer et « Votre maison » (`niak-comfort/docs/HABITUDES-FOYER.md` v1.0, validé par Frank le 5 novembre).
- `household.py` : `Habits.shutters_away` / `shutters_night` / `shutters_summer` (`volets_absence`, `volets_nuit`, `volets_ete` : `fermes` · `ouverts` · `variable`, défaut `variable` = rien ne change), `empty_day` (`journee_vide` {de, a}), `laundry` (`linge_pieces`, gardé, pas encore lu par une règle), `Sleep.weekend_end` (`sommeil.fin_weekend`) ; `Habits.away` (alarme absent ou vacances, sinon heures vides en semaine si aucune alarme), `Habits.shut`.
- `nightly.py` : `RoomSpec.panes`, `manual`, `habits`, `alarm`, `summer` ; `_shut_windows` lit l'alarme dans l'historique. Volet à la main fermé = surface de la fenêtre × `SHUT_SHADE` dans le soleil des façades, plus `shutter_insulation(surface, 1)` ; sans orientation, l'ombre de la pièce baisse de la part fermée. `advisor_home.learn` passe habitudes, alarme et saison (`summer` = saison de Weather).
- `room/advice.py` : même fermeture pour les prévisions (`coming`) et pour la nuit (`night_coming`, plus les volets de nuit si `fermes`) ; heures vides sans alarme = `armed_away` pour `safety.forbidden` (pas les vacances).
- Vitrage par type : `thermal.GLAZINGS` (g, U) simple 0,85 / 5,8, double 0,6 / 2,8, triple 0,5 / 1,0 dans `ordinary` ; facteur solaire par fenêtre en 4ᵉ élément des tuples de `through_windows` (défaut `GLASS` 0,6) ; buée par `surface.GLASS_FACTORS` (1 − U·0,13 : 0,25 / 0,64 / 0,87), la vitre la plus froide de la pièce. Vitrage de l'ouvrant (`openings.*.glazing`), sinon `foyer.vitrage`.
- « Votre maison » (`foyer.py`) : `volet`, `hauteur`, `murs`, `plage` ; `spec()` les prend pour l'ouvrant ou la pièce qui n'a pas les siens ; la plage cède au thermostat comme avant (`from_thermostat`). `repondu` : questions déjà vues.
- Tests : `tests/test_habitudes_foyer.py` (15).

### 3.6.0 — 5 novembre 2026

- Soleil sous une avancée par son ombre (`physics/sunlight.py` `Overhang`, `lit_share`) au lieu de `SHELTER_ATTENUATION` = 3 : part de la hauteur de la fenêtre éclairée = 1 − (A·tan(angle de profil) − B) / hauteur, angle de profil = tan(élévation) / cos(écart d'azimut) ; diffus × `SKY_UNDER` = 0,7. A et B lus dans `overhang_depth` / `overhang_gap` (« Avancée au-dessus », jamais lus jusque-là), sinon 0,6 m / 0,3 m si « Abritée » est cochée ; hauteur = celle de la fenêtre. `room/advice.py` `_overhang` met l'`Overhang` (ou False) à la place du booléen dans `orientations` : nuit et conseil en direct. La pluie garde le booléen (`sheltered`).
- Porte-fenêtre sud du Salon (A = 1 m, B = 0,3 m, 2,1 m) : 86 à 96 % éclairée de 10 h à 16 h le 5 novembre (avant : 33 %), moins de 5 % le 21 juin à 13 h 30.
- Rejeu du Salon · Cuisine sur l'historique du labo (31 oct. → 5 nov.) : le jumeau garde ~5 % du soleil calculé (`glass` 0,05) quel que soit le calcul, soit +0,2 °C prévus. Pas de journée propre : lundi 2 volets manuels fermés (absents ; FP2 5-13 lx à midi contre 70-270 lx), poêle aux heures de soleil les 1er, 3 et 4. Les volets manuels fermés seront traités à part (formulaire prévu par Frank).

### 3.5.0 — 5 novembre 2026

- Arrêt tôt des recherches (`physics/fit.py` `_nelder_mead`, `SETTLED` = 0,05 %) : fin dès que les sommets ne diffèrent plus que de 0,05 % (relatif), ou que le meilleur coût est infini (capteur sans historique). Avant, toujours 300 (chaleur) ou 400 (air) tours ; un coût plat multipliait les rétrécissements (Chambre test, humidité 0,001 → 0,001 : 3 328 évaluations, 26 % de la nuit). Rejeu de la nuit du 5 novembre (base du labo copiée) : 170 s → 38 s en local (28 min → ~6 min au NAS), coût d'entraînement atteint à moins de 1 % de la recherche complète (2,3 % au pire), décisions dans le bruit.
- Jugement sur la veille (`nightly.judged`, `EVEN` = 1,05) : le nouveau jumeau est gardé s'il prévoit la veille pas plus de 5 % moins bien (« egal »), plus seulement s'il fait mieux (« meilleur ») ; « pire » refusé ; un jumeau à erreur infinie jamais gardé. Nuit du 5 : 9 refus sur 15 étaient à moins de 5 %, le même jumeau inchangé ratant sa veille du simple au double d'un jour à l'autre. Rejeu : 8 meilleurs, 7 égaux gardés, 8 refusés (avant : 7 gardés, 15 refusés). Rapport de nuit : champ `verdict` ajouté, `avant`/`apres` à `null` au lieu d'`Infinity` (JSON invalide, jumeau COV du Salon).
- Mesures et banc : note `apprentissage-de-nuit-mesures.md` (dossier des sessions). Reste : Chambre P humidité jamais apprise depuis le 3 novembre (+31 % sur la veille), jumeau à revoir à part.

### 3.4.0 — 5 novembre 2026

- Aération en cours (`decide.under_way`) : une fois la fenêtre ouverte, le geste « open » ou « open_more » de N min montré au pas précédent (ou montré « À essayer », `tried`, avec `held` remis à 0) devient `Gesture("close", after=N)`, « Laissez ouvert encore N min ». Avant, les scénarios d'une pièce ouverte ne parlant que de refermer, le geste suivi disparaissait et la carte disait « Rien à faire — Ouverte ou fermée » (Salon · Cuisine, 5 novembre 7 h 26, porte-fenêtre ouverte sur « Aérez 5 min », fixture `salon-cuisine-5-novembre-7h26.json`). Le maintien (`HOLD_MINUTES`) garde aussi un « close » tant qu'il ne coûte pas plus que laisser ouvert, sans le gain `GAIN / 2`.
- Jumeau d'air jamais appris (`airfit.untrained`) : paramètres identiques à ceux du départ (`first`) = aucune nuit ne l'a ajusté aux mesures (capteur sans historique, ou jamais mieux). `RoomAdvisor._proof` ne le renforce plus par le moment : sujet « supposed », geste « À essayer » seulement. Au labo, le jumeau COV du Salon (`sensor.cov_cuisine` absent de l'enregistreur, erreur de la nuit infinie) mettait « Aérez 5 min — le COV retombe en 5 min » au bandeau. `phrase()` dit au conditionnel tout effet non prouvé (avant : seulement « reinforced »), pour un geste supposé gardé à l'écran.
- Pluie annoncée qui ne vient pas (`safety.rain_believed`, `AdvisorHome.rain_soon_since`) : « la pluie arrive » (≤ `RAIN_SOON`) crue `RAIN_SOON_WAIT` = 45 min sans pluie mesurée par la station, puis ignorée jusqu'à la pluie mesurée ou une prévision au-delà de `RAIN_GONE` = 60 min (ou aucune). Sans pluviomètre, toujours crue. Nuit du 4 novembre : radar à 20 min dès 20 h 16, premières gouttes à 21 h 49, pluie à 22 h 27.

### 3.3.0 — 4 novembre 2026

- L'ombre de la station vient de Hestia Weather quand il la partage (`api.station_shade`, Weather 3.1, CAHIER-MOTEUR.md § 7.4) : apprise chaque nuit sur 92 jours de statistiques horaires du capteur de soleil face à Open-Meteo (global, direct, diffus, nuages), complétée par les cases voisines puis par l'ombre déclarée par le foyer. `AdvisorHome.shade()` la donne aux nuages manqués (`clouds_missed`) ; l'ombre apprise par Confort (`station_shade`, 7 à 60 jours d'historique) ne sert plus qu'avec un Weather plus ancien, et sa nuit n'est plus faite sinon.
- Banc du 4 novembre (56 jours de la GW2000A de la maison) : 31 cases apprises dès la première nuit (28 identiques à la règle du ciel clair, 3 de plus par le rayonnement direct), 143 des 161 positions du soleil connues avec les voisines. Au labo, dont l'archive commence le 31 octobre, Confort seul n'en avait appris aucune.
- `outside()` (« Fiabilité », « Le dehors ») : `ombre_cases` (apprises), `ombre_positions` (positions du soleil ici sur un an), `ombre_connues`, `ombre_declaree`, `ombre_source`.

### 3.2.0 — 4 novembre 2026

- Planning du chauffage lu dans ha-chauffage (issue #42, `engine/schedule.py`, `schedule_link.py`) : « Prochain changement » (`…_next_change`, armellarcier/ha-chauffage#82) s'il existe, sinon « Préréglage prévu » (`next_start`, `next_preset`, `temperatures`), et la fin de la dérogation quand elle est en cours (le créneau annoncé peut alors ne jamais venir). À défaut, Scheduler (issue #46) : les plannings en marche qui pilotent le thermostat (`entities`), l'action du prochain créneau qui change quelque chose (`actions`, `next_slot`, `next_trigger`), la température du préréglage lue dans le Versatile Thermostat ; le plus proche de plusieurs plannings. Ses conditions (jour ouvré, présence) ne sont pas prévues.
- `Thermostat.then` / `Thermostat.at` : la consigne du créneau suivant et dans combien de minutes ; `scheduled(minutes)` la donne à chaque pas de chaque scénario, aussi pour « Rallumez » et « Remettez le chauffage à … » (la consigne donnée à la main ne tient que jusqu'au créneau suivant). `heating_back` en tient compte de lui-même.
- Note « Chauffage prévu à {at} : {temperature} °C visés » (`knowing.heating_planned`) quand le créneau suivant relève la consigne dans les 6 h, jamais pendant le sommeil ; un plan, donc prouvé.
- `features.planned` : le prochain changement, pièce froide ou non (la carte complète le met dans « À venir »). `schedule.heard` le tait dans une pièce non chauffée et quand le chauffage est éteint (mode `off`, ou chauffage hors Versatile Thermostat à l'arrêt), sauf si le changement le rallume (`heat`, `auto`, `heat_cool`) ou que l'arrêt est une pause que le thermostat lève seul (fenêtre, délestage, sommeil, sécurité, inhibition).
- `schedule.is_schedule` : un planning Scheduler reconnu à ses attributs (`entities`, `actions`, `timeslots`, `next_trigger`), même recopié par Remote Home-Assistant.

### 3.1.1 — 4 novembre 2026

- « À essayer » tient comme le bandeau : l'essai affiché reste tant qu'il est presque aussi bon que le meilleur (même marge), et il traverse une rafale qui l'interdit un instant. Chambre AL, 4 novembre, rejeu de 14 h 18 à 16 h 53 : 6 changements de geste au lieu de 12 (30 changements de texte depuis 21 h la veille).
- L'heure annoncée pour l'humidité est arrondie au quart d'heure. Pour une fenêtre laissée ouverte, c'est l'heure de fin de la prévision (« 58 % d'humidité à 18 h au lieu de 70 % ») : elle n'avance plus de 5 minutes à chaque calcul.
- Une règle de sécurité qui fait refermer (pluie, rafales) ne fait plus échouer le conseil d'une pièce dont la fenêtre vient d'être vue ouverte (Salon · Cuisine, 4 novembre à 6 h 26).

### 3.1.0 — 4 novembre 2026

- Une note pour chaque geste (CAHIER-MOTEUR.md § 15.1, proposé par Frank, `advisor/notes.py`). Une aération, une marche de la VMC rapide ou du purificateur est jugée **1 h après sa fin**, contre le jumeau **sans le geste** : effet annoncé (avec − sans) et effet mesuré (mesuré − sans). Note + (de la moitié au double, ou plus), 0 (moins de la moitié), − (l'inverse).
- Rien n'est noté si autre chose a agi pendant le geste ou l'heure qui suit : fenêtre rouverte, VMC ou purificateur qui change, source d'humidité (douche, cuisine). Un geste écarté le jour (`ecartes`) l'est aussi la nuit.
- La nuit corrige chaque catégorie (pièce × geste × sujet) vers la médiane de ses notes récentes (poids divisé par 2 en 15 jours, 3 notes au moins), au plus ×2 ou ÷2 par nuit, gardée si la dernière journée n'est pas prévue plus de 5 % moins bien. Pour la chaleur, elle remplace l'ancienne correction des fenêtres ; pour l'humidité, le CO₂, les COV et les particules, elle est nouvelle ; la part du débit de la VMC (`boost_scale`) et du purificateur (`purifier_scale`, nouveau) en viennent aussi.
- Preuves : « appris » si la médiane des 10 dernières notes est entre la moitié et le double ; « démenti » dès que les 2 dernières sont à 0 ou −, quoi qu'il y ait eu avant.
- « Ce que Hestia-FB sait » reçoit pour chaque effet ses dernières notes (« 0 0 − ») et la correction de la nuit.

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
