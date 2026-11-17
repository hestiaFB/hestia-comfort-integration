# Les réglages de Hestia Confort pour le moteur 3.0

Version 1.0 — 1er novembre 2026. **Validée par Frank le 1er novembre** (« les réglages me paraissent ok »). Rien n'est encore codé dans les réglages ; le moteur a reçu les paliers de 5 minutes (commit `ad07d86`).

La maquette : [maquette-reglages-3.html](maquette-reglages-3.html), à ouvrir dans un navigateur. Elle reprend le style du hub.

Ce document répond à la décision 6 du [plan de passage](PASSAGE-CONFORT-3.md) (§ 8) : « repenser les réglages de Confort pour l'enrichir et l'améliorer pour le moteur 3.0 ».

Sources lues le 1er novembre :
- l'intégration 2.1.0b7 : `configuration.py` (`validate`, `save`), `config_flow.py`, `engine/assessment.py` (`Settings`), `air_references.py`, `frontend/panel.ts` ;
- le moteur 3.0 de la branche `moteur-conseil-3` : `advisor/household.py`, `house.py`, `decide.py`, `safety.py`, `knowing.py` ;
- l'essai du labo : `hestia_advisor_dev/__init__.py` et `rooms.json` ;
- le [cahier du moteur](CAHIER-MOTEUR.md) v0.16 (§ 6.3, 6.7, 6.8, 9, 10.2 bis, 10.3, 15, 16.2, 20) et le plan de passage v0.2 (§ 4.3, 5, 7 bis) ;
- le hub tel qu'il s'affiche sur le labo.

---

## 1. Les règles suivies

1. **Tout est facultatif.** Seule la température de la pièce est obligatoire, comme en 2.1.
2. **Ce qui dépend du foyer est un réglage, avec une valeur par défaut** : heures de sommeil, durées, nombre de conseils… **La physique et les normes restent fixes** : EN ISO 13788, repères du HCSP et de l'OMS, règles de sécurité du § 9.3 du cahier.
3. **Chaque réglage à un seul endroit.** La maison dans « Réglages du foyer », la pièce dans ses onglets, et une pièce qui diffère dans un encart à part.
4. **Ce que Hestia lit tout seul n'est pas demandé.** Puissance et consignes de Versatile Thermostat, angle et taille d'Adaptive Cover Pro : affichés, avec « Une valeur saisie ici le remplace ».
5. **Ce que Hestia apprend n'est pas demandé.** Inertie, part du poêle dans chaque pièce, ombre de la station, renouvellement d'air des fenêtres.
6. **« Pour aller plus loin »** en bas de chaque onglet, replié, avec un compteur « 1 sur 3 renseignés » et ce que chaque donnée débloque (§ 16.2 du cahier).
7. **Rien n'est réécrit à la mise à jour** (§ 4.1 du plan) : une valeur absente prend son défaut à la lecture.
8. **Une donnée facultative dit d'abord ce qu'elle apporte**, puis ce qui se passe sans elle : « la bonne durée d'aération dès le premier jour », puis « Vide, Hestia suppose une pièce ordinaire et se corrige au fil des jours ». Jamais « Hestia l'apprend de toute façon » : la phrase pousse à ne rien remplir (remarque de Frank).

---

## 2. Inventaire des réglages de la 2.1

Légende de la dernière colonne :
- **Gardé** : la 3.0 le lit tel quel.
- **Gardé, lu autrement** : la 3.0 le lit, mais il ne veut plus dire la même chose.
- **Pas encore lu** : le cahier le prévoit, le moteur ne le lit pas encore.
- **Plus lu** : la 3.0 l'ignore. Gardé dans les options jusqu'à la 3.1, puis retiré de la page.

### 2.1 Où sont les réglages

- **Le flux de configuration** (`config_flow.py`) ne règle rien : il crée « Mon logement » et renvoie vers le panneau. Les options aussi (« Ouvrez /hestia/confort »).
- **Le panneau** (`panel.ts`) règle tout, par le websocket `hestia_comfort/save_config` :
  - la **maison** dans le store `hestia_comfort.home` ;
  - chaque **pièce** dans les options de son entrée.
- **`Configuration.save`** contrôle tout par `validate`, puis :
  - pour la maison, ne recopie que `answers`, `alarm`, `pollen_allergy` et `lights` : **une nouvelle clé comme `foyer` serait effacée** (point déjà noté au § 5.3 du plan) ;
  - pour une pièce, garde les clés inconnues du premier niveau (`{**data, **options, **cleaned}`) : une clé `foyer` de pièce survivrait, mais sans contrôle.

### 2.2 La maison

