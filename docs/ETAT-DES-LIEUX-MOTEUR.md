# État des lieux du moteur de conseil — 16 novembre 2026

Demande de Frank (16 nov.) : « Tous les jours on a le même type d'erreur yoyo. […] analyse profondément le moteur, fais
un état des lieux de la maison sur 10 jours, et propose une amélioration nette du moteur pour qu'on en finisse et qu'on
publie une version stable. »

## 1. En bref

- Le moteur **calcule** bien : ses scénarios (« si on aère 20 min, l'humidité finit à 63 % ») sont le plus souvent
  sensés.
- Il **n'a pas de mémoire de ce qu'il a dit**. Toutes les 5 minutes, il recalcule le conseil de zéro, puis une série
  de rustines essaie de garder le conseil précédent : minuteries de 30 min, marges, sujet tenu…
- Quand une minuterie expire, le conseil retombe ; 5 minutes plus tard, le calcul le fait revenir. **C'est le yoyo.**
  Chaque correctif quotidien a ajouté une rustine de plus, et la suivante a trouvé une autre fente : 42 yoyos
  consignés depuis le 31 octobre, environ 35 mécanismes de tenue, aucun testé pour lui-même.
- Proposition, revue avec Frank le 16 au soir :
  - **conseiller par créneaux** (matin, après-midi, soir, nuit), au meilleur moment appris de chaque pièce, plutôt
    qu'à chaque instant ;
  - garder les **urgences** à toute heure, sur mesure ;
  - juger chaque pièce sur **sa propre normale** ;
  - confier la mémoire de ce qui est dit à **un seul « tableau d'affichage »**, qui ne change d'avis que sur un
    événement, jamais quand une minuterie expire.
- Preuve avant la stable : rejouer les 10 jours réels de la maison, ancien et nouveau côte à côte, avec des critères
  chiffrés.

## 2. Ce que disent 10 jours de la maison (6 → 16 novembre)

Sources :
- titres du conseil de la maison, archivés par le labo ;
- fenêtres de la maison ;
- journal du moteur (maison : 24 h ; labo, même moteur sur les mêmes mesures : 10 jours).

### Le titre du conseil

| | 10 jours | par jour |
|---|---:|---:|
| Changements de titre (7 pièces) | 189 | ≈ 19 |
| dont **yoyos** : le titre part et revient en 5 à 60 min, sans fenêtre touchée | **43** | ≈ 4 |
| dont éclairs de moins de 5 min (souvent un contact de fenêtre) | 16 | ≈ 2 |
| dont réponses à une fenêtre ouverte ou fermée (normal) | 32 | ≈ 3 |

Aucun progrès d'une version à l'autre : 7 yoyos le 13, 6 le 14, 6 le 16.

| Pièce | changements | yoyos |
|---|---:|---:|
| Salon · Cuisine | 65 | 10 |
| Chambre A | 40 | 10 |
| Chambre P | 26 | 12 |
| Chambre M | 23 | 5 |
| Salle de bain | 13 | 2 |
| Chambre AL | 12 | 3 |
| Buanderie | 10 | 1 |

### Les aérations proposées

- **47 aérations proposées en 10 jours, 8 suivies (17 %).**
- Les 39 autres ont été retirées sans que personne n'ait rien fait, **au bout de 35 min en médiane**.
- Au labo (même moteur, mêmes mesures), sur 29 gestes retirés fenêtre fermée, **16 l'ont été entre 25 et 36 min** :
  c'est la minuterie de 30 min (`HOLD_MINUTES`) qui expire.
  - 19 passent en « Rien à faire — À essayer : le même geste » ;
  - 10 passent en « aucun geste ne ferait vraiment mieux ».
  - Puis le même geste revient 5 à 25 min plus tard.

Exemple du 16 novembre, Chambre A, fenêtre jamais ouverte :

| Heure | Titre affiché |
|---|---|
| 7 h 03 | Aérez 15 min |
| 7 h 33 | Rien à faire (« À essayer : Aérez 15 min ») |
| 7 h 38 | Aérez 20 min |
| 8 h 13 | Rien à faire (« À essayer ») |
| 8 h 38 | Aérez 25 min |
| 9 h 43 | Rien à faire |

Le soir, même chose de 17 h 38 à 20 h 20.

### La phrase sous « Rien à faire »

- Son sujet change **66 fois en 24 h** (≈ 9 fois par pièce). Elle passe de « Humidité 70 % à 23 h » à « Aucun geste ne
  ferait vraiment mieux : 18,8 °C à 22 h », puis à « Fermée : 18,3 °C à 10 h »…
- Une phrase calculée pendant une ouverture de quelques secondes (Chambre A, 20 h 20) est restée affichée 30 min, alors
  qu'elle était fausse : « repasse seule sous 60 % vers 20 h 35 » à 71 %.

### Le rythme des versions

- 37 versions du moteur en 13 jours (3.0.0 le 3 nov. → 3.17.1).
- La plus longue, la 3.17.0, a tourné 46 h. Aucune n'a tenu 2 jours sans retouche.

## 3. Pourquoi : le moteur

### Les rustines, en chiffres

Inventaire fait dans les bilans, les notes de version, les tests et les commentaires du code :

- **42 yoyos consignés** depuis le 31 octobre.
- Chacun a reçu son correctif. Le code compte aujourd'hui **environ 35 mécanismes de tenue** (délais, marges,
  bandes, arrondis). **11 d'entre eux s'arrêtent sur une minuterie**, et c'est à ce moment-là que le conseil
  retombe.
