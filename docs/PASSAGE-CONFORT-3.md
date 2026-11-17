# Passage de Hestia Confort 2.1 au moteur de conseil 3.0

Version 0.2 — 1er novembre 2026. Décisions de Frank prises (§ 8) ; réglages à repenser.

Ce document dit comment le moteur 3.0, en essai dans le HA de test, entrera dans l'intégration publiée.
Il ne décide rien de nouveau sur le moteur : la référence reste le [cahier du moteur](CAHIER-MOTEUR.md) (v0.16).
Rien n'est codé ici. Ce plan sert le jour où la 3.0 aura fait ses preuves (§ 18.3 du cahier).

Sources lues le 1er novembre :
- le moteur 3.0, `custom_components/hestia_comfort/advisor/` (branche `moteur-conseil-3`) ;
- le branchement d'essai, `~/niak-ha-test/config/custom_components/hestia_advisor_dev/__init__.py`, et sa configuration `rooms.json` ;
- le moteur 2.1, `custom_components/hestia_comfort/engine/`, et le reste de l'intégration (coordinateur, entités, LED, panneau, carte).

---

## 1. Quand passer

On ne commence pas le passage avant que ces conditions soient remplies dans le HA de test.

| Condition | Où c'en est (1er novembre) |
|---|---|
| Les indicateurs du § 18.3 tenus, pièce par pièce | jumeaux de la chaleur, de l'eau, du CO₂, des particules et du COV validés au banc ; reste à les tenir sur plusieurs semaines |
| Le journal des désaccords avec la 2.1 revu avec Frank | 137 changements de conseil notés dans `journal.jsonl` |
| Les gestes de la 3.0 (§ 3 bis) tous présents | présents : fermer, ouvrir N min, plus tard, VMC rapide, purificateur, volet relié ; **manquent** : chauffage, climatisation, ventilateur, plan du logement |
| Les entités et l'évènement du § 20.1 décrits dans le code | rien encore : l'essai écrit des capteurs `sensor.conseil_3_*` à la main |
| Le calcul de toute la maison sous une seconde sur un Raspberry Pi 4 | pas encore mesuré sur un Pi |

---

## 2. Où le moteur se branche

### 2.1 Le principe

- `advisor/` reste tel quel : il n'importe rien de Home Assistant.
- Une couche mince fait le lien avec Home Assistant. Elle reprend le rôle de `hestia_advisor_dev/__init__.py`.
- Cette couche a deux parties, comme l'essai :
  - **une partie pour la maison**, créée une seule fois au démarrage (prévisions, soleil, ombre de la station, apprentissage de la nuit, journal) ;
  - **une partie par pièce**, dans le coordinateur de la pièce (mesures, décision, rédaction).
- Le moteur décide **et** rédige. La carte, les entités, les LED et l'évènement lisent la même décision (principe 3).

### 2.2 Les fichiers

| Nouveau fichier | Ce qu'il fait | Repris de l'essai |
|---|---|---|
| `advisor_home.py` | Prévisions de Weather, soleil prévu recoupé par la station, contrôle de l'intégration Soleil, apprentissage de la nuit à 3 h 30, journal | `Engine` : `_refresh_forecast`, `_from_weather`, `_station_clouds`, `_coming`, `_sun_check`, `learn`, `_keep_twins`, `_journal` |
| `room/advice.py` | La pièce : mesures contrôlées, jumeaux, interdits, décision, phrases, « Bon à savoir », « Cette nuit », suivi des gestes | `Engine._advise` et ses aides (`_measures`, `_missed`, `_proof`, `_seen`, `_good_to_know`, `_tonight`) |
| `advisor_store.py` | Ce qui est gardé sur disque (§ 2.5) | `_keep`, `_signal`, `_feedback` |

- Le coordinateur appelle `room/advice.py` à chaque mise à jour, à la place de `assess()` et `verdict()`.
- Le pas du jumeau reste de 5 minutes. Entre deux pas, un changement de fenêtre relance la décision, pas le jumeau.
- L'anti-rebond des contacts est appliqué **une seule fois**, dans `advisor/observe.py` (couche 1). Celui du coordinateur (`OPEN_DEBOUNCE_SECONDS`) disparaît.

### 2.3 D'où vient chaque donnée

L'essai lit des identifiants écrits en dur. L'intégration les lit dans ses réglages et chez Weather.

