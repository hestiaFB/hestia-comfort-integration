## 3.1.0b10 — Le poêle au ralenti compte

### Corrections

- Le poêle au ralenti chauffe toujours : les prévisions et l'apprentissage le comptent.
- Sous une pluie fine, « Gardez fermé : il pleut » ne clignote plus.
- Le soir, plus de « Ouvrez » sans durée dans une pièce chauffée.
- Un conseil d'aération ne change plus d'heure ni de durée pour presque rien.

### Moteur de conseil 3.16.0

- Flamme minimale du poêle à granulés, pluie tenue 30 minutes, aération courte le soir, conseils et phrases plus stables.

## 3.1.0b9 — La pièce comparée à la maison

### Nouveautés

- Quand le poêle chauffe, « À savoir » dit si la pièce est nettement plus froide que le reste de la maison, et pourquoi. Exemple : « 1,8 °C sous la moyenne de la maison (21,2 °C) : le poêle chauffe peu cette pièce ».

### Moteur de conseil 3.15.1

- Nouveau « À savoir » : l'écart avec la moyenne de la maison, poêle allumé.

## 3.1.0b8 — Des conseils qui tiennent

### Corrections

- L'humidité dehors vient de votre station : plus de « Refermez » sur une prévision trop humide.
- La chaleur du poêle suit sa vraie courbe dans toutes les pièces. Exemple : 24,8 °C annoncés dans une chambre où il a fait 21,8 °C.
- Un conseil mis en pause est dit « en pause jusqu'à 22 h 35 », plus « aucun geste ne ferait mieux ».
- « À savoir » ne contredit plus le conseil affiché.
- 2 minutes de fenêtre ouverte ne comptent plus comme une aération de 20 minutes.

### Moteur de conseil 3.15.0

- L'apprentissage de nuit juge aussi les prévisions à 8 heures.
- « À essayer », l'heure d'« Aérez » et le sujet de la phrase restent stables.

## 3.1.0b7 — Le poêle compté quand il chauffe

### Corrections

- Un poêle qui attend la confirmation de son allumage ne fausse plus les prévisions de toute la maison. Exemple : « 21,7 °C à 20 h » annoncé au Salon à 19 °C alors que le poêle n'a jamais démarré.
- La nuit, la VMC rapide d'une douche s'arrête après 20 minutes.
- Une VMC arrêtée à la main reste arrêtée 2 heures, sauf nouvelle douche.
- Un extracteur qui ne sèche pas la pièce attend de plus en plus longtemps avant de repartir : 2, 4 puis 8 heures.

### Moteur de conseil 3.14.1

- Le poêle n'est compté que lorsqu'il chauffe vraiment, dans les prévisions comme dans l'apprentissage de nuit.
- La chaleur du poêle partagée entre les pièces ne dépasse plus 100 %.
- Le journal note aussi les changements de phrase.

## 3.1.0b6 — Une pastille qui dit vrai

### Améliorations

- La pastille se lit sur les mesures : « Tout va bien » seulement si tout est dans votre plage, « Au mieux » si une mesure en sort et qu'aucun geste n'aiderait. Elle ne clignote plus avec la pluie ou l'absence.
- La pluie annoncée est dite au conditionnel. Avec un pluviomètre, seule la pluie mesurée fait refermer ; une pluie annoncée s'affiche dans « À savoir ».
- Demande Hestia Météo 3.6.1 pour la force et la probabilité de la pluie. Avec une version plus ancienne, la carte fonctionne sans ces informations.

### Moteur de conseil 3.14.0

- Pastille calculée sur les mesures, au plus un changement par demi-heure.
- Pluviomètre d'abord ; pluie annoncée au conditionnel ; probabilité Météo-France prise en compte.

## 3.1.0b5 — De l'air quand il le faut

### Nouveautés

- Quand le CO₂ mesuré dépasse 1 400 ppm, la carte conseille d'aérer 10 min et donne la mesure. Exemple : « Aérez 10 min — CO₂ mesuré à 1 470 ppm : l'air est à renouveler ».

### Améliorations

- Un conseil laissé sans suite ne revient pas avant 2 heures, sauf si la pièce se dégrade nettement.
- « À essayer » garde la même durée au moins une demi-heure.

### Corrections

- Fini les phrases contradictoires comme « Aérez 15 min : l'air pourrait redevenir sain en 5 min ».

### Moteur de conseil 3.13.0

- CO₂ mesuré au-dessus de 1 400 ppm : aération conseillée, même sans preuve.
- Conseil non suivi : pas reproposé avant 2 heures.
- « À essayer » stable une demi-heure ; temps de retour arrondi au quart d'heure.
- Le journal note la pastille et ne double plus ses lignes au rechargement.

## 3.1.0b4 — Une lune pour la nuit

### Nouveautés

- La nuit, une petite lune s'affiche sur l'image du conseil, dans la tuile et la carte complète. Elle dit que les conseils sont en pause jusqu'au réveil. Exemple : « Nuit : conseils en pause jusqu'à 7 h ».
- Le « i » l'explique : pas d'aération proposée avant le réveil ; une fenêtre restée ouverte ou un appareil allumé restent signalés.

### Moteur de conseil 3.12.1 — inchangé

## 3.1.0b3 — Des phrases justes

### Améliorations

- Quand le CO₂ ou les COV dépassent leur seuil mais redescendent seuls, la carte le dit au lieu de « La pièce restera dans votre plage ».
- La pastille ne repasse à « Tout va bien » qu'après une heure de calme : elle ne change plus plusieurs fois par heure.

### Corrections

- L'interrupteur « Je participe » est de nouveau enregistré. Avant, il bougeait à l'écran sans rien garder.
- Au redémarrage de Home Assistant, « VMC conseillée » reprend son état. Avant, la VMC s'arrêtait une minute.

### Moteur de conseil 3.12.1

## 3.1.0b2 — La VMC à sa place

### Nouveautés

- Réglage « Fonctionnement » de la VMC, dans Équipements : « En continu » pour une VMC classique, « À la demande » pour un extracteur.
- Nouvelle entité « Turbo conseillé » dans les pièces qui ont une vitesse rapide : elle s'allume pendant une douche et quand Hestia conseille le turbo.

### Améliorations

- « VMC conseillée » en continu reste toujours allumée ; seul le turbo va et vient.
- « VMC conseillée » à la demande s'arrête au coucher de la pièce. Exemple : 78 % d'humidité à 23 h, l'extracteur ne tourne plus jusqu'au matin.
- Une heure de VMC qui ne fait pas baisser l'humidité d'au moins 1 point met l'extracteur au repos 2 heures.
- Une mesure qui hésite une minute n'arrête plus la VMC : il faut 3 minutes de « non ».

### Corrections

- « VMC conseillée » ne reste plus allumée toute la nuit dans une pièce humide qu'elle n'arrive pas à assécher.

### Après la mise à jour

- VMC classique pilotée par « VMC conseillée » : choisissez « En continu » dans Équipements, sinon elle s'arrêtera la nuit.

### Moteur de conseil 3.12.0 — inchangé

## 3.1.0b1 — Des conseils plus posés

### Nouveautés

- Carte du logement : la grande température peut montrer le dehors ou la moyenne des pièces, au choix.
- Carte complète : un encart « Bon à savoir », replié, rassemble les informations utiles de la pièce.

### Améliorations

- Un conseil affiché reste en place au moins une demi-heure tant qu'il aide encore : il ne change plus toutes les 5 minutes.
- « À essayer » ne clignote plus.
- Une aération se termine avant l'heure du coucher de la pièce, avec 15 minutes de marge pour une nouvelle. Pas de « Ouvrez » sans durée dans l'heure qui précède le coucher.
- Une porte ou une fenêtre qu'on vient d'ouvrir n'affiche pas « Refermez » pendant 3 minutes : le temps de passer. La pluie et le vent fort font toujours refermer tout de suite.
- La nuit, la pastille ne passe plus de « Tout va bien » à « Au mieux » quand une mesure frôle la limite.
- Le réglage « Allergie aux pollens » compte de nouveau : les jours de pollens élevés, les aérations sont courtes et au bon moment.

### Corrections

- Une aération n'est plus dite « sans effet » avant que le capteur ait envoyé une nouvelle mesure.
- L'alarme en mode absence ne fait plus dire « Refermez » : c'est le rôle de l'alarme.
- Le chauffage prévu est annoncé à la bonne minute.

### Moteur de conseil 3.12.0 — en bêta

- Le détail de chaque version du moteur est dans le changelog du moteur.

## 3.0.1 — Correctif : le panneau après « Enregistrer »

### Corrections

- Après « Enregistrer » dans une pièce, l’onglet Apprentissage restait sur « Chargement… », et la pièce affichait « À régler » sans ses mesures, jusqu’au rechargement de la page. Tout revient seul en quelques secondes.

### Moteur de conseil 3.10.0 — inchangé

## 3.0.0 — Un nouveau moteur de conseil, des cartes refaites, un Confort plus léger

### Avant de mettre à jour

- Vous venez de la 1.7.x ? Hestia Confort prend son nom technique `hestia_comfort`. Au premier démarrage, tout passe seul au nouveau nom : pièces, réglages, apprentissages, entités, tableaux de bord et automatisations faites dans l’interface.
- Un encart dans **Hestia-FB → Accueil** suit chaque étape. Si une réparation « quelques lignes à changer à la main » apparaît, elle liste les fichiers YAML à modifier.
- Si HACS affiche « No manifest.json file found », redémarrez Home Assistant puis relancez la mise à jour.
- Mettez à jour Hestia Weather en même temps (3.2.0), si vous l’avez.
- Le nouveau moteur change des valeurs d’entités. Vérifiez les automatisations qui s’en servent :
  - « État » ne donne plus que `calm`, `best`, `benefit`, `action`, `urgent` et `neutral` ;
  - toutes les valeurs de « Raison » changent ;
  - le % d’« Apprentissage » compte maintenant les effets prouvés dans la pièce.
- Les premiers jours, Hestia conseille peu : elle attend d’avoir vu chaque geste marcher chez vous.

### Nouveautés

- Les cartes sont refaites : un bandeau qui dit le geste, sa durée et sa raison, puis « À venir », puis une case par mesure avec sa flèche et sa courbe.
- Dans l’éditeur, on choisit d’abord le type de carte : grandes cartes, cartes à la pièce, petites cartes.
- Nouvelles cartes à la pièce : Température, Humidité, Air, Ouvertures, Chauffage et À venir.
- Le ressenti de la pièce : la chaleur et l’humidité telles qu’on les sent, avec une flèche qui dit où ça va.
- Le panneau Confort est refait : un accueil à lire, une page « Réglages du foyer », vos habitudes en quelques questions.
- Une lumière peut montrer le conseil : un bandeau WLED ou une ampoule couleur, pour tout le logement ou pièce par pièce.
- Une douche dans la pièce : l’humidité qui la suit est reconnue.
- Les volets pilotés par CoverAutomatic ou Cover Extender sont reconnus, comme Adaptive Cover Pro.
- Sur l’accueil, « Participez à l’amélioration du moteur » : un rapport anonyme à télécharger, à partager si vous le voulez.
- Le menu et les réglages communs de Hestia-FB parlent allemand.
- Une intégration trouvée mais pas encore lue se demande en un clic.

### Améliorations

- Confort est beaucoup plus léger : Home Assistant ne se fige plus, même sur une petite box.
- Au démarrage, chaque pièce ne relit que l’historique qu’elle n’a pas encore lu.
- Le panneau s’ouvre plus vite : il ne charge que ce qu’il montre.
- Chaque mesure montre sa tendance : vert quand elle revient vers votre plage, orange quand elle s’en éloigne.
- Le texte suit les mêmes tailles sur toutes les cartes Hestia.
- On glisse du doigt d’une mesure à l’autre ; plus rien ne défile tout seul.

### Corrections

- « Températures sur 24 h » dessine la plage de chaque pièce, et aucune pour une pièce non chauffée.
- La tendance apparaît dès le redémarrage.
- L’humidité s’affiche en nombre entier partout.

### Moteur de conseil 3.10.0 — en bêta

- Pour chaque pièce, il compare les gestes possibles (ouvrir, refermer, VMC, purificateur, volet, chauffage) et garde celui qui aide le plus.
- Il apprend chaque nuit comment chaque pièce réagit, et n’affirme que ce qu’il a déjà vu marcher chez vous.
- Il dit à quel point il est sûr : « Aérez », « devrait », ou « à vérifier ».
- Une aération qui ne fait pas l’effet prévu est dite au bout de 10 minutes, au lieu de conseiller l’inverse.
- Jamais d’ouverture sous la pluie, par grand vent, pendant une vigilance, une absence, le sommeil ou le gel.
- Il suit le thermostat, le poêle et le planning du chauffage (ha-chauffage, Scheduler).
- Vos retours l’aident : « Ce conseil ne va pas » sur la carte, et le rapport de l’accueil.
- Le détail de chaque version du moteur est dans [CHANGELOG-MOTEUR.md](CHANGELOG-MOTEUR.md).

## 2.1.0b8 — Bêta : l'air en liste et l'encart d'information

### Avant de mettre à jour

- Gardez Hestia Weather 3.1.0b2.

### Améliorations

- L'air de la pièce s'affiche en liste : une ligne par mesure et par appareil, rangées par pièce quand deux pièces partagent le même air, celles hors plage d'abord.
- L'humidité d'un air partagé porte le nom de chaque pièce ; le texte ne cite que celles hors plage.
- Glisser du doigt ou de la souris passe à l'onglet suivant ou précédent ; plus rien ne défile tout seul.
- La courbe du chauffage n'apparaît que s'il a chauffé.
- Dans le panneau Hestia, les explications sont rangées dans un encart d'information violet.

## 2.1.0b7 — Bêta : les retours du premier essai

### Avant de mettre à jour

- Gardez Hestia Weather 3.1.0b2.

### Améliorations

- L’humidité de deux pièces au même air défile, pièce par pièce, comme les mesures de l’air.
- La bulle de la pièce suit la mesure affichée : « Cuisine » quand on voit les COV de la cuisine.
- Les mesures qui défilent se font glisser, au doigt comme à la souris.
- « À venir » ne s’affiche que s’il a quelque chose à dire : un geste à comparer, une prévision qui sort de votre plage, un prochain geste, de la pluie.
- Le graphique d’« À venir » prend toute la largeur et dit ce qu’il montre en toutes lettres.
- La courbe du soleil disparaît la nuit ; les courbes du soleil et de la chauffe portent une légende claire.
- Le module Température ne répète plus le mini et le maxi du bandeau.
- Une pièce qui suit le conseil de sa voisine montre le conseil de la pièce qui mène, avec ce qu’elle a appris.

### Corrections

- L’humidité s’affiche en nombre entier partout.
- L’écart à la consigne n’est plus affiché en hors-gel, en éco ou en absence.

## 2.1.0b6 — Bêta : une carte plus claire, chaque chose à sa place

### Avant de mettre à jour

- Gardez Hestia Weather 3.1.0b2.
- Vos cartes gardent leur format. Une carte « Intermédiaire » s’affiche toujours ; l’éditeur propose maintenant la tuile dépliable.

### Nouveautés

- Le bandeau est refait : la pièce et son état, le moment (« Maintenant », « En cours »), le geste avec sa durée, sa raison en une ligne, un rond animé et la température en haut à droite.
- Le « i » s’ouvre sous le titre et explique la pastille : pourquoi « Au mieux », ce qui limite le geste, si les mesures répondent, ce que la pièce a appris et sa dernière aération.
- Un conseil appris dans la pièce porte une fiole sur le rond et « Optimisé par l’apprentissage ».
- « À venir » remplace « Prochaines heures » : le graphique de chaque mesure, le prochain geste et le temps dehors.
- Le module Air fait défiler le CO₂, les COV et les particules, chacun avec sa valeur, sa flèche et sa courbe.
- Ouvertures montre la courbe du soleil dehors ; Chauffage montre sa puissance, sa consigne, l’écart et le temps de chauffe sur 24 h.
- Les cartes « À la carte » existent en version détaillée ou compacte.
- Le panneau WLED parle d’effets visibles sur une LED, règle une vitesse par état, montre un aperçu sur chaque ligne et le tableau des segments, avec l’automatisation qui pilote déjà un segment.