- **Aucun de ces mécanismes n'a de test à lui** : on ne sait pas s'ils tiennent ensemble.
- **4 correctifs ont eux-mêmes créé une erreur** :
  - la pluie tenue 30 min → faux « Refermez : il pleut » (14 nov.) ;
  - la phrase tenue 30 min → phrase fausse à 71 % (16 nov.) ;
  - le seuil du soir doublé → aération utile cachée (16 nov.) ;
  - l'aération « plus tard » écartée → son heure oubliée d'un calcul à l'autre.

### Les familles de yoyo

| Famille | Cas | État |
|---|---:|---|
| « Aérez » ↔ « Rien à faire — À essayer » | 5 | **toujours ouvert** (16 nov.) |
| Durée qui change (5, 10… 30 min) | 6 | rustiné 5 fois |
| Heure « vers … » qui recule | 6 | rustiné 6 fois |
| Phrase : sujet, chiffres, texte « À essayer » | 7 | **toujours ouvert** (15 et 16 nov.) |
| « Laissez ouvert » ↔ « Refermez », passages par la porte | 6 | rustiné 6 fois |
| Sécurité qui clignote (pluie, gel) | 5 | calme depuis le 15 |
| Pastille | 3 | calme depuis le 10 |
| Geste non suivi reproposé | 4 | **toujours ouvert** (Chambre P, A, M) |
| Ancien conseil au redémarrage | 1 | réglé |

### Quatre défauts de construction

1. **Le calcul repart de zéro toutes les 5 min.** Ce qui a été dit n'est retrouvé qu'à travers des « tenues » qui
   expirent. Résultat : **30 min** revient partout. Le ping-pong de la Chambre A, le sujet de la phrase, le gel la
   nuit et « Ouvrez » en Chambre P tournent tous sur 30 min.
2. **« Aérez » et « À essayer » ne tiennent pas pareil.**
   - « Aérez » est tenu 30 min. Ensuite, il doit de nouveau franchir tous les seuils.
   - « À essayer » est tenu sans limite, pour un demi-gain.
   - Un geste juste sous le seuil de confiance passe donc de l'un à l'autre toutes les 30 min. C'est exactement la
     Chambre A le 16.
3. **La stabilité est répartie sur quatre étages**, chacun avec sa propre mémoire : le geste, l'essai, la phrase, la
   pastille. Personne ne voit l'ensemble, et chaque correctif d'un étage ouvre une fente dans un autre.
4. **« Ça fait une vraie différence » se mesure au bout des 3 prochaines heures.** Ce bout avance avec l'horloge, donc
   le verdict bouge à chaque calcul, même quand rien ne change dans la pièce.

## 4. La proposition : le conseil par créneaux (moteur 3.18.0)

Frank, 16 nov. : « dans la vie de tous les jours on ne regarde pas l'application pour savoir si à un instant T il faut
ouvrir ou pas ».

Ce que fait vraiment la famille (10 jours de contacts) :
- 2 à 5 vraies aérations (plus de 3 min) par pièce en 10 jours ;
- presque toujours vers 9 h, 15 h-16 h ou 19 h ;
- souvent plus d'une heure, parce que l'air dehors est doux ces jours-ci et ne refroidit pas la maison.

Le moteur, lui, a proposé 47 aérations à toute heure.