| Dans l'essai | Dans l'intégration |
|---|---|
| `outdoor.temperature`, `outdoor.humidity` | sources de la maison `outdoor_temperature`, `outdoor_humidity` (souvent la station de Weather) |
| `SAFETY.rain_rate` (`sensor.gw2000a_rain_rate`) | source de la maison `rain` |
| `SAFETY.gust` (`sensor.gw2000a_wind_gust`) | source de la maison `wind_gust` |
| `SAFETY.rain_in`, `SAFETY.vigilance` | l'interface de Weather (`hestia_weather_api`), jamais un nom d'entité |
| `SAFETY.alarm` (`alarm_control_panel.alarmo`) | l'alarme choisie dans les Réglages généraux (`home.alarm`) |
| `season` | la saison de Weather (`api.season`) ou le capteur Saison choisi dans Confort, comme en 2.1 |
| prévision horaire | `api.hourly()` de Weather ; Open-Meteo seulement pour le rayonnement (§ 2.4) |
| capteur de rayonnement de la station | `api.station()` de Weather |
| `house_heaters` (`climate.thermostat_poele`: 8 500 W) | chauffage de la pièce réglé « chauffe toute la maison » (§ 6.7 bis) ; puissance lue dans Versatile (`power_manager.device_power`) |
| `thermostat` | source `heating` de la pièce |
| `windows` (largeur × hauteur) | `windows` + `openings[…].width`, `height` |
| `orientations` (angle, abrité) | `openings[…].azimuth` (ou `exposure`), `sheltered` |
| `cover` | `openings[…].cover_entity` |
| `cover_auto` | `openings[…].auto_entity` |
| `acp` (début et fin du soleil) | lus par `cover_link.py`, qui connaît déjà Adaptive Cover Pro |
| `co2`, `particles`, `voc` | sources `co2`, `pm25`, `voc` |
| `boost` (entité, débit) | source `ventilation_boost` + débit déclaré (§ 4.3) |
| `purifier` (entité, débit) | source `purifier` + débit déclaré (§ 4.3) |
| `comfort` | `settings` de la pièce (§ 4.2) |
| `foyer` | Réglages du foyer (§ 5) |
| `legacy` (conseil de la 2.1, pour comparer) | retiré au stable ; gardé pendant les préversions si Frank le veut (§ 7, étape D) |

### 2.4 Weather et Open-Meteo