| Réglage (où) | Clé | Défaut | Lu en 2.1 par | En 3.0 |
|---|---|---|---|---|
| Le dehors : Hestia Weather ou ses propres capteurs (Extensions) | `home.weather`, `home.sources` | Weather s'il est là | `exterior.py`, coordinateur | **Gardé** |
| Capteurs du dehors : température, humidité, pluie, rafales, direction du vent, soleil, pollution, saison | `home.sources.*` | — | `exterior.py` | **Gardé** (le soleil prévu vient d'Open-Meteo, recoupé par la station) |
| Pollution : bloquer l'aération dès le niveau ATMO… | `sources.pollution.block_from` | 4 (Mauvais) | `exterior.py` | **Pas encore lu** (interdit « air extérieur pollué », § 9.3) |
| Utiliser une extension tierce (Versatile, ACP, CoverAutomatic, Cover Extender, WLED) | `home.disabled` | toutes utilisées | `presence.py`, `light_driver.py`, `health.py` | **Gardé** |
| Alarme (Alarmo trouvé seul, aucune, ou une autre) | `home.alarm` | trouvée seule | `presence.py`, `assessment.py` | **Gardé** (sommeil, absence, vacances) |
| Allergie aux pollens (Réglages généraux, « Le foyer ») | `home.pollen_allergy` | non | `panel.py` | **Pas encore lu** |
| Notifications lumineuses : tout le logement ou pièce par pièce, couleur et effet par état | `home.lights` | aucune | `light_driver.py` | **Gardé** (lit le niveau de la décision, § 6.4 du plan) |
| Réponses Oui / Non aux questions d'apprentissage | `home.answers` | — | `room/learning.py` | **Pas encore lu** (sources d'humidité, après la 3.0) |

### 2.3 La pièce, onglet par onglet