### Améliorations

- Deux grandes cartes : la complète, toute ouverte, et la tuile dépliable. Les détails restent repliés.
- « À savoir » ne garde que « Pour le geste » et « À surveiller ». Le purificateur et la VMC sont dans le module Air.
- Les modules sont plus compacts : quatre sur une ligne en pleine largeur, deux en largeur moyenne, un sur téléphone.
- La Mini tient sur une ligne et l’Alerte devient un bandeau bas.
- La flèche de tendance est dans un rond teinté ; la courbe n’a plus de cadre de plage.
- Dans l’éditeur, les formats se choisissent en vignettes, et « Cartes à la pièce » s’appelle « À la carte ».

### Corrections

- Une bêta installée s’affiche à jour sans vider le cache du navigateur.
- « Mesures » ne compte plus le nombre de mesures : seulement ce qui est à surveiller.

## 2.1.0b5 — Bêta : les cartes rangées comme Hestia Weather

### Avant de mettre à jour

- Gardez Hestia Weather 3.1.0b2.
- Vos cartes gardent leur format : rien à refaire sur vos tableaux de bord.

### Nouveautés

- Dans l’éditeur, on choisit d’abord le type de carte, comme dans Hestia Weather : grandes cartes, cartes à la pièce, petites cartes.
- Nouvelles cartes à la pièce : Température, Humidité, Air, Ouvertures, Chauffage et Prochaines heures.
- La carte complète s’ouvre sur une « Synthèse », puis trois sections repliables : Maintenant, Prochaines heures, Détails.
- « Maintenant » range les mesures en modules : la valeur, sa flèche, sa courbe et quelques chiffres (plage, dehors, mini et maxi…).
- Le bandeau montre « En ce moment » à droite : la température, et son mini et son maxi sur 24 h.

### Améliorations

- La tuile repliée montre le conseil dans une bulle ; un appui la déplie, un appui long ouvre la carte complète.
- « À savoir » prend un cadre en verre, et le halo du bandeau descend derrière sans arête.
- Pour deux pièces au même air, l’humidité montre chaque pièce, et les fenêtres et le soleil ne sont dits qu’une fois.
- Une lumière qui ne sait pas clignoter clignote avec son propre effet ; « Fixe » arrête un effet WLED en cours.

### Corrections

- La tendance apparaît dès le redémarrage : la dernière demi-heure est relue dans l’historique.
- Un capteur qui ne donne des nouvelles que quand sa valeur bouge compte comme stable, et a sa courbe.
- Les petites courbes s’affichaient en pointillés : elles se tracent d’un seul trait.
- Dans Extensions, le bouton « Régler » de WLED mène bien à Réglages généraux.

## 2.1.0b4 — Bêta : la tendance de chaque mesure

**En bref**

- **Chaque mesure montre sa tendance** : une flèche animée et la courbe des 30 dernières minutes.
- **La couleur dit si c’est bon** : vert quand la mesure revient vers votre plage, orange quand elle s’en éloigne, gris sinon.
- **« À savoir » est rangé** : Pour le geste, À surveiller, Appris.

### Avant de mettre à jour

- Gardez Hestia Weather 3.1.0b2.

### Nouveautés

- Température, humidité, CO₂, COV et particules : une flèche qui monte, descend ou reste stable.
- Sous la valeur, une courbe des 30 dernières minutes, avec votre plage en léger fond vert.
- La flèche apparaît après une dizaine de minutes de mesures.

### Améliorations

- « À savoir » range ses lignes en trois rubriques ; une rubrique vide n’apparaît pas.
- Les fenêtres à ouvrir pour le geste sont sur un léger fond orange ; sous « Rien à faire », il n’y en a pas.

### Corrections

- Deux pièces qui partagent le même air disaient chacune « Ouvrez aussi … » : les fenêtres sont maintenant dites en une seule ligne.

## 2.1.0b3 — Bêta : WLED à part, les plages de chaque pièce

**En bref**

- **WLED devient une extension** : on l’active ou non dans Extensions, comme les autres.
- **Les notifications lumineuses ont leur encart** dans Réglages généraux.
- **Chaque pièce montre sa propre plage** dans « Températures sur 24 h ».
- **Le bilan respecte votre minimum** : une chambre réglée à 16 °C n’est plus invitée à chauffer sous 18 °C.

### Avant de mettre à jour

- Gardez Hestia Weather 3.1.0b2.

### Améliorations

- Dans Extensions, WLED a sa carte, son interrupteur et un lien pour l’ajouter à Home Assistant.
- WLED activé : ses bandeaux et leurs segments sont proposés tout seuls dans les notifications lumineuses, avec leurs effets.
- WLED coupé : ses lumières ne sont plus proposées ni commandées, et reviennent comme avant.
- L’onglet Notifications d’une pièce renvoie vers Réglages généraux en mode « Tout le logement ».

### Corrections

- « Températures sur 24 h » dessinait la même plage pour toutes les pièces : chacune a maintenant la sienne, et une pièce non chauffée n’en a pas.
- « Chauffez-la davantage l’hiver » suit le minimum de la pièce quand il est sous 18 °C.

## 2.1.0b2 — Bêta : une lumière qui montre le conseil, et les pollens

**En bref**

- **Une lumière montre le conseil** : un bandeau WLED ou une ampoule couleur prend la couleur du conseil, pour tout le logement ou pièce par pièce.
- **Allergie aux pollens** : les jours de pollens élevés, les aérations restent courtes, tôt le matin ou juste après la pluie.
- **Une douche dans la pièce** : l’humidité qui suit une douche est reconnue et nommée.
- **Deux nouveaux pilotes de volets** : CoverAutomatic et Cover Extender sont lus comme Adaptive Cover Pro.

### Avant de mettre à jour

- Mettez à jour Hestia Weather en même temps (3.1.0b2) : les pollens viennent de lui.

### Nouveautés

- Dans Extensions, l’encart « WLED et lumières couleur » : une lumière pour tout le logement, ou une par pièce.
- Dans chaque pièce, un onglet « Notifications » pour régler sa lumière.
- Pour chaque état, une couleur, un effet et une luminosité, avec un bouton pour essayer tout de suite.
- La lumière ne change que si elle est déjà allumée, sauf si vous permettez de l’allumer pour un geste ou une alerte.
- Jamais la nuit, et seulement si quelqu’un est à la maison : ces deux réglages sont cochés d’office.
- Quand tout va bien, la lumière revient comme avant. Éteinte à la main, elle est laissée tranquille.
- Un bandeau WLED découpé en segments peut montrer une pièce sur chaque segment.
- Dans Réglages généraux, le réglage « Allergie aux pollens ». « À savoir » dit quand les pollens sont élevés.
- Dans La pièce, un cadre « Équipements » : douche ou baignoire.
- Les volets pilotés par CoverAutomatic ou Cover Extender sont reconnus, avec leur reprise à la main et le soleil sur la façade.

### Améliorations

- Une intégration trouvée mais pas encore lue se demande en un clic, avec un formulaire déjà rempli.
- Une aération utile pour l’humidité ou le CO₂ reste toujours conseillée, même les jours de pollens.

## 2.1.0b1 — Bêta : le hub Hestia en allemand

**En bref**

- **Le hub Hestia parle allemand** : le menu, l’accueil et les réglages communs, quand Home Assistant est en allemand.
- Les pages de Hestia Confort restent en anglais pour l’instant pour un germanophone, au lieu du français.

### Avant de mettre à jour

- Vous venez de la 1.7.x ? Le passage au nom Hestia se fait comme avec la 2.0.0b2 : voir ses notes.
- Mettez à jour Hestia Weather en même temps (3.1.0b1), si vous l’avez.

### Nouveautés

- Le menu, l’accueil et les réglages du hub Hestia en allemand.

## 2.0.0b2 — Bêta : le passage au nom Hestia, suivi pas à pas

**En bref**

- **Le passage au nom Hestia se suit dans le hub** : un encart dans Hestia → Accueil montre chaque étape, puis s’en va quand tout est fait.
- **La 2.0.0b1 ne démarrait pas après la mise à jour** : c’est corrigé.

### Avant de mettre à jour

- Mettez à jour Hestia Weather en même temps (3.0.0b2), si vous l’avez.
- Avec Hestia Confort 1.7.28 installée avant, tout démarre seul au redémarrage.
- Sinon, après le redémarrage : **Paramètres → Ajouter une intégration → Hestia Confort**. Votre installation est reprise, rien n’est créé en double.
- Si HACS affiche « No manifest.json file found », redémarrez Home Assistant puis relancez la mise à jour.

### Nouveautés

- L’encart « Passage au nom Hestia » dit ce qui a été repris : pièces, apprentissages, entités, tableaux de bord et automatisations.
- Il liste les lignes à changer à la main, s’il y en a.
- Il propose de redémarrer Home Assistant quand il le faut, en un bouton.
- Un clic sur « J’ai compris » le ferme pour de bon.

### Corrections

- « Ajouter une intégration » reprend maintenant l’installation existante au lieu d’en créer une nouvelle.
- Hestia Confort démarre Hestia Weather quand il le faut, et l’inverse : un seul geste suffit pour les deux.

## 2.0.0b1 — Bêta : le nom technique devient hestia_comfort

**En bref**

- **Hestia Confort prend son nom technique Hestia : `hestia_comfort`.** Au premier démarrage, votre installation passe seule au nouveau nom.
- **Rien n’est perdu** : vos pièces, réglages, apprentissages, historiques et statistiques restent, comme le nom, la pièce et l’icône de vos entités.

### Avant de mettre à jour

- Mettez à jour Hestia Weather en même temps (3.0.0b1), si vous l’avez : la liaison entre les deux suit d’elle-même.
- Après le redémarrage, une réparation peut demander un second redémarrage : faites-le.
- Si une réparation « quelques lignes à changer à la main » apparaît, elle liste les fichiers YAML et les lignes où remplacer l’ancien nom.

### Améliorations

- Les automatisations, scripts, scènes et tableaux de bord faits dans l’interface sont mis à jour tout seuls.
- Les cartes deviennent `custom:hestia-comfort-card`, `custom:hestia-comfort-home-card` et `custom:hestia-comfort-review-card`.
- L’ancienne adresse du panneau mène toujours à `/hestia/confort`.

## 1.7.27 — Préversion : correctif d’affichage sur petit écran

### Corrections

- Sur un téléphone étroit (320 px), une ligne « À régler » avec un raccourci n’était plus lisible : le raccourci passe maintenant sous le texte.

## 1.7.26 — Préversion : Hestia Confort en anglais, un panneau plus clair et plus léger

**En bref**

- **Hestia Confort parle anglais** : carte, panneau et bilan s’affichent en anglais quand Home Assistant n’est pas en français.
- **Le panneau Hestia est rangé comme celui de Hestia Weather** : Accueil, Réglages généraux, Extensions, puis les réglages de chaque pièce.
- **Moins de charge pour Home Assistant** : l’historique est lu par petits morceaux et les cartes se redessinent moins souvent.

### Nouveautés

- Une page « Extensions » à part dans le menu, rangée par thème : chauffage, volets, présence.
- Le panneau est maintenant à l’adresse `/hestia` ; l’ancienne adresse mène toujours au bon endroit.

### Améliorations

- L’historique de 10 jours est lu pièce par pièce et jour par jour, sans tout garder en mémoire.
- L’apprentissage reprend là où il en était après un redémarrage.
- Les cartes ne se redessinent plus à chaque changement sans rapport dans la maison.
- Les diagnostics ne contiennent plus les noms ni les zones des personnes.

### Corrections

- Un retour sur un conseil enregistré juste avant un rechargement n’est plus perdu.
- Le bilan dit de chercher « comfort » dans les journaux.

### À savoir

- Home Assistant 2026.7 ou plus récent est demandé (2026.10 jusqu’ici) : Hestia Confort est maintenant testé sur ces deux versions.

## 1.7.25 — Mon logement devient un petit bilan

**En bref**

- **La carte « Mon logement » devient un petit bilan** : les conseils des pièces défilent en haut, puis la journée, la semaine ou le mois.
- **Fenêtre ouverte comme conseillé, la carte passe en bleu**, et repasse en orange quand il faut refermer.
- **Les COV ne font plus ouvrir et fermer à la suite.**

### Nouveautés

- Carte « Mon logement » : onglets Jour, Semaine et Mois.
- Les 4 thèmes du bilan sur la période choisie : Confort, Chaleur, Humidité et Air, chacun avec sa lettre.
- Une ligne par pièce : la température du moment ou la moyenne, le mini et le maxi, votre plage en vert.
- Une partie « Plus de détails » à déplier : la courbe dedans et dehors, les pièces, les détails.
- Dans l'éditeur de la carte : les sections à afficher, celles à ranger dans « Plus de détails », et la période au départ.

### Améliorations

- COV : après une aération, une pause avant de redemander d'ouvrir.
- COV : quand ils redescendent seuls, fenêtres fermées, rien n'est demandé.
- COV : les heures où ouvrir les fait monter sont apprises.
- COV : « Refermez » quand l'air du dehors en apporte, au début d'une aération.

### Corrections

- Fenêtre ouverte comme conseillé : « Au mieux » en bleu au lieu de « Geste conseillé » en orange, sur la carte de la pièce, la carte « Mon logement » et les entités.

## 1.7.24 — Le nouveau nom, Hestia Confort

**En bref**

- **Le projet prend le nom Hestia Confort.** Le nom change partout : cartes, panneau, textes et documentation.
- **Rien à refaire de votre côté.** Mêmes pièces, mêmes réglages, mêmes entités, mêmes cartes.

### Améliorations

- Nouveau logo du hub : un H à la place du N.
- La liaison s’appelle maintenant « Hestia Weather », et le panneau commun « Hestia ».
- Dans HACS, l’intégration s’appelle « Hestia Comfort ».
- Les noms internes (`hestia_comfort`, `hestia-comfort-card`) ne changent pas, pour ne rien casser chez vous.

## 1.7.23 — Journal de Home Assistant allégé

**En bref**

