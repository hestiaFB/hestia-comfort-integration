# Moteur de conseil — Changelog

Le moteur de conseil de Hestia Confort a son propre numéro de version, à part de celui de Confort. Il est affiché dans « Versions et liens » et écrit dans chaque conseil gardé.

Chaque version de Confort dit quelle version du moteur elle contient. Le détail technique de chaque version est dans [docs/dev/MOTEUR-VERSIONS.md](docs/dev/MOTEUR-VERSIONS.md).

## 3.11.0 — 6 novembre 2026

Pas encore dans une version de Confort.

### Corrections

- Le réglage « Allergie aux pollens » compte de nouveau. Les jours de pollens élevés :
  - pour l'humidité ou le CO₂, l'aération reste conseillée à toute heure, aussi longue qu'il le faut ;
  - pour rafraîchir ou chasser une odeur, elle attend le matin après le réveil, ou l'heure qui suit la pluie, et dure 10 minutes au plus ;
  - une fenêtre ouverte depuis 10 minutes : « Refermez », sauf si elle aide pour l'humidité ou le CO₂ ;
  - pas de fenêtre ouverte conseillée pour la nuit.
- « Bon à savoir » dit quand les pollens sont élevés, et quand la pluie vient de laver l'air.

## 3.10.0 — 6 novembre 2026

Dans Confort 3.0.0.

### Nouveautés

- Une aération conseillée qui ne fait pas l'effet prévu est dite clairement après 10 minutes : « L'aération ne fait pas l'effet prévu : 74 % → 75 % en 10 min. Refermez pour ne pas empirer. » Hestia le note pour la prochaine fois.
- Les conseils disent à quel point Hestia en est sûre : affirmatif quand la pièce l'a déjà montré, « devrait » quand c'est probable, « pourrait…, à vérifier » quand ce n'a jamais été vérifié dans la pièce.

### Améliorations

- Une fenêtre ouverte est jugée à part sur la chaleur et sur l'humidité : une pièce qui se refroidit peu mais sèche bien n'est plus vue comme une pièce qui ne sèche pas.
- Ce qu'une fenêtre peut faire est borné par la physique : un apprentissage trompé par quelques jours étranges ne peut plus prévoir une chambre à 12 °C après une aération.

## 3.9.6 — 6 novembre 2026

Dans Confort 3.0.0.

### Corrections

- « Laissez ouvert encore 45 min » descend bien : 40, 35… Il restait bloqué quand Hestia recalculait souvent.
- « La pluie arrive » ne s'allume et ne s'éteint plus toutes les quelques minutes quand la prévision hésite.

## 3.9.5 — 5 novembre 2026

Dans Confort 3.0.0.

### Nouveautés

- Chaque chauffage a son type : convecteur, panneau rayonnant, radiateur à inertie ou à eau, plancher chauffant, poêle à bois, poêle à granulés, climatisation réversible.
- Un radiateur à inertie ou un plancher continue de chauffer après l'arrêt et remonte lentement : une aération pendant la chauffe compte ce qu'elle coûte vraiment.
- Une fenêtre ouverte n'éteint pas un poêle à bois ; une climatisation réversible coûte environ trois fois moins de courant.

## 3.9.4 — 5 novembre 2026

Dans Confort 3.0.0.

### Corrections

- Après une aération, Hestia ne redemande plus d'aérer pour l'humidité avant d'avoir vu son effet, une heure après la fermeture.
- « Laissez ouvert encore 10 min » ne repart plus à 15 min, et « Refermez » ne redevient plus « Laissez ouvert encore… ».
- « Refermez » s'affiche toujours au bandeau, même quand son effet n'est pas encore prouvé : la fenêtre ne reste plus ouverte toute la nuit sous « Rien à faire ».

## 3.9.3 — 5 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- Fenêtre ouverte, et la refermer maintenant ferait nettement moins bien : la carte dit « Laissez ouvert » et ce que l'on y gagne, en bleu, au lieu de « Rien à faire ».

## 3.9.2 — 5 novembre 2026

Dans Confort 3.0.0.

### Corrections

- Après « Ouvrez », une fois la fenêtre ouverte, la carte dit « Laissez ouvert » et ce que l'on y gagne, au lieu de « Rien à faire ».

## 3.9.1 — 5 novembre 2026

Dans Confort 3.0.0.

### Corrections

- « Rien à faire » et « Volet à fermer » ne s'affichent plus ensemble : le volet suit le conseil de la carte.
- « Baissez le volet ce soir » n'est plus dit pour un gain minuscule (0,1 kWh).

