# Moteur de conseil — Changelog

Le moteur de conseil de Hestia Confort a son propre numéro de version, à part de celui de Confort. Il est affiché dans « Versions et liens » et écrit dans chaque conseil gardé.

Chaque version de Confort dit quelle version du moteur elle contient. Le détail technique de chaque version est dans [docs/dev/MOTEUR-VERSIONS.md](docs/dev/MOTEUR-VERSIONS.md).

## 3.2.0 — 4 novembre 2026

Pas encore dans une version de Confort.

### Nouveautés

- Avec ha-chauffage ou Scheduler (en bêta), Hestia connaît l'heure du prochain changement de chauffage : « Chauffage prévu à 17 h : 20 °C visés ».
- Les prévisions de la pièce suivent le planning : passé 17 h, le chauffage remonte à 20 °C dans les calculs, comme dans la maison.
- Le prochain changement est donné même quand la pièce n'a pas froid : la carte le place dans « À venir ».
- Un chauffage éteint pour l'été n'annonce plus les changements de son planning, sauf celui qui le rallume ; une pause du thermostat (fenêtre ouverte) ne l'efface pas.
- Les plannings Scheduler sont reconnus à leur contenu, même recopiés d'un autre Home Assistant.

## 3.1.1 — 4 novembre 2026

Pas encore dans une version de Confort.

### Améliorations

- « À essayer » ne change plus à chaque calcul : le geste proposé reste tant qu'il est presque aussi bon, et revient tel quel après une rafale.
- L'heure annoncée pour l'humidité ne bouge plus toutes les cinq minutes : elle est donnée au quart d'heure, ou à l'heure de fin pour une fenêtre laissée ouverte.

### Corrections

- Le conseil d'une pièce ne s'arrête plus quand la pluie ou les rafales font refermer une fenêtre qui vient d'être ouverte.

## 3.1.0 — 4 novembre 2026

Pas encore dans une version de Confort.

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

### Améliorations

- L'humidité gagnée par une aération se dit une heure après avoir refermé : les murs et la literie la rendent vite à l'air.
- Si rien ne reste, la carte dit « l'humidité baisse pendant l'aération, puis revient ».
- Deux aérations qui n'ont presque rien changé, et « Aérez » passe en « À essayer ».

## 3.0.5 — 3 novembre 2026

### Améliorations

- Une fenêtre à peine entrouverte est reconnue au bout de dix minutes : le conseil suit ce qu'elle fait vraiment.
- « Bon à savoir » le dit : « Ouverte depuis 19 h 19 : 18,2 → 18,1 °C, 67 → 69 % : elle renouvelle peu l'air ».

## 3.0.4 — 3 novembre 2026

### Corrections

- « Cette nuit, pensez à ouvrir » ne s'affiche plus si votre foyer n'ouvre pas la nuit.

### Améliorations

- Quand l'humidité est en jeu, « Bon à savoir » dit l'eau de l'air de dehors, pas seulement son % : « Dehors 78 % à 9,9 °C, mais moins d'eau qu'ici ».

## 3.0.3 — 3 novembre 2026

### Améliorations

- L'humidité se dit en valeur, à l'heure où le geste fait le plus : « Vers 19 h 35 : 56 % d'humidité au lieu de 67 % ».
- « Optimisé par l'apprentissage » ne s'affiche que pour un effet que la pièce a vraiment montré.

## 3.0.2 — 3 novembre 2026

### Corrections

- « Aérez plus tard » ne recule plus sans fin : il ne vient que si le dehors sera vraiment meilleur.
- « Laissez ouvert encore 10 min » dit le bon gain : celui de rester ouvert, pas celui d'une fenêtre oubliée trois heures.
- Une chambre ne croit plus recevoir toute la chaleur du poêle avant sa première nuit.

### Améliorations

- Une surface déclarée après coup garde ce qui a été appris sur la chaleur.
- L'apprentissage de nuit est bien plus rapide.

## 3.0.1 — 3 novembre 2026

### Corrections

- Une heure annoncée (« Aérez 5 min vers 17 h 15 ») ne recule plus à chaque calcul.
- Deux pièces au même air comptent leurs deux surfaces.
- Une surface déclarée après coup est prise en compte : le CO₂ ne monte plus trop vite dans une grande pièce.

## 3.0.0 — 3 novembre 2026

### Nouveautés

- Un nouveau moteur de conseil : pour chaque pièce, il compare plusieurs gestes possibles et garde celui qui aide le plus.
- Il suit la chaleur, l'humidité, le CO₂, les particules et les COV de chaque pièce.
- Il ne propose jamais d'ouvrir sous la pluie, par grand vent, pendant une vigilance, une absence ou le gel.
- Il suit la consigne du thermostat et le poêle, et dit « Coupez le poêle » quand il chauffe trop longtemps.
- Un geste prévu plus tard dit son heure : « Aérez 15 min vers 13 h 50 ».
- Il apprend chaque nuit comment chaque pièce réagit.