### 4.1 Quatre familles de conseils

| Famille | Quand | Exemples |
|---|---|---|
| **Créneau** | une fois par créneau, au meilleur moment | « Aérez 45 min vers 14 h 30 », « Fermez les volets vers 17 h 30 » |
| **Urgence** | à toute heure, sur mesure | « Aérez 10 min : CO₂ 1 450 ppm » |
| **Réponse à un geste** | quand une fenêtre vient d'être ouverte | « Laissez ouvert encore 20 min », « Refermez vers 15 h 10 » |
| **Sécurité** | à toute heure | « Gardez fermé : il pleut », « Coupez le poêle » |

### 4.2 Les créneaux et le meilleur moment

Les quatre créneaux du jour, calés sur les heures de lever et de coucher, réglables :

| Créneau | Par défaut | Exemples de gestes |
|---|---|---|
| Matin | du lever à 12 h | aérer les chambres, ouvrir les volets à l'est |
| Après-midi | de 12 h à 18 h | aérer au plus doux et au plus sec (hiver), fermer les volets au soleil (été) |
| Soir | de 18 h au coucher | fermer les volets pour garder la chaleur, aérer avant de dormir |
| Nuit | du coucher au lever | dit le soir (« Cette nuit, pensez à… ») : ouvrir pour rafraîchir l'été |

Pour chaque pièce et chaque créneau, **au plus un geste** pour les fenêtres et un pour les volets :

1. **Le calcul** : le jumeau simule tout le créneau avec la prévision et trouve le moment et la durée qui font le
   plus de bien. La durée suit le dehors :
   - longue par temps doux, comme vous le faites (45 min, 1 h) ;
   - courte par grand froid.
2. **L'apprentissage** : chaque aération faite est mesurée (ce qu'elle a vraiment donné contre ce qui était promis)
   et rangée par pièce et par créneau. Après quelques semaines, on aura par exemple : « en Chambre A, l'aération de
   l'après-midi fait trois fois plus que celle du matin ». Le créneau qui marche le mieux est préféré, et la promesse
   est corrigée du même coup.
3. **Les habitudes** : le moteur voit quand la famille ouvre vraiment. Un créneau où personne n'ouvre jamais n'est
   proposé que s'il est nettement le meilleur.

Le geste d'un créneau est **fixé au début du créneau et ne bouge plus**.
- Entre deux, la carte annonce le suivant : « Rien à faire — prochain moment : aérer vers 14 h 30 ».
- Pas suivi : il s'efface à la fin du créneau, sans relance.

### 4.3 La normale de chaque pièce

- Chaque pièce a sa propre normale, apprise sur ses 14 derniers jours. La Chambre P vit à 75-80 % d'humidité, la
  Chambre M vers 65 %.
- On ne cherche pas à rendre une pièce comme les autres. Les conseils visent ce que **cette pièce** peut atteindre.
  - En Chambre P, une aération est proposée quand elle la ramène nettement sous sa normale à elle (par exemple de
    86 % après une douche à 77 %), pas pour viser 60 %.
- Ce qui est chronique devient un **conseil du logement**, sur la carte « Mon logement », dit une fois et pas chaque
  jour. Par exemple :
  « Chambre P : 78 % en moyenne depuis 30 jours. Ses murs sont froids : aérer ne suffira pas. Pistes : un
  déshumidificateur, un chauffage doux et continu. »

### 4.3 bis La carte d'identité de chaque pièce

Frank, 16 nov. : « apprendre la globalité de la pièce sur tous les capteurs qu'on connaît […] une sorte de carte
d'identité de la pièce, qui nous permet de comprendre cette pièce et donner les meilleurs conseils possibles ».

Chaque nuit, avec l'apprentissage, le moteur refait la carte d'identité de chaque pièce. Chaque ligne dit d'où elle
vient (mesurée, apprise, déclarée) et sur combien de jours.