## 3.9.0 — 5 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- « Volets fermés quand vous partez » : une sortie de moins de 2 heures ne compte plus. Les volets restent ouverts pour Hestia, et le soleil qui entre est compté.

## 3.8.0 — 5 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- Station contre un mur ou sur le toit, au soleil : Hestia prend la température que retient Hestia Weather, pas celle du mur chaud.
- Station abritée du vent d'un côté : la rafale prévue compte, une fenêtre n'est pas conseillée grande ouverte par vent fort.
- Pluviomètre sous un arbre ou un avant-toit : une pluie annoncée reste crue, même sans goutte mesurée.

## 3.7.0 — 5 novembre 2026

Dans Confort 3.0.0.

### Nouveautés

- « Vos habitudes » : quelques questions sur ce que les capteurs ne voient pas.
- Les volets à la main fermés quand vous partez, la nuit ou l'été au soleil : Hestia ne compte plus le soleil derrière eux.
- La maison vide en semaine, quand il n'y a pas d'alarme : pas de conseil pendant ces heures.
- Le lever du week-end : ni conseil ni lumière avant.

### Améliorations

- Le vitrage simple, double ou triple compte : la buée, le soleil qui entre, la chaleur perdue.
- « Votre maison » : vitrage, volets, hauteur, murs et plage repris par chaque fenêtre et chaque pièce.

## 3.6.0 — 5 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- Une fenêtre sous une avancée ou un balcon reçoit le soleil selon la saison : en hiver, le soleil bas passe dessous et entre dans la pièce ; en été, le soleil haut reste au-dessus. Avant, Hestia comptait toujours un tiers du soleil.
- La profondeur de l'avancée et son écart avec le haut de la fenêtre, réglés dans « Avancée au-dessus », sont pris en compte.

## 3.5.0 — 5 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- L'apprentissage de la nuit est environ quatre fois plus rapide : Hestia arrête de chercher dès qu'il n'apprend plus rien. Il reste aussi juste.
- Ce qu'Hestia apprend la nuit est gardé quand il prévoit la veille aussi bien qu'avant, et plus seulement quand il fait mieux : il suit mieux les derniers jours au lieu de rester sur les premiers.

## 3.4.0 — 5 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- Une pluie annoncée « dans quelques minutes » qui ne tombe toujours pas au bout de 45 minutes n'empêche plus d'aérer, si votre station mesure la pluie. Elle compte de nouveau dès la première goutte.

### Corrections

- Quand vous ouvrez la fenêtre après « Aérez 5 min », la carte dit « Laissez ouvert encore 5 min » au lieu de « Rien à faire — Ouverte ou fermée ». Pareil pour une aération « À essayer ».
- Un capteur d'air (CO₂, particules, COV) dont Hestia n'a encore rien appris ne fait plus apparaître de geste dans le bandeau : il est proposé « À essayer ».

## 3.3.0 — 4 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- L'ombre de la station (une maison, un arbre qui cache le soleil à son capteur) est maintenant apprise par Hestia Weather, sur les trois derniers mois de la station : elle est connue dès la première nuit, au lieu d'attendre des semaines de beau temps.
- Les positions du soleil pas encore vues prennent la valeur de leurs voisines, ou l'ombre que vous avez indiquée dans Hestia Weather.
- « Le dehors » montre où en est l'apprentissage : « 31 positions sur 161 ».

## 3.2.0 — 4 novembre 2026

Dans Confort 3.0.0.

### Nouveautés

- Avec ha-chauffage ou Scheduler (en bêta), Hestia connaît l'heure du prochain changement de chauffage : « Chauffage prévu à 17 h : 20 °C visés ».
- Les prévisions de la pièce suivent le planning : passé 17 h, le chauffage remonte à 20 °C dans les calculs, comme dans la maison.
- Le prochain changement est donné même quand la pièce n'a pas froid : la carte le place dans « À venir ».
- Un chauffage éteint pour l'été n'annonce plus les changements de son planning, sauf celui qui le rallume ; une pause du thermostat (fenêtre ouverte) ne l'efface pas.
- Les plannings Scheduler sont reconnus à leur contenu, même recopiés d'un autre Home Assistant.
- L'humidité du dehors dite en une phrase simple : « Dehors, l'air est plus sec qu'ici : aérer assèche ».

### Corrections

- Une porte-fenêtre « abritée par une avancée ou un balcon » peut rester ouverte sous la pluie : plus de « Refermez, il pleut ». Seules des rafales qui poussent la pluie de son côté la font refermer.

## 3.1.1 — 4 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- « À essayer » ne change plus à chaque calcul : le geste proposé reste tant qu'il est presque aussi bon, et revient tel quel après une rafale.
- L'heure annoncée pour l'humidité ne bouge plus toutes les cinq minutes : elle est donnée au quart d'heure, ou à l'heure de fin pour une fenêtre laissée ouverte.