- **Plus d’avertissements de thread** : les entités « Mon logement » ne remplissent plus le journal toutes les 30 secondes (issue #37).

### Corrections

- Le minuteur de 30 s des entités « Mon logement » et l’écoute des changements de pièces et d’étages exécutaient leur code hors de la boucle d’événements de Home Assistant, ce qui provoquait des avertissements répétés. Ils s’exécutent maintenant dans la boucle.

## 1.7.22 — Créer une pièce depuis les Réglages généraux

**En bref**

- **Création de pièce corrigée** : depuis les Réglages généraux, « Créer » ou le choix d’une pièce Home Assistant ouvre bien la configuration de la nouvelle pièce.

### Corrections

- Dans les Réglages généraux, « Créer » (pièce libre) ou le choix d'une pièce Home Assistant ne faisait que changer l'adresse : l'écran restait sur les réglages. La configuration de la nouvelle pièce s'ouvre maintenant.

## 1.7.21 — Une seule liaison avec Hestia Weather

**En bref**

- **Liaison avec Hestia Weather** : elle se coupe ou se rétablit depuis Confort comme depuis Hestia Weather, et les deux disent toujours la même chose.

### Améliorations

- Dans Hestia Weather 2.9.0, Réglages → Extensions → Hestia Confort : un interrupteur relie le lieu à Confort. Allumé, Confort reprend les mesures de ce lieu. Éteint, Confort garde ces capteurs comme les siens, sans l’air de Hestia Weather.
- Choisir « Vos propres capteurs » dans les Réglages généraux de Confort coupe aussi la liaison côté Hestia Weather.

## 1.7.20 — Un indicateur de chauffe pour les thermostats muets

**En bref**

- **Indicateur de chauffe** : un thermostat qui ne dit pas s’il chauffe peut s’appuyer sur sa vanne, son relais ou son état de marche (demande de hellmer1234, issue #12).

### Nouveautés

- **Indicateur de chauffe**, dans l’onglet Chauffage d’une pièce, sous le thermostat. Facultatif. Un capteur oui/non, un `input_boolean` ou un capteur qui dit `heating`, `open`, `on` ou `idle`, `close`, `off`.
- « Chauffage observé » porte un attribut **source** : `indicateur`, `hvac_action` ou `mode`.

### Améliorations

- L’apprentissage du chauffage suit l’indicateur : une pièce dont le thermostat ne dit pas s’il chauffe peut enfin atteindre « Optimal ».
- Le guide explique comment « Chauffage observé » est calculé.

### Corrections

- Le graphique en anneau « Air » du Bilan du logement s’affiche en entier : il sortait de son cadre pendant son animation.
- Pour des pièces au même air, le graphique « Prochaines heures » suit le conseil commun : la carte montrait celui de l’autre pièce.

## 1.7.19 — Le graphique « Prochaines heures » enfin visible, un hub plus fluide

**En bref**

- **Le graphique « Prochaines heures » s’affiche** quand une aération est conseillée : il ne se montrait presque jamais.
- **Plus de « Chargement… » sans fin** après avoir enregistré une pièce.

### Améliorations

- **Pièce chauffée** : un interrupteur en tête de l’onglet Chauffage. Éteint, il masque le thermostat et ses réglages.
- **Aperçu de la carte** après l’enregistrement d’une pièce, sans recharger la page.

### Corrections

- Le graphique « Prochaines heures » ne voyait pas une aération conseillée « maintenant » : il se repliait au lieu de s’ouvrir.
- « Retour à Mon logement » après un enregistrement restait bloqué sur « Chargement… ».
- Plus de page fugace en cliquant sur « Modifier » depuis les Réglages généraux.
- L’anneau tournant « Au mieux » est bien centré sur sa piste.

## 1.7.18 — Le bilan du logement, des entités qui disent ce que dit la carte, un hub refait

Tout ce qui est nouveau depuis la 1.6.0.

**En bref**

- **Le bilan du logement** : une note de confort de A à E pour le logement et pour chaque pièce, sur douze mois, selon la norme européenne EN 16798-1.
- **Des entités qui disent ce que dit la carte** : même conseil, même pastille, même couleur, prêtes pour vos automatisations (VMC, LED, fenêtres).
- **Un hub refait** : un accueil Confort à lire, et des Réglages généraux complets, avec vos pièces et les extensions.
- **Des conseils plus justes** : le graphique « Prochaines heures », pas d’aération la nuit ni quand attendre suffit, un « À savoir » qui ne se contredit plus.

### Nouveautés

- **Bilan du logement**, dans le menu de gauche du hub, sous « Accueil » : la note du logement, la chaleur, l’humidité et l’air en graphiques, puis la fiche de chaque pièce (mois par mois, journée type l’hiver et l’été).
- **Conseils du bilan** : chauffer une pièce restée trop froide, faire tourner la VMC ou aérer une pièce trop humide, ouvrir la nuit après un été chaud. Rien quand tout va bien.
- **Carte « Hestia Confort · bilan »** : en résumé ou complète, pour toute la famille.
- **Nouvelles entités** pour chaque pièce :
  - **Conseil** : le titre de la carte (« Rien à faire », « Aérez 10 min », « Lancez la VMC »…).
  - **État** : la pastille de la carte (Tout va bien, Au mieux, Geste conseillé…).
  - **Couleur** : la couleur de la carte, prête pour une lumière.
  - **Oui/non** : Geste à faire, Aération conseillée, Fenêtres à refermer, VMC conseillée, Trop humide.
  - **Humidité** et **Apprentissage**.
- **Mon logement** : le geste le plus important, sa couleur, et le nombre de pièces qui demandent un geste.
- **Un seul appareil « Salon · Cuisine »** pour les pièces au même air, avec leur conseil commun.
- **Extensions dans les Réglages généraux** : Hestia Weather, Versatile Thermostat, Adaptive Cover Pro et Alarmo, chacune avec son utilité et un interrupteur pour l’activer ou la couper.
- **Versions et liens** sur l’accueil, comme dans Hestia Weather, avec un bouton « Soutenez mon travail ».
- **Graphique « Prochaines heures »** sous l’échelle : la pièce sans le geste conseillé et avec, pour voir ce qu’il change.
- **Les bonnes fenêtres à ouvrir** dans « À savoir », selon le vent, les façades et la taille des ouvrants. Une fenêtre où la pluie entrerait est écartée.
- **« Ouvrez pour réchauffer »** quand il fait nettement plus doux dehors qu’une pièce fraîche.
- **« Chauffez un peu plus »** quand des murs plus chauds suffisent à écarter la moisissure.
- **« Rallumez le chauffage »** pour une pièce nettement froide, chauffage coupé.

### Améliorations

- **Un accueil Confort à lire** : tout ce qui se modifie est dans Réglages généraux. Une pièce s’ouvre sur son bilan.
- **Une extension coupée** n’est plus lue dans aucune pièce, et les réglages des pièces le disent. Pour Alarmo, plus de liste à choisir : il est trouvé tout seul.
- **VMC conseillée** reste allumée tant que la VMC assèche une pièce encore humide : une automatisation ne la coupe pas trop tôt.
- **Le menu du hub** : le logo Hestia en tête, et « Vue d’ensemble » devient « Accueil ».
- **Pas d’« Aérez » en pleine nuit** : la carte attend le réveil et dit à partir de quelle heure aérer.
- **Aérer seulement si c’est mieux qu’attendre**, avec une durée d’aération apprise pièce par pièce.
- **Nouvelle pastille « Au mieux »**, en bleu, quand rien ne peut améliorer une mesure.
- **« À savoir » par ordre d’importance**, une seule ligne pour l’humidité.
- **Une icône dans chaque pastille** et un anneau animé différent selon l’état.
- **Le soleil montré tel qu’il est**, et seulement s’il arrive dans les 3 heures.
- **COV plus calmes** : la carte juge la moyenne des 10 dernières minutes.
- **L’éditeur de la carte suit ses quatre sections** : Bandeau conseil, À savoir, Mesures, Détails techniques.
- Le guide donne des exemples de LED aux couleurs de la carte et de VMC qui suit le conseil.

### Corrections

- **Salon · Cuisine** : l’encart Salon montrait deux appareils, il n’en reste qu’un. Les mesures du Salon y gardent leur nom d’entité et leur historique.
- **Le degré d’humidité** reste dit sous « Lancez la VMC » ou « Aérez » : « Très humide », et non plus seulement « Humidité ».
- **Les pièces au même air** disent la même chose, avec la ligne de la plus humide.
- **Plus de phrases opposées** dans « À savoir », ni de doublon VMC ou humidité.
- **L’interrupteur « Échelle de température »** se coupe enfin.
- **Plus de page fugace** en passant d’une page du menu à une autre.

### Après la mise à jour

- Redémarrez Home Assistant, puis rechargez la page (ou videz le cache de l’application mobile). Vos cartes gardent leurs réglages.
- **Situation** et **Geste** sont retirées : dans vos automatisations, remplacez-les par **État** et **Conseil** (ou les oui/non).
- Salon et Cuisine n’ont plus leur propre Conseil : il est sur l’appareil « Salon · Cuisine ».

## 1.7.17 — Un seul appareil pour Salon · Cuisine

**En bref**

- Dans Home Assistant, la pièce où vous avez coché « Même air » ne montre plus qu’un appareil : « Salon · Cuisine ».

### Corrections

- **Salon · Cuisine** : l’encart Salon montrait deux appareils, « Salon » et « Salon · Cuisine ». Il n’en reste qu’un, « Salon · Cuisine ».
- Les mesures propres au Salon y passent sous les noms « Humidité · Salon », « Apprentissage · Salon »… Elles gardent leur nom d’entité et leur historique.
- La Cuisine garde son propre appareil.

## 1.7.16 — Des entités qui disent ce que dit la carte

**En bref**

- Les entités disent maintenant exactement ce que dit la carte : même conseil, même pastille, même couleur.
- « Salon · Cuisine » a son propre appareil dans Home Assistant.
- De nouvelles entités pour vos automatisations : VMC, LED de notification, fenêtres.

### Nouveautés

- **Conseil** : le titre de la carte (« Rien à faire », « Aérez 10 min », « Lancez la VMC »…).
- **État** : la pastille de la carte (Tout va bien, Au mieux, Geste conseillé…).
- **Couleur** : la couleur de la carte, prête pour une lumière (`hs_color` en attribut).
- **Oui/non** : Geste à faire, Aération conseillée, Fenêtres à refermer, VMC conseillée, Trop humide.
- **Humidité** et **Apprentissage** pour chaque pièce.
- **Pièces au même air** : un appareil « Salon · Cuisine » porte leur conseil commun.
- **Mon logement** : le geste le plus important, sa couleur, et le nombre de pièces qui demandent un geste.

### Améliorations

- **VMC conseillée** reste allumée tant que la VMC assèche une pièce encore humide : une automatisation ne la coupe pas trop tôt.
- **Raison** passe en diagnostic, masquée par défaut.
- Guide : exemples pour des LED aux couleurs de la carte et une VMC qui suit le conseil.

### Après la mise à jour

- **Situation** et **Geste** sont retirées : remplacez-les par **État** et **Conseil** (ou les oui/non) dans vos automatisations.
- Salon et Cuisine n’ont plus leur propre Conseil : il est sur l’appareil « Salon · Cuisine ».

## 1.7.15 — Le bon degré d’humidité sous un conseil

**En bref**

- Sous « Lancez la VMC » ou « Aérez », « À savoir » dit maintenant à quel point la pièce est humide.

### Corrections

- **Degré d’humidité** : une chambre à 78 % sous « Lancez la VMC » affichait seulement « Humidité ». Elle affiche « Très humide », comme sous sa mesure, et le conseil ne change pas.

## 1.7.14 — Un accueil à lire, des réglages complets

**En bref**

- L’accueil Confort se lit seulement : tout ce qui se modifie est dans **Réglages généraux**.
- Les réglages ont une rubrique **Extensions** : Hestia Weather, puis Versatile Thermostat, Adaptive Cover Pro et Alarmo, chacune avec son utilité.

### Nouveautés

- **Extensions tierces** : chacune dit si elle est liée, à lier (un bouton « Lier ») ou pas installée (un lien « Installer avec HACS » et ce que Confort fait sans elle).
- **Extensions pas encore lues** : celles trouvées dans Home Assistant que Confort ne lit pas encore (Better Thermostat, SmartIR, Scheduler) ; « Demander » ouvre une demande toute prête sur GitHub.
- **Versions et liens** sur l’accueil, comme dans Hestia Weather : versions (dont le socle commun), liaisons, liens utiles et un bouton « Soutenez mon travail ».
- **Logo Hestia** en tête du menu de gauche (et de la barre du haut sur téléphone), lisible sur fond clair comme sur fond foncé.

### Améliorations

- **Accueil plus simple** : plus de boutons « Modifier » ni « Ajouter une pièce », plus de courbe 24 h. Une pièce s’ouvre sur son bilan, et un bouton mène aux réglages.
- **Hestia Weather recommandé** : le choix dit pourquoi les conseils sont meilleurs avec lui, et ce qu’on perd avec ses propres capteurs. Ses mesures reprises sont repliées.
- **Alarme** : réglée dans l’encart Alarmo.

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile) pour voir le nouvel accueil.

## 1.7.13 — Le bilan dans le menu

**En bref**

- « Bilan du logement » est dans le menu de gauche, sous l’accueil de Confort.
- Le bilan s’anime à l’ouverture.

### Améliorations

- **Menu de gauche** : « Vue d’ensemble » s’appelle désormais « Accueil », pour Confort comme pour Weather. Le bouton « Bilan du logement » quitte le haut de l’accueil pour le menu.
- **Bilan animé** : les barres montent, les courbes se tracent, la note et les panneaux apparaissent en douceur. Rien ne bouge si votre appareil demande de réduire les animations.

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile) pour voir le nouveau menu.

## 1.7.12 — Un « À savoir » qui ne se contredit plus

**En bref**

- « À savoir » ne dit plus deux choses opposées : plus de « vous pouvez refermer » à côté de « vous pouvez laisser ouvert ».
- Quand il fait nettement plus doux dehors, une pièce fraîche reçoit « Ouvrez pour réchauffer ».

### Nouveautés

- **« Ouvrez pour réchauffer »** : une pièce sous votre plage, avec un air nettement plus doux dehors, de jour et quelqu’un à la maison. Fenêtre déjà ouverte : « Laissez ouvert · L’air du dehors, plus doux, réchauffe la pièce ».

### Améliorations

- **Une pièce fraîche et humide peut être aérée** quand l’air du dehors est plus doux : l’aération la réchauffe et l’assèche à la fois.
- **Les pièces qui partagent le même air** (Salon · Cuisine) jugent l’effet de la fenêtre sur leur température commune : elles disent la même chose.
- **Une vérification de toutes les situations** : plus de 30 000 cartes produites par le vrai moteur sont relues à chaque changement, à la recherche de phrases qui se contredisent.

### Corrections

- **« Aérer refroidirait une pièce déjà fraîche »** ne s’affiche plus quand il fait plus doux dehors.
- **« Ouverte ou fermée, cela ne change rien »** ne s’affiche plus quand la fenêtre ouverte réchauffe la pièce.
- **« Aérez » pour le CO₂** n’est plus suivi de « aérer refroidirait » sur la ligne d’humidité.
- **La ligne d’humidité** ne répète plus deux fois la même raison.

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile) pour voir la nouvelle carte.

## 1.7.11 — Le bilan du logement

**En bref**

- Une note de confort pour le logement et pour chaque pièce, de A à E, sur les douze derniers mois.
- Elle suit la norme européenne EN 16798-1 : chaleur, humidité et air.
- Des conseils seulement pour un problème qui dure, et une carte pour toute la famille.

### Nouveautés

- **Bilan du logement dans le hub** : un bouton sur l’accueil Confort ouvre la note du logement, un graphique par thème (chaleur, humidité, air) et la liste des pièces.
- **La fiche de chaque pièce** : sa note, sa température mois par mois face à la zone de confort, une journée type l’hiver et l’été, son humidité et son CO₂ heure par heure.
- **Des conseils mesurés** : chauffer une pièce restée sous 18 °C, faire tourner la VMC ou aérer une pièce au-dessus de 70 % d’humidité, ouvrir la nuit après un été chaud. Rien quand tout va bien.
- **Carte « Hestia Confort · bilan »** : en résumé (la note, les thèmes et le conseil le plus important) ou complète. Un appui ouvre le bilan entier, pour toute la famille.

### À savoir

- Il faut deux semaines de mesures pour noter un thème. Une pièce sans capteur de CO₂ n’est pas notée sur l’air, une pièce non chauffée pas sur la chaleur.
- L’énergie viendra plus tard.

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile) pour voir la nouvelle carte.

## 1.7.10 — Aérer quand ça sert vraiment

**En bref**

- Plus de « Aérez » en pleine nuit : la carte attend le réveil.
- La carte compare l’aération avec « ne rien faire » : elle ne la demande que si elle fait nettement mieux qu’attendre.
- La durée d’aération est apprise pièce par pièce, au lieu d’une heure presque à chaque fois.

### Nouveautés