| Rubrique | Ce qu'elle dit (exemple) | D'où |
|---|---|---|
| **Sa normale** | « 19,5 °C et 77 % d'humidité en moyenne ; le matin 79 %, l'après-midi 75 % » | mesures des 14 derniers jours, par créneau |
| **Son isolation** | « perd 0,4 °C par heure quand il fait 10 °C de moins dehors » | jumeau de chaleur |
| **Son inertie** | « suit le dehors avec 6 h de retard » | mesures (retard intérieur / extérieur) et jumeau |
| **Son chauffage** | « le radiateur la remonte de 1 °C en 40 min » ; « le poêle du salon lui donne 1,5 °C » | jumeau, chauffage de la maison |
| **Le soleil** | « +1,2 °C par après-midi de soleil (façade sud) » | jumeau, orientation déclarée |
| **Ses murs** | « murs plus froids que l'air de 1,5 °C : ils gardent l'eau » | jumeau d'eau et de chaleur |
| **Ce que fait une aération** | « 20 min à 10 °C dehors : −0,8 °C et −7 points d'humidité ; l'humidité remonte de 4 points dans l'heure » | aérations mesurées et jumeau |
| **Ses sources** | « +6 points après la douche, +3 points la nuit (2 personnes) » ; « CO₂ 1 200 ppm le matin » | jumeaux d'eau et de CO₂ |
| **Ses habitudes** | « ouverte 2 fois par semaine, l'après-midi, 1 h en moyenne » | contacts de fenêtre |
| **Ses appareils** | « VMC rapide : −5 points en 1 h » | jumeau, appareils déclarés |
| **Ce qu'on ne sait pas encore** | « son humidité est encore mal comprise : promesses à vérifier » | contrôle du jumeau contre les mesures |
| **Ce qui est chronique** | « humide toute l'année : murs froids (ancien garage) » → conseil du logement | normale comparée aux repères |

À quoi elle sert :
- **le moteur la lit** : la normale fixe les urgences, le meilleur créneau, ce que la pièce peut atteindre ;
- **la famille la lit** : on comprend pourquoi la Chambre P est humide et pourquoi on ne lui demande pas l'impossible.
- Chaque chiffre du jumeau est **contrôlé contre une mesure directe**. Par exemple, l'inertie apprise est comparée au
  refroidissement réellement mesuré les nuits sans chauffage. S'ils ne concordent pas, la ligne le dit, au lieu d'en
  tirer des conseils faux.

### 4.4 Les urgences, les réponses, la sécurité

**Urgences**, à toute heure, déclenchées par une mesure :
- CO₂ au-dessus de 1 400 ppm, particules fines au-dessus de 25 µg/m³, COV élevé ;
- humidité nettement au-dessus de la normale de la pièce (8 points ou plus), avec un air dehors plus sec ;
- un geste en cours qui dégrade le confort : fenêtre ouverte et pièce qui passe sous son minimum → « Refermez ».

Une urgence a un seuil d'entrée et un seuil de sortie plus bas : par exemple, elle entre à 1 400 ppm de CO₂ et sort
sous 1 100 ppm. Elle est dite une fois et ne clignote pas. Si elle n'est pas suivie, elle passe en pause 2 h, sauf
si la mesure empire nettement.

**Réponses à un geste** : une fenêtre ouverte depuis plus d'1 min.
- La carte ne dit quelque chose que si c'est vraiment utile : « Laissez ouvert encore 20 min : 62 % au lieu de
  70 % », ou « Refermez vers 15 h 10 ».
- Sinon, elle dit « Rien à faire ».
- Si l'ouverture dégrade le confort, la réponse devient une urgence.

**Sécurité** : pluie, rafales, absence, poêle. Inchangée.

### 4.5 Les notifications sur le téléphone

- Chaque nouveau conseil d'un créneau, chaque urgence et chaque alerte de sécurité émet un événement Home Assistant
  (`hestia_comfort_conseil`), avec la pièce, le titre, la phrase et le niveau.
- Une automatisation peut déjà l'envoyer sur l'application du téléphone.
- Ensuite, dans Réglages, on choisit :
  - le téléphone ;
  - les niveaux envoyés (urgences seulement, ou aussi le plan des créneaux) ;
  - jamais la nuit ;
  - au plus 3 par jour par défaut.

## 5. Le tableau d'affichage (la mémoire de ce qui est dit)

On sépare deux métiers aujourd'hui mélangés :

1. **Le calcul** (inchangé) : toutes les 5 min, les scénarios disent ce que chaque geste donnerait, et de combien il
   ferait mieux que « rien ». Le calcul ne sait plus rien de ce qui est affiché : plus de `previous`, `held`, `tried`.
2. **Le tableau d'affichage** (nouveau, un seul fichier `advisor/board.py`) : il se souvient de ce qu'il a dit et
   ne change d'avis que sur un **événement**. Toute la stabilité est là, et nulle part ailleurs.

### Les cinq états d'une pièce

