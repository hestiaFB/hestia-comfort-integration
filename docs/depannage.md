# Dépannage

Commencez par l’**Accueil Hestia-FB** : il dit ce qui va, et ce qui reste à régler en orange.

Puis ouvrez **Confort → Accueil**. Quand quelque chose est à régler, l’encadré **À régler** liste chaque problème, avec un bouton vers le bon réglage. Le tableau **Vos pièces** montre où en est l’apprentissage de chaque pièce.

- [Un capteur ne répond pas](#un-capteur-ne-répond-pas)
- [Mesures en chargement ou absentes](#mesures-en-chargement-ou-absentes)
- [Calcul arrêté dans une pièce](#calcul-arrêté-dans-une-pièce)
- [La carte est invisible](#la-carte-est-invisible)
- [L’extérieur et Hestia Weather](#lextérieur-et-hestia-weather)
- [La qualité de l’air](#la-qualité-de-lair)
- [Un conseil semble faux](#un-conseil-semble-faux)
- [Volets et Adaptive Cover Pro](#volets-et-adaptive-cover-pro)
- [Le bilan n’a pas encore de note](#le-bilan-na-pas-encore-de-note)
- [Les journaux](#les-journaux)
- [Signaler un problème](#signaler-un-problème)

## Un capteur ne répond pas

Exemple : « Cuisine : le CO₂ ne répond pas · Depuis 2 h ».

Home Assistant dit que ce capteur est indisponible ou inconnu.

1. Ouvrez le capteur dans Home Assistant : sa pile, sa connexion, son intégration.
2. S’il revient, Hestia-FB le reprend tout seul.
3. S’il est remplacé, choisissez le nouveau dans les réglages de la pièce.

« **N’existe plus** » : l’entité a été supprimée ou renommée. Choisissez-la à nouveau.

Ce qui manque reste inconnu : Hestia-FB conseille avec le reste. Seule la température de la pièce est indispensable.

Beaucoup de capteurs n’envoient une valeur que quand elle change. Une valeur stable reste valable tant que l’appareil donne signe de vie, et au plus 3 heures (réglable dans **La pièce → Réglages avancés**).

## Mesures en chargement ou absentes

**Mesures en chargement** : Home Assistant vient de démarrer. Les capteurs arrivent un à un. Attendez quelques minutes.

**Mesures absentes**, en gris : les capteurs de la pièce restent muets. Ce n’est pas un conseil. Voir [un capteur ne répond pas](#un-capteur-ne-répond-pas).

Un capteur secondaire muet (le CO₂, par exemple) ne change pas le conseil. Sa tuile passe en pointillés.

## Calcul arrêté dans une pièce

Home Assistant n’a pas pu démarrer cette pièce.

1. Vérifiez ses capteurs dans ses réglages.
2. **Paramètres → Appareils et services → Hestia Comfort** : rechargez la pièce.
3. Si rien ne change, regardez [les journaux](#les-journaux).

## La carte est invisible

La carte est fournie par l’intégration : rien à installer à part.

- **Juste après une mise à jour** : redémarrez Home Assistant, puis rechargez la page.
- **Dans l’application Home Assistant** : **Paramètres → Application compagnon → Dépannage → Réinitialiser le cache du frontend**.
- **Vous aviez installé l’ancienne carte Confort à part, dans HACS** : supprimez-la de HACS, puis rechargez la page. Vos cartes restent en place.
- **« Ouvrez Hestia Confort dans la barre latérale »** : aucune pièce n’est encore créée.
- **« Connexion indisponible »** : la carte réessaie seule. Vérifiez que Home Assistant répond.

## L’extérieur et Hestia Weather

**« Extérieur à configurer »** : sans l’extérieur, Hestia-FB ne peut pas dire s’il vaut mieux ouvrir ou fermer. Réglez-le dans **Confort → Réglages généraux**.

**Hestia Weather est installé, mais n’est pas proposé** :

- vérifiez que Hestia Weather a au moins un lieu (onglet **Météo** du panneau Hestia-FB) ;
- Confort a besoin de Hestia Weather 2.1 ou plus récent ;
- après l’installation de Weather, redémarrez Home Assistant.

Une fois relié, l’encadré **Extensions** de l’Accueil indique Hestia Weather « liée », et **Versions et liens** le cite dans ses liaisons. Weather affiche aussi « Relié à Hestia Confort ».

**La liaison s’est coupée toute seule** : elle se règle des deux côtés. Un interrupteur éteint dans Hestia Weather (**Réglages → Extensions → Hestia Confort**), ou **Vos propres capteurs** choisi dans Confort, la coupe des deux côtés. Rallumez-la depuis l’un ou l’autre.

**Une mesure du dehors à changer** : avec Hestia Weather, elles sont reprises de sa station et ne se choisissent pas dans Confort. Changez la station dans Hestia Weather, ou choisissez **Vos propres capteurs** dans Réglages généraux.

**Pas d’anticipation** (« Refermez avant la pluie », « Aérez vers 22 h ») : elle vient des prévisions de Hestia Weather.

## La qualité de l’air

**« Pollution · ne répond pas »** : la source de l’indice ne donne plus de valeur.

Le conseil reste valable. Hestia-FB le signale dans **Détails** et sur l’Accueil Hestia-FB.

Seule la pluie reste une protection : si son capteur se tait, Hestia-FB demande de vérifier dehors.

**Atmo France est en panne** : avec Hestia Weather 2.5.7 ou plus, choisissez une station WAQI dans **Weather → Qualité de l’air**. Confort suit ce choix, sans autre réglage.

**Votre propre capteur de pollution** est gardé tel quel : il ne suit pas Hestia Weather.

## Un conseil semble faux

Ouvrez **Détails** sur la carte. Vous y voyez :

- les mesures utilisées, leur source et leur âge ;
- ce qui manque ;
- l’apprentissage de la pièce (« Séchage »).

Vérifiez aussi les réglages de la pièce :

- **l’exposition** des fenêtres : elle décide du soleil et de la pluie ;
- **abrité** : une fenêtre abritée peut rester ouverte sous la pluie ;
- **votre plage** de température et le seuil d’humidité ;
- **Pièce chauffée** (onglet Chauffage), à éteindre si la pièce n’a pas de chauffage ;
- les **Extensions** des Réglages généraux : une extension coupée n’est lue dans aucune pièce.

Une pastille **« Au mieux »** n’est pas une erreur : une mesure sort de votre plage, mais aucun geste ne ferait mieux. « À savoir » dit pourquoi.

« **Rien à faire** » alors qu’il fait chaud ? Dehors n’est pas plus frais, ou ouvrir n’aiderait pas. Hestia-FB ne parle que pour un geste utile.

La durée d’aération change ? La pièce apprend. Les premiers jours, elle reste prudente. Son état d’apprentissage et la précision de ses prévisions sont dans **Vos pièces**, sur l’Accueil Confort.

## Volets et Adaptive Cover Pro

**« Piloté par Adaptive Cover Pro » n’apparaît pas** dans le panneau :

- la fenêtre doit avoir **Volet connecté** et le bon volet choisi ;
- ce volet doit faire partie des volets réglés dans Adaptive Cover Pro ;
- après avoir ajouté Adaptive Cover Pro, rechargez Hestia Confort (ou redémarrez Home Assistant).

**Hestia-FB dit « automatisme coupé »** alors qu’Adaptive Cover Pro est installé : un de ses interrupteurs est éteint (Integration Enabled, Automatic Control ou Sun Tracking). Le panneau dit lequel.

**Hestia-FB vous demande de fermer le volet** : Adaptive Cover Pro ne le pilote pas en ce moment, et le soleil arrive sur une pièce trop chaude.

Le mode climat ou une autre fonction d’Adaptive Cover Pro est indisponible ? Hestia-FB l’ignore : ce n’est pas un capteur en panne.

## Le bilan n’a pas encore de note

**« Pas encore de note »** ou **« pas encore assez de mesures »** : il faut deux semaines de mesures pour noter un thème. Le bilan se remplit seul.

Le bilan lit les statistiques à long terme de Home Assistant. Un capteur sans statistiques (sans `state_class: measurement`) ne compte pas : ses mois passés restent vides.

**« Le bilan n’a pas pu être chargé »** : vérifiez que l’enregistreur de Home Assistant est actif, puis rechargez la page.

## Les journaux

**Paramètres → Système → Journaux**, puis cherchez « comfort ».

Pour plus de détails, ajoutez dans `configuration.yaml`, puis redémarrez :

```yaml
logger:
  default: warning
  logs:
    custom_components.hestia_comfort: debug
```

Retirez-le une fois le problème trouvé : les journaux grossissent vite.

Deux messages connus, sans gravité :

- « Home Assistant statistics could not be read » : la plage d’été ou le minimum de 24 h attendent l’historique ;
- « Past openings could not be read for … » : la pièce garde ce qu’elle avait appris.

## Signaler un problème

Ouvrez un ticket sur [GitHub](https://github.com/hestiaFB/hestia-comfort-integration/issues), avec :

- les versions de Home Assistant, Hestia Confort et Hestia Weather ;
- la pièce concernée et ce que dit la carte ;
- une capture de **Détails** ;
- le **fichier de diagnostic** de la pièce (ci-dessous) ;
- les lignes des journaux qui contiennent « comfort ».

Retirez vos informations personnelles avant d’envoyer.

### Le fichier de diagnostic

**Paramètres → Appareils et services → Hestia Comfort**, puis, sur la ligne de la pièce, **⋮ → Télécharger les diagnostics**. Glissez le fichier dans le ticket.

Il contient ce que Hestia-FB calcule pour la pièce : le conseil tel que la carte le reçoit, les mesures lues, l’état brut de chaque capteur choisi (et du thermostat), ce que la pièce a appris et les premières heures de prévision. Les coordonnées de la maison sont retirées. Les noms des capteurs restent : relisez-le si certains vous semblent trop personnels.