### Corrections

- Le conseil d'une pièce ne s'arrête plus quand la pluie ou les rafales font refermer une fenêtre qui vient d'être ouverte.

## 3.1.0 — 4 novembre 2026

Dans Confort 3.0.0.

### Nouveautés

- Chaque geste reçoit une note, une heure après sa fin : une aération, la VMC en vitesse rapide, le purificateur.
- La note compare ce qui s'est passé à ce qui se serait passé sans le geste : « + » il a fait ce qui était annoncé, « 0 » il a fait peu, « − » il a fait l'inverse.
- Chaque nuit, Hestia corrige ce qu'elle sait d'une fenêtre, de la VMC ou du purificateur à partir de leurs dernières notes, sur l'humidité, la chaleur et l'air.
- « Ce que Hestia sait de votre maison » montre les dernières notes de chaque effet et la correction de la nuit.

### Améliorations

- Rien n'est noté si autre chose s'est passé pendant le geste ou l'heure qui suit : une fenêtre rouverte, la VMC ou le purificateur, une douche, la cuisine.
- Deux gestes ratés d'affilée, et le conseil passe en « À essayer » au lieu du bandeau.
- La VMC et le purificateur apprennent leur vrai débit, même quand vous ne le connaissez pas.

## 3.0.6 — 3 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- L'humidité gagnée par une aération se dit une heure après avoir refermé : les murs et la literie la rendent vite à l'air.
- Si rien ne reste, la carte dit « l'humidité baisse pendant l'aération, puis revient ».
- Deux aérations qui n'ont presque rien changé, et « Aérez » passe en « À essayer ».

## 3.0.5 — 3 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- Une fenêtre à peine entrouverte est reconnue au bout de dix minutes : le conseil suit ce qu'elle fait vraiment.
- « Bon à savoir » le dit : « Ouverte depuis 19 h 19 : 18,2 → 18,1 °C, 67 → 69 % : elle renouvelle peu l'air ».

## 3.0.4 — 3 novembre 2026

Dans Confort 3.0.0.

### Corrections

- « Cette nuit, pensez à ouvrir » ne s'affiche plus si votre foyer n'ouvre pas la nuit.

### Améliorations

- Quand l'humidité est en jeu, « Bon à savoir » dit l'eau de l'air de dehors, pas seulement son % : « Dehors 78 % à 9,9 °C, mais moins d'eau qu'ici ».

## 3.0.3 — 3 novembre 2026

Dans Confort 3.0.0.

### Améliorations

- L'humidité se dit en valeur, à l'heure où le geste fait le plus : « Vers 19 h 35 : 56 % d'humidité au lieu de 67 % ».
- « Optimisé par l'apprentissage » ne s'affiche que pour un effet que la pièce a vraiment montré.

## 3.0.2 — 3 novembre 2026

Dans Confort 3.0.0.

### Corrections

- « Aérez plus tard » ne recule plus sans fin : il ne vient que si le dehors sera vraiment meilleur.
- « Laissez ouvert encore 10 min » dit le bon gain : celui de rester ouvert, pas celui d'une fenêtre oubliée trois heures.
- Une chambre ne croit plus recevoir toute la chaleur du poêle avant sa première nuit.

### Améliorations

- Une surface déclarée après coup garde ce qui a été appris sur la chaleur.
- L'apprentissage de nuit est bien plus rapide.

## 3.0.1 — 3 novembre 2026

Dans Confort 3.0.0.

### Corrections

- Une heure annoncée (« Aérez 5 min vers 17 h 15 ») ne recule plus à chaque calcul.
- Deux pièces au même air comptent leurs deux surfaces.
- Une surface déclarée après coup est prise en compte : le CO₂ ne monte plus trop vite dans une grande pièce.

## 3.0.0 — 3 novembre 2026

Dans Confort 3.0.0.

### Nouveautés

- Un nouveau moteur de conseil : pour chaque pièce, il compare plusieurs gestes possibles et garde celui qui aide le plus.
- Il suit la chaleur, l'humidité, le CO₂, les particules et les COV de chaque pièce.
- Il ne propose jamais d'ouvrir sous la pluie, par grand vent, pendant une vigilance, une absence ou le gel.
- Il suit la consigne du thermostat et le poêle, et dit « Coupez le poêle » quand il chauffe trop longtemps.
- Un geste prévu plus tard dit son heure : « Aérez 15 min vers 13 h 50 ».
- Il apprend chaque nuit comment chaque pièce réagit.