| État | Ce que voit la famille |
|---|---|
| Calme | « Rien à faire » + une phrase |
| Proposé | « Aérez 20 min » (ou « À essayer », décidé une fois pour toutes) |
| En cours | « Laissez ouvert encore 10 min », « Refermez vers 9 h 30 » |
| De côté | « Rien à faire » + « « Aérez » en pause jusqu'à 10 h 15 » |
| Sécurité | « Gardez fermé : il pleut », « Coupez le poêle »… |

### Les règles, une phrase chacune

1. **Sécurité d'abord** : pluie, rafales, absence, gel, surchauffe mesurée → tout de suite. Elle s'arrête quand sa
   cause s'arrête.
2. **Entrer** :
   - un geste de créneau entre au début de son créneau, avec son heure et sa durée ;
   - une urgence entre quand sa mesure dépasse le seuil d'entrée **deux fois de suite** (10 min). Une mesure isolée
     ne fait rien apparaître.
3. **Rester** : un geste proposé garde son titre, sa durée, son heure et son niveau (« Aérez » ou « À essayer »).
   **Aucune minuterie** ne le fait tomber.
   - Un geste de créneau reste jusqu'à la fin du créneau ou jusqu'au geste.
   - Une urgence reste tant que sa mesure n'est pas repassée sous le seuil de sortie.