- **« La nuit, aérez plutôt au réveil »** : en dehors des heures de la saison (8 h – 21 h au printemps et en automne), une pièce humide ne demande plus d’ouvrir. « À savoir » indique l’heure à partir de laquelle aérer si l’humidité reste haute.
- **« Elle sèche d’elle-même »** : chaque pièce apprend à quelle vitesse elle perd seule l’humidité d’une douche ou de la nuit, fenêtres fermées. Si elle fait seule la moitié du travail, la carte ne demande pas d’ouvrir.

### Améliorations

- **Une durée d’aération plus juste** : l’aération s’arrête dès que la pièce revient dans sa plage, ou quand cinq minutes de plus n’apporteraient presque plus rien.
- **Un apprentissage qui ne se laisse plus tromper** : seule la première heure de chaque ouverture compte. Une fenêtre oubliée toute une journée ne fait plus croire que la pièce sèche mal.
- **Un conseil qui n’hésite plus** : un « Aérez » déjà donné n’est plus retiré puis redonné pour un dixième de point.

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile) pour voir la nouvelle carte.

## 1.7.9 — Chaque état a son allure

**En bref**

- Chaque pastille porte une icône, et le bandeau s’anime différemment selon l’état : on reconnaît l’état d’un coup d’œil.

### Améliorations

- **Une icône dans chaque pastille** : ✓ Tout va bien, demi-cercle Au mieux, étincelle À saisir, main Geste conseillé, triangle Attention, point d’interrogation À vérifier, fiole Conseil optimisé.
- **L’anneau autour du rond, un par état** : il respire quand tout va bien, tourne en demi-anneau pour « Au mieux », passe en comète pour « À saisir », envoie des ondes pour un geste, bat deux fois pour une alerte, en pointillés pour « À vérifier ». Plus épais et plus visible qu’avant.
- **La lumière du bandeau** : plus diffuse, calée sur le bord droit, et animée au rythme de l’anneau.

### Corrections

- **« Mon logement », tuile Salon · Cuisine** : elle reprend les mesures des deux pièces, l’humidité de la plus humide d’abord, comme « À savoir ».

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile) pour voir la nouvelle carte.

## 1.7.8 — Des murs humides, jamais une fatalité

**En bref**

- Risque de moisissure : la carte dit ce qui s’en occupe, ou ce que vous pouvez faire.
- Nouveau geste « Chauffez un peu plus » quand des murs plus chauds suffisent à écarter la moisissure.

### Nouveautés

- **« Chauffez un peu plus »** : quand aérer et la VMC n’aident pas, un ou deux degrés de plus réchauffent les murs froids et font passer l’air qui les touche sous le seuil de la moisissure. Le chauffage n’assèche pas, il garde les murs assez chauds. Demandé seulement pour un risque net, en journée, jamais contre un thermostat en éco ou hors-gel, ni quand la VMC tourne.

### Améliorations

- **Plus de « Murs à surveiller »** : la VMC en marche donne « Au mieux » et « risque de moisissure, la VMC l’assèche » ; sans rien à faire, la ligne donne un conseil (ne pas sécher de linge dans la pièce, écarter les meubles du mur).
- **« Mon logement »** : « Au mieux » en bleu au lieu de « 5 à surveiller » à côté de « Rien à faire ».
- **Le disque** montre le sujet de la première ligne d’« À savoir ».
- **Tuiles des pièces** : un froid déjà pris en charge passe après les autres mesures.

### Corrections

- **Salon · Cuisine** : la ligne d’humidité reprend aussi la raison donnée par l’autre pièce.
- **Plus de doublon VMC** : « VMC · en marche » ne répète plus l’humidité.

## 1.7.7 — Une seule ligne pour l’humidité

**En bref**

- « À savoir » ne parle plus deux fois de l’humidité : une seule ligne dit l’état et pourquoi aérer n’aide pas.

### Corrections

- **Plus de doublon dans « À savoir »** : « Air humide » puis « Humidité · aérer refroidirait… » deviennent « Air humide · aérer refroidirait une pièce déjà fraîche ». De même « Air humide · depuis plusieurs heures, aérer ne gagnerait presque rien », et « Humidité élevée · risque de moisissure, depuis plusieurs heures ».
- **Salon · Cuisine** : la ligne est celle de la pièce la plus humide, avec sa raison.

## 1.7.6 — « Au mieux » et un « À savoir » par ordre d’importance

**En bref**

- Quand une mesure sort de votre plage sans que rien ne puisse l’améliorer, la pastille dit « Au mieux », en bleu, au lieu de nommer le problème.
- « À savoir » commence par ce qui compte le plus, et le met en évidence.

### Améliorations

- **Nouvelle pastille « Au mieux »** : « Rien à faire » ne s’affiche plus à côté de « Air humide » ou « Légèrement humide ». L’humidité est dite dans « À savoir » (« Air humide · au-dessus de votre plage »), avec la raison juste en dessous. « Tout va bien » reste pour une pièce entièrement dans sa plage.
- **« À savoir » par ordre d’importance** : où ouvrir, puis un risque (moisissure, en jaune), puis ce qui sort de votre plage, puis pourquoi rien de mieux n’est possible, les appareils en marche, et enfin la dernière aération. La première ligne est mise en avant.
- **Un froid déjà pris en charge passe après** un problème laissé seul (ici l’humidité).
- **« Murs à surveiller » reste dans la pastille** : c’est un risque pour le logement.

### Corrections

- **Salon · Cuisine** : une seule ligne d’humidité, celle de la pièce la plus humide, nommée (« Air humide · Cuisine »), comme sa tuile.

## 1.7.5 — Une pièce fraîche dit vrai

**En bref**

- Quand le chauffage s’occupe d’une pièce un peu fraîche, la carte dit « Rien à faire » sans laisser croire à un problème.
- Quand personne ne la réchauffe, elle demande de rallumer le chauffage.

### Améliorations

- **Plus de « Un peu frais » à côté de « Rien à faire »** : la pastille dit « Tout va bien », ou nomme l’autre problème de la pièce (« Murs à surveiller », « Trop humide »). Le froid passe dans « À savoir » : « Un peu frais · le chauffage s’en charge ».
- **« Rallumez le chauffage » aussi sans détecteur de présence** : une pièce nettement froide depuis 30 min, chauffage coupé à la main, le demande même quand Hestia ne sait pas si quelqu’un est là.
- **Carte « Mon logement »** : une pièce juste un peu fraîche n’est plus comptée « à surveiller ».

### Corrections

- **« un peu sous votre plage » seulement quand c’est un peu** : une pièce nettement froide dit « sous votre plage ».
- **Pièce chauffée sans chauffage relié** : elle garde « Trop frais » quand elle est nettement sous sa plage, jamais « Tout va bien ».

## 1.7.4 — Le soleil montré tel qu’il est

**En bref**

- Le graphique du soleil compare la pièce sans soleil et avec le soleil : l’écart est ce qu’il apporte.
- Le graphique montre où est « maintenant ».

### Améliorations

- **Deux courbes pour le soleil** : « sans soleil » en pointillés, « avec le soleil » en couleur, et la phrase « +1,4 °C grâce au soleil vers 17 h ».
- **Un soleil qui n’apporte presque rien n’est plus dessiné** (moins de 0,3 °C), même en mode « Toujours » : la pièce qui se réchauffe parce que la journée est douce n’est plus attribuée au soleil.
- **« maintenant » sous le premier point** de la courbe : elle se lit comme ce qui arrive, pas comme le passé. Les heures du lendemain disent « demain ».

### Corrections

- **Le soir, plus de « le soleil va réchauffer la pièce ».** Le soleil n’est un conseil que s’il arrive dans les 3 heures. Sinon il ne s’affiche qu’en mode « Toujours », titré « soleil demain 8 h », sans « inutile de chauffer ».

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile) : une ancienne carte en cache affiche deux onglets « Température », dont un vide.

## 1.7.3 — Le graphique suit le conseil, les bonnes fenêtres à ouvrir

**En bref**

- Le graphique « Prochaines heures » n’apparaît plus que s’il montre ce que le conseil change.
- Nouveau réglage pour le garder toujours visible.
- « À savoir » dit quelles fenêtres ouvrir pour que l’air traverse.

### Nouveautés

- **Les bonnes fenêtres à ouvrir.** Quand il faut aérer, « À savoir » nomme les ouvrants : « Ouvrez Fenêtre Ouest et Fenêtre Cuisine · l’air traverse de part en part ».
  - Choix selon le vent, les façades opposées et la taille des ouvrants.
  - Une fenêtre où la pluie entrerait, face aux rafales ou au soleil en été est écartée : « Pas Fenêtre Ouest · la pluie y entrerait ».
  - Déjà ouvert ? La carte complète : « Ouvrez aussi Fenêtre Ouest ».
- **Appris chez vous.** Chaque aération mesure à quelle vitesse le CO₂ baisse, pour chaque combinaison de fenêtres. Après 3 aérations, la carte préfère ce qu’elle a mesuré : « 2 fois plus rapide (d’après 4 aérations) ».
- Le bandeau ne change pas.

### Améliorations

- **Un graphique seulement quand il aide.** Un « Aérez » pour le CO₂ n’affiche plus une courbe de température où rien ne bouge (« −0 °C »).
  - Il apparaît quand le geste change vraiment la pièce : au moins 0,4 °C, ou 3 points d’humidité.
  - Une fois affiché, il reste tant que le conseil ne change pas, jusqu’à 0,2 °C : il ne clignote plus.
  - Le graphique du soleil ne sort que si le conseil parle de chauffage.
- **La carte change de taille en douceur.** Le graphique s’ouvre et se replie en 0,3 s, sans saut.
- **Nouveau réglage « Quand l’afficher »** (Section 1 · Bandeau conseil) :
  - « Seulement quand il aide le conseil » (par défaut) ;
  - « Toujours » : sans geste à montrer, la carte garde sa taille et montre la température prévue sans rien faire (ou la montée due au soleil).

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile).

## 1.7.2 — Des COV plus calmes, l’interrupteur de l’échelle répond

### Améliorations

- **COV : un conseil qui ne va plus et vient.** L’indice des COV bouge beaucoup (cuisine, produit ménager, bougie, quelqu’un qui entre). Confort ne le compare plus mesure par mesure au seuil :
  - il juge la **moyenne des 10 dernières minutes** ;
  - il conseille d’aérer quand elle reste au-dessus du seuil **pendant 10 minutes**, tout de suite si l’indice atteint **le double du seuil** ;
  - le conseil cesse quand la moyenne repasse sous **le seuil moins 20 %** (120 pour un seuil de 150), comme pour le CO₂ ;
  - après une aération, il attend **45 minutes** avant de redemander, sauf si l’indice remonte nettement : si la source est encore là, rouvrir ne sert à rien.
- Le texte dit ce qui se passe : « COV au-dessus de l’habituel depuis 12 min » (ou « au-dessus du seuil » pour un capteur avec unité). La tuile COV affiche « depuis 12 min ».
- **Réglages** (panneau Hestia, pièce, onglet Air intérieur, capteur COV) : le délai et la pause sont modifiables.

### Corrections

- **Section 1 · Bandeau conseil : l’interrupteur « Échelle de température » se coupe enfin.** Le formulaire de Home Assistant renvoyait aussi l’ancienne liste des repères, qui rallumait l’échelle aussitôt.
- Format Mesures : le même interrupteur affiche ou retire l’échelle.

### Après la mise à jour

- Rechargez la page (ou videz le cache de l’application mobile).

## 1.7.1 — Un graphique plus lisible, un bandeau plus simple à régler

**En bref**

- **Le graphique « Prochaines heures » est plus lisible** : une courbe lissée, une échelle qui ne grossit plus quelques dixièmes, la plage de confort en simples lignes pointillées, les valeurs de départ et d’arrivée au bout de la courbe.
- **La courbe prévue se voit** quand il n’y a pas de geste (le soleil) : en couleur, avec un léger fond dessous. « Le soleil va réchauffer la pièce » quand la pièce est déjà dans sa plage, « inutile de chauffer » seulement quand elle est fraîche.
- **Section 1 · Bandeau conseil plus simple** : le conseil est la base de la carte et ne se coupe plus. Il reste trois interrupteurs : faire défiler les conseils, l’échelle de température, le graphique « Prochaines heures ».

### Après la mise à jour

- Redémarrez Home Assistant, puis rechargez la page. Une carte qui avait retiré des repères de l’échelle garde son réglage tant qu’on ne touche pas à l’interrupteur.

## 1.7.0 — Le graphique « Prochaines heures », une carte réglable section par section

**En bref**

- **Le graphique « Prochaines heures »**, sous l’échelle de température : la pièce sans le geste conseillé (pointillé gris) et avec (en couleur), et une frise qui dit quand. Il change de sujet avec le conseil : rafraîchir la nuit en été (« demain 16 h : 25,5 °C au lieu de 28,6 »), aérer sans perdre la chaleur en hiver (« −0,8 °C, revenu vers 17 h »), laisser le soleil réchauffer (« inutile de chauffer »), assécher (« 57 % au lieu de 65 % »). Deux onglets, Température et Humidité, quand les deux ont quelque chose à montrer.
- **L’éditeur de la carte suit ses quatre sections**, numérotées dans le même ordre que l’affichage : 1 Bandeau conseil, 2 À savoir, 3 Mesures, 4 Détails techniques, puis Apparence et Appui long.
- **À savoir et Détails techniques se règlent** : afficher ou non, les sujets ou les lignes gardés, le nombre de lignes d’À savoir.
- La tuile garde son principe (le bandeau conseil, puis une partie qui se déplie) et peut afficher le graphique une fois dépliée.

### Améliorations

- « Remèdes en cours » devient « Équipements en marche » ; « Plus tard » devient « Meilleur moment plus tard ».
- Le graphique est calculé par le jumeau de chaque pièce ; un thermostat qui chauffe ou se repose est simulé comme tenant sa consigne.

### Après la mise à jour

- Redémarrez Home Assistant, puis rechargez la page. Vos cartes gardent leurs réglages ; les nouveaux sont activés par défaut.

## 1.6.0 — Les personnes de chaque pièce, l’alarme, « un peu frais »

**En bref**

- **Les personnes de chaque pièce.** Dans l’onglet Présence, cochez à qui sert la pièce : une personne pour une chambre, plusieurs pour une pièce commune. Quand elles sont toutes absentes, la pièce compte comme vide, même si d’autres sont à la maison : pas de « Rallumez le chauffage » dans une chambre dont l’occupant est parti, et « Fenêtre ouverte · Paul est absent » si la sienne est restée ouverte.
- **Alarmo devient une extension**, avec son réglage dans Réglages généraux : Alarmo trouvé tout seul, une autre alarme, ou aucune. Armée en absence ou en vacances avec une fenêtre ouverte : « Refermez », urgent. En mode nuit : « Refermez », sauf pour la fenêtre laissée ouverte exprès pour dormir au frais.
- Une pièce vide alors que quelqu’un est à la maison : « Pièce vide · le bon moment pour aérer longuement ».
- **« Un peu frais » au lieu de « Trop frais »** quand la pièce reste dans la tolérance de son chauffage (1 °C par défaut, réglable dans l’onglet Chauffage). « Trop frais » est gardé pour un vrai écart.
- **La présence n’est plus « inconnue » pour rien.** Pendant le délai avant de dire la pièce vide, la carte affiche « personne depuis 4 min (vide après 5 min) ». Et après un redémarrage de Home Assistant, Hestia sait tout de suite depuis quand personne n’a été détecté.

### Corrections

- Deux pièces qui partagent leur air (salon et cuisine) : carte repliée, les mesures à surveiller portent le nom de leur pièce (« Salon », « Cuisine ») au lieu de deux fois « Température ».

### Après la mise à jour

- Redémarrez Home Assistant, puis rechargez la page. Cochez ensuite les personnes de chaque pièce (Modifier → Présence) et vérifiez l’alarme (Réglages généraux).