- Le principe 11 dit : seule la position arrondie part vers Open-Meteo, **par Weather**.
- L'essai appelle Open-Meteo lui-même, pour le rayonnement prévu et passé : Weather ne le donne pas encore.
- **Décidé (§ 8)** : Confort appelle Open-Meteo lui-même, position arrondie au dixième, une fois par heure (comme l'essai). Quand Weather 3.x est installé et donne le rayonnement, Confort prend celui de Weather.
- Sans Weather : le dehors mesuré est tenu constant, comme l'essai le fait déjà quand la prévision manque.

### 2.5 Ce qui est gardé sur disque

L'essai garde son état en mémoire. Après un redémarrage, il perd l'écart de la dernière heure et le conseil précédent : la stabilité saute une fois. L'intégration le garde.

| Quoi | Où | Durée |
|---|---|---|
| Jumeaux appris de chaque pièce, gestes vus | Store `hestia_comfort.advisor.<entry_id>` | toujours ; les 7 nuits précédentes gardées |
| État de la pièce : murs, dernière heure, conseil affiché, geste suivi, gestes mis de côté | même Store | réécrit toutes les 5 min, au plus |
| Ombre de la station, date du dernier apprentissage | Store `hestia_comfort.advisor_home` | toujours (jusqu'à ce que Weather 3.x la reprenne, § 7.4 du cahier) |
| Journal des conseils | `<config>/hestia_comfort/journal.jsonl` | 60 jours |
| Instantanés rejouables | `<config>/hestia_comfort/instantanes/` | 10 jours |
| Situations signalées (« Ce conseil ne va pas ») | `<config>/hestia_comfort/signales/` | sans limite |

- Les diagnostics téléchargeables ajoutent les derniers instantanés et les situations signalées (§ 16 bis.4).

### 2.6 Ce que l'essai faisait par des pages web, l'intégration le fait par le websocket

| Essai | Intégration |
|---|---|
| `/api/hestia_advisor_dev/avis` | `hestia_comfort/advice_opinion` (tout utilisateur) |
| `/api/hestia_advisor_dev/atelier` | `hestia_comfort/atelier` (administrateur) |
| `/api/hestia_advisor_dev/trace/{fichier}` | `hestia_comfort/trace` (administrateur) |
| `sensor.conseil_3_savoir`, `sensor.conseil_3_fiabilite`, `sensor.conseil_3_soleil`, `sensor.conseil_3_apprentissage` | pages du hub (« Ce que Hestia sait », « Fiabilité », « Journal », « Atelier » en mode expert), lues par le websocket ; plus d'entités écrites à la main |
| `cartes.js` (carte 3.0 et pages du hub d'essai) | la carte `hestia-comfort-card` et le panneau `panel.js` |

### 2.7 L'apprentissage de la nuit

- Même heure : 3 h 30, et 10 minutes après un démarrage si la dernière nuit date de plus d'un jour.
- Chaque pièce apprend dans un travail à part (`async_add_executor_job`), l'une après l'autre.
- **Différence avec l'essai** : le HA de test garde 60 jours ; une maison ordinaire en garde 10.
- Avec 10 jours, les jumeaux apprennent (il en faut 3), mais les gestes rares restent longtemps « supposés ».
- L'enregistreur en coulisses (`advisor/shadow.py`) n'est pas branché (§ 8, décision 2) : la documentation conseille de garder 30 jours d'historique (`purge_keep_days: 30`).

---

## 3. Ce qu'on retire de la 2.1

Rien n'est retiré à la préversion 3.0.0b1. Tout part au stable 3.0.0 (étape F), une fois les préversions passées.

### 3.1 Le moteur `engine/`

| Module | Sort | Pourquoi |
|---|---|---|
| `assessment.py` | **retiré** | la cascade de règles (28 branches, 32 raisons) est remplacée par la comparaison de scénarios |
| `verdict.py` | **retiré** | copie Python de la carte ; le moteur rédige lui-même |
| `twin.py` | **retiré** | jumeau par régression, remplacé par les jumeaux physiques |
| `horizon.py`, `night.py`, `outlook.py` | **retirés** | « Prochaines heures » et la nuit sortent des chemins simulés du moteur |
| `learning.py`, `airflow.py`, `voc.py`, `shower.py`, `wind.py` | **retirés** | ce qu'ils apprenaient ou devinaient est dans les jumeaux et dans `advisor/safety.py` |
| `volume.py` (`arbitrate`) | **retiré** | le « même air » est une seule pièce pour le moteur (§ 12 du cahier) |
| `evolution.py` | **retiré** | estimations remplacées par les jumeaux |
| `habits.py`, `feedback.py` | **retirés** du moteur | leurs données restent sur disque (§ 4.4) ; « Ce conseil ne va pas » et le suivi les remplacent |
| `home.py` (`synthesis`) | **refait** | « Mon logement » lit les décisions des pièces |
| `sunlight.py` | **gardé jusqu'à Weather 3.x** | l'ombre de la station part chez Weather (§ 7.4 du cahier) ; le moteur 3.0 a déjà sa propre copie (`advisor/physics/station_sun.py`) |
| `sources.py` | **gardé** | lecture et normalisation des capteurs (§ 21 du cahier) |
| `thermostat.py`, `people.py` | **gardés** | lecture de Versatile Thermostat et de la présence |
| `light_plan.py` | **gardé** | les LED ; il lit le niveau de la décision 3.0 (§ 6.4) |
| `review.py` | **gardé** | le bilan de confort (EN 16798-1) se fait sur les mesures ; ses phrases de conseil viennent du moteur 3.0 |
| `i18n.py`, `i18n_en.py`, `legacy.py` | **gardés** | textes du panneau ; ancien nom technique |

### 3.2 Le reste de l'intégration

| Élément | Sort |
|---|---|
| `room/learning.py`, `room/airings.py`, `room/sun.py`, `room/volume.py` | retirés ou réduits à la lecture (les apprentissages passent dans `advisor/`) |
| `coordinator.py` | garde la lecture des capteurs ; appelle `room/advice.py` |
| `OPEN_DEBOUNCE_SECONDS` (`const.py`) | retiré (anti-rebond unique dans `advisor/observe.py`) |
| Carte : `advice()` et `slides()` dans `card/src/views/room.ts` | retirés : la carte affiche les phrases du moteur |
| Encart « Apprentissage » et questions Oui / Non du hub | remplacés par « Ce que Hestia sait de votre maison » |
| Tests du moteur 2.1 (`test_engine*.py`, `test_invariants.py`, `test_verdict_parity.py`, `test_scenarios.py`…) | retirés **après** conversion des cas réels en tests du moteur 3.0 (§ 21 du cahier) |

### 3.3 Ce qui ne bouge pas

- Le panneau, l'assistant des pièces, les onglets de réglage.
- Les liens avec Weather, Versatile Thermostat, Adaptive Cover Pro, Alarmo.
- Les volumes « même air ».
- Le pilotage des LED (`light_driver.py`) et ses garde-fous.
- L'interface pour les autres briques (`api.py`), avec une nouvelle version (§ 6.5).

---

## 4. La migration des réglages

Il y a deux migrations différentes.

1. **Pour tous les utilisateurs** : les réglages 2.1 deviennent ceux de la 3.0. Presque rien à faire : la 3.0 lit les mêmes clés.
2. **Pour la maison de Frank seulement** : ce que l'essai a réglé et appris (`rooms.json`, `jumeaux.json`) passe dans l'intégration.

### 4.1 La règle : rien n'est réécrit à la mise à jour

- La 3.0 lit les réglages 2.1 tels qu'ils sont.
- Une valeur absente prend sa valeur par défaut **à la lecture**, sans être écrite.
- Elle n'est écrite que quand la personne enregistre un onglet.
- Pas de nouvelle version de l'entrée (`async_migrate_entry`) : un retour à la 2.1 retrouve des réglages qu'elle comprend.

### 4.2 Plage et repères de la pièce

La 3.0 les lit dans les `settings` de la pièce, réglés par la personne.

| `Comfort` du moteur 3.0 | Réglage 2.1 de la pièce | Défaut |
|---|---|---|
| `minimum` | `settings.minimum` | 20 °C |
| `maximum` | `settings.maximum` | 24 °C |
| `summer_maximum` | `settings.summer_maximum` | 26 °C |
| `humidity` | `settings.humidity_high` | 60 % |
| `co2` | `settings.co2_action` | 1 000 ppm |
| `particles` | `settings.pm25_action` | 15 µg/m³ |
| `voc` | `evolution.voc_threshold.value` (repère lu sur le capteur) | indice 150 |

- Les autres réglages 2.1 (`co2_potential`, `co2_urgent`, `temperature_hysteresis`, `cooling_delta`, `drying_delta`, `heating_tolerance`, `sun_facade`…) ne servent plus au moteur.
- Ils restent dans les options, ignorés, jusqu'à la 3.1.

### 4.3 Ce que la 3.0 demande en plus (tout est facultatif)

| Nouvelle donnée | Où elle se règle | Sans elle |
|---|---|---|
| Taille de chaque ouvrant (`width`, `height`) | onglet Fenêtres et portes (existe déjà en 2.1) | une valeur ordinaire selon le type : fenêtre, porte-fenêtre, velux |
| « Ce chauffage chauffe : cette pièce · toute la maison » | onglet Chauffage | « toute la maison » pour un poêle ou une cheminée reconnus, « cette pièce » sinon |
| Débit de la VMC rapide (m³/h) | Équipements, « Pour aller plus loin » | une valeur ordinaire |
| Débit d'air propre du purificateur (m³/h) | Équipements, « Pour aller plus loin » | une valeur ordinaire |
| Réglages du foyer | page « Réglages du foyer » (§ 5) | les défauts du § 10.3 du cahier |

### 4.4 Ce que la 2.1 avait appris

| Donnée 2.1 | Fichier | Ce qu'en fait la 3.0 |
|---|---|---|
| Jumeau par régression | `hestia_comfort.twin.<entry_id>` | **non repris** : le modèle n'est pas le même. La 3.0 réapprend la première nuit |
| Aérations apprises | `hestia_comfort.learning.<entry_id>` | **non repris** : les gestes sont recomptés depuis l'historique |
| Réponses Oui / Non | `hestia_comfort.home`, clé `answers` | gardées, pas encore lues : elles serviront aux sources d'humidité, après la 3.0 |
| Réglages des pièces, maison, LED, alarme | entrées et `hestia_comfort.home` | repris tels quels |

- **Décidé (§ 8)** : `hestia_comfort.twin.*` et `hestia_comfort.learning.*` sont **effacés** au passage à la 3.0, pour repartir sur du propre. Un retour à la 2.1 garde ses réglages mais réapprend.

### 4.5 La maison de Frank : de `rooms.json` aux réglages

Les identifiants des entités sont les mêmes dans le HA de test et dans la maison (Remote Home-Assistant les recopie). La plupart des réglages existent déjà dans le Confort de la maison.

| Dans `rooms.json` | Dans l'intégration | Comment |
|---|---|---|
| `foyer` (sommeil 22 h – 7 h, aérations 10 et 20 min…) | Réglages du foyer, maison | à saisir dans la page, ou importé (§ 4.6) ; ce sont les défauts |
| `house_heaters` : poêle, 8 500 W | Chauffage du Salon : « toute la maison » | à régler dans l'onglet Chauffage ; puissance lue dans Versatile, à vérifier contre les 8 500 W |
| Salon : 4 ouvrants avec tailles et angles | ouvrants du volume « Salon · Cuisine » | tailles et angles à reporter dans Fenêtres et portes ; la fenêtre C appartient à la Cuisine |
| Salon : `voc` de la cuisine, `purifier` 150 m³/h | sources de la Cuisine et du Salon | le moteur voit un seul air : il lit les capteurs des deux pièces |
| Chambre P : `cover`, `cover_auto`, `acp`, `boost` 60 m³/h | ouvrant de la Chambre P, Adaptive Cover Pro reconnu, VMC rapide | déjà réglés ; débit de la VMC à saisir |
| `comfort` de chaque pièce | `settings` | déjà réglés (Chambre P 18–24 °C, les autres 19–24 °C, 26 °C l'été) ; à vérifier un par un |
| `season: null` | saison de Weather | rien à faire |
| `legacy` | — | ne sert qu'à l'essai |

**Le « même air » Salon · Cuisine.** L'essai le traite comme une seule pièce nommée « Salon ». L'intégration garde deux pièces liées, avec un seul jumeau et une seule décision pour le volume, portée par l'appareil « Salon · Cuisine » (comme en 2.1).

### 4.6 Reprendre les jumeaux appris dans le HA de test

- **Décidé (§ 8) : non.** La 3.0 réapprend aussi chez Frank, en une nuit. Ce qui suit reste comme trace, sans être codé.
- Pour Frank seulement, et seulement s'il le veut : sinon la 3.0 réapprend en une nuit, sur 10 jours.
- Une commande d'administrateur, une fois : `hestia_comfort/import_advisor`, qui lit `jumeaux.json`.
- Chaque pièce de l'essai est retrouvée par **son capteur de température**, pas par son nom.
- L'ombre de la station (`station_ombre`) va dans `hestia_comfort.advisor_home`.
- Un jumeau importé est gardé seulement s'il prévoit les derniers jours de la maison au moins aussi bien qu'un jumeau neuf (même règle que l'apprentissage de la nuit).
- L'import ne touche ni le HA de test, ni les réglages des pièces.

---

## 5. La page « Réglages du foyer »

> **Proposition complète, validée par Frank le 1er novembre** : [REGLAGES-3.md](REGLAGES-3.md) et sa maquette [maquette-reglages-3.html](maquette-reglages-3.html).
> Elles reprennent ce paragraphe et vont plus loin (décision 6 du § 8) : inventaire des réglages 2.1, ce qui reste, part ou s'ajoute dans chaque onglet, les bornes revues, sept questions.
> Elles remplacent les § 5.1 à 5.4 ci-dessous, gardés comme trace.

### 5.1 Où

- Dans le hub Confort, sous **Réglages généraux**, une page « Réglages du foyer ».
- Pour une pièce qui diffère (chambre d'enfant, travail de nuit) : un encart **« Différent pour cette pièce »** dans l'onglet « Pièce et confort » de la pièce.
- La plage de confort et les repères restent dans l'onglet de la pièce, sans doublon.
- La physique et les normes ne sont pas dans cette page (§ 10.3 du cahier).

### 5.2 Ce qu'elle contient

Chaque ligne : le réglage, sa valeur par défaut, et une phrase « Ce que ça change ».

| Rubrique | Réglage | Par défaut | Ce que ça change |
|---|---|---|---|
| **Sommeil** | Heures de sommeil | 22 h – 7 h | la nuit du moteur ; l'alarme en mode nuit compte aussi |
| | Ouvrir une fenêtre la nuit | non | aucune ouverture conseillée pendant le sommeil ; « Refermez », la VMC et le purificateur restent |
| **Gestes** | Combien de conseils (curseur) | au milieu | plus haut : moins de gestes, seulement les plus nets |
| | Durées d'aération proposées | 10 et 20 min | les gestes « Aérez… » |
| | Gestes « plus tard » | dans 1 h et 2 h | « Aérez vers 16 h », « Refermez vers 16 h » |
| | Durées des appareils | 30 et 60 min | VMC rapide, purificateur |
| | « Pas maintenant » | 1 h | combien de temps un geste refusé est mis de côté |
| **Le soir** | « Cette nuit, pensez à… » | 4 h avant le coucher | quand la phrase apparaît |
| | Buée de la nuit | 5 h avant le coucher | quand la phrase apparaît |
| **Absence** | Hors-gel pendant une absence | 7 °C | le seul confort gardé en mode vacances |

- Le cahier (§ 10.3) prévoit aussi deux curseurs : « Confort ou économie » et « La nuit ». Ils ne sont pas encore dans le moteur (`Habits`). Ils viendront avec la brique Énergie ; la page leur garde une place.

### 5.3 Où c'est rangé

| Niveau | Rangement | Clés |
|---|---|---|
| Maison | Store `hestia_comfort.home`, nouvelle clé `foyer` | celles de `rooms.json` : `sommeil`, `ouvrir_la_nuit`, `aerations_min`, `plus_tard_min`, `appareils_min`, `cette_nuit_avant_h`, `buee_avant_h`, `hors_gel`, `tolerance`, `pas_maintenant_min` |
| Pièce | options de l'entrée, clé `foyer` | seulement ce qui diffère de la maison |

- Le moteur lit déjà ces clés : `Habits.of(maison, pièce)` (`advisor/household.py`).
- **Point à corriger avant la 3.0** : l'enregistrement de la maison (`Configuration.save`, `home=True`) ne recopie que `answers`, `alarm`, `pollen_allergy` et `lights`. Sans changement, enregistrer l'onglet Extérieur effacerait `foyer`.

### 5.4 Les bornes proposées

Chaque valeur est contrôlée à l'enregistrement, comme les autres réglages. Bornes à valider avec Frank :

| Réglage | Bornes |
|---|---|
| Heures de sommeil | heures et minutes, coucher ≠ lever |
| Durées d'aération | de 5 à 60 min, deux au plus |
| Gestes « plus tard » | de 15 min à 4 h, deux au plus |
| Durées des appareils | de 10 à 120 min, deux au plus |
| « Cette nuit », buée | de 1 à 8 h avant le coucher |
| Hors-gel | de 5 à 12 °C |
| Combien de conseils | de 0,5 à 2 |
| « Pas maintenant » | de 15 min à 4 h |

---

## 6. Les entités et leurs consommateurs

### 6.1 Qui lit quoi

| Consommateur | Ce qu'il lit | Effet du passage |
|---|---|---|
| La carte `hestia-comfort-card` | le websocket `hestia_comfort/subscribe`, pas les entités | elle reçoit les phrases du moteur au lieu des mesures à interpréter |
| Les LED (`light_driver.py`) | la décision dans le coordinateur, pas les entités | elles lisent le niveau de la décision 3.0 (§ 6.4) |
| Weather (`extensions.py`) | `hestia_comfort_api` : `weather()`, `set_weather()` | inchangé |
| Énergie (plus tard) | `hestia_comfort_api.twin()` | nouveau contenu (§ 6.5) |
| L'essai du HA de test | `sensor.*_conseil` de la maison, recopiés | retiré avec l'essai |
| Automatisations et tableaux des utilisateurs | les entités | identifiants gardés ; voir § 6.2 |
| Frank | aucune automatisation sur ces entités (§ 20 du cahier) | rien |

### 6.2 Entités gardées

Les identifiants uniques ne changent pas (`<entry_id>_<clé>`, ou `volume_…_<clé>` pour un même air). Les `entity_id` restent donc les mêmes.

| Entité | Clé | En 2.1 | En 3.0 | Changement pour une automatisation |
|---|---|---|---|---|
| Conseil | `advice` | titre du bandeau | titre du bandeau, rédigé par le moteur ; attributs geste, sujet, moment, gain, preuve, appareils concernés | les textes changent ; l'attribut `geste` prend les valeurs du moteur (`close`, `open`, `boost`…) |
| État | `state` | 11 valeurs (`calm`, `best`, `optimized`, `too_cold`…) | `calm`, `benefit`, `action`, `urgent`, `neutral` | les autres valeurs ne sont plus produites ; elles restent dans la liste jusqu'à la 3.1 |
| Couleur | `colour` | couleur du bandeau | même règle : bleu, vert, orange, rouge, gris | aucun |
| Humidité | `humidity` | 7 degrés | mêmes 7 degrés, calculés sur la mesure et le repère de la pièce | aucun |
| Apprentissage | `learning` | % appris (2.1) | part des effets « avérés » parmi ceux que la pièce peut avoir (§ 4.1 du cahier) | le sens du % change |
| Chauffage observé | `heating_action` | lu sur le thermostat | inchangé | aucun |
| Raison (diagnostic) | `reason` | 32 raisons | geste × sujet × moment | toutes les valeurs changent ; annoncé dans la note de version |
| Couverture des données | `coverage` | inchangé | inchangé | aucun |
| Température, humidité prévues dans 1 h | `twin_temperature`, `twin_humidity` | jumeau 2.1 | jumeau 3.0, sans geste | plus justes |
| Geste à faire | `gesture` | oui si un geste est demandé | oui si le bandeau porte un geste | aucun |
| Aération conseillée | `airing` | oui / non | oui pour « Aérez », maintenant | « Aérez vers 16 h » reste non jusqu'à 16 h |
| Fenêtres à refermer | `close` | oui / non | oui pour « Refermez » ; attribut : la liste des fenêtres | attribut ajouté |
| VMC conseillée | `ventilation` | oui / non | oui pour « Lancez la VMC rapide » ; attribut : durée | attribut ajouté |
| Trop humide | `humid` | oui / non | oui au-dessus du repère de la pièce | aucun |
| Mon logement : Pièces demandant un geste, Conseil, Couleur, Un geste à faire | `rooms_asking`, `advice`, `colour`, `gesture` | la pièce la plus pressée | la même chose, sur les décisions 3.0 | aucun |

### 6.3 Entités nouvelles

| Entité | Type | Dans la 3.0.0 |
|---|---|---|
| Cette nuit | texte, avec la liste des points | oui |
| Volet à baisser · Volet à ouvrir | oui / non, avec les volets (`cover`) | oui, pour un volet relié non piloté par une automatisation |
| Purificateur conseillé | oui / non, avec la durée | oui (le moteur sait déjà ce geste ; absent du § 20.1, à confirmer) |
| Chauffage à baisser pendant l'aération | oui / non | quand le geste chauffage existera |
| Climatisation conseillée, Ventilateur conseillé | oui / non | quand ces gestes existeront |
| Mon logement : Mode vacances | oui / non | oui |
| Mon logement : Plan du logement | texte, gestes de chaque pièce en attributs | quand le plan du logement existera |
| Évènement `hestia_comfort_advice` | à chaque nouveau conseil : pièce, geste, moment, appareils | oui |

**Décidé (§ 8)** : Moment, Gain et Confiance sont **des attributs** du capteur « Conseil » (§ 20.1 du cahier), pas des entités. Ils n'ont de sens qu'avec le conseil ; une automatisation lit un attribut aussi bien ; trois entités de moins par pièce.

### 6.4 Le niveau de la décision, pour les LED et la couleur

Les LED attendent un des cinq états de `LIGHT_STATES` : `calm`, `benefit`, `action`, `airing`, `urgent`.

| Décision 3.0 | Niveau | Couleur |
|---|---|---|
| « Rien à faire » | `calm` | bleu |
| « Rien à faire » avec un geste « À essayer » | `benefit` | vert |
| « Aérez… », « Ouvrez » | `airing` | orange |
| « Refermez », VMC, purificateur, volet | `action` | orange |
| Interdit de sécurité qui impose « Fermez » (pluie, rafales) | `urgent` | rouge |
| Température de la pièce douteuse : pas de conseil | `neutral` (LED : rien ne change) | gris |

### 6.5 L'interface pour les autres briques

- `hestia_comfort_api.version` passe de 1 à 2.
- `rooms()`, `weather()`, `set_weather()` ne changent pas.
- `twin()` rend les paramètres du jumeau 3.0 (chaleur, eau, air) et les effets avec leur niveau de preuve ; l'ancien champ `model` (demi-heures, 2.1) disparaît.
- Personne ne lit `twin()` aujourd'hui ; Énergie le lira.

---

## 7. L'ordre des étapes

Chaque étape dit ce qu'elle change, ses risques et comment revenir en arrière.

### Étape A — Finir la 3.0 dans le HA de test

- Ajouter les gestes manquants (chauffage, climatisation, ventilateur), le plan du logement, le mode vacances complet.
- Tenir les indicateurs du § 18.3 plusieurs semaines.
- Revoir le journal des désaccords avec Frank.
- **Pour les utilisateurs** : rien.
- **Risque** : aucun pour la maison.
- **Retour arrière** : sans objet.

### Étape B — Enregistrer en coulisses (abandonnée le 1er novembre, § 8)

- Brancher `advisor/shadow.py` dans une 2.1.x stable : 30 jours enregistrés, aucun conseil changé.
- Au passage à la 3.0, chaque maison aura 30 jours au lieu de 10 : les gestes rares seront plus vite « avérés ».
- **Risque** : c'est du code nouveau dans la maison, que le § 18.4 du cahier écarte pour l'essai. Il n'écrit qu'un fichier, mais il tourne chez tous les utilisateurs.
- **Retour arrière** : la 2.1.x précédente ; le fichier est ignoré.

### Étape C — Le moteur dans l'intégration, essayé dans le HA de test

- Écrire la couche du § 2 dans la branche `moteur-conseil-3`.
- Dans le HA de test : régler les mêmes pièces que la maison dans Confort (il n'en a que deux aujourd'hui), importer `rooms.json` et `jumeaux.json` (§ 4.5, § 4.6).
- Arrêter `hestia_advisor_dev` ; garder son dossier pour comparer.
- Comparer une semaine avec la 2.1 de la maison.
- **Risque : deux entités de même nom.** Le HA de test reçoit déjà `sensor.chambre_p_conseil` de la maison ; son propre Confort en créera un second, renommé `…_2` par Home Assistant. Solution : comparer avec les entités recopiées sous un préfixe, ou exclure les entités de Confort de la recopie.
- **Risque : le calcul.** Mesurer décision et apprentissage sur un Raspberry Pi 4 avant la préversion.
- **Risque : le redémarrage.** Vérifier qu'un redémarrage ne fait pas sauter le conseil (état gardé, § 2.5).
- **Retour arrière** : relancer `hestia_advisor_dev`.

### Étape D — Préversion Confort 3.0.0b1

- Publiée en pre-release sur GitHub (règle des numéros : 3.0.0b1).
- Le moteur 3.0 décide. Le moteur 2.1 reste dans le code, sans rien afficher.
- Pendant les préversions, la 2.1 continue de juger en coulisses ; ses désaccords vont dans le journal (décidé, § 8). Cela donne le journal des désaccords chez chaque testeur, exporté par l'essai terrain (§ 7 bis).
- Note de version courte, classée Nouveautés / Améliorations / Corrections ; elle annonce les valeurs de « Raison » et d'« État ».
- **Risques** :
  - peu de gestes affichés les premières semaines, faute de gestes « avérés » : la personne croit que Confort ne fait plus rien. Réponse : « À essayer » et « Bon à savoir » le disent ;
  - une automatisation d'utilisateur sur « Raison » ou sur une valeur d'« État » retirée ne se déclenche plus ;
  - l'appli mobile garde l'ancienne carte en cache un moment (déjà vu en 1.2.5).
- **Retour arrière** : réinstaller la 2.1.x par HACS. Les entités gardent leurs identifiants, les réglages sont intacts (§ 4.1), les fichiers 2.1 sont là (§ 4.4).
  - Seule perte : une page enregistrée sous la 3.0 puis réenregistrée sous la 2.1 perd ce que la 2.1 ne connaît pas (`foyer` de la maison, débits). À refaire après un retour à la 3.0.
  - Ce retour est essayé dans le HA de test avant de publier la b1.

### Étape E — Préversions 3.0.0bN

- Retours des testeurs, situations signalées rejouées sur le banc.
- Réglage des poids entre sujets, dans leurs bornes.
- Gestes manquants ajoutés s'ils ne l'ont pas été à l'étape A.
- **Risque** : corriger un cas par une exception. Règle du cahier (§ 23.3) : on corrige au bon endroit, mesure, jumeau, poids, interdit ou phrase.
- **Retour arrière** : la préversion précédente.

### Étape F — Confort 3.0.0 stable

- Retrait du moteur 2.1, de la logique de la carte et des tests 2.1 (§ 3).
- Les fichiers 2.1 restent sur disque.
- **Risque** : un utilisateur saute de la 2.1 au stable sans passer par les préversions. Même retour arrière qu'à l'étape D.
- **Retour arrière** : 2.1.x par HACS, comme à l'étape D.

### Étape G — Confort 3.1 : le ménage

- Effacer `hestia_comfort.twin.*` et `hestia_comfort.learning.*`.
- Retirer de la liste d'« État » les valeurs qui ne sont plus produites.
- Retirer des options les réglages 2.1 que la 3.0 ne lit plus.
- **Risque** : après la 3.1, un retour à la 2.1 repart sans son apprentissage.
- **Retour arrière** : la 3.0.x.

### En résumé

| Étape | Pour les utilisateurs | Retour arrière |
|---|---|---|
| A — Finir la 3.0 au banc | rien | — |
| B — Enregistreur en coulisses (facultatif) | 2.1.x stable | 2.1.x précédente |
| C — Moteur dans l'intégration, HA de test | rien | relancer l'essai |
| D — 3.0.0b1 | préversion | 2.1.x par HACS |
| E — 3.0.0bN | préversions | préversion précédente |
| F — 3.0.0 | stable | 2.1.x par HACS |
| G — 3.1 | stable | 3.0.x |

---

## 7 bis. L'essai terrain (idée de Frank, 1er novembre)

Plutôt que des semaines d'essai sur une seule maison, les testeurs des préversions 3.0.0bN aident à améliorer le moteur avec leurs propres chiffres. Plusieurs maisons, c'est d'autres murs, d'autres chauffages, d'autres capteurs.

**Un encart sur l'accueil du hub Confort** : « Participez à l'amélioration du moteur de conseil ».
- Il montre, en clair, **ce qui serait exporté**, rubrique par rubrique, avant tout envoi.
- Il dit aussi **ce qui manque et serait utile** : « vos fenêtres n'ont pas de taille », « 10 jours d'historique seulement : 30 aideraient ».
- Deux boutons :
  - **« Télécharger mon rapport »** : un fichier JSON ;
  - **« Préparer une issue sur GitHub »** : ouvre une issue « Essai terrain » préremplie (résumé dans le texte), où le testeur dépose le fichier. Rien ne part sans son clic sur GitHub.
- Créer l'issue tout seul demanderait le jeton GitHub du testeur : écarté. Un envoi automatique vers un serveur aussi : il faudrait un serveur, et « tout reste local ».
- **L'issue est publique** : l'encart le dit avant le bouton.

**Ce que contient le rapport** (anonyme : aucun nom d'entité, aucune position, aucun historique brut) :
- les indicateurs du § 18.3 du cahier, par pièce : effet des gestes prévu contre mesuré, erreur à 1 h et 3 h, changements de conseil, temps de calcul ;
- les paramètres des jumeaux, et les preuves de chaque effet ;
- les désaccords avec la 2.1 jugeant en coulisses ;
- les situations signalées (« Ce conseil ne va pas ») avec leur instantané, rejouables sur le banc ;
- le contexte utile : nombre et type de pièces, capteurs présents, type de chauffage, jours d'historique, version.

**Ce qu'il faut avant** : les indicateurs du § 18.3 (en cours dans le HA de test), et le moteur dans l'intégration (étape C). Les pièces sont nommées « Pièce 1, Pièce 2… » dans le rapport.

## 8. Décisions de Frank (1er novembre)

1. **Open-Meteo** : Confort l'appelle lui-même (position arrondie au dixième, une fois par heure). Quand Weather 3.x est installé et donne le rayonnement, Confort prend le sien (§ 2.4).
2. **Pas d'enregistreur en coulisses** dans la 2.1 (étape B abandonnée). La documentation conseille de garder 30 jours d'historique (`purge_keep_days: 30`).
3. **Moment, Gain, Confiance en attributs** du capteur « Conseil », pas d'entités à part (§ 6.3).
4. **La 2.1 juge en coulisses pendant les préversions**, et seulement pendant elles : ses désaccords alimentent l'essai terrain (§ 7 bis). Retirée à la 3.0.0 stable.
5. **La 3.0 réapprend** dans la maison de Frank : les jumeaux du HA de test ne sont pas repris (§ 4.6).
6. **Les réglages de Confort sont repensés pour la 3.0**, pas seulement les bornes du § 5.4 : proposition et maquette dans [REGLAGES-3.md](REGLAGES-3.md), validées le 1er novembre.
7. **Les fichiers appris par la 2.1 sont effacés** au passage à la 3.0 : on repart sur du propre (§ 4.4). Un retour à la 2.1 repart alors sans son apprentissage.

## 9. Historique du document

- **v0.2 — 1er novembre 2026** : les 7 décisions de Frank (§ 8) ; l'essai terrain avec export volontaire depuis l'accueil (§ 7 bis), à la place des seules semaines d'essai chez Frank ; étape B abandonnée ; fichiers 2.1 effacés au passage.
- **v0.1 — 1er novembre 2026** : premier plan, écrit à partir du cahier du moteur v0.16, du moteur 3.0 de la branche `moteur-conseil-3`, de l'essai du HA de test et de l'intégration 2.1.0b7.
