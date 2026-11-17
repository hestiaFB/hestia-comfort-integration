# Les habitudes du foyer : ce que les capteurs ne disent pas

Version 1.0 — 5 novembre 2026. **Validée par Frank le 5 novembre** (« ok pour tout », avec la plage de confort que le thermostat remplace).

**Codé le 5 novembre** dans `niak-comfort-integration` (branche `moteur-conseil-3`, moteur 3.7.0, non commité), déployé au labo. Reste : le linge est enregistré mais aucune règle ne le lit encore (le moteur 3.x n'a pas de phrase « c'est le linge ») ; « Baissez le volet ce soir » pour un volet à la main « Ouverts » n'est pas encore dit (seulement pour un volet motorisé, comme avant) ; la plage de la maison ne sert qu'aux pièces créées ensuite et aux pièces sans plage enregistrée (chaque pièce existante garde la sienne).

La maquette : [maquette-habitudes.html](maquette-habitudes.html), à ouvrir dans un navigateur (style du hub, `CAHIER-HUB.md`).

Sources lues : moteur 3.4 de la branche `moteur-conseil-3` (`advisor/household.py`, `nightly.py`, `safety.py`, `decide.py`, `physics/thermal.py`, `physics/sunlight.py`), `engine/habits.py` et `engine/people.py` de la 2.x, `REGLAGES-3.md` v1.0, `CAHIER-MOTEUR.md` § 6.6, 6.7 ter, 10.3, `CAHIER-HUB.md`.

---

## 1. Le problème, vu dans le code

- **Un volet à la main n'est vu nulle part.** Le jumeau ne connaît que la position d'un volet motorisé (`Inputs.shade`, `Inputs.shutter`). Pour un volet manuel, l'habitude « est dans le soleil appris » (`thermal.py`) : le moteur apprend une **moyenne**.
- **L'apprentissage de nuit ne lit pas l'alarme.** `nightly.samples` compte le soleil sur les fenêtres à chaque pas de 5 min, que la maison soit vide ou non. Au Salon, les jours d'absence volets fermés, le soleil compté n'entre pas : le jumeau baisse la part de soleil gardée (`glass`) et conclut que le soleil chauffe moins qu'en vrai.
- **Les anciennes questions Oui / Non** (`engine/habits.py`, 1.2.5-beta.7) existent encore dans la 2.x : humidité qui monte à la même heure, fenêtre ouverte la nuit. Le moteur 3.x ne les lit pas (`home.answers` : « Pas encore lu », REGLAGES-3 § 2.2).

---

## 2. Les questions retenues (6, plus le vitrage du § 3 bis)

Chaque réponse est un **réglage du foyer**, avec une valeur par défaut qui garde le moteur tel qu'il est aujourd'hui. Une pièce qui diffère se règle dans « Différent du foyer ».

| # | Question | Réponses | Par défaut | Un capteur le dit déjà ? |
|---|---|---|---|---|
| 1 | Quand vous partez, les volets restent… | Fermés · Ouverts · Ça dépend | Ça dépend | Non pour un volet manuel. Volet motorisé ou ACP : lu, la question ne le concerne pas |
| 2 | La nuit, les volets sont… | Fermés · Ouverts · Ça dépend des pièces | Ça dépend | Idem |
| 3 | L'été, aux heures chaudes, côté soleil, les volets sont… | Fermés · Ouverts · Ça dépend | Ça dépend | Idem |
| 4 | En semaine, dans la journée, la maison est… | Souvent vide (de … à …) · Souvent occupée · Ça change | Ça change | **Oui** si l'alarme (Alarmo) ou les personnes (`zone.home`) sont reliées : la question n'est pas posée, la page dit « Absences lues sur Alarmo » |
| 5 | L'hiver, le linge sèche… | Dehors ou au sèche-linge · Dans la maison · Les deux, selon le temps (quelle pièce ; `linge_parfois`, ajouté par Frank le 5 nov.) | rien de dit | Non. Un sèche-linge relié reste dans Équipements |
| 6 | Le week-end, vous vous levez… | Comme en semaine · Plus tard, vers … | Comme en semaine | En partie : l'alarme en mode nuit compte comme sommeil, si on l'arme |