## 1.5.2 — Le thermostat en éco compte, la fenêtre qui réchauffe reste ouverte

**En bref**

- **La consigne de Versatile Thermostat sert de minimum** : en éco à 17 °C, une pièce à 18 °C n’est plus « trop fraîche ». Avant, seule sa température confort comptait. Le hors-gel protège sans être un confort : sa consigne (7 °C, ou 14 °C pour un poêle) ne sert pas de minimum, la température confort reste la référence, sans conseil de rallumer.
- **Plus de « Refermez » quand l’air du dehors réchauffe la pièce.** Une pièce trop fraîche, fenêtre ouverte, avec un dehors plus chaud : Hestia dit que vous pouvez laisser ouvert.

### Améliorations

- **Télécharger les diagnostics** : Paramètres → Appareils et services → Hestia Confort → ⋮ sur une pièce. Un fichier à joindre à un ticket : le conseil tel que la carte le reçoit, l’état brut des capteurs et du thermostat, ce que la pièce a appris, les premières heures de prévision. Les coordonnées de la maison sont retirées.
- **La jauge de température montre toujours votre plage.** La barre se colore : bleu sous la plage (trop frais), vert dans la plage, orange au-dessus (trop chaud). Le min–max des 24 h devient un trait fin à deux extrémités, posé dessus sans la cacher.

### Corrections

- « Fermeture conseillée · NaN h · NaN °C » : la ligne n’apparaît plus quand l’heure ou la température manque.
- La ligne d’un volet piloté par Adaptive Cover Pro est plus courte : qui le règle, où il en est, quand vient le soleil. Le texte technique d’Adaptive Cover Pro, qui répétait la même chose, est retiré.

### Après la mise à jour

- Redémarrez Home Assistant, puis rechargez la page. Si la case « Prendre la consigne du thermostat comme minimum » est décochée dans l’onglet Chauffage d’une pièce, c’est le minimum de la pièce qui reste utilisé.

## 1.5.1 — Vos pièces lisibles sur petit écran

**En bref**

- **« Vos pièces » s’adapte à l’écran.** Sur un grand écran, les colonnes restent alignées. Sur une tablette ou un téléphone, chaque pièce devient une fiche : son nom et « Modifier » en haut, puis ses mesures, ce que Hestia a observé, ses conseils optimisés et sa courbe sur 24 h. Plus de tableau coupé à droite.
- **« Votre plage de confort »** remplace « Votre plage de température », avec une explication plus simple.

### Corrections

- Le bouton « Modifier » n’a plus de bloc de fond qui reste visible au survol.
- Avec un Versatile Thermostat dont la température confort sert de minimum, la plage de confort le dit.

### Après la mise à jour

- Redémarrez Home Assistant, puis rechargez la page (ou videz le cache de l’application mobile).

## 1.5.0 — Chauffage plus tolérant, Versatile Thermostat, la nuit simulée

**En bref**

- **« Rallumez le chauffage » seulement quand ça vaut le coup.** Une pièce juste sous son minimum est dite dans « À savoir ». Le geste n’apparaît que si elle reste plus bas que la tolérance (1 °C par défaut) pendant 30 minutes, avec quelqu’un à la maison et le chauffage coupé, et qu’elle ne se réchauffe pas d’elle-même.
- **Versatile Thermostat devient une extension**, reconnue toute seule : sa température confort sert de minimum à la pièce, et Hestia comprend pourquoi il est arrêté.
- **La nuit simulée sur le jumeau de chaque pièce**, d’après la méthode de NADIR : « Cette nuit : ouvrez de 22 h à 7 h · 1,8 °C de mieux demain au plus chaud ».
- **Les cadres restent visibles avec les thèmes Home Assistant** dont les séparateurs ont la couleur du fond (Nordic et dérivés).

### Nouveautés

- Tolérance du chauffage réglable de 0 à 5 °C (Modifier une pièce → Chauffage). 0 rend la règle d’avant.
- Versatile Thermostat (reconnu par sa plateforme) : consigne confort comme minimum (désactivable), raison d’un arrêt (manuel, fenêtre, arrêt automatique, mode central, délestage…), préréglages éco, hors-gel et absence, pente de température, présence ou mouvement suivis, fenêtre ouverte détectée. Seul un arrêt manuel appelle « Rallumez ». En éco, hors-gel ou absence, ou arrêté par une fenêtre, la carte l’explique.
- Une section **Extensions** sur l’accueil Confort : Hestia Weather, Versatile Thermostat, Adaptive Cover Pro, et les pièces où chacune sert.
- Le jumeau apprend la masse des murs (second nœud qui suit l’air en environ 3 h) : une aération courte refroidit l’air, pas les murs, et la pièce remonte une fois fermée.
- La simulation des 30 prochaines heures pèse le soleil qui entre volets relevés contre l’air frais, n’ouvre jamais sous la pluie ni sous le minimum, et signale un air humide (point de rosée au-dessus de 16 °C).

### Corrections

- Un thermostat qui ne publie pas son action est lu « coupé » quand son mode est arrêt.
- Un seul compte partout : le nombre de capteurs qui répondent inclut tous ceux vérifiés (présence, volets, extérieur…), et l’accueil Hestia, le sous-titre et l’indicateur donnent le même nombre de points à régler. Les suggestions sont comptées à part.
- Un capteur que Home Assistant affiche mais que le conseil ne peut pas utiliser (trop ancien, unité) est nommé « ne donne pas de mesure exploitable ».
- « Pas de contact de fenêtre ici, c’est voulu » (Modifier une pièce → Ouvertures) arrête la suggestion pour un garage ou une pièce jamais aérée.

### Remerciements