**Température** (titre de l'onglet : « Température et humidité »)

| Réglage | Clé | Défaut | Lu en 2.1 par | En 3.0 |
|---|---|---|---|---|
| Température de la pièce (obligatoire) | `sources.indoor_temperature` | — | tout | **Gardé** |
| Humidité de la pièce | `sources.indoor_humidity` | — | tout | **Gardé** |
| Luminosité | `sources.illuminance` | — | `sources.py` | **Pas encore lu** (§ 6.7 quater) |
| Minimum | `settings.minimum` | 20 °C | `assessment.py` | **Gardé** (`Comfort.minimum`) |
| Maximum en hiver | `settings.maximum` | 24 °C | `assessment.py` | **Gardé** |
| Maximum en été | `settings.summer_maximum` | 26 °C | `assessment.py` | **Gardé** |
| Humidité maximale | `settings.humidity_high` | 60 % | `assessment.py` | **Gardé** (`Comfort.humidity`) |
| Humidité minimale | `settings.humidity_low` | 40 % | `assessment.py` | **Plus lu** : la 3.0 ne parle pas d'air sec (question 1, § 7) |

**Ouvertures** (titre : « Fenêtres et portes »), pour chaque ouvrant

| Réglage | Clé | Défaut | Lu en 2.1 par | En 3.0 |
|---|---|---|---|---|
| Contacts des ouvrants | `windows` | — | tout | **Gardé** |
| « Pas de contact ici, c'est voulu » | `windows_unmeasured` | non | `health.py` | **Gardé** |
| Exposition (8 directions ou « Je ne sais pas ») | `openings.*.exposure` | inconnue | `assessment.py`, `sunlight.py` | **Gardé** |
| Angle précis | `openings.*.azimuth` | — | `sunlight.py` | **Gardé** |
| Type : fenêtre, porte-fenêtre, velux, porte | `openings.*.kind` | fenêtre | `assessment.py` | **Gardé** (taille ordinaire par type, `house.py`) |
| Abrité par une avancée ou un balcon | `openings.*.sheltered` | non | `assessment.py`, `volume.py` | **Gardé** (pluie battante) |
| Volet : aucun, manuel, connecté | `openings.*.shutter` | aucun | `assessment.py` | **Gardé** (§ 6.7 ter) |
| Volet de cet ouvrant | `openings.*.cover_entity` | — | `assessment.py` | **Gardé** |
| Interrupteur du pilotage automatique, capteur « repris à la main » | `openings.*.auto_entity`, `override_entity` | lus dans ACP | `assessment.py`, `health.py` | **Gardé** (aucun geste sur un volet piloté) |
| Largeur, hauteur (repliées dans « Dimensions et avancée de toit ») | `openings.*.width`, `height` | lues dans ACP, sinon vides | `evolution.py` (ombre) | **Gardé, lu autrement** : la 3.0 en tire le débit d'air et le soleil reçu ; sans elles, une taille ordinaire |
| Profondeur de l'avancée, écart avec l'ouvrant | `openings.*.overhang_depth`, `overhang_gap` | vides | `evolution.py` | **Gardé** (ombre) |

**Air intérieur**

| Réglage | Clé | Défaut | Lu en 2.1 par | En 3.0 |
|---|---|---|---|---|
| CO₂, PM2.5, COV | `sources.co2`, `pm25`, `voc` | — | tout | **Gardé** |
| Purificateur | `sources.purifier` | — | `sources.py` | **Gardé** |
| VMC, VMC rapide | `sources.ventilation`, `ventilation_boost` | — | `evolution.py` | **Gardé** |
| CO₂ : « aérer ferait du bien » | `settings.co2_potential` | 800 ppm | `assessment.py` | **Plus lu** |
| CO₂ : « aérer » | `settings.co2_action` | 1 000 ppm | `assessment.py` | **Gardé** (`Comfort.co2`) |
| CO₂ : « attention » | `settings.co2_urgent` | 1 500 ppm | `assessment.py` | **Plus lu** : le second repère de la 3.0 est fixe, 1 500 ppm (HCSP) |
| PM2.5 : seuil de signalement | `settings.pm25_action` | 15 µg/m³ | `assessment.py` | **Gardé** (`Comfort.particles`) |
| Seuil COV, dans l'unité du capteur | `evolution.voc_threshold` | indice 150 (VINDSTYRKA) | `voc.py` | **Gardé** (`Comfort.voc`) |
| COV : au-dessus du seuil depuis… | `evolution.voc_delay_minutes` | 10 min | `evolution.py` | **Plus lu** (le jumeau du COV le remplace) |
| COV : pause après une aération | `evolution.voc_pause_minutes` | 45 min | `evolution.py` | **Plus lu** (idem) |

**Présence**

| Réglage | Clé | Défaut | Lu en 2.1 par | En 3.0 |
|---|---|---|---|---|
| Capteurs de présence | `presence` | — | `presence.py` | **Pas encore lu** (§ 6.6 : prévu dans la 3.0) |
| Personnes de la pièce | `persons` | toutes | `presence.py` | **Pas encore lu** |
| Délai avant de considérer la pièce vide | `evolution.presence_delay_minutes` | 5 min | `evolution.py` | **Pas encore lu** |

**Chauffage**

| Réglage | Clé | Défaut | Lu en 2.1 par | En 3.0 |
|---|---|---|---|---|
| Pièce chauffée | `heated` | oui | `twin.py`, `assessment.py`, `words.py` | **Gardé** |
| Chauffage (thermostat) | `sources.heating` | — | tout | **Gardé** |
| Témoin de chauffe (vanne, relais) | `sources.heating_indicator` | — | `learning.py`, `volume.py` | **Gardé** (chauffe réelle sans Versatile) |
| Consigne du thermostat comme minimum | `thermostat_reference` | oui | `assessment.py` | **Gardé** (`from_thermostat`) |
| Tolérance sous le minimum avant « Rallumez » | `settings.heating_tolerance` | 1 °C | `assessment.py` | **Plus lu** : « Rallumez » est un conseil passif, jugé par l'écart minimal (§ 9.1 bis) |

**La pièce** (titre : « La pièce et ses réglages »)

| Réglage | Clé | Défaut | Lu en 2.1 par | En 3.0 |
|---|---|---|---|---|
| Nom, pièce Home Assistant, étage | `name`, `area_id`, `floor_id` | — | tout | **Gardé** |
| Même air (pièces ouvertes l'une sur l'autre) | `open_to` | — | `Configuration.volume` | **Gardé** (un jumeau et une décision par volume) |
| Équipements : douche ou baignoire | `equipment` | aucun | `habits.py`, `learning.py` | **Pas encore lu** (sources d'humidité, après la 3.0) |
| Rafales : rien d'ouvert au-delà de | `settings.gust_max` | 45 km/h | `assessment.py` | **Plus lu** : règle fixe de la 3.0, 45 km/h (`safety.py`) |
| Gel : pas d'ouverture prolongée sous | `settings.frost` | 1 °C | `assessment.py` | **Plus lu** : règle fixe, 1 °C |
| Soleil compté sur une fenêtre à partir de | `settings.sun_facade` | 250 W/m² | `assessment.py` | **Plus lu** : le soleil est calculé en W/m² et entre dans le jumeau |
| Facteur estimé du vitrage | `evolution.glazing_factor` | 0,7 | `evolution.py` (buée) | **Plus lu** : remplacé par le type de vitrage (§ 4.4) |
| Luminosité basse | `settings.illuminance_low` | 100 lx | `assessment.py` | **Plus lu** : repères fixes 100 et 300 lx (§ 6.7 quater) |
| Ancienneté maximum des mesures | `settings.max_age_seconds` | 3 h | `readings.py` | **Gardé, lu autrement** : le contrôle des mesures (`checks.py`) juge seul un capteur figé ; le réglage peut partir |

**Notifications**

| Réglage | Clé | Défaut | En 3.0 |
|---|---|---|---|
| Lumière de la pièce (quand les lumières vont pièce par pièce) | `home.lights.rooms[entrée]` | aucune | **Gardé** |
| Sur le téléphone | — | « Bientôt » | inchangé |

**Pas affichés dans le hub**, mais dans `Settings` : `temperature_hysteresis` (0,5 °C), `co2_hysteresis` (100 ppm), `humidity_hysteresis` (3 points), `cooling_delta` (1,5 °C), `drying_delta` (1,5). **Plus lus** : la 3.0 a sa propre stabilité (§ 11 du cahier).

### 2.4 En bref

- **56 lignes** de réglages affichés dans le hub 2.1 (tableaux ci-dessus).
- **37 gardées**, dont 2 lues autrement ; **8 pas encore lues** par le moteur ; **11 plus lues**, plus les 5 réglages cachés.
- Le cadre « Réglages avancés » de l'onglet « La pièce » se vide : il disparaît.

---

## 3. Ce que la 3.0 demande

| Besoin | Source | Le moteur le lit déjà ? |
|---|---|---|
| Réglages du foyer : sommeil, ouvrir la nuit, durées d'aération, gestes « plus tard », durées des appareils, « Cette nuit », buée, hors-gel, tolérance, « Pas maintenant » | cahier § 10.3, § 15 ; plan § 5 | oui, `Habits.of(maison, pièce)` |
| Une pièce qui diffère du foyer (chambre d'enfant, travail de nuit) | cahier § 10.3 ; plan § 5.1 | oui (la pièce gagne) |
| Curseurs « Confort ou économie » et « La nuit » | cahier § 10.3 | non : place réservée |
| Taille de chaque ouvrant | cahier § 6.3 ; plan § 4.3 | oui (`Opening.area`, `height`) |
| Type de vitrage : simple, double, triple | cahier § 6.3, § 16.2 | non |
| Habitude d'un volet manuel : le plus souvent ouvert ou fermé | cahier § 6.7 ter | non |
| « Ce chauffage chauffe : cette pièce · toute la maison » | cahier § 6.7 bis ; plan § 4.3 | oui (`house_heaters`) |
| Thermostat principal de la plage (le Salon suit le poêle) | cahier § 6.8 | oui (`thermostat_plage`) |
| La plage suit le thermostat | cahier § 6.8 | oui (`thermostat_reference`) |
| Puissance du chauffage, si Versatile ne la donne pas | cahier § 6.8 | oui (`Room.heating_power`) |
| Débit de la VMC rapide (m³/h) | plan § 4.3 | oui (`boost`) |
| Débit d'air propre du purificateur (m³/h) | plan § 4.3 | oui (`purifier`) |
| Volet relié et Adaptive Cover Pro | cahier § 6.2 bis, § 6.7 ter | oui (`cover`, `cover_auto`, `acp`) |
| Ventilateur déclaré ou relié | cahier § 9.2 | non (geste encore à faire pour la 3.0) |
| La pièce : surface et hauteur (ou volume), murs lourds ou légers | cahier § 6.3, § 16.2 | oui (`Room.volume`, `walls`) |
| Usage de la pièce : chambre, cuisine, salle de bain… | cahier § 6.3 | oui (`Room.uses`), pas encore utilisé |
| Encart d'essai terrain sur l'accueil | plan § 7 bis | — |
| Après la 3.0 : dormeurs, porte habituellement fermée, cuisson, sèche-linge, masques par direction, place de la station | cahier § 3 bis, § 6.3 | non : **pas dans cette maquette** |

---

## 4. La nouvelle organisation

Les pages et les onglets restent ceux de la 2.1 ; leur contenu change. Pour chaque page : ce qui **reste**, ce qui **s'ajoute**, ce qui **part**.

### 4.1 Accueil Confort

- **Reste** : l'en-tête, les compteurs, « À régler », « À améliorer », « Vos pièces ».
- **S'ajoute** : l'encart **« Participez à l'amélioration du moteur »**, pendant les préversions 3.0.0bN seulement (plan § 7 bis).
  - Ce qui serait exporté, rubrique par rubrique, en clair.
  - Ce qui manque et aiderait : « 3 fenêtres sans taille », « 10 jours d'historique : 30 aideraient ».
  - « L'issue est publique », écrit avant les boutons.
  - Deux boutons : « Télécharger mon rapport », « Préparer une issue sur GitHub ».
- **S'ajoute dans « À améliorer »** : les données « Pour aller plus loin » qui aideraient le plus, une ligne par pièce (« Salon : la taille des fenêtres affinerait les aérations »), avec un lien vers le bon onglet.

### 4.2 Réglages généraux

- **Reste** : « Vos pièces », « Notifications lumineuses », « Les cartes ».
- **Change** : l'encart « Le foyer » devient un **résumé** de la page « Réglages du foyer » (sommeil, nombre de conseils, hors-gel) avec un bouton **« Régler le foyer »**.
- **Déplacé** : l'allergie aux pollens va dans la page « Réglages du foyer », rubrique « Santé ».

### 4.3 Nouvelle page « Réglages du foyer »

Chemin : `/hestia/confort/reglages/foyer`, ouverte depuis Réglages généraux, enregistrée tout de suite comme les lumières. Une rubrique par cadre. Chaque ligne : le réglage, « Ce que ça change », et « Par défaut : … » avec un bouton pour y revenir.

| Rubrique | Réglage | Par défaut | Contrôle | Clé (`home.foyer`) |
|---|---|---|---|---|
| **Sommeil** | Coucher, lever | 22:00, 07:00 | deux heures | `sommeil.debut`, `sommeil.fin` |
| | Ouvrir une fenêtre la nuit | non | interrupteur | `ouvrir_la_nuit` |
| **Combien de conseils** | Plus de conseils ↔ moins de conseils | au milieu (1) | curseur à 5 crans : 0,5 · 0,75 · 1 · 1,5 · 2 | `tolerance` |
| **Gestes proposés** | Aération la plus longue | 30 min | liste : 10, 15, 20, 30, 45 min, 1 h | `aeration_max_min` |
| | Gestes « plus tard », jusqu'à | 2 h | liste : 30 min, 1 h, 2 h, 3 h, 4 h | `plus_tard_max_min` |
| | VMC rapide et purificateur, durée la plus longue | 1 h | liste : 15, 30, 45 min, 1 h, 1 h 30, 2 h | `appareils_max_min` |
| | « Pas maintenant » met le geste de côté | 1 h | liste : 15 min, 30 min, 1 h, 2 h, 4 h | `pas_maintenant_min` |
| **Le soir** | « Cette nuit, pensez à… » | 4 h avant le coucher | liste de 1 à 8 h | `cette_nuit_avant_h` |
| | Buée de la nuit | 5 h avant le coucher | liste de 1 à 8 h | `buee_avant_h` |
| **Absence** | Hors-gel pendant les vacances | 7 °C | nombre, au demi-degré | `hors_gel` |
| **Santé** | Allergie aux pollens | non | interrupteur | `home.pollen_allergy` (déplacé, clé gardée) |
| **Bientôt** (grisé) | Confort ou économie ; La nuit | — | curseurs grisés, « avec Hestia Énergie » | réservées |

- **Un curseur plutôt qu'un nombre** : « tolérance 1,5 » ne parle à personne. Le curseur dit son effet juste dessous : « Moins de conseils : seulement les gestes les plus nets ».
- **Des limites plutôt que des durées** (décidé avec Frank le 1er novembre) : Hestia calcule la durée de chaque geste, de 5 en 5 minutes, avec le jumeau de la pièce. Le foyer fixe seulement jusqu'où il accepte d'aller. Voir le § 4.5.
- **Des listes plutôt que des champs libres** : les bornes sont tenues sans message d'erreur.

### 4.4 La pièce, onglet par onglet

Les sept onglets et le récapitulatif restent. En bas de chaque onglet qui en a, **« Pour aller plus loin »**, replié, avec son compteur.

**Température**
- **Reste** : les trois capteurs ; la plage (minimum, maximum en hiver, maximum en été) ; l'humidité maximale.
- **Change** : quand un thermostat porte la plage, elle le dit : « Le minimum suit le thermostat du poêle : 21 °C en ce moment ». Le choix lui-même se fait dans Chauffage.
- **Part** : l'humidité minimale (question 1, § 7).

**Ouvertures**, pour chaque ouvrant
- **Reste** : exposition, angle précis, type, abrité, volet et qui le pilote.
- **Remonte** : la **taille** (largeur × hauteur) sort du repli « Dimensions ». Vide, elle montre la taille ordinaire du type en grisé : « 1,2 × 1,2 m si vide ». Reprise d'Adaptive Cover Pro quand il la donne.
- **S'ajoute** : pour un volet manuel, **« Le plus souvent : ouvert · fermé · ça dépend »** (§ 6.7 ter).
- **Pour aller plus loin** : vitrage (simple, double, triple, « je ne sais pas ») ; avancée au-dessus de la fenêtre (débord de toit, balcon de l'étage, casquette).
  - **Un croquis** vu de côté montre les deux mesures : **A**, la profondeur, du mur au bord de l'avancée ; **B**, l'écart, du dessous de l'avancée au haut de la fenêtre.
  - **« Comment mesurer »**, replié : au mètre ruban depuis le sol, ou en comptant les tuiles qui dépassent (environ 0,3 m par tuile) ; à 10 cm près.
  - Ce que ça débloque : l'heure où l'avancée cache le soleil. L'été, le soleil haut est caché ; l'hiver, le soleil bas entre.

**Air intérieur**
- **Reste** : CO₂, PM2.5, COV, purificateur, VMC, VMC rapide ; un repère par mesure : CO₂ « aérer à partir de » 1 000 ppm, PM2.5 15 µg/m³, seuil COV dans l'unité du capteur.
- **Change** : les trois repères de CO₂ deviennent un seul. Le second repère (1 500 ppm, HCSP) est affiché, pas réglable : c'est une norme.
- **S'ajoute, sous chaque appareil choisi** : son **débit** en m³/h. Vide : « une valeur ordinaire », puis le débit appris quand il l'est.
- **Part** : les deux délais du COV.

**Présence**
- **Reste** tel quel : capteurs, personnes, délai. Le moteur 3.0 doit les lire (§ 6.6 du cahier).

**Chauffage**
- **Reste** : « Pièce chauffée », témoin de chauffe, ce que Versatile donne (affiché).
- **Change** : **plusieurs chauffages par pièce** au lieu d'un. Le Salon de Frank en a deux : le poêle et les radiateurs. La 2.1 n'en gardait qu'un (le poêle) ; l'essai du labo lit les deux.
- **S'ajoute, sous chaque chauffage** : **« Ce chauffage chauffe : cette pièce · toute la maison »**. Proposé d'office « toute la maison » pour un poêle, un insert ou une cheminée reconnus. Quand c'est appris, la page dit où va la chaleur.
- **S'ajoute** : **« La plage de la pièce suit »** : un des chauffages de la pièce · aucun. Cette liste remplace la case `thermostat_reference` (« aucun » vaut non).
- **Pour aller plus loin** : type de chauffage (convecteur ou soufflant par défaut, panneau rayonnant, radiateur à inertie ou à eau, plancher chauffant, poêle à bois ou insert, poêle à granulés, climatisation réversible ; lu par le moteur depuis 3.9.5, CAHIER-MOTEUR.md § 6.7 bis) ; puissance en W, seulement sans Versatile (avec lui : « 8 500 W, lue dans Versatile Thermostat »).
- **Part** : la tolérance avant « Rallumez ».

**La pièce**
- **Reste** : nom, pièce Home Assistant, étage, même air.
- **Change** : **Équipements** s'enrichit (demande de Frank). Relié à une entité, un équipement dit quand il marche : Hestia connaît alors la source du moment au lieu de la deviner (§ 4.5, décision 2).
  - **Une liste d'équipements courants**, chacun avec ce qu'il change : douche ou baignoire (humidité) ; plaque de cuisson (humidité, COV, particules, chaleur) ; four (COV, chaleur) ; hotte (enlève l'humidité et le COV) ; sèche-linge ou linge qui sèche (humidité) ; ventilateur (rafraîchit la peau).
  - **Sous chaque équipement coché**, une entité facultative « Pour savoir quand il marche » : un interrupteur, une prise, ou un capteur de puissance (en marche au-dessus de quelques watts).
  - **« Ajouter un autre équipement »** : un nom libre (« Déshumidificateur », « Aquarium »), ce qu'il change, en puces (chauffe, rafraîchit, mouille l'air, assèche l'air, COV et odeurs, particules et fumée, purifie), et son entité facultative.
  - Le ventilateur garde ses trois choix : aucun, sans entité, relié (une entité `fan`).
- **S'ajoute** : **« Différent du foyer pour cette pièce »**, replié. Une case par réglage du foyer qui peut différer : sommeil, ouvrir la nuit, combien de conseils. Cochée, la ligne s'ouvre avec la valeur de la maison, prête à changer. Seul ce qui diffère est rangé, dans `foyer` des options de la pièce.
- **Pour aller plus loin** : usage (chambre, séjour, cuisine, salle de bain, bureau, autre) ; surface (m²) ; hauteur sous plafond (m) ; et les murs, précisés (remarque de Frank : « quel mur ? ») :
  - **Murs qui donnent dehors** : Nord, Est, Sud, Ouest, en puces. Les autres touchent une autre pièce ou le voisin.
  - **Murs du dehors, faits en** : pierre, béton ou brique · bois, ossature bois · je ne sais pas.
  - **Isolés** : par l'intérieur (doublage) · par l'extérieur · pas isolés · je ne sais pas. C'est ce qui décide si la masse du mur garde la chaleur de la pièce : isolé par l'intérieur, presque plus.
  - **Murs entre les pièces** : cloisons légères (placo, carreaux de plâtre) · murs lourds · je ne sais pas.
  - Avec ces réponses, Hestia part de votre maison, pas d'une maison ordinaire : des conseils justes dès la première semaine, et plus sûrs la première fois qu'il fait très chaud ou très froid.
- **Part** : tout le cadre « Réglages avancés » (rafales, gel, soleil compté, facteur du vitrage, luminosité basse, ancienneté des mesures).

**Notifications** : inchangé.

### 4.5 Ce que ces réglages demandent au moteur (décidé avec Frank le 1er novembre)

Dans la branche `moteur-conseil-3`, le moteur ne compare que les durées de la liste : 10 min, 20 min, ou « Ouvrez » sans durée (`decide.py`, `candidates`). Il faudrait 6 min ? Il dit « Aérez 10 min ». Fenêtre ouverte, il affiche « Rien à faire » tant que refermer n'est pas meilleur, ce qui ne dit pas s'il faut refermer.

Frank a validé cinq changements du moteur. Ils ne sont pas dans cette maquette : ils remontent au cahier du moteur, par le fil principal.

1. **Des paliers de 5 minutes, calculés** : la durée la plus courte qui suffit, jusqu'à la limite du foyer. Fenêtre ouverte : « Laissez ouvert encore 5 min », puis « Refermez ». Pareil pour les gestes « plus tard » et pour la VMC rapide et le purificateur.
2. **La source du moment**, pour toutes les mesures (COV, CO₂, humidité, particules). Si la mesure ne fait pas ce que le jumeau prévoit, une source tourne encore (cuisson, douche, invités, poêle) : le moteur en déduit sa force et la garde un temps appris. Sans elle, une cuisson qui continue donnerait « Refermez » à tort ; le jumeau ne connaît aujourd'hui qu'une source moyenne selon l'heure (`physics/air.py`).
3. **L'air traversant** : « Ouvrez aussi la porte-fenêtre : 5 min au lieu de 15 » (prévu au § 9.1 du cahier, pas encore dans le moteur).
4. **Dire quand refermer** : « encore 4 min » sur la carte, et la lumière qui change quand c'est le moment.
5. **Prévoir une source habituelle** (après la 3.0) : « Il est 19 h, entrouvrez avant de cuisiner ».

### 4.6 Extensions (le dehors)

- **Inchangé** : Weather ou ses propres capteurs, le niveau ATMO qui bloque l'aération, les extensions tierces.
- **S'ajoute, sous Hestia Weather**, en lecture : « Soleil prévu : Open-Meteo, recoupé par votre station » ou « Open-Meteo seul » (décision 1 du § 8 du plan).

---

## 5. Où chaque nouveau réglage est rangé

| Réglage | Rangement | Lu par le moteur comme |
|---|---|---|
| Réglages du foyer | store `hestia_comfort.home`, clé `foyer` | `Habits.of(maison, …)` |
| Différent pour cette pièce | options de la pièce, clé `foyer` (seulement ce qui diffère) | `Habits.of(…, pièce)` |
| Taille d'un ouvrant | `openings.*.width`, `height` (existent) | `Opening.area = width × height`, `Opening.height` |
| Vitrage | `openings.*.glazing` : `simple` · `double` · `triple` | nouveau |
| Habitude du volet manuel | `openings.*.shutter_habit` : `open` · `closed` · `varies` | nouveau |
| Les chauffages de la pièce et ce qu'ils chauffent | options de la pièce, `heaters` : liste de `{entity_id, scope: room · house, kind, power}` | `thermostat` (le chauffage `room`) ; `house_heaters` = les chauffages `house` de toutes les pièces, puissance lue dans Versatile |
| La plage suit | `thermostat_plage` (entité `climate`) ; « aucun » écrit `thermostat_reference: false` | inchangé |
| Repli pour un retour à la 2.1 | `sources.heating` = le chauffage que suit la plage | la 2.1 retrouve le chauffage qu'elle connaissait |
| Débit de la VMC rapide, du purificateur | `flows.ventilation_boost`, `flows.purifier` (m³/h) | `boost`, `purifier` |
| Équipements | `equipment` : liste de `{kind, name, effects, entity_id}` ; `kind` = `shower` · `hob` · `oven` · `hood` · `drying` · `fan` · `custom` ; `effects` parmi `heat` · `cool` · `humid` · `dry` · `voc` · `particles` · `purify`. Une ancienne valeur `"shower"` se lit `{kind: shower}` | nouveau : la source du moment connue quand l'entité dit « en marche » |
| Usage, surface, hauteur | `room.uses`, `room.surface`, `room.height` | `Room.uses`, `volume = surface × hauteur` |
| Murs | `room.outside` (`N` · `E` · `S` · `O`), `room.wall_material` (`heavy` · `wood`), `room.insulation` (`inside` · `outside` · `none`), `room.partitions` (`light` · `heavy`) | `Room.walls` : `heavy` si les murs lourds sont du côté chaud (isolés par l'extérieur, pas isolés, ou cloisons lourdes), sinon `light` ; murs du dehors pour la chaleur perdue |

**À corriger dans `Configuration.save`** (maison) : recopier aussi `foyer`, sinon enregistrer l'onglet Extérieur l'efface. Et ajouter une commande `hestia_comfort/set_foyer`, enregistrée tout de suite, comme l'allergie et les lumières.

**À ajouter dans `validate`** (pièce) : le contrôle de `foyer`, `heaters`, `thermostat_plage`, `flows`, `room`, `glazing`, `shutter_habit`, avec les bornes du § 6.

---

## 6. Les bornes

Celles du § 5.4 du plan, revues, et celles des nouveaux réglages.

| Réglage | Bornes | Pourquoi |
|---|---|---|
| Heures de sommeil | heures et minutes ; coucher ≠ lever ; une nuit de 4 à 14 h | une « nuit » de 2 h ou de 20 h est une erreur de saisie |
| Aération la plus longue | 10 min à 1 h | au-delà d'une heure, c'est « Ouvrez », sans durée |
| Gestes « plus tard », jusqu'à | 30 min à 4 h | au-delà, la prévision est trop incertaine |
| VMC rapide et purificateur, durée la plus longue | 15 min à 2 h | |
| Les paliers eux-mêmes | 5 min, fixe | le pas du moteur (`STEP_MINUTES`) |
| « Cette nuit », buée | 1 à 8 h avant le coucher | |
| Hors-gel | 5 à 12 °C | sous 5 °C, les canalisations ; au-dessus de 12 °C, ce n'est plus un hors-gel |
| Combien de conseils | 0,5 à 2, en 5 crans | |
| « Pas maintenant » | 15 min à 4 h | |
| Taille d'un ouvrant | largeur et hauteur de 0,2 à 6 m | la 2.1 acceptait 0,01 à 20 m |
| Débit de la VMC rapide | 10 à 600 m³/h | |
| Débit d'air propre du purificateur | 20 à 1 000 m³/h | |
| Puissance du chauffage | 100 à 20 000 W | |
| Surface | 2 à 200 m² | |
| Hauteur sous plafond | 1,8 à 8 m | une mezzanine, un séjour cathédrale |
| Plage, repères | ceux de la 2.1 | inchangés |

---

## 7. Questions pour Frank

**Réponses retenues avec la validation du 1er novembre** : les réponses proposées ci-dessous, sauf avis contraire de Frank.

1. **L'humidité minimale** (40 %) : la 3.0 ne dit jamais « air sec ». On la retire (proposé), ou on garde un « Bon à savoir : air sec » ?
2. **Rafales et gel** : la 2.1 les laissait régler par pièce, la 3.0 en fait des règles fixes (§ 9.3 du cahier). Proposé : règles fixes, comme le cahier. Un utilisateur qui les avait changées le lira dans la note de version.
3. **« Combien de conseils »** : un curseur à 5 crans (proposé), ou trois choix « Plus · Normal · Moins » ?
4. **« La plage suit »** remplace la case « Prendre la consigne du thermostat comme minimum » : d'accord pour une seule liste ?
5. **L'usage de la pièce** dans « Pour aller plus loin » de « La pièce », et non dans « Air » comme le dit le cahier (§ 16.2) : une seule place pour décrire la pièce. D'accord ?
6. **Surface et hauteur** plutôt qu'un volume en m³ : plus simples à connaître. D'accord ?
7. **Plusieurs chauffages par pièce** (le poêle et les radiateurs du Salon) : d'accord pour cette liste, à la place du chauffage unique de la 2.1 ?

---

## 8. La maquette

[maquette-reglages-3.html](maquette-reglages-3.html) : un seul fichier, sans réseau, au style du hub (Manrope, cadres arrondis, thème sombre ou clair selon le système). Huit écrans :

1. Accueil Confort, avec l'encart d'essai terrain.
2. Réglages généraux, avec le résumé du foyer.
3. Réglages du foyer.
4. Salon · Température.
5. Salon · Ouvertures.
6. Salon · Air intérieur.
7. Salon · Chauffage.
8. Salon · La pièce, avec « Différent du foyer pour cette pièce ».

Les onglets Présence, Notifications et Récapitulatif ne changent pas : la maquette le dit seulement.

L'interrupteur **« Montrer les changements »**, en haut, pose sur chaque élément une étiquette de maquette (**Nouveau**, **Déplacé**, **Changé**) et liste en bas de chaque écran ce qui **part**. Les valeurs sont celles de la maison de Frank : le Salon suit le poêle, Chambre P 18–24 °C, purificateur 150 m³/h, VMC rapide 60 m³/h.

Les boutons ne font rien : rien n'est enregistré.

---

## 9. Historique du document

- **v1.0 — 1er novembre 2026** : validée par Frank.
- **v0.3 — 1er novembre 2026** : croquis et « Comment mesurer » pour l'avancée ; équipements courants et libres, chacun avec ce qu'il change et une entité facultative ; murs précisés (côtés dehors, matière, isolation, cloisons).
- **v0.2 — 1er novembre 2026** : les durées en puces deviennent trois limites (aération, « plus tard », appareils) ; Hestia calcule la durée par paliers de 5 minutes. Cinq changements du moteur validés par Frank, notés au § 4.6, à remonter au cahier.
- **v0.1 — 1er novembre 2026** : inventaire de la 2.1.0b7, besoins de la 3.0, nouvelle organisation, bornes, sept questions, maquette HTML.
