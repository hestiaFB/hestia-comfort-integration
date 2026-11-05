# Logement et étages — 0.6.0-beta.1

Bêta du bloc 6, préparée le 15 octobre 2026. Vérifiée localement ; les contrôles décrits ci-dessous ne constituent pas une validation sur le logement de production.

## Réglage et affichage

Les pièces rattachées à Home Assistant reprennent l’étage de leur zone. Dans **Pièce et confort**, Hestia-FB indique cet étage et explique où le modifier. Pour une pièce libre, un sélecteur facultatif permet de choisir un étage Home Assistant existant. Les identifiants font foi ; Hestia-FB ne devine rien à partir des noms. Supprimer un étage conserve les pièces, dans le groupe sans étage. La carte se met à jour à la modification des registres de zones et d’étages.

La carte affiche les niveaux dans l’ordre de leur numéro, sous-sols inclus, puis les niveaux sans numéro et les pièces sans étage. Chaque groupe affiche sa moyenne arithmétique, sa couverture (n pièces mesurées sur N), sa pièce la plus chaude et toutes ses pièces. Les mesures inconnues, périmées ou non finies ne participent pas aux moyennes. La moyenne n’est pondérée ni par la surface ni par le volume ; elle ne remplace pas les conseils des pièces.

Avec un seul groupe, la carte présente simplement **Mon logement**. Le plain-pied reste pleinement utilisable, y compris sans étage configuré. L’absence d’étages ne permet pas à Hestia-FB d’affirmer que la maison est de plain-pied. Des niveaux peuvent aussi ne contenir aucune pièce suivie.

## Conseils

La priorité dépend du besoin et de la possibilité d’ouverture de chaque pièce. À niveau d’attention et geste comparables, la plus chaude des pièces à rafraîchir mène le bandeau. Le conseil « Commencez par » désigne la pièce la plus chaude qui peut être ouverte maintenant, avec son étage quand il est connu. Le besoin d’une pièce reste visible même si la moyenne est modérée.

Les écarts entre moyennes sont décrits comme des températures observées. Le libellé « la chaleur stagne » n’est pas employé : un instantané ne prouve pas une stagnation dans le temps.

Pour rafraîchir, une paire d’ouvrants peut être proposée :

- deux niveaux numérotés différents : effet cheminée possible, même sans vent ;
- façades opposées : aération traversante possible, y compris de plain-pied ou sans étages renseignés ;
- ouvertures basses au vent et hautes sous le vent sur des façades opposées : vent compatible avec le tirage ascendant.

Le conseil suppose un passage intérieur libre et ne garantit aucun courant d’air ni débit. Deux contacts ouverts confirment des ouvertures, pas une circulation. Un vent opposé au tirage ascendant ne devient pas un conseil de tirage combiné.

Une paire nécessite un besoin de rafraîchissement ou de pré-refroidissement dans au moins une pièce, une opportunité de fraîcheur calculée dans les deux, un extérieur plus frais et une température supérieure au minimum de confort de chaque pièce + 1 °C. Les contraintes et données incomplètes de chaque pièce excluent cette paire. Une exception d’aération courte pour le CO₂ avec chauffage en marche n’est pas transformée en conseil de rafraîchissement du logement entier. Les ouvertures déjà engagées restent présentées comme telles, sans effacer la chaleur mesurée.

## Données publiées

Ajouts compatibles au message WebSocket `hestia_comfort/home_subscribe`, version 1 :

| Champ | Contenu |
|---|---|
| `rooms[].floor` | Identifiant HA, nom, numéro de niveau, ou `null` |
| `home.floors[]` | Même identité, identifiants des pièces, moyenne, couverture, pièce la plus chaude, niveau d’attention et bilan incomplet |
| `home.floor_contrast` | Noms des groupes plus chaud / plus frais, différence des moyennes et couverture incomplète, ou `null` |
| `home.start_floor` | Étage de la pièce à ouvrir en priorité, ou `null` |
| `home.ventilation` | Possibilité de traversant, cheminée ou combinaison, paire de pièces et d’ouvrants, état d’ouverture, passage intérieur non confirmé, ou `null` |

L’API de configuration version 1 ajoute `floors`, `areas[].floor_id` et l’étage résolu de chaque pièce. `floor_id` est un réglage facultatif des seules pièces libres. Les pièces rattachées ne peuvent pas contredire leur zone HA.

Ces informations préparent une future consommation par Hestia Chauffage. Elles ne créent ni zone physique de commande ni action de chauffage. Un futur contrat Confort → Chauffage devra être défini avant ce raccordement.

## Vérifications locales

- 137 tests Python : calcul des pièces et du logement, vrais registres HA isolés, étages négatifs, renommage, déplacement et suppression, sauvegarde et effacement du choix d’une pièce libre, pièce indisponible conservée et nettoyage des abonnements.
- 15 tests de carte et 10 tests de panneau ; vérification TypeScript et compilation des deux interfaces.
- Neuf situations fictives produites par le vrai moteur Python, affichées par la vraie carte compilée : deux niveaux, plain-pied, mesure manquante, étages inconnus, rafales, extérieur chaud, ouvertures engagées, trois niveaux et vent compatible.
- Contrôle navigateur des sélections et des restrictions, thèmes clair/sombre, largeur mobile de 390 px sans débordement horizontal observé. Contrôle visuel du panneau de réglage : choix d’un étage libre, récapitulatif, puis rattachement à une zone reprenant son étage HA.

Les interfaces utilisent une connexion simulée pour ces contrôles visuels ; les tests de sauvegarde et des registres s’exécutent avec Home Assistant 2026.10 isolé. Ce n’est pas une validation sur le logement de production ni un test d’installation HACS.

Aperçus locaux : `card/preview/floors.html` et `card/preview/floor-settings.html`. Régénération des situations : `scripts/floor_fixtures.py` avec l’environnement Python de test HA.