- La nuit simulée et la masse des murs s’inspirent de **NADIR**, de Solal Gendrin : [son dépôt](https://github.com/solal3105/NADIR2) et [sa méthodologie](https://solal3105.github.io/NADIR2/methodologie.html). Le code de Hestia a été écrit indépendamment, à partir des équations publiées.
- Merci à Gaël (@gael1980) d’avoir fait découvrir NADIR et partagé sa carte ([#2](https://github.com/hestiaFB/hestia-comfort-integration/issues/2)), et à Louis (@hellmer1234) pour ses retours sur l’affichage ([#1](https://github.com/hestiaFB/hestia-comfort-integration/issues/1)).

### Après la mise à jour

- Redémarrez Home Assistant, puis rechargez votre tableau de bord. Le jumeau réapprend la masse des murs à partir des mesures déjà gardées : rien à faire.

## 1.4.0 — Une humidité mieux nuancée, de l’air sec à l’air humide

**En bref**

- **Une plage d’humidité avec deux limites réglables** : minimum 40 % et maximum 60 % proposés. Le maximum déjà choisi est conservé.
- **À 60,6 % pour une limite de 60 %, « Légèrement humide »** remplace le verdict trop catégorique. Un léger écart seul ne compte plus la pièce parmi celles à surveiller.

### Nouveautés

- Même graduation pour l’air humide et l’air sec : jusqu’à 3 points hors de la plage, « Légèrement humide / sec » ; jusqu’à 10 points, « Air humide / sec » ; au-delà, « Très humide / sec ». Ce sont des paliers Hestia, pas des seuils sanitaires.
- Les cartes de pièce et de logement suivent la mesure actuelle, avec une indication d’amélioration ou d’écart durable dans « À savoir ».
- Pour l’air sec, l’effet de l’air extérieur est expliqué quand les mesures permettent de le calculer ; sans ces mesures, cet effet reste inconnu.

### Corrections

- Un besoin d’assécher antérieur ne conserve plus une indication alarmiste près de la limite. Un léger dépassement seul ne déclenche plus de conseil d’aération.
- Les risques estimés sur les murs froids et les autres conseils utiles restent distincts de la graduation d’humidité.

### Après la mise à jour

- Redémarrez Home Assistant, puis rechargez votre tableau de bord. Les deux limites se trouvent dans Hestia → Confort → Modifier une pièce → Température et humidité.

## 1.3.2 — Observé et conseils optimisés, chacun sa colonne

**En bref**

- **Le soleil à l’ombre est vraiment estimé.** La couverture nuageuse de Hestia Weather est trouvée même quand sa prévision commence à l’heure suivante.
- **« Observé » et « Conseils optimisés » en deux colonnes** sur l’accueil Confort : un pourcentage élevé et « pas encore » ne se contredisent plus.

### Améliorations

- Accueil Confort : la colonne « Observé » dit ce que Confort a vu de chaque pièce, la colonne « Conseils optimisés » ce qu’il prévoit assez juste pour annoncer un résultat, ou ce qui manque (« prévisions à affiner (±0,57 °C, ±5 %) », « fenêtres à observer davantage »).
- Le pavé Extérieur indique quand votre station est à l’ombre (« station à l’ombre le matin et l’après-midi : soleil estimé »).

### Corrections

- Station à l’ombre : le soleil restait à la mesure brute quand la prévision horaire commençait à l’heure suivante.

## 1.3.1 — Le soleil juste, même station à l’ombre

**En bref**

- **Le soleil est juste même quand la station est à l’ombre.** Confort apprend tout seul les heures où la maison cache le capteur, et y estime le soleil avec la couverture nuageuse de Hestia Weather, corrigée par la mesure réelle.
- **Le soleil est lissé sur 15 minutes** : un nuage qui passe ne fait plus apparaître et disparaître les conseils.

### Nouveautés

- Les directions du soleil où la station perd sa mesure chaque jour ensoleillé sont reconnues (par exemple une station côté est, à l’ombre de la maison l’après-midi). Rien n’est à régler ; une station bien dégagée ne change pas.
- Station à l’ombre : soleil théorique × couverture nuageuse de Hestia Weather (2.6.3), corrigée de l’écart mesuré juste avant ; sinon, la dernière mesure prise au soleil. La tuile Soleil indique « estimé, station à l’ombre ».
- L’apprentissage des pièces se fait sur l’historique corrigé : l’effet du soleil sur les fenêtres ouest n’est plus sous-estimé.

### Améliorations

- Le réglage du soleil s’appelle « Soleil compté sur une fenêtre à partir de (W/m²) » et explique son effet (Modifier une pièce › Réglages avancés).

## 1.3.0 — Des conseils qui suivent la saison

**En bref**

- **Des conseils qui suivent la saison.** Été, hiver ou entre-saisons : les heures, la durée d’une aération, le soleil et la fenêtre ouverte la nuit ne se jugent plus de la même façon.
- **La saison vient de Hestia Weather** (2.6.2), ou d’un capteur Saison choisi dans « Extérieur ». Rien n’est deviné.
- **Plus d’« Aérez vers 3 h »** : une heure d’aération n’est proposée qu’à des heures où l’on peut ouvrir.

### Nouveautés

- Heures d’aération selon la saison : de 7 h à 23 h en été (l’aération du soir jusqu’au coucher), de 8 h à 21 h au printemps et en automne, de 10 h à 18 h en hiver.
- Hiver : une aération courte et franche (5 à 10 min), conseillée dès 3 points d’humidité à gagner. Une pièce trop chaude ne se rafraîchit pas en ouvrant : « baissez le chauffage plutôt que d’ouvrir ».
- Soleil : toujours bienvenu en hiver ; en été, « baissez le volet » dès que la pièce approche du haut de sa plage.
- Le haut de la plage de température suit la saison : votre valeur d’hiver, votre valeur d’été, entre les deux au printemps et en automne.
- Nouvelle source « Saison » dans « Extérieur » quand Hestia Weather n’est pas la source ; avec Hestia Weather, sa saison est reprise et affichée.
- Le flacon d’apprentissage s’affiche dans la pastille dès qu’un chiffre vient des aérations apprises de la pièce, aussi sur la carte logement.

### Améliorations

- Fenêtre ouverte la nuit, voulue : elle n’est tolérée que si elle rafraîchit la pièce. Dehors plus chaud, pièce trop fraîche ou plus humide : « Refermez ». La réponse vaut pour une saison et la question revient à la suivante ; en hiver, une fenêtre ouverte la nuit est toujours signalée.
- Sous « Aérez vers … h », plus de ligne qui semblait contredire le conseil.

## 1.2.12 — Des conseils optimisés sans attendre 100 %

**En bref**

- **Des conseils optimisés sans attendre 100 %.** Humidité, température et air s’apprennent chacun de leur côté : dès qu’une pièce en a appris un, son conseil annonce le résultat (« Conseil optimisé »).
- **Le soleil utile est signalé** : « Soleil · il réchauffe la pièce : volets et rideaux ouverts, fenêtre fermée ».

### Nouveautés

- « Refermez » appris : la carte dit ce que la fenêtre ouverte coûte, par exemple « Ouverte, 18,3 → 17,6 °C en 30 min ».
- « À savoir » signale le soleil qui réchauffe une pièce fraîche, ou qui chauffe trop une pièce déjà chaude (« baissez le volet ou le store »).
- Accueil Confort : sous chaque pièce, « Conseils appris : humidité · température · CO₂ ». Le pavé Apprentissage compte les pièces qui ont déjà des conseils optimisés.

### Améliorations

- Une prévision encore imprécise ne bloque plus les autres : une humidité à affiner laisse passer les conseils de température.
- La ligne Apprentissage d’« À savoir » dit ce qui manque au geste conseillé, par exemple « humidité : 2 aérations sur 5 ».

## 1.2.11 — Des mots qui ne se contredisent plus

**En bref**

- **Des mots qui ne se contredisent plus.** « Votre plage » ne parle plus que de température. Une autre mesure qui dépasse est « à surveiller », et la pastille dit ce qui ne va pas : « Trop humide », « Trop frais »…

### Améliorations

- Pastille d’une pièce sans geste à faire : « Trop humide », « Trop frais », « Trop chaud » ou « Air à renouveler », au lieu de « Hors plage ».
- Le rond du conseil montre le problème (une goutte pour l’humidité) ; la coche ne s’affiche que s’il n’y a rien à signaler.
- Mesures : « 1 à surveiller » ou « rien à signaler ». Détails : « Votre plage de température ».
- Carte logement : elle signale les pièces trop humides comme les cartes de pièce, et affiche « 2 à surveiller » au lieu de « Tout va bien ».

### Corrections

- Carte logement : la température ne s’affiche plus deux fois (« 18,8 °C 18,8 °C trop frais »).
- Hub : un capteur repris de la pièce au même air n’est plus compté comme muet (« 30 / 32 capteurs qui répondent »).

## 1.2.10 — Des cartes qui ne se contredisent plus

**En bref**

- **Des cartes qui ne se contredisent plus.** Vérifiées sur 10 jours réels d’une maison : 7 296 situations, plus aucune contradiction entre le bandeau, la pastille, « À savoir » et les mesures.

### Corrections

- Une fenêtre ouverte qui ne change rien : « Ouverte ou fermée, cela ne change rien », au lieu de « Ouvrir n’apporterait rien ».
- Salon et cuisine sur une seule carte : chaque mesure s’affiche une fois, sous la pièce qui l’a.
- Une pièce humide ou fraîche sans geste n’affiche plus « Tout va bien » : la pastille dit « Hors plage ».
- « Refermez » dans une pièce humide dit pourquoi : « l’aération ne la baisserait que d’un point à peine ».
- Pluie ou rafales : « Aérer n’est pas possible pour l’instant », et « À savoir » dit pourquoi. Une fenêtre abritée ouverte n’est plus priée de rester fermée.
- Une pièce humide en « Rien à faire » dit toujours pourquoi l’humidité reste.
- L’humidité du bandeau est celle de la pièce, comme sur sa tuile.
- « Mesures absentes » n’affiche plus de lignes de conseil dessous.
- La ligne Apprentissage n’apparaît que si un résultat est annoncé.

## 1.2.9 — Les pièces au même air apprises ensemble

**En bref**

- **Les pièces au même air sont vraiment liées** : une cuisine ouverte sur le salon reprend son chauffage et son CO₂, et les deux pièces apprennent ensemble.
- **Chaque pièce apprend ce que l’autre pèse chez elle** : ses fenêtres, son air, son chauffage.

### Nouveautés

- Une pièce sans chauffage, sans CO₂, sans COV, sans purificateur ni VMC reprend ceux de la pièce au même air. Ses propres capteurs passent toujours avant. Une pièce « non chauffée » ne reprend pas de thermostat.
- Dans « Vos pièces », la ligne affiche « Chauffage · Salon » ou « CO₂ · Salon » pour ce qui vient de l’autre pièce.
- Sous « Même air que… », les poids appris : « Poids ici : fenêtres 50 % · air 4 % par heure · chauffage 40 % ».
- Les pièces au même air ont un seul pourcentage d’apprentissage : elles sont « Optimal » ensemble.

### Améliorations

- Les fenêtres de l’autre pièce ne comptent plus comme les siennes : leur effet est appris à part.
- La température et l’humidité de l’autre pièce entrent dans les prévisions : elles sont plus justes, surtout dans le salon.

## 1.2.8 — Une fenêtre ouverte seulement quand ça vaut le coup

**En bref**

- **Une fenêtre ouverte n’est plus gardée pour un ou deux points d’humidité.** Il faut qu’elle en fasse encore gagner 3 au moins.

### Corrections

- La carte pouvait dire « Encore 56 min d’aération » pour un point d’humidité à peine, alors que la pièce se refroidissait. Elle propose maintenant de refermer.

## 1.2.7 — L’apprentissage de chaque pièce en pourcentage

**En bref**

- **Chaque pièce a son pourcentage d’apprentissage**, et « Optimal » veut dire qu’elle a tout appris : ses mesures, ses fenêtres, son chauffage, son air.

### Nouveautés

- Dans « Vos pièces », le pourcentage de chaque pièce et ce qui reste à apprendre, une ligne par élément (« fenêtres : 2 aérations sur 5 », « chauffage pas encore vu en marche »).
- Le pavé Apprentissage explique en trois lignes ce que Confort observe, et donne le pourcentage du logement.
- Sur la carte, « À savoir » dit quand le résultat annoncé est encore estimé.

### Corrections

- Une pièce pouvait rester « À vérifier » sans fin : une demi-heure manquante après un redémarrage empêchait de vérifier ses prévisions.
- Une porte ouverte quelques secondes n’est plus comptée comme une aération, et le résultat d’une aération est lu quelques minutes après la fermeture.

## 1.2.6 — La qualité de l’air de Hestia Weather gardée

**En bref**

- **La qualité de l’air de Hestia Weather est bien gardée dans les Réglages généraux.**

### Corrections

- Avec Hestia Weather (air WAQI ou Atmo France), les Réglages généraux affichaient la pollution « non fournie », et l’enregistrer la retirait. Elle s’affiche maintenant avec sa source et son niveau (« Hestia Weather · WAQI — Moyen »), et reste prise en compte.
- Les valeurs longues ne sortent plus du cadre.

### Améliorations

- Un sous-titre plus simple au-dessus des mesures de Hestia Weather.

## 1.2.5 — Des conseils qui ne se contredisent plus, et l’apprentissage de chaque pièce

**En bref**

- **Des conseils qui ne se contredisent plus** : une seule pluie pour tout le logement, et les pièces au même air (un salon ouvert sur sa cuisine) jugées ensemble, avec une seule carte.
- **Chaque pièce apprend** : quand son apprentissage est optimal, le conseil annonce le résultat (« Aérez 15 min · 76 → 68 % »), aussi pour le CO₂ et les COV.
- **Le bandeau dit le geste à faire ; l’encart « À savoir » dit le reste.**
- **Un vrai accueil Confort dans le hub Hestia**, et des réglages généraux plus simples.

### Nouveautés

- Pièces au même air : à cocher dans les réglages d’une pièce ; une seule carte « Salon · Cuisine ».
- L’humidité est jugée sur ce qu’aérer peut gagner ; le risque de moisissure sur les murs froids devient une alerte.
- Apprentissage de chaque pièce : optimal après 7 jours, quand ses prévisions tiennent à ±0,5 °C et ±3 %.
- Chaque aération suivie est mesurée : son résultat sur la carte, le bilan de la semaine dans le hub.
- Des questions Oui / Non pour affiner l’apprentissage : une humidité qui revient à la même heure, une fenêtre ouverte la nuit.
- Accueil Confort : l’état du logement, trois compteurs, puis « Vos pièces » avec, pour chacune, ses mesures, son apprentissage, sa courbe sur 24 h et un bouton Modifier. Une pièce s’ajoute sur place.

### Améliorations

- Réglages généraux : avec Hestia Weather, les mesures du dehors sont reprises de sa station et seulement affichées ; avec vos propres capteurs, un choix par mesure, avec sa valeur du moment.
- Chaque conseil est vérifié dans 32 400 situations (hiver, été, pluie, rafales, chauffage, présence…), à chaque mise à jour.
- Une fenêtre ouverte après « Aérez » compte aussitôt.
- Des messages plus justes ; une mesure hors plage n’a plus de cadre orange quand rien n’est à faire.

### Corrections

- Le panneau et les cartes restaient affichés dans leur ancienne version : leur numéro suit maintenant chaque mise à jour.
- Le bouton « Réglages des pièces » de l’accueil ne menait nulle part : chaque pièce a désormais son bouton Modifier.

## 1.2.5-beta.9 — Préversion : l’accueil Confort

**En bref**
- **Un vrai accueil pour Confort dans le hub Hestia : l’état technique du logement en un coup d’œil.**

### Nouveautés
- L’onglet Confort s’ouvre sur son accueil : « Tout fonctionne » et les versions, puis quatre compteurs (capteurs qui répondent, pièces en apprentissage optimal, points à régler, sources en place).
- « À régler » en premier quand il y a quelque chose ; sinon une seule ligne rassurante.
- L’apprentissage en tableau : l’état et les jours de chaque pièce, la précision de ses prévisions, l’air appris (CO₂, COV) et la courbe des dernières 24 heures, puis les questions et le bilan de la semaine.
- « Pièces et capteurs » : ce qui équipe chaque pièce, son « même air », et un bouton Configurer.
- Sources partagées, versions et liens, et comment ajouter les cartes, sur le côté.

### Améliorations
- La liste des pièces devient « Réglages des pièces », à un clic de l’accueil, avec un retour à l’accueil.

## 1.2.5-beta.8 — Préversion : le panneau et les cartes à jour

**En bref**
- **Le panneau Hestia et les cartes s’affichent enfin dans leur dernière version.**

### Corrections
- Depuis la 1.2.0-beta.1, le panneau et les cartes gardaient le numéro 1.1.4 : le navigateur et l’application mobile continuaient d’afficher leur ancienne version en mémoire. Le numéro suit maintenant chaque mise à jour.

## 1.2.5-beta.7 — Préversion : l’air appris, la boucle de retour et les questions

**En bref**
- **Les conseils d’aération pour le CO₂ et les COV peuvent aussi être optimisés.**
- **Chaque aération suivie est mesurée : la carte montre le résultat, le hub le bilan de la semaine.**
- **Des questions simples pour affiner l’apprentissage : la cause d’une humidité qui revient, une fenêtre ouverte la nuit.**

### Nouveautés
- L’apprentissage de chaque pièce comprend maintenant l’air : la vitesse à laquelle le CO₂ et les COV redescendent, fenêtres fermées et ouvertes. Un conseil peut annoncer « CO₂ 1 180 → 890 ppm en 15 min ».
- Après une aération conseillée et suivie, À savoir montre pendant 24 h son résultat : « Dernière aération · humidité 76 → 70 % (prévu 68 %) ».
- Encart Apprentissage, « Cette semaine » : aérations suivies, gain moyen d’humidité, prévisions tenues, la pièce qui gagne le plus, conseils laissés sans suite.
- Encart Apprentissage, « Pour affiner l’apprentissage » : quand l’humidité d’une pièce monte souvent à la même heure, ou qu’une fenêtre reste ouverte la nuit, une question Oui / Non / Je ne sais pas.

### Améliorations
- Les écarts entre prévision et résultat corrigent les prévisions suivantes de la pièce. Si elles ne tiennent plus, la pièce repasse en conseil estimé.
- Une cause n’est jamais devinée : seul un « Oui » la nomme, et seulement à l’heure habituelle (« habituelle à cette heure : la douche, elle retombe d’elle-même »).
- Une fenêtre ouverte la nuit volontairement n’est plus signalée comme un oubli ; la pluie et le vent la font toujours refermer.

## 1.2.5-beta.6 — Préversion : conseils optimisés et encart Apprentissage

**En bref**
- **Conseils optimisés : quand l’apprentissage d’une pièce est optimal, son conseil annonce le résultat (« Aérez 15 min · 76 → 68 % en 15 min »).**
- **Nouvel encart Apprentissage en tête de l’accueil Confort du hub Hestia.**

### Nouveautés
- « Conseil optimisé » en haut à droite de la carte, à la place de « Geste conseillé », quand le conseil vient de l’apprentissage de la pièce : au moins 7 jours de mesures, des prévisions justes à ±0,5 °C et ±3 %, et au moins 5 aérations apprises. Sinon, le conseil reste estimé.
- « Action à faire » au-dessus de chaque geste ; « Conseil » reste pour « Rien à faire ».
- Quand le conseil est estimé, À savoir dit où en est l’apprentissage : « en cours : 5 jours sur 7 », « vérification en attente ».
- Encart Apprentissage : pour chaque pièce, son état (Connue, À affiner, En cours, À vérifier) avec le nombre de jours, la précision de ses prévisions, et ce qu’elle a appris en mots simples (« garde bien sa température », « le soleil la réchauffe un peu »).
- Angle précis facultatif pour chaque ouvrant (0 à 359°), en plus de l’exposition.

### Améliorations
- Le soleil est compté fenêtre par fenêtre, selon son orientation et la position du soleil à chaque demi-heure, au lieu de la mesure à plat de la station.
- Des phrases plus naturelles dans le panneau : Hestia n’est plus le sujet des phrases.

## 1.2.5-beta.5 — Préversion : des messages plus justes

### Améliorations
- « Humidité élevée · risque de moisissure » : un seul message, sans deviner la cause. Après plusieurs jours de pluie, la maison elle-même rend de l’humidité, sans douche ni cuisson.
- Le risque de moisissure n’apparaît que s’il dure au moins une heure : le pic d’une douche, qui retombe seul, ne le déclenche plus.
- « Lancez la VMC » revient plus tôt : une VMC arrêtée aide même quand l’air de la pièce n’est qu’un peu plus humide que dehors.
- Une mesure hors de votre plage garde son cadre orange seulement quand un geste est conseillé. Sinon, la tuile reste neutre, avec la pastille orange qui bat devant la note.
- « Aération » remplace « Humidité » pour dire qu’aérer n’aiderait pas.

## 1.2.5-beta.4 — Préversion : une seule carte pour les pièces au même air

**En bref**
- **Salon et cuisine ouverts l’un sur l’autre : une seule carte « Salon · Cuisine ».**

### Nouveautés
- Dans les réglages de la carte, les pièces au même air ne sont proposées qu’une fois : « Salon · Cuisine », la pièce la mieux équipée en premier. Une carte déjà réglée sur l’une des deux continue de marcher et montre tout le volume.
- La carte commune a un seul bandeau et un seul « À savoir » ; les mesures sont rangées sous le nom de chaque pièce, fenêtres et soleil une seule fois.
- Mon logement : une seule tuile « Salon · Cuisine » dans la grille des pièces.

### Améliorations
- Quand il faut refermer, la carte dit quelle fenêtre : utile quand elle est dans l’autre pièce du volume.

## 1.2.5-beta.3 — Préversion : le conseil suivi se voit tout de suite

### Corrections
- Vous ouvrez la fenêtre que Hestia vient de conseiller : « Aération en cours » s’affiche aussitôt, au lieu d’attendre 30 secondes. Une fenêtre ouverte sans conseil garde ce court délai, pour ne pas crier « Refermez » au moindre courant d’air.

## 1.2.5-beta.2 — Préversion : le bandeau pour les gestes, « À savoir » pour le reste

**En bref**
- **Le bandeau ne dit plus qu’une chose : le geste à faire**, ou « Rien à faire ».
- **Nouvel encart « À savoir » juste dessous**, en mots simples : risque de moisissure, air humide dehors, fenêtre ouverte sans effet, maison vide, purificateur ou VMC en marche, même air qu’une autre pièce.

### Améliorations
- Une pièce froide quand quelqu’un est là et que le chauffage est coupé : « Rallumez le chauffage ».
- « Risque de moisissure » dit d’où il vient : « à cause du temps humide dehors, il baissera quand le temps sera plus sec », ou « l’humidité vient de la pièce : douche, cuisine ou linge ».
- Le purificateur et la VMC en marche ne défilent plus dans le bandeau : ils sont dans « À savoir ».

### Corrections
- « Murs humides » s’affichait comme un conseil, avec « Tout va bien » : ce n’était pas un geste.

## 1.2.5-beta.1 — Préversion : des conseils vérifiés dans toutes les situations, et le jumeau de chaque pièce

**En bref**
- **Les pièces au même air disent enfin la même chose** : le salon et la cuisine sont jugés ensemble.
- **Chaque conseil a été vérifié dans 32 400 situations** (hiver, été, pluie, rafales, chauffage, présence…), et cette vérification tourne désormais à chaque mise à jour.
- **Chaque pièce a son jumeau** : quelques chiffres appris sur ses mesures. Il observe seulement, aucun conseil ne change.

### Nouveautés
- Une pièce froide dit pourquoi : « le chauffage est coupé » en orange quand quelqu’un est là, « Maison vide : pas besoin de chauffer » quand Alarmo est en absence ou que personne n’est à la maison, « le chauffage s’en charge » quand il tourne.
- Murs humides : quand l’air touche les murs froids au-delà de 80 %, la carte le dit, avec le geste qui aide (VMC, un peu de chauffage, aérer quand le temps le permettra).
- Fenêtre ouverte qui n’aide ni ne gêne : « Fenêtre ouverte · sans effet sur le confort », en bleu.
- Panneau Hestia, rubrique « Ce que Hestia a appris » : pour chaque pièce, son inertie, ce que lui apportent le soleil et la vie de la maison, l’effet d’une fenêtre ouverte, le renouvellement d’air, et sa précision sur les dernières 24 heures.
- Deux capteurs de diagnostic par pièce, désactivés au départ : « Température prévue dans 1 h » et « Humidité prévue dans 1 h ».

### Améliorations
- Pièces au même air : l’humidité est jugée sur l’air commun ; la pièce dont le conseil compte le plus parle pour toutes (« Même air : Salon »).
- Une fenêtre déjà ouverte est toujours rejugée : utile, on laisse ; sans effet, c’est neutre ; nuisible, « Refermez ».
- Chauffage en marche : une pièce humide de l’intérieur peut quand même être aérée 5 minutes.
- La pluie, l’orage ou l’air extérieur ne disent « gardez fermé » que si ouvrir aurait servi.

### Corrections
- « Refermez » s’affichait « Rien à faire » quand l’air extérieur était mauvais.
- « Aération en cours » alors que l’aération n’asséchait plus rien (« environ 80 % après », déjà à 80 %).
- En été, une fenêtre ouverte sur un dehors plus chaud passait pour une aération utile.
- Une pièce froide ou des murs humides affichaient « Rien à faire ».
- Le capteur Raison ne connaissait pas « Air du dehors plus humide » : il restait vide dans ce cas.

## 1.2.0-beta.1 — Préversion : des conseils qui ne se contredisent plus

**En bref**
- **Une seule pluie pour tout le logement** : plus de « Refermez avant la pluie » dans une pièce et « Aérez » dans la voisine.
- **Les pièces ouvertes l’une sur l’autre partagent leur air** : un salon ouvert sur sa cuisine partage ses fenêtres et ses conseils.
- **L’humidité est jugée sur ce qu’aérer peut gagner** : l’humidité du temps n’est plus une alerte, le risque de moisissure sur les murs froids en devient une.

### Nouveautés
- Réglage « Même air », page La pièce : cochez les pièces sans mur ni porte entre elles. Une fenêtre ouverte dans l’une aère l’autre.
- Dans un même air, jamais deux gestes contraires : le plus important parle pour les deux pièces (« Laissez ouvert : Salon a besoin d’air »), et la carte logement n’en montre qu’un.
- Risque de moisissure : Hestia estime l’humidité contre le coin le plus froid des murs extérieurs. Au-delà de 80 % qui dure, il conseille d’assécher, même si la pièce semble dans votre plage.

### Améliorations
- La pluie vient de Hestia Weather 2.6.1, à la minute avec la pluie dans l’heure de Météo-France. Une pluie dans les 20 minutes fait refermer et empêche d’ouvrir ; une pluie plus tardive raccourcit l’aération : « Refermez avant 15 h 20 ».
- Avec une station qui mesure la pluie, la prévision heure par heure ne fait plus refermer : la station dira quand il pleut.
- Air humide dehors : « Aérer n’y changerait rien : 72 % au mieux », au lieu de « trop humide ». La tuile dit « humide dehors aussi ».

### Corrections
- « Pluie dans 0 min » alors qu’il ne pleuvait pas.
- « Lancez la VMC » n’affiche plus « 85 → 85 % seulement ».

## 1.1.4 — La station avant la prévision

- Quand Hestia Weather a une station qui mesure la pluie et les rafales, ce sont ses mesures qui comptent. Sec, vent calme et pas de pluie dans l’heure : malgré un orage prévu ou une vigilance orange, Confort propose « Aérez 5 minutes » si l’air en a besoin.
- Sans station, rien ne change : la prévision Météo-France garde le dernier mot.
- Il pleut, le vent souffle fort, la pluie arrive dans l’heure ou la vigilance est rouge : tout reste fermé, comme avant.
- Pas d’ouverture longue sous un orage prévu : seulement une aération courte.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 1.1.3 — Correction des volets

- Une fonction d’Adaptive Cover Pro désactivée (par exemple le mode climat) n’est plus comptée comme un capteur qui ne répond pas : plus de « À vérifier » ni de « Ne répond pas » au nom de la fenêtre.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 1.1.2 — Dimensions reprises d’Adaptive Cover Pro

- La largeur, la hauteur et l’orientation de la fenêtre sont reprises des réglages d’Adaptive Cover Pro ; une valeur saisie dans Hestia reste prioritaire.
- Quand Adaptive Cover Pro est détecté, le panneau ne propose plus de choisir d’autres signaux.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 1.1.1 — Volets mieux compris

- Le panneau montre, en pleine largeur, ce que Hestia lit d’Adaptive Cover Pro : intégration, pilotage automatique, suivi du soleil, mode climat, détection de la reprise à la main, soleil devant la fenêtre, orientation exacte.
- Si l’un de ces interrupteurs coupe le pilotage, Hestia le dit et reprend ses conseils ; sans détection, il ignore le signal « repris à la main ».
- Le soleil sur la fenêtre est calculé avec l’orientation exacte donnée par Adaptive Cover Pro.
- Hestia prévient avant que le soleil n’arrive sur la fenêtre d’une pièce déjà trop chaude (« à fermer avant 13 h 50 »).
- Les détails donnent la raison d’Adaptive Cover Pro et l’heure de fin d’une reprise à la main.
- Nouvelle icône Hestia Confort dans HACS ; badge de version corrigé.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 1.1.0 — Adaptive Cover Pro reconnu

- **Adaptive Cover Pro est détecté tout seul** : pour un volet connecté qu’il pilote, Hestia lit son pilotage automatique, la reprise à la main, le soleil devant la fenêtre et la position visée. Plus rien à renseigner.
- Quand Adaptive Cover Pro pilote le volet, Hestia ne vous demande plus de le fermer ; s’il est coupé, le conseil le dit.
- Nouvelle tuile « Volet » sur la carte pièce : ouvert, fermé ou position, et qui le pilote. Les détails donnent les heures de soleil sur la fenêtre.
- Carte logement : une pièce qui demande un geste fait défiler ses besoins mesurés (« 68 % trop humide », « 282 COV élevés ») au lieu de répéter le conseil.
- Réglages du volet plus clairs, sans libellé en double.
- Une VMC ou un purificateur en marche n’est plus compté « hors de votre plage ».

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 1.0.2 — Carte logement plus calme

- Un capteur qui ne répond plus (présence, luminosité…) n’affiche plus « Bilan partiel » ni « À vérifier » sur la carte logement : elle reste sur « Rien à faire ». L’état des capteurs se consulte dans le panneau Hestia.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 1.0.1 — Appui long sur la carte logement

- La carte logement complète et la liste des pièces ont, elles aussi, leur groupe « Fonctionnalités » : un appui long peut ouvrir une page de votre tableau de bord (par exemple votre page Maison). Sur la carte complète, le choix est « Rien » ou « Ouvrir une page ».

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 1.0.0 — Première version stable

Hestia Confort conseille, pièce par pièce, le geste qui améliore vraiment le confort. Il ne commande aucun équipement.

- **Des conseils utiles** : aérer, refermer, rafraîchir, assécher, lancer la VMC, attendre le bon moment. Sans geste utile, la carte reste calme.
- **Chaque pièce apprend de ses aérations** : gain réaliste, durée propre à la pièce, meilleur moment selon la prévision de Hestia Weather.
- **La saison et la météo** : plage de confort qui suit la saison, pluie, rafales, orage, vigilance et qualité de l’air dehors, lien avec Hestia Weather.
- **Des cartes comme Hestia Weather** : carte pièce (complète, tuile, tuile dépliée, mini, mesures, alerte) et carte logement (complète, tuile, liste, mini, alerte), avec le même panneau de réglages.
- **Des couleurs qui disent s’il y a quelque chose à faire** : bleu tout va bien, vert à saisir, orange geste conseillé, rouge urgent ; une panne de capteur n’est jamais un conseil.
- **Le panneau Hestia** pour configurer les pièces, les capteurs et l’extérieur, avec l’état technique du logement.

Depuis une préversion : mise à jour HACS, redémarrage de Home Assistant, puis rechargement de la page. Vos pièces et réglages sont conservés.

## 0.9.9.1 — Corrections

- Juste après un démarrage de Home Assistant, un ou deux capteurs secondaires en retard (présence, luminosité…) ne bloquent plus la carte sur « Mesures en chargement » : le conseil s’affiche, seules leurs tuiles restent « en attente ».
- Un logement relié à Hestia Weather sans qualité de l’air choisie ne reprend plus l’indice de Weather.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.9-beta.1 — Les formats de Hestia Weather et des pannes qui ne sont plus des conseils

- **Six formats pour la carte pièce**, comme Hestia Weather : complète, tuile (le conseil et ses pastilles, qui se déplie d’un appui), tuile dépliée, mini (une ligne), mesures (les tuiles seules) et alerte (visible seulement quand un geste est conseillé).
- **Cinq formats pour la carte logement** : complète, tuile, liste des pièces, mini et alerte.
- **Un appui long** sur une tuile (un appui sur mini et alerte) ouvre la carte complète en fenêtre, une page de votre choix, ou rien.
- **Panneaux de réglages refaits comme celui de Hestia Weather** : le format en liste, puis des groupes repliables qui changent avec lui (Visuel et performance, Bandeau, Échelle, Mesures, Détails, Fonctionnalités). Le contenu du bandeau, les repères de l’échelle, les pastilles et les rubriques se cochent et s’ordonnent. Le réglage du thème disparaît : la carte suit Home Assistant.
- **Une panne n’est plus un conseil** : juste après un démarrage, « Mesures en chargement » et des tuiles « en attente » ; si les capteurs restent muets, « Mesures absentes » en gris, avec leur nombre plutôt qu’une longue liste, et sans échelle vide ; un capteur secondaire muet laisse le bandeau calme et sa tuile passe en pointillés.
- Le survol d’une section n’affiche plus de bande grise : c’est le chevron qui s’allume.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.8-beta.1 — Des conseils qui apportent un plus, des cartes plus vivantes

- **Un conseil apporte toujours un plus.** Hestia ne dit plus « gardez fermé » à quelqu’un qui n’allait pas ouvrir : sans geste utile, le bandeau reste calme (« Rien à faire »). Il parle pour un geste qui aide maintenant, une fenêtre à refermer, un mauvais réflexe à éviter (ouvrir quand il fait plus chaud dehors, ou pour aérer sous la pluie), un moment précis (« Ouvrez vers 22 h ») ou un autre équipement (« Lancez la VMC »).
- **Les couleurs disent s’il y a quelque chose à faire**, comme sur vos autres cartes : bleu tout va bien, vert à saisir, orange geste conseillé, rouge urgent. Une mesure hors de votre plage, sans geste demandé, se repère en ambre.
- **L’humidité compte quand elle gêne vraiment** : nettement au-dessus de votre seuil (5 points), ou au-dessus depuis trois heures.
- **Des cartes plus vivantes** : une lumière douce qui se déplace dans le coin du bandeau, un anneau de lumière qui tourne autour du rond (lentement si tout va bien, plus vite pour un geste, très vite pour une alerte), des conseils qui se succèdent en glissant, des tuiles et une échelle qui arrivent en douceur. Tout se coupe avec le réglage « Animations » et respecte la réduction des animations de l’appareil.
- Le rond du bandeau se tient en retrait du bord, et une mesure hors de votre plage se repère d’un coup d’œil : liseré ambre, et un point qui bat devant son état.
- **L’air du dehors suit la source choisie dans Hestia Weather** (Atmo France ou une station WAQI) quand le logement est relié à Hestia Weather 2.5.7 ou plus : une panne d’Atmo France ne prive plus Hestia Confort de l’indice du jour.
- **La carte logement a ses réglages**, comme les cartes pièce : titre, défilement des conseils, échelle, sections Pièces et Détails (affichées, dépliées au départ), thème, animations et effet de verre.
- Sur la carte logement, une pièce qui demande un geste l’affiche sur sa tuile, même non chauffée.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.7-beta.1 — Chaque pièce apprend de ses aérations

- **Les conseils d’aération apprennent de votre maison.** Hestia relit les ouvertures des 10 derniers jours et retient, pour chaque pièce, ce qu’une aération y a vraiment donné : vitesse de séchage, humidité qui reste, humidité qui revient après la fermeture. Les nouvelles aérations s’ajoutent ensuite (jusqu’à 90 jours).
- La promesse est réaliste : « 76 % d’humidité, environ 70 % après l’aération » au lieu d’un remplacement complet de l’air qui n’arrive jamais.
- La durée est celle de la pièce : 20 min dans une buanderie qui sèche vite, une heure dans une chambre où l’air se renouvelle mal.
- Si aérer ne gagnerait presque rien, Hestia ne le demande plus : « Aérer ici : 76 → 74 % seulement », et propose la VMC quand la pièce en a une.
- Le meilleur moment : « Aérez vers 22 h » quand l’air du soir sera nettement plus sec, ou « Encore mieux vers 22 h » en second message.
- Dans « Détails », la ligne « Séchage » dit sur combien d’aérations la pièce a appris.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.6-beta.1 — Mode du chauffage et échelle plus lisible

- La tuile Chauffage indique le mode du thermostat : hors gel, éco, confort, boost…
- Le minimum et le maximum des dernières 24 h sont plus visibles sur l’échelle.
- Toutes les valeurs de l’échelle portent leur unité (« dehors 13,5 °C », « 20 °C »), et la bulle de température garde ses marges et reste dans son cadre.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.5-beta.1 — Fenêtres affichées tout de suite, valeurs stables valables

- La durée d’aération est dans le conseil : « Aérez 3 à 8 min », puis, fenêtre ouverte, « Encore 5 min d’aération » et enfin « Vous pouvez refermer ».
- Une fenêtre qu’on ouvre apparaît sur la carte en une à deux secondes. Seul le conseil attend 30 secondes (au lieu d’une minute) pour ignorer les rebonds du contact, puis se met à jour aussitôt.
- Quand l’air du dehors affiche plus d’humidité que dedans mais asséchera quand même la pièce, la carte l’explique : « Dehors 79 %, mais l’air froid contient peu d’eau : réchauffé chez vous, il ferait 46 % ».
- Beaucoup de capteurs n’envoient une valeur que lorsqu’elle change : une humidité stable pendant la nuit n’est plus considérée comme trop ancienne. Une valeur reste valable tant que son appareil donne signe de vie (par exemple, la température du même capteur).
- Le délai d’expiration passe de 30 minutes à 3 heures ; les pièces réglées sur l’ancien délai sont mises à jour automatiquement.
- Sur la carte, « pas de nouvelle mesure » (capteur silencieux) se distingue désormais d’« indisponible » (capteur perdu).

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.4-beta.1 — Des conseils chiffrés et plus clairs

- Le conseil montre ce qu’il compare : « 60 % d’humidité, l’air du dehors la ferait descendre à 48 % », « 22 °C dedans, 15 °C dehors ».
- La durée d’aération s’affiche sous le pictogramme, avec l’ouvrant à ouvrir : « 4 à 11 min · Fenêtre Ouest ».
- Le bandeau ne montre que des conseils : une source qui ne répond pas reste signalée dans « Détails ».
- « Détails » est allégé : plus de doublon sur les sources, plus de volet « rien à faire ».

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.3-beta.1 — VMC simplifiée, détails d’un appui

- Un appui sur une tuile de mesure, sur la bulle de température, sur le repère « dehors » ou sur une pièce de la carte logement ouvre la fenêtre de détails de Home Assistant (historique, attributs).
- Une entité cachée par Home Assistant n’est plus proposée (par exemple l’interrupteur d’origine d’une VMC changée en ventilateur) : fini les « VMC » en double.
- Une VMC à deux vitesses : « Ventilation (VMC) » propose la position normale, « Vitesse rapide de la VMC (Turbo) » la position rapide ; ce second réglage apparaît une fois la VMC choisie.
- Une VMC n’est plus proposée comme purificateur.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.2-beta.1 — Une VMC mieux reconnue, avec sa grande vitesse

- Le choix « Ventilation (VMC) » ne propose plus que des ventilations : les ventilateurs (sauf les purificateurs) et les interrupteurs dont le nom l’évoque (VMC, ventilation, extraction, aération, hotte). Chauffe-eau, fil pilote et prises n’apparaissent plus, et les deux positions d’une VMC sont visibles.
- Nouveau réglage facultatif « Ventilation · grande vitesse » pour la position Turbo d’une VMC à deux vitesses. La carte indique « grande vitesse » quand elle tourne.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page. Dans la Chambre P : « Ventilation (VMC) » = VMC, « Ventilation · grande vitesse » = VMC Turbo, et retirez la VMC de « Purificateur ».

## 0.9.1-beta.1 — Défilement corrigé, verre dépoli, pièces qui défilent

Même contenu que la 0.9.0-beta.10, renumérotée : GitHub et HACS classaient « beta.10 » avant « beta.9 ».

- Les conseils défilent vraiment : une mesure qui bouge (le CO₂ toutes les quelques secondes) ne relance plus le compte à rebours, qui restait bloqué sur le premier conseil.
- La carte logement fait défiler les pièces qui demandent quelque chose, la plus urgente d’abord, avec le nom de la pièce.
- L’échelle de température est posée sur un verre dépoli, comme la frise de Hestia Weather ; le réglage « Effet de verre » le rend opaque.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.0-beta.9 — Les conseils défilent, la carte se règle

- Quand il y a plusieurs conseils, ils défilent dans le bandeau, un toutes les 4,5 s, comme dans Hestia Weather : le plus important d’abord, une barre par conseil, pause au survol, un appui pour passer au suivant. La carte garde la hauteur du conseil le plus long : plus de saut quand le texte change.
- Le purificateur qui tourne pendant que les particules sont élevées est un remède en cours : les particules seules ne demandent plus d’aérer, et la carte l’indique (« Le purificateur filtre »).
- Nouvelle source « Ventilation (VMC) » dans l’étape Air intérieur, distincte du purificateur : la carte indique qu’elle renouvelle l’air et aide à assécher.
- Réglages de la carte refaits, comme pour Weather : format (complète, tuile, mini), échelle, mesures et détails affichés ou non, dépliés ou repliés au départ, défilement automatique des conseils.

Si une VMC est déclarée comme purificateur dans une pièce, choisissez-la plutôt dans « Ventilation (VMC) ». Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.0-beta.8 — Une panne d’Atmo ne bloque plus le conseil

- Quand l’indice de qualité de l’air extérieur ne répond plus (panne d’Atmo France), le conseil reste valable au lieu de demander de « regarder dehors ». La panne est signalée dans « Détails » et dans l’état technique. La pluie reste une protection : si son capteur se tait, Hestia demande toujours de vérifier.
- La carte distingue une source jamais configurée (« non suivie ») d’une source configurée qui ne répond pas (« indisponible »), et ne présente plus le chauffage comme une source extérieure.
- L’Accueil Hestia signale aussi une source qui ne répond pas, même quand le conseil reste valable.

Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page.

## 0.9.0-beta.7 — Des cartes plus visuelles, une plage de confort qui suit les saisons

- Cartes pièce et logement refaites, moins de texte et plus visuelles : un bandeau avec le geste en quelques mots et sa raison en une ligne, un grand pictogramme, puis une échelle qui place la pièce dans votre plage (valeur actuelle, minimum et maximum des dernières 24 h, température dehors). Sur la carte logement, un point par pièce.
- Les mesures deviennent des tuiles compactes, repliables ; celles qui sortent de votre plage restent visibles et s’encadrent. Les explications passent derrière le bouton « i » et dans « Détails ».
- Même charte que Hestia Weather : tailles de texte, étiquettes, couleurs, contours et sections repliables. La charte est désormais commune aux cartes Hestia.
- La température maximale de confort suit la saison : 24 °C l’hiver, 26 °C l’été par défaut, avec un passage progressif quand la température extérieure moyenne des 7 derniers jours monte de 12 à 20 °C. Sans historique extérieur, la plage enregistrée reste inchangée.
- Nouveau réglage « Température maximum en été » ; les pièces existantes reçoivent 26 °C pour l’été, modifiable. Nouvelle option « Pièce non chauffée » : Hestia ne conseille jamais de la réchauffer.
- Un contact qui s’ouvre moins d’une minute n’est plus compté comme une ouverture.

Bêta en observation. Après mise à jour HACS, redémarrez Home Assistant, puis rechargez la page du navigateur ou de l’application.

## 0.9.0-beta.6 — Formulaires harmonisés

- Les rubriques Weather reprennent les composants de Confort : réglages regroupés par sujet, mêmes titres et espacements, aides nommées en info-bulles.
- Les prévisions, alertes, mesures principales, sources d’air et de pollens et familles d’entités restent visibles. Les détails avancés gardent un repli.
- Les réglages généraux de Confort utilisent des lignes ouvertes à l’intérieur des groupes, sans cadre supplémentaire pour chaque capteur.

## 0.9.0-beta.5 — Affichage du hub

- L’accueil et le menu occupent toute la hauteur disponible dans Home Assistant, y compris lorsque seule une brique est à jour.
- Le menu de configuration d’une pièce s’aligne sur toute la largeur du formulaire.
- Dans Accueil Hestia → Réglages, choix mémorisé entre les couleurs et la police du thème Home Assistant et la palette Hestia. Hestia conserve le suivi du mode clair ou sombre de Home Assistant.
- La section Affichage reste toujours visible, sans repli.

## 0.9.0-beta.4 — Le nouveau hub Hestia

- Interface claire ou sombre, menu par brique et mise en page adaptée au téléphone.
- Vue d’ensemble des pièces avec Configurer. Les six rubriques restent dans la pièce choisie ; l’extérieur partagé est dans Réglages généraux.
- Menu des pièces en deux rangées de boutons avec icônes, sans glissière horizontale.
- Textes d’aide en info-bulles et valeurs par défaut explicites, avec possibilité de les rétablir ; recommandations et erreurs toujours visibles.
- Ouverture de Confort stabilisée : la liste des pièces apparaît sans attendre le bilan technique. Liens directs, retours arrière et brouillons séparés par pièce.
- Le menu ne propose que les briques installées ; l’entrée Hestia du menu Home Assistant peut être masquée dans Réglages Hestia.

Bêta en observation. Les paramètres existants sont conservés. Après mise à jour HACS, redémarrez Home Assistant.

## 0.9.0-beta.3 — Seuils expliqués auprès des capteurs

- Chaque capteur regroupe sa sélection, ses seuils modifiables et une explication repliable avec ses sources (HCSP, OMS, ADEME et fabricant).
- Repères proposés : CO₂ 800 / 1 000 / 1 500 ppm, PM2.5 15 µg/m³, humidité haute 60 %, indice COV 150 pour une IKEA VINDSTYRKA identifiée. La portée de chaque référence est explicitée, notamment moyenne OMS sur 24 h versus mesure ponctuelle et indice COV relatif versus concentration.
- Application unique de ces repères aux pièces existantes, puis conservation des personnalisations. Les seuils COV des modèles non reconnus ne sont pas remplacés par un indice arbitraire.
- « Pièce et confort » devient « Réglages / autres » pour les paramètres transversaux.

Après mise à jour HACS, redémarrez Home Assistant. Vérifiez les repères auprès des capteurs ; ils restent personnalisables.

## 0.9.0-beta.2 — Détection des indices COV IKEA

- Les indices VOC Zigbee2MQTT sans catégorie Home Assistant, notamment la sonde IKEA VINDSTYRKA, sont reconnus à partir de leur identifiant technique ; le nom de l’entité peut être personnalisé.
- Le rattachement à la pièce via l’appareil est conservé, ainsi que le seuil personnel dans l’indice sans unité, sans conversion en concentration.
- Les capteurs Atmo France mal catégorisés, dont les pollens, sont exclus des COV de pièce.

Après mise à jour HACS, redémarrez Home Assistant, puis recherchez à nouveau les capteurs dans la pièce.

## 0.9.0-beta.1 — Soleil, aération et présence

- Volets manuels en bois ou autres, volets reliés à Home Assistant, ou aucun volet : conseils par ouvrant, position inconnue conservée et dérogation suivie lorsqu’elle est renseignée.
- Soleil, luminosité et ombre estimée d’une avancée de toit ; dimensions facultatives.
- Durée d’aération indicative, temps d’ouverture lorsqu’il est connu, tendances de température et risque de buée estimé.
- PM2.5 et COV avec leurs unités et leurs seuils ; purificateur observé sans le confondre avec un renouvellement d’air.
- Présence facultative : une pièce vide reste suivie et les besoins mesurés restent visibles.

Bêta en observation. Hestia conseille et ne commande aucun équipement. Après mise à jour HACS, redémarrez Home Assistant.

- La roue de l’intégration mène directement à l’onglet Confort.

## 0.6.0-beta.2 — Chargement fiable des cartes

- Les cartes du logement et des pièces attendent que Home Assistant soit prêt avant de s’enregistrer, y compris après un rechargement ou à la réouverture des onglets.
- La ressource du tableau de bord est tenue à jour automatiquement ; les anciennes adresses locales encodées sont regroupées.
- Le chargement de secours pour les tableaux de bord en YAML bénéficie de la même protection.

## 0.6.0-beta.1 — Logement et étages

- La carte logement regroupe les pièces par étage Home Assistant, avec moyenne, nombre de mesures disponibles et pièce la plus chaude.
- Une pièce libre peut choisir un étage existant ; les pièces rattachées reprennent automatiquement celui de Home Assistant.
- Les logements de plain-pied gardent une synthèse complète et les possibilités d’aération traversante, sans réglage d’étage obligatoire.
- Les conseils proposent, lorsque les conditions le permettent, deux ouvertures pour l’effet cheminée ou une aération traversante. Ils expliquent les conditions et les limites du passage de l’air.
- Une pièce devenue indisponible reste visible ; sa température est exclue des moyennes. Les changements d’étage se répercutent sur la carte.

Bêta en observation, vérifiée localement. Hestia conseille, sans commander les équipements.

## 0.5.0-beta.9 — Des étapes plus claires dans l’onglet Confort

- Les étapes d’une pièce disent ce qu’on règle : Température et humidité, Fenêtres et portes, CO₂, Chauffage, Pièce et confort.
- En haut de chaque étape, un cadre « À quoi sert cet onglet ? » ; replié, il le reste.
- À l’extérieur, les mesures sont rangées en cadres : Température et humidité, Pluie et vent, Soleil.
- Les mesures du dehors viennent de Hestia Weather ou de vos capteurs ; la qualité de l’air, d’Atmo France ou de Hestia Weather, puis sa zone.
- Une intégration absente est grisée, avec un lien pour l’installer.

## 0.5.0-beta.8 — Le lien avec Hestia Weather des deux côtés

- Hestia Weather affiche lui aussi « Relié à Hestia Confort ».
- Le lien avec Hestia Weather tient dès le démarrage de Home Assistant.

## 0.5.0-beta.7 — La carte visible dans l’application mobile

- La carte Hestia Confort s’affiche aussi dans l’application Home Assistant, même juste après une mise à jour.
- Elle apparaît désormais dans Paramètres → Tableaux de bord → Ressources : c’est Hestia Confort qui la tient à jour, rien à faire.
- Carte toujours invisible dans l’application ? Paramètres → Application compagnon → Dépannage → Réinitialiser le cache du frontend, une seule fois.

## 0.5.0-beta.6 — L’état technique du logement

- L’onglet Confort du panneau Hestia s’ouvre sur l’état du logement, en cadres : ce qui fonctionne, ce qui est à régler, ce qu’on peut améliorer.
- À régler : un capteur d’une pièce ou de l’extérieur qui ne répond pas, avec ce que ça interrompt.
- À améliorer : un capteur disponible dans une pièce, des fenêtres non mesurées, une pièce pas encore suivie.
- Un tableau montre les capteurs de chaque pièce. Le bouton Modifier mène aux pièces ; chaque ligne ouvre la bonne pièce.

## 0.5.0-beta.5 — Le panneau Hestia

- Les réglages sont dans **Hestia** (barre latérale), onglet **Confort**.
- Un onglet **Accueil** montre l’état de Hestia Confort : en bleu si tout est suivi, en orange s’il y a quelque chose à régler.
- Les autres briques Hestia installées (Hestia Weather) y apparaissent aussi.
- L’ancienne adresse et le bouton « Configurer » mènent toujours aux réglages.

## 0.5.0-beta.4 — Fenêtres ouvertes depuis longtemps

- Une fenêtre ouverte (ou fermée) depuis plus de 30 minutes n’est plus considérée comme « à vérifier » : un contact ne parle que quand il change.
- Même chose pour l’état du chauffage.
- L’indice ATMO sous votre seuil ne rend plus le bilan incomplet : Hestia conseille normalement, et bloque toujours au-dessus du seuil.
- La carte nomme la fenêtre en cause (« Fenêtre Ouest ») au lieu de « Contact de fenêtre ».

## 0.5.0-beta.3 — Indice ATMO du matin

- L’indice ATMO du jour, publié la veille, est de nouveau pris en compte le matin : fini « Information incomplète » entre minuit et la mise à jour d’ATMO.
- Quand une mesure n’est pas à jour, la carte dit laquelle (« Qualité de l’air dehors : ne répond pas ou est trop ancienne »).

## 0.5.0-beta.2 — Supprimer une pièce

- Une pièce peut être supprimée depuis son assistant (« Supprimer cette pièce », avec confirmation).
- Vos capteurs et appareils Home Assistant ne sont pas touchés.
- La pièce Home Assistant supprimée est de nouveau proposée dans Mon logement.

## 0.5.0-beta.1 — Hestia Weather et le vent

- Hestia Weather est détecté : un clic reprend sa station pour l’extérieur (avec Hestia Weather 2.1.0b1 ou plus récent).
- Le vent compte : Hestia dit quelles fenêtres ouvrir, au vent et sous le vent, pour faire traverser l’air.
- La pluie poussée par le vent est repérée, même sous un avant-toit.
- Créneaux d’ouverture : « Ouvrez vers 21 h : il fera 18 °C, vent d’ouest ».
- Orage, vigilance orange ou rouge, pluie qui arrive : Hestia conseille de fermer à temps.
- La nuit avant une journée chaude, Hestia propose de stocker le frais.

## 0.4.0-beta.4 — Logement et carte plus visuelle

- Première installation : toutes les pièces détectées sont proposées, cochées, et créées d’un coup.
- Nouvelle carte « Hestia Confort · logement » : la pièce qui demande le plus d’attention, la plus chaude, la plus fraîche, ce qui est ouvert.
- Carte d’une pièce plus visuelle et deux fois plus courte : des bulles de mesures, les ouvrants en pastilles, les explications derrière « Pourquoi ? ».
- Sans indice ATMO ni capteur de pluie, Hestia conseille quand même et précise ce qu’il ne surveille pas.

## 0.4.0-beta.3 — Récapitulatif allégé

- Récapitulatif court : une ligne par catégorie.
- Une seule case à cocher pour confirmer les capteurs à vérifier, au lieu d’une par capteur.
- Une ancienne pièce n’est plus bloquée par des capteurs extérieurs invisibles dans la page.

## 0.4.0-beta.2 — Changer un capteur en un clic

- Chaque capteur choisi peut être remplacé directement, sans le retirer d’abord ; un ouvrant garde son exposition.
- Les anciennes pièces utilisent elles aussi l’extérieur commun dès qu’il est configuré.
- La carte s’appelle « Hestia Confort » dans la liste des cartes.
- Un capteur qui ne répond pas est indiqué plus clairement.

## 0.4.0-beta.1 — Pièces, ouvrants et extérieur

- La carte est incluse dans l’intégration : un seul téléchargement, rien à déclarer.
- Salon proposé au départ ; pièces libres, sans pièce Home Assistant.
- Choix des capteurs avec le sélecteur de Home Assistant.
- Exposition, type et abri de chaque fenêtre ou porte.
- L’extérieur s’applique à toutes les pièces ; rafales et ensoleillement ajoutés.
- Pluie : seuls les ouvrants exposés sont à fermer.
- Nouveaux conseils : rafales fortes, gel, chauffage en marche, soleil qui entre par une fenêtre ouverte.
- Les capteurs confirmés ne sont plus redemandés.

## 0.3.0-beta.3 — Mon logement

- Configuration dans une page Hestia Confort de la barre latérale, avec Salon proposé et ajout des pièces Home Assistant.
- Parcours par catégories, propositions expliquées, correction manuelle et récapitulatif avant enregistrement.
- Données extérieures communes sur activation explicite par pièce ; pluie actuelle et indice ATMO quotidien expliqués.
- Les alias de capteurs, portes d’appareils et diagnostics ne sont plus sélectionnés automatiquement. Les choix existants et champs volontairement vides sont conservés.

# Historique

## 0.3.0-beta.2 — deuxième préversion de test

- Assistant par catégories, détection par pièce et choix manuels.
- Récapitulatif avant enregistrement et modification par catégorie.
- Recherche explicite conservant les choix existants.
- Température extérieure facultative et chauffage non configuré explicite.

## 0.2.0 — alpha

Première publication de test. Observation et conseils par pièce, sans commande d’équipement. Weather, prévisions et coordination chauffage restent à raccorder.
