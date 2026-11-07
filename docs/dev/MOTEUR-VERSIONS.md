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

### 3.12.0 — 7 novembre 2026

Moins de yoyo, après le bilan d'une journée en prod (7 novembre, moteur 3.10) et au labo (3.11.2) ; accord de Frank sur les quatre points et sur l'alarme (« on parle de confort, pas de sécurité »).
- `room/advice.py` : **« À essayer » n'était jamais retenu** — `self.tried` effacé au même pas que noté (`elif gesture != nothing or not taken`) ; effacé maintenant seulement sans `passive`. C'est ce qui le faisait clignoter (Chambre M, 20 h 20-20 h 45).
- `advisor/opening.py` : `seen_shares(..., read=)` et `failed(..., read=)` lisent chaque mesure à l'heure où le capteur l'a envoyée (`last_reported`) et seulement envoyée `OBSERVE_MINUTES` après l'ouverture ; les minutes dites sont celles de la mesure. `room/advice.py` `_sent()`. Chambre A, 9 h 39 : « ne fait pas l'effet prévu, 68 → 67 % » sur une valeur envoyée à l'ouverture (capteur muet de 9 h 24 à 9 h 56, puis 63 %).
- `advisor/decide.py` : le geste du bandeau tenu (`hold`, HOLD_MINUTES) l'emporte sur un nouveau meilleur seulement « À essayer » (règle `kept`) ; « À essayer » (`tried`) tenu tant qu'il gagne GAIN/2 quand plus rien ne vaut GAIN (même pause `aired` que `worth`).
- `advisor/decide.py` : `_past_bedtime` → `late(g, held=False)` ; un geste pas encore affiché finit `BED_MARGIN` (15 min) avant le coucher, « Ouvrez » sans fin interdit dans les 2 × `airing_max` dernières minutes ; un geste déjà affiché (`previous`, `tried`) garde la règle de 3.11.2.
- `room/advice.py` : `GRACE_MINUTES` (3) — un « Refermez » de confort (`best`/`kept`, sans `after`) sur une ouverture de moins de 3 min, sans « Refermez » déjà affiché, est redécidé pièce fermée (`decided_on`) ; l'instantané garde ces entrées ; `opened_seen` attend la fin de la grâce. Buanderie : 4 « Refermez » de 20 s à 2 min.
- `advisor/words.py` : `EDGE` (0,3 °C, 2 points, 50 ppm, 2 µg, 10) et `_outside` — près d'une limite, la phrase garde ce que disait le dernier « Rien à faire » (`beyond_before`, attribut `au_dela` du résultat, clé `beyond_before` des instantanés, None pour les anciens).
- `advisor/safety.py` : l'alarme en absence retire `absent` (aucune ouverture proposée) au lieu de `open` : plus de « Refermez » de sécurité. Raison `away` gardée pour « Gardez fermé ».
- Tests : `EveningOf7November`, `TriedKeepsItsMargin` (test_advisor_decide), `EdgeOfTheRange` (test_advisor_words), lecture à l'heure d'envoi (test_advisor_opening), alarme (test_advisor_safety), `AiringEndsByBedtime` mis à la marge. Fixtures `chambre-a-7-novembre-19h58.json`, `-20h28.json`. 884 tests OK.
- Rejeu des 1 873 instantanés du labo (3-7 nov.) : 5 conseils changés, aucune erreur — Chambre A le 7 à 19 h 58 (geste tenu), Chambre P le 4 à 19 h 54 (« Aérez 10 min » tenu), Chambre AL le 6 à 12 h 57 et 13 h 42 (« À essayer » gardé), Chambre M le 7 à 21 h 02 (« Ouvrez » à moins d'une heure du coucher). Le gain principal est dans l'enchaînement des pas, que les instantanés isolés ne montrent pas.

### 3.11.2 — 7 novembre 2026

L'aération finit au coucher de la pièce (Frank, 7 novembre, Chambre A couchée à 21 h, « Aérez 30 min » à 20 h 27).
- `advisor/decide.py` : `Now.bed_in`, minutes jusqu'au coucher (`Sleep.bedtime`), None la nuit ; gardé dans les instantanés, None pour les anciens. `_past_bedtime(now, habits)` : un « open »/« open_more » qui finit après le coucher (`after + minutes`), un « close » après lui, « Ouvrez » sans fin dans les `airing_max` dernières minutes ; demi-pas de marge ; rien la nuit ni avec `open_at_night`.
- `decide` : `previous` et `tried` qui débordent ne sont plus tenus ; juste avant le choix du geste (après le tri des aérations « plus tard »), les gestes qui débordent sortent de `worth`. Si le geste qu'on aurait conseillé débordait (`cut`), une ouverture plus courte reste seulement si son effet est PROVEN — ni bandeau, ni « À essayer » sinon. Aucun scénario de plus simulé.
- `room/advice.py` : `bed_in` donné à `Now` ; heure du chauffage prévu arrondie à la minute (`planned`).
- Tests : `tests/test_advisor_household.py` `AiringEndsByBedtime` (instantané réel Chambre AL du 4 novembre).
- Rejeu des 1 830 instantanés du labo (3-7 nov.) : 7 conseils changés — Chambre A le 7 à 20 h 33 (« Ouvrez » sans fin, coucher dans 26 min → rien), Chambre M le 5 de 21 h 33 à 21 h 48 (« Refermez dans 45-60 min » → 10-15 min, coucher à 22 h). Temps de décision identique (43,3 s → 43,2 s).

### 3.11.1 — 7 novembre 2026

Les gestes conseillés gardent leurs kWh, pour Hestia Énergie (`hestia_comfort_api.gestures`, INTERFACE.md d'Énergie § 2, CAHIER-MOTEUR § 17). Rien de recalculé, aucun conseil changé.
- `advisor/decide.py` : `gesture_energy(paths, gesture)` → `(kWh, heated)` = `paths[geste].spent − paths[rien].spent`, l'écart que la trace montre déjà ; None si l'un des deux n'est pas simulé (les « Fermez » de sécurité).
- `advisor/feedback.py` : `Asked.kwh`, `Asked.heated`, pris au premier affichage (`follow(..., energy)`) ; `_record` ajoute `kwh` et `chauffage` (aussi dans `retours.jsonl` quand l'analyse est allumée).
- `room/advice.py` : `RoomAdvisor.gestures`, les gestes finis (suivis ou remplacés) avec `fin`, gardés `GESTURES_KEPT` (62 jours) dans le Store de la pièce (clé `gestures`) ; `gestures_between(start, end)` y ajoute le geste encore affiché (`fin` None). Ne dépend pas de l'interrupteur `analysis`.
- `api.py` : `gestures(entry_id, start, end)`, `version` reste 1. Tests : `tests/test_api_gestures.py` (instantanés réels du labo).
- Rejeu des 1 682 instantanés du labo (3-7 nov.) : 379 gestes affichés sur 381 retrouvent leurs kWh, 374 égaux à la trace gardée ; chaîne complète pièce par pièce : 99 gestes, 97 avec kWh, gestes et « suivi » conformes à `retours.jsonl` (les écarts viennent des instantanés, gardés seulement aux changements de conseil).

### 3.11.0 — 6 novembre 2026

Le réglage « Allergie aux pollens » (`home.pollen_allergy`, Confort 2.1.0b2) n'était plus lu par le moteur 3. Règle revue et validée par Frank le 6 nov. (les quatre choix recommandés, puis la durée nécessaire pour l'humidité et le CO₂ après le rejeu des 3-6 nov.). Nouvelle source : les pollens du jour de Hestia Weather (`api.pollen`, via `configuration.pollen()`, donnés seulement si quelqu'un est allergique).
- `advisor/pollen.py` : `Pollen` (niveau, espèce principale, bons moments en minutes depuis maintenant, `after_rain`, `open_for`) et `today()` : None sauf `high` (niveau ≥ 3). Bons moments : les `MORNING` (2) heures après le réveil (`Sleep.end_on`, aujourd'hui et demain) et les `RINSED` (60) minutes après la pluie mesurée (`RoomAdvisor.rained_at`, posé quand `rain_rate > safety.RAIN`).
- `decide(pollen=)`, après les coûts : (1) `open`/`open_more` dont le sujet principal n'est pas dans `FREE` (humidité, moisissure, CO₂) retiré des scénarios s'il n'est pas à un bon moment (`after`) ou s'il dure plus de `AIRING` (10) min ou sans fin (`_too_long`) : ni conseillé, ni gardé, ni « À essayer ». Les sujets `FREE` gardent la durée qu'il leur faut (choix de Frank après le rejeu : bornées à 10 min, les aérations de la Chambre A pour son humidité ne changeaient plus rien et disparaissaient — environ 150 cas sur 1 645). (2) Fenêtre ouverte : si la laisser encore ouverte (pour de bon, `keep`, ou `close` plus tard) n'aide pas un sujet `FREE` (`_needed`, `significant` contre refermer maintenant), « Refermez » dès `open_for ≥ 10 min` (règle `pollen`, phrase `pollen_close`) ; avant, ni `keep` ni `close` plus tard que ce qui reste des 10 min.
- `tonight(pollen=)` : jamais « Cette nuit, pensez à ouvrir ».
- « Bon à savoir » : `knowing.pollen_today` → « Pollens élevés aujourd'hui (graminées) : aérez seulement si c'est utile, de préférence tôt le matin », ou après la pluie « La pluie a lavé l'air des pollens : bon moment pour aérer » (fr, en, de).
- Instantanés : `pollen` capturé et rejoué. Tests `tests/test_advisor_pollen.py`. Sans allergie ou sans pollens élevés, rien ne change.

### 3.10.0 — 6 novembre 2026

Chambre P, 6 nov. : 74 % sans conseil d'aérer ; ouverte quand même par Frank à 16 h 20, l'humidité baisse (74 → 71 % en 28 min, 19,5 → 18,7 °C), alors que le jumeau prévoyait 16,7 °C et 83 % en 30 min. Coefficient de fenêtre appris 6,73 (Chambre A 0,42 pour une fenêtre comparable). Puis demande de Frank : dire quand un conseil suivi ne marche pas, et plus de nuances.
- `physics/thermal.WINDOW_RANGE` (0,1 – 1,5, comme `opening.LOWEST/HIGHEST`) et `bounded()` : appliqué au chargement des jumeaux (`room/advice.py`), dans `fit.params_of` et `fit_windows`. Chambre P : 6,73 → 1,5 ; la prévision de chaleur fenêtre ouverte devient juste (18,6 °C prévus, 18,7 °C mesurés à 30 min). L'eau reste sous-estimée (74 % prévus, 71 % mesurés) : à corriger par la note de l'aération du jour, la nuit.
- `opening.seen_shares` : la part de la fenêtre lue à part sur la chaleur et sur l'eau ; `scaled(twins, share, water=)` règle les flux d'air (eau, CO₂, particules, COV) sur la part de l'eau quand elle est lue. Avant, la part de la chaleur (0,16) s'appliquait aussi à l'eau (lue 1,5) et le jumeau voyait l'humidité monter. `seen_share` garde son sens (chaleur, sinon eau).
- `opening.failed` + `decide(failed=)` : l'aération montrée (bandeau ou « À essayer ») puis suivie dans l'heure (`RoomAdvisor.aim`, `AIM_MINUTES`), lue après 10 min (`OBSERVE_MINUTES`) à moins de `INEFFECTIVE` (0,3) de sa prévision sur son sujet (humidité ou moisissure : l'eau ; chaleur : la chaleur) → « Refermez », règle `ineffective`, phrase mesurée (`words["ineffective"]`). « Noté : ici, la fenêtre sèche moins que prévu. Hestia en tiendra compte » dans « À savoir » pendant `RESTING_MINUTES`. La mémoire elle-même = la note de l'aération jugée 1 h après la fermeture (`proof.belied`, réglage de nuit de la fenêtre). CO₂, particules, COV : pas encore lus à part, jamais dits inefficaces.
- `words.phrase` : trois façons de dire un gain selon `decision.level` — avéré tel quel ; probable `…_likely` (« devrait ») ; supposé `…_maybe` (« pourrait ») + `words["maybe"]` (« , à vérifier »). Une phrase sans forme propre garde « , sans doute ». Les faits mesurés (`ineffective`, `overheat`, sécurité) jamais au conditionnel. `sure=False` (« À essayer ») = au plus probable.
- Instantanés : `failed` capturé et rejoué. Fixture `chambre-p-6-novembre-16h20.json` ; tests `ReadApart`, `WithinPhysics` ; phrases revues dans `test_advisor_decide/proof/words`.

### 3.9.6 — 6 novembre 2026

Bilan de la nuit du 5 au 6 nov.
- Chambre M, 5 nov. de 21 h 40 à 21 h 49 : « Laissez ouvert encore 45 min » à chaque pas. `RoomAdvisor.previous` gardait le geste déjà vieilli avec l'heure du pas ; vieilli de nouveau au pas suivant (1 à 2 min plus tard) et arrondi aux 5 min (`aged`), il revenait à 45. → `decide.remembered(shown, at, decided, now)` : un compte à rebours que la décision garde compte depuis le moment où il a été dit ; même chose pour `tried`.
- Chambre A et Salon, 6 nov. de 8 h 06 à 8 h 36 : « la pluie arrive » allumé, éteint, rallumé (prévision autour de 20 min). → `safety.rain_believed` : une fois dite (`since` posé), la pluie reste « proche » (`RAIN_SOON`) tant que la prévision reste à `RAIN_SOON_KEPT` (40 min) ou moins, dans l'attente de `RAIN_SOON_WAIT` (45 min) ; au-delà de 60 min ou sous la pluie, comme avant. Sans pluviomètre, rien ne change.

### 3.9.5 — 5 novembre 2026

Frank, 5 nov. : « À essayer — Aérez 5 min » à Chambre P à 21 h 22, radiateur en chauffe ; est-ce pertinent selon le type de chauffage ? Proposition validée le 5 nov.
- Sept types (`advisor/physics/heaters.py`, `HEATERS`), lus dans le réglage « Type » de chaque chauffage (`heaters[].kind`) : `radiator` (convecteur ou soufflant, défaut), `radiant`, `inertia` (inertie fluide, pierre, fonte, radiateur à eau), `floor`, `stove` (bois, insert), `pellet`, `ac` (clim réversible, PAC).
- La chaleur rendue suit la chaleur demandée avec un délai du premier ordre (`given_off`) : 0 pour convecteur, rayonnant et clim ; 20 min granulés ; 30 min inertie ; 1 h poêle à bois ; 3 h plancher. Le compteur compte la demande (`Path.heating`), la pièce reçoit la chaleur rendue. Départ : la demande actuelle du thermostat, fenêtres telles qu'elles sont ; le poêle part de sa part mesurée (`house_now`).
- Un poêle à bois n'est pas coupé par une fenêtre ouverte (`Heater.window_cut`), quel que soit son thermostat.
- Clim réversible : kWh payés = chaleur / 3 (SCOP ordinaire).
- `Thermostat.kind` (facultatif, gardé dans les instantanés) ; `room/advice.py` `heater_kinds` lit le type dans toutes les pièces (celui d'un poêle est réglé dans sa pièce).
- Sans type réglé, rien ne change (testé : mêmes trajectoires, même décision).
- Instantané réel `tests/fixtures/chambre-p-5-novembre-21h22.json` : Aérez 5 min coûte +0,36 kWh avec un convecteur, +0,51 kWh avec l'inertie et reste « À essayer » (moisissure, effet supposé) ; avec un plancher, « Rien à faire ». Tests `tests/test_advisor_heaters.py`.
- Le délai reste une valeur par type ; l'apprendre pièce par pièce (puissance Versatile × température) est une piste.

### 3.9.4 — 5 novembre 2026

Soir du 5 nov., deux chambres :
- Chambre P, 21 h 33 : « À essayer — Aérez 5 min » 45 s après le « Refermez » qui finissait la première (75 → 73 %). → `decide(aired=)` (minutes depuis la fermeture d'une aération, `RoomAdvisor.shut_at`, gardé au redémarrage) : pendant `RESTING_MINUTES` (60, = `opening.SETTLE`, le temps de juger l'aération), plus d'« Aérez » dont le sujet principal n'est pas dans `FAST_SUBJECTS` (CO₂, particules, COV, mesurés en direct). Une aération de moins de 10 min n'est toujours pas jugée (`opening.settling`).
- Chambre M, 20 h 59 → 21 h 33 : « Refermez », puis « Rien à faire — Ouverte : 17,0 °C à 0 h » avec « À essayer — Laissez ouvert encore 15 min » qui allait 15, 10, 15, 10… → (1) `close` (maintenant ou plus tard) n'est jamais retenu faute de preuve, comme `keep` : la preuve ne règle que le conditionnel ; c'est une exception à CAHIER-MOTEUR § 4.1 ; (2) un compte à rebours affiché (`previous` ou `tried` de type `close`, « Refermez » = 0) n'est jamais allongé : les `close` à `after` plus grand sortent de `worth`.
- Instantanés : `tried` et `aired` capturés et rejoués. Fixtures `chambre-p-5-novembre-21h33.json`, `chambre-m-5-novembre-21h02.json` ; tests `AfterAnAiring`, `test_advisor_proof` revus.

### 3.9.3 — 5 novembre 2026

Frank, 5 nov. : « Laissez ouvert » partout, pas seulement après « Ouvrez ».
- `keep` est dans les scénarios dès qu'une fenêtre est ouverte. Après l'hystérésis (`hold` : une aération suivie garde son « Laissez ouvert encore N min »), un « Rien à faire » fenêtre ouverte devient `keep` (règle `best`) quand refermer maintenant coûte au moins `GAIN` de plus et fait une différence qui se sent (`significant(close, keep)`). Il tient ensuite comme en 3.9.2 (refermer ≥ `GAIN / 2` de plus).
- `keep` n'est jamais « À essayer » : la preuve ne règle que le conditionnel de la phrase (« sans doute »).
- Bandeau bleu « Au mieux » (`banner_level`, `level3` de `advisor3.ts`) : le geste est fait, rien de plus à faire — la phrase de la carte 2.1 « Le geste est fait : l'aération en cours fait son effet » (`room.ts`).
- Tests revus : Salon · Cuisine 5 nov. 7 h 26 sans aération demandée → `keep` (le COV reviendrait) ; Chambre P 3 nov. battant entrouvert → `keep` (59 % à 22 h au lieu de 70 % avec la part réelle de la fenêtre).

### 3.9.2 — 5 novembre 2026

Chambre A, 5 nov. : « À essayer — Ouvrez : 65 % d'humidité à 23 h au lieu de 74 % » à 20 h 31, fenêtre ouverte à 20 h 37, puis « Rien à faire — Humidité 65 % à 23 h : aucun geste ne ferait vraiment mieux » à 67 % (instantané `tests/fixtures/chambre-a-5-novembre-20h38.json`). `under_way` ne reconnaissait que les aérations à durée (« Aérez 20 min » → « Laissez ouvert encore 20 min », Chambre M au même moment) : « Ouvrez » n'a pas de durée, et une fois la fenêtre ouverte, son scénario est celui de « ne rien faire ».
- Nouveau geste `keep` (« Laissez ouvert ») : `under_way` change un « Ouvrez » suivi (bandeau ou « À essayer ») en `keep`, ajouté aux scénarios tant que la fenêtre est ouverte ; même trajectoire que `nothing`, sans dérangement.
- Il tient sans limite de 30 min tant que refermer maintenant coûterait au moins `GAIN / 2` de plus ; sinon le choix redevient libre (« Refermez », « Laissez ouvert encore N min » ou « Rien à faire »).
- `reference(keep)` = refermer maintenant : la phrase dit le gain contre la fenêtre fermée (« 65 % d'humidité à 23 h au lieu de 75 %, sans doute »), « Pourquoi ? » montre Ouverte et Fermée.
- « À essayer » gardé au redémarrage (`state["tried"]` de `room/advice.py`), comme le geste du bandeau.
- Verdict `keep_open`, `feedback.done("keep")` vrai (le geste suivi est l'« Ouvrez »), pictogramme `open` sur la carte (`advisor3.ts`).

### 3.9.1 — 5 novembre 2026

Chambre P, 5 nov. vers 18 h : bandeau « Rien à faire », mais « Baissez le volet ce soir : environ 0,1 kWh de chauffage en moins » dans le Ressenti et « Volet ouvert · à fermer » dans les appareils.
- `knowing.SHUTTER_HEAT, SHUTTER_ENERGY` 0,1 °C / 0,05 kWh → 0,3 °C / 0,25 kWh (la moitié de `SIGNIFICANT["energy"]`).
- Nouveau champ `volet` du conseil (`"fermer"` quand le Bon à savoir du volet est dit, sinon `null`) ; la carte (`room.ts` `shutterAdvice`) prend le volet du moteur 3 et plus la règle 2.1 (`engine/evolution.py` : volet à fermer dès le coucher du soleil si la pièce a besoin de chaleur). Sans moteur 3, la carte garde la règle 2.1.

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