Les questions 1 à 3 ne paraissent que si la maison a **au moins un volet manuel** déclaré (onglet Ouvertures).

### Écartées

| Question | Pourquoi |
|---|---|
| Fenêtre ouverte la nuit | Les contacts le mesurent. La question « est-ce voulu ? » reste dans Apprentissage, quand le moteur le voit |
| Ouvrir une fenêtre la nuit (se lever pour aérer) | Existe déjà : Réglages › Sommeil |
| Heures de coucher et de lever | Existent déjà : Réglages › Sommeil (la 6 les complète) |
| Douches | Équipement « douche » de la pièce + humidité mesurée : l'heure est trouvée seule |
| Cuisine | Idem (plaque, hotte dans Équipements) ; prévoir la cuisson du soir vient après la 3.0 (REGLAGES-3 § 4.5, point 5) |
| Porte de chambre fermée | La part de chaleur apprise par pièce la contient déjà (cahier § 6.7 bis) |
| Rideaux, voilages | Dans la part de soleil apprise (`glass`) |

---

## 3. Comment chaque réponse entre dans le moteur

Rangement : `home.foyer` (maison), `foyer` des options de la pièce (ce qui diffère), lus par `Habits.of(maison, pièce)` comme les autres réglages du foyer. Clés plates, pour la fusion maison → pièce.

**Qui est absent, quand** (sert aux questions 1 et 4) : l'alarme armée « absent » ou « vacances » ; sinon `zone.home` à 0 ; sinon les horaires de la question 4, en semaine. Rien de tout ça : la question 1 n'a pas d'effet, et la page le dit.