4. **Sortir tout seul** : si la pièce s'arrange d'elle-même → Calme.
   - Urgence : la mesure passe sous le seuil de sortie deux fois de suite.
   - Créneau : le geste n'aide plus qu'à peine (moins d'un tiers du seuil).
5. **Patience** :
   - un geste de créneau non suivi s'efface à la fin du créneau, sans relance ;
   - une urgence non suivie au bout de 45 min passe De côté pendant 2 h, et la carte le dit. Elle ne revient avant
     que si la mesure empire nettement.
6. **Suivi** : fenêtre ouverte plus d'1 min → En cours, avec son compte à rebours, qui ne s'allonge jamais (déjà en
   place).
7. **Après une aération** : 1 h de repos pour l'humidité et la chaleur (déjà en place), puis Calme.
8. **Changer de geste** : seulement pour un autre geste (aérer → VMC) qui fait nettement mieux (une fois et demie).
   Changer de durée ou d'heure ne compte pas : on garde celle du départ.
9. **La phrase de « Rien à faire »** : son sujet est choisi en entrant dans le Calme et gardé tout le Calme ; seuls
   les chiffres bougent. Une phrase ne survit jamais à un changement d'état (fenêtre, sécurité).
10. **Contacts** : une fenêtre ouverte moins d'1 min ne compte pas pour le confort ; la sécurité, elle, réagit tout de
    suite.

### Ce qui disparaît

Ces mécanismes sont remplacés par les 10 règles ci-dessus, toutes dans le même fichier et toutes testées :

| Mécanisme supprimé | Remplacé par |
|---|---|
| Tenue du bandeau 30 min (`HOLD_MINUTES`) | règles 3, 4 et 5 |
| Tenue de l'essai 30 min (`tried_held`), essai à demi-gain | règle 3 (niveau gardé) |
| Règle « gardé » à 20 % près (`MARGIN`, `longer`) | règles 3 et 8 |
| Heure « vers … » tenue à 60 min près (`LATER_SLACK`) | règle 8 (heure du départ) |
| Phrase tenue 30 min (`LINE_HOLD`), sujet gardé à 80 % (`SUBJECT_KEPT`) | règle 9 |
| Seuil du soir doublé (`EVENING_TOLERANCE`) | le créneau du soir : un seul geste, fixé à son début |
| Heures et durées recalculées toutes les 5 min | le geste du créneau, fixé à son début |
| Grâce de 3 min aux passages (`GRACE_MINUTES`) | règle 10 (contact d'1 min) |
| Geste ignoré 2 h (`IGNORED_MINUTES`), qui ne se déclenchait pas quand le geste passait en « À essayer » | règle 5 |

Ce qui reste tel quel, parce que c'est stable :
- les règles de pluie ;
- la pastille ;
- les comptes à rebours ;
- le repos après une aération ;
- « Pas maintenant ».

Le calcul (`decide`) perd ses paramètres de mémoire (`previous`, `held`, `tried`, `tried_held`) : il dit ce qui est
le mieux maintenant, rien de plus.

### Ce que ça donnerait sur les 10 jours

- Les 43 yoyos viennent de deux causes :
  - une minuterie qui expire (le geste retombe à 30 min, puis revient) : règles 3 et 5 ;
  - un gain qui hésite autour du seuil : règles 2 et 3, qui posent un seuil pour entrer et un autre, bien plus bas,
    pour sortir.
- Avec les créneaux, la Chambre A le 16 aurait eu un seul geste par créneau, fixé à son début :
  - au lever, « Aérez 30 min vers 9 h » ;
  - à 9 h 48, l'absence ;
  - au retour, « Aérez 45 min vers 15 h 30 » ;
  - le soir, rien ou un seul geste.
  
  Soit 3 ou 4 changements dans la journée, au lieu de 12.
- Les 37 aérations pour l'humidité et les murs (au labo) passent aux créneaux. Les 14 pour les COV de la cuisine
  restent des urgences.

## 6. Comment on prouve que c'est fini

### Les critères de la stable, fixés avant de coder

Sur 48 h de maison, toutes pièces confondues :

1. **Au plus 1 yoyo par jour** (titre qui part et revient en moins d'1 h sans fenêtre touchée), contre 4 à 7
   aujourd'hui.
2. Hors urgences, **au plus un conseil par pièce et par créneau**, fixé à son début, qui ne change ni d'heure ni de
   durée.
3. Une urgence est dite une fois et ne clignote pas.
4. La Chambre P n'a plus de conseil quotidien pour son humidité habituelle. À la place, un conseil du logement.
5. La phrase sous « Rien à faire » change de sujet au plus 3 fois par pièce et par jour, contre 9 aujourd'hui.
   Aucune phrase calculée pour une fenêtre qui n'est plus dans cet état.
6. Aucune erreur dans le journal, tous les tests verts.

### Deux phases

**Phase 1, pour la stable 3.1.0 :**
- les quatre créneaux, avec le meilleur moment calculé par le jumeau et une durée qui suit le dehors ;
- les urgences avec seuils d'entrée et de sortie ;
- les réponses à un geste ;
- la carte d'identité de chaque pièce, refaite chaque nuit et lue par le moteur (normale, isolation, inertie,
  chauffage, aération, sources, habitudes, ce qui est mal compris), visible dans l'Atelier ;
- le conseil du logement pour ce qui est chronique ;
- le tableau d'affichage ;
- l'événement `hestia_comfort_conseil` pour les notifications ;
- l'enregistrement, dès maintenant, de chaque aération faite par pièce et par créneau, pour la phase 2.

**Phase 2, ensuite (3.2.0) :**
- le meilleur créneau appris sur les aérations mesurées : il faut quelques semaines de données ;
- les réglages des notifications dans le panneau (téléphone, niveaux, nombre par jour) ;
- la carte d'identité mise en page dans le panneau, pièce par pièce ;
- la précision des promesses d'humidité.

### Les étapes de la phase 1

1. **Code et tests** : le tableau d'affichage et le choix des créneaux sont des fonctions pures. Leurs tests rejouent
   les vraies journées du 16 novembre (Chambre A, Chambre P, Salon · Cuisine), plus des mesures qui hésitent exprès
   autour des seuils.
2. **Labo, 48 h, en parallèle de la maison** : mêmes mesures (le labo recopie la maison). Le labo tourne en 3.18.0, la
   maison reste en 3.17.1. Le même script compte les yoyos et les conseils des deux côtés.
3. **Maison** si les critères sont tenus au labo, puis 2 jours de gel, puis la **stable 3.1.0**.

Le script de comptage existe déjà : c'est celui qui a produit les chiffres du § 2.

## 7. Hors de ce chantier

- **La précision des promesses d'humidité** (phase 2). Dans 6 pièces sur 7, la façon dont le moteur a appris
  l'humidité bute contre les limites posées le 13 novembre. Exemple : en Chambre P, la nuit, il annonçait « 84-85 % à
  7 h » et on a mesuré 79 %. L'apprentissage par créneau (mesuré contre promis) aidera aussi.
- **« VMC conseillée »** (l'interrupteur des automatisations) : il est décidé par l'ancien moteur
  (`engine/ventilation.py`), avec ses propres règles. En Chambre P, il s'est allumé 56 fois en 10 jours, dont 17 fois
  dans la demi-heure qui suivait un arrêt. À regarder ensuite : le comportement est voulu pour une VMC « à la demande »,
  mais c'est un deuxième cerveau.