| # | Clé | Apprentissage de nuit | Conseils du jour |
|---|---|---|---|
| 1 | `volets_absence` : `fermes` · `ouverts` · `variable` | **Fermés** : pendant les absences, les fenêtres à volet manuel de la pièce ne comptent plus de soleil, et gagnent la chaleur gardée par le volet (EN ISO 10077-1, comme un volet motorisé fermé). Le jumeau garde ces jours pour tout le reste. **Ça dépend** : comme aujourd'hui | Absence en cours : la prévision de la pièce ne compte pas ce soleil (température au retour) |
| 2 | `volets_nuit` | **Fermés** : du coucher au lever, chaleur gardée par le volet et pas de soleil du matin avant le lever (fenêtres à l'est l'été) | **Fermés** : « Baissez le volet ce soir » n'est plus dit (c'est déjà fait). **Ouverts** : dit en « Bon à savoir » quand le gain atteint le seuil du § 6.7 ter. **Ça dépend** : dit au conditionnel, comme prévu |
| 3 | `volets_ete` | **Fermés** : l'été (saison de Weather), quand le soleil est sur la façade d'une fenêtre à volet manuel, ce soleil n'est pas compté | **Fermés** : pas de rappel « Baissez le volet avant 14 h » ; la prévision « trop chaud cet après-midi » en tient compte. Sinon : le rappel reste |
| 4 | `journee_vide` : `null` ou `{de, a}` | Sert à la question 1 quand rien d'autre ne dit l'absence | Pendant ces heures, en semaine : aucun geste (comme l'alarme « absent », `safety.forbidden`) ; un geste « plus tard » peut viser l'heure du retour |
| 5 | `linge_pieces` : liste de pièces, ou `[]` pour « dehors » | Le jumeau de l'humidité de ces pièces attend une source longue l'hiver : une hausse de plusieurs heures n'est pas prise pour un manque d'air | La hausse a un nom : « C'est le linge qui sèche » ; aération courte répétée ou VMC rapide. Plus de question « Est-ce une habitude ? » pour ces pièces |
| 6 | `sommeil.fin_weekend` : heure ou absent | — | `Sleep.asleep` prend le lever du week-end : ni geste d'ouverture ni lumière (WLED) avant ; « Aérez au lever » à la bonne heure |

**Pas de constante nouvelle.** Le volet fermé reprend ce qui existe pour un volet motorisé (`SHUT_SHADE`, `shutter_insulation`). Les heures viennent des réglages du foyer.

**Touche à `nightly.py`** (`samples`) pour 1, 2 et 3 : à coordonner avec la session sur l'apprentissage de nuit 3.5.0 avant de coder.

---

## 3 bis. Votre maison : une valeur pour toutes les pièces (remarque de Frank, 5 novembre)

Certains réglages sont presque toujours les mêmes partout : le vitrage, le volet, la hauteur sous plafond, les murs. Les demander fenêtre par fenêtre ou pièce par pièce, c'est dix fois la même réponse.

**Le principe** : une valeur de la maison, dans Réglages › Votre maison. Chaque ouvrant et chaque pièce la reprend, **« Comme la maison »**, et la montre déjà choisie. On la change sur place si cette fenêtre ou cette pièce diffère : elle devient « Propre à cet ouvrant », avec « Comme la maison » pour revenir.

- **Repris, pas recopié** : un ouvrant « Comme la maison » suit la maison si on la change plus tard. Seul ce qui diffère est rangé dans l'ouvrant ou la pièce (comme « Différent du foyer »).
- **Un nouvel ouvrant ou une nouvelle pièce** arrive avec les valeurs de la maison déjà choisies.
- **Les ouvrants et les pièces existants** n'ont rien d'enregistré : ils lisent la valeur de la maison. Rien n'est réécrit à la mise à jour.
- La ligne de la maison dit combien la reprennent : « 9 ouvrants · 2 différents ».

| Valeur de la maison | Choix | Par défaut | Reprise par | Ce qu'elle change dans le moteur |
|---|---|---|---|---|
| **Vitrage** | Simple · Double · Triple | Double (le plus courant) | chaque ouvrant (`openings.*.glazing`) | Aujourd'hui figé en double partout : le soleil qui traverse (`G_VALUE` 0,6), la chaleur perdue (`GLAZING_U` 2,8) et **la buée** (`GLASS_FACTOR` 0,64, `surface.py`). Ce sont des valeurs de norme par type, pas des réglages : un simple vitrage s'embue bien plus tôt, un triple presque jamais. La buée n'est pas apprise : seul ce choix la corrige |
| **Volets** | Aucun · À la main · Motorisé | Aucun | chaque ouvrant (`openings.*.shutter`) | Les questions 1 à 3 ; un volet motorisé demande ensuite son entité, ouvrant par ouvrant |
| **Hauteur sous plafond** | 2,40 · 2,50 · 2,70 m · autre | vide (2,50 m supposé) | chaque pièce (`room.height`) | Le volume de la pièce, avec sa surface |
| **Murs du dehors** | Pierre, béton, brique · Bois · Je ne sais pas | Je ne sais pas | chaque pièce (`room.wall_material`) | La chaleur gardée par les murs, au départ de l'apprentissage |
| **Isolation** | Par l'intérieur · Par l'extérieur · Pas isolés · Je ne sais pas | Je ne sais pas | chaque pièce (`room.insulation`) | Idem |
| **Plage de confort** | minimum, maximum hiver, maximum été | 20 · 24 · 26 °C | chaque pièce (`settings.*`) | Le coût d'inconfort ; une chambre plus fraîche se change dans sa page. **Le thermostat passe avant** (Frank, 5 novembre) : dans une pièce dont la plage suit un thermostat (Chauffage › La plage suit), le minimum est la consigne du thermostat, pas la valeur de la maison. La ligne de la maison le dit : « Le thermostat la remplace, s'il est renseigné » |

**Pas reprises**, parce qu'elles changent d'une fenêtre ou d'une pièce à l'autre : exposition, type d'ouvrant, taille, abri et avancée, murs qui donnent dehors, usage, surface.

Le vitrage est aussi posé dans le questionnaire (une question de plus, en tête : « Vos fenêtres sont en… ») ; les autres valeurs de la maison restent dans Réglages.

---

## 4. Où, dans le hub

- **Vue d'ensemble › À améliorer** : une ligne « Vos habitudes · 7 questions, une minute », tant qu'il reste des questions sans réponse. Gris, jamais orange : rien n'est cassé.
- **Le questionnaire**, ouvert par cette ligne : une question par écran, de gros boutons, « Je ne sais pas » et « Passer ». À la fin : « C'est noté. Vous pouvez tout changer dans Réglages. »
- **Le questionnaire reprend à la première question sans réponse** (5 novembre), qu'il soit ouvert depuis la Vue d'ensemble ou depuis Réglages ; chaque réponse est enregistrée aussitôt.
- **L'un ou l'autre** (Frank, 5 novembre, comme dans Weather › Station › Emplacement) : tant que rien n'est répondu, Réglages › Vos habitudes ne montre que la carte qui ouvre le questionnaire ; dès la première réponse, seulement les lignes.
- **Réglages › Vos habitudes** : les mêmes questions, en lignes (libellé à gauche, choix à droite), « Par défaut : … » et « Rétablir ». C'est là qu'on change d'avis plus tard.
- **Pièce › La pièce › Différent du foyer** : les volets de cette pièce, si elle diffère (la chambre M, volet presque jamais fermé).
- **Le réglage d'ouvrant « Le plus souvent : ouvert · fermé · ça dépend »** (REGLAGES-3 § 4.4, pas encore codé) est remplacé par les questions 1 à 3 et « Différent du foyer » : un seul endroit.
- **« Linge qui sèche »** quitte la liste des Équipements de la pièce (REGLAGES-3 § 4.4) : c'est une habitude, pas un appareil. Le sèche-linge relié y reste.

---

## 5. Plus tard (pas dans cette proposition)

- **Le moteur qui demande** : quand une pièce prend nettement moins de soleil les jours d'absence, la question 1 remonte dans Apprentissage, avec ce qui a été vu.
- Les anciennes questions de `engine/habits.py` (humidité à heure fixe, fenêtre la nuit) reprises par le moteur 3.x, dans la page Apprentissage.

---

## 6. Questions pour Frank

**Réponses du 5 novembre** : oui aux sept, avec les réponses proposées (questionnaire guidé et lignes dans Réglages ; « Ça dépend » par défaut ; repris plutôt que recopié). Pour la plage de confort de la maison : gardée, en disant que le thermostat la remplace s'il est renseigné.

1. Les **6 questions** vous vont ? Une à retirer, une à ajouter ?
2. **« Ça dépend »** comme réponse par défaut, qui garde le moteur d'aujourd'hui : d'accord ?
3. Les **trois questions de volets** remplacent le réglage « Le plus souvent » de chaque ouvrant : d'accord ?
4. **Le linge** passe des Équipements aux habitudes : d'accord ?
5. Le questionnaire guidé depuis la Vue d'ensemble **et** les mêmes lignes dans Réglages : ou seulement Réglages ?
6. **Votre maison** (§ 3 bis) : les six valeurs reprises vous vont ? La plage de confort de la maison, surtout : chaque pièce l'a aujourd'hui en propre.
7. **Repris plutôt que recopié** : un ouvrant « Comme la maison » suit la maison quand on la change. D'accord, ou préférez-vous une simple copie à la création ?

---

## 7. Historique

- **v1.0 — 5 novembre 2026** : validée par Frank ; la plage de confort de la maison cède au thermostat de la pièce.
- **v0.2 — 5 novembre 2026** : « Votre maison » (§ 3 bis), demande de Frank : vitrage d'abord, puis volet, hauteur, murs, isolation, plage ; chaque ouvrant et chaque pièce les reprend « Comme la maison », modifiables sur place. Le vitrage entre dans le questionnaire.
- **v0.1 — 5 novembre 2026** : liste, entrée dans le moteur, places dans le hub, maquette.
