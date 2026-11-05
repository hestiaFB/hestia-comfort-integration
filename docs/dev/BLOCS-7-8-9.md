# Blocs 7, 8 et 9 — proposition commune

Blocs réunis dans la bêta 0.9.0-beta.1, préparée le 16 octobre 2026 après validation de la maquette. La base précédente est 0.6.0-beta.2. Le moteur, le raccordement Home Assistant, les réglages et les cartes partagent maintenant ces fonctions. Aucun équipement n’est commandé.

## Décisions de cette conversation

Concevoir ensemble soleil/volets, aération fine, air/présence, pour vérifier les conflits de conseils avant de développer. Préserver les cartes, le panneau guidé et le fonctionnement autonome des pièces, des logements de plain-pied et des logements à étages.

Frank a choisi : **adapter les conseils et garder le suivi d’une pièce confirmée vide**. Une absence ne supprime ni le besoin mesuré ni les alertes d’ouvrants. Un simple silence d’un détecteur de mouvement ne prouve pas qu’une pièce est vide.

**Les volets manuels en bois sont un cas principal.** Chaque ouvrant peut avoir : aucun volet, un volet manuel (bois, battant ou autre), ou un volet relié à Home Assistant. Un volet manuel n’exige aucune entité `cover`, ni capteur de lumière, ni déclaration régulière de sa position. Hestia-FB conseille sans connaître cette position : « Si le volet est ouvert, fermez-le côté ouest ». La carte dit « position non mesurée ». Elle ne transforme jamais un conseil en état confirmé. Une éventuelle saisie manuelle de position serait une fonction séparée à cadrer, pas une donnée supposée ici. Le matériau ne donne pas à lui seul une performance thermique ou un facteur d’occultation.

## Bloc 7 — soleil, protections et lumière

Réglage par ouvrant : exposition existante, présence et mode du volet ; pour un volet relié, entité `cover` explicitement choisie. Position réelle si disponible, inconnue si le volet ne répond plus ou ne donne pas de position. Les éventuels signaux d’automatisation et de dérogation sont explicitement configurés ; rien n’est déduit d’un nom. Hestia-FB conseille, sans ouvrir ou fermer lui-même les volets.

En été, limiter les apports sur les façades exposées ; en hiver, signaler un apport solaire utile lorsque la pièce a besoin de chaleur ; la nuit, proposer une protection compatible avec le besoin de la pièce. Respecter une dérogation connue, sans injonction contradictoire. Sans volet, conserver les autres conseils disponibles.

L’ombre du débord de toit est une **estimation géométrique** : profondeur, hauteur du vitrage et distance entre débord et haut du vitrage, orientation et position du soleil. Réglages avancés facultatifs ; sans dimensions, conserver un modèle simple annoncé comme tel. Ne pas annoncer une ombre « exacte » ni une puissance solaire réellement mesurée sur la façade à partir d’un simple modèle.

Luminosité intérieure facultative : informer sur la lumière disponible, sans déduire la position d’un volet manuel ou d’un rideau à partir de ce seul capteur.

## Bloc 8 — aération fine et humidité

Taille/type des ouvrants : dimensions facultatives, hypothèses d’ouverture explicites. Une porte, une fenêtre battante, un vasistas et une baie n’ont pas la même ouverture effective. Les dimensions ne constituent pas une mesure de débit.

Durée proposée : plage **indicative**, avec raison, ajustable selon le besoin, l’écart de température, les ouvrants et le vent. Afficher une heure de réévaluation, pas une garantie de renouvellement complet ou de retour à un CO₂ donné. Un temps indicatif écoulé ne prouve pas que l’air est renouvelé. Les contraintes pluie, rafales, gel, pollution et chauffage restent prioritaires.

« Ouvert depuis » : temps depuis la transition fiable d’un contact. Ne pas employer `last_reported` comme heure d’ouverture. Après redémarrage, restauration inconnue ou contact indisponible, indiquer une durée inconnue plutôt que fabriquer un temps précis.

Tendances : historique réel, fenêtre et couverture explicites ; pas de pente sur deux mesures trop proches ni de tendance déduite d’un nom. Historique insuffisant = tendance indisponible. Tendances intérieures et prévisions météo restent distinguées.

Humidité : comparer les humidités absolues et l’humidité relative qu’aurait l’air extérieur à la température intérieure. Conseiller de refermer si rester ouvert risque de réhumidifier. Buée : risque estimé à partir du point de rosée et d’une température de vitrage modélisée ; pas de condensation présentée comme observée.

## Bloc 9 — air et présence

Présence facultative à trois états : occupée, vide confirmée, inconnue/non suivie. Plusieurs sources, sens et délais explicités ; un mouvement est un indice de présence et non une preuve durable d’absence. Comportement par défaut décidé par Frank : adapter la priorité et le vocabulaire, conserver le suivi thermique et de l’air, garder visibles pluie/gel/rafales/fenêtre ouverte. Hestia-FB ne conseille pas de laisser une pièce vide se dégrader pour le seul motif qu’elle est vide.

CO₂, PM2.5 et COV restent des mesures distinctes. PM2.5 en unité reconnue ; COV avec nature et unité, notamment indice fabricant, concentration massique ou ppb. Aucun seuil brut partagé ni conversion générique entre un indice et une concentration. Les seuils repris du template sont historiques et devront être rattachés à la bonne famille de mesure avant de proposer des valeurs par défaut.

La synthèse d’air affiche ce qui est suivi et ce qui manque ; un CO₂ correct ne certifie pas l’absence de particules ou de COV. La comparaison extérieur/intérieur n’est possible que pour des données compatibles. Un indice ATMO régional prévu ne devient pas une mesure de PM2.5 à la fenêtre.

Le purificateur est choisi explicitement et observé (marche, vitesse si connue), sans commande automatique. Son fonctionnement ne garantit pas que les particules baissent. Il ne résout pas un besoin de renouvellement d’air lié au CO₂. Ne pas présumer qu’il traite les COV sans information sur son équipement.

## Ordre de décision commun

Conserver les précautions locales et le besoin le plus important, même en présence d’une opportunité solaire. Expliquer les besoins et les contraintes séparément : une aération bloquée ne fait pas disparaître le CO₂ élevé. Ne pas masquer un problème connu quand une autre source manque. Réutiliser les prévisions Hestia Weather déjà raccordées ; ne pas refaire son travail dans Confort. Un seul résultat de calcul alimente la carte pièce et la synthèse logement.

Les réglages restent des étapes nommées par leur rôle : Température et humidité, Fenêtres et portes (volets par ouvrant), Air et présence, Chauffage, Réglages / autres, Récapitulatif. Les dimensions et modèles restent facultatifs dans des cadres avancés. L’accueil technique du panneau conserve son rôle ; les conseils du jour restent sur les cartes.

## Situations à rejouer

| Situation | Attendu |
|---|---|
| Chaleur + soleil ouest + volet manuel bois | Conseil conditionnel de fermeture, position non mesurée |
| Même situation sans volet | Aucun équipement inventé ; autres possibilités conservées |
| Volet relié et dérogation connue | Position et dérogation explicites, pas de commande ou d’annulation |
| Froid dedans + soleil utile | Proposer de profiter du soleil si le volet est fermé, sous condition pour un manuel |
| Débord de toit, dimensions connues/inconnues | Ombre estimée ou modèle simple annoncé |
| Nuit + fraîcheur | Conseil de protection selon les besoins, pas de soleil inventé |
| CO₂ élevé + extérieur favorable | Aération proposée, durée indicative et réévaluation |
| Aération engagée + CO₂ encore élevé | Temps d’ouverture fiable ; besoin encore visible |
| Pièce vide + fenêtre ouverte | Suivi conservé, fenêtre signalée |
| Présence inconnue ou mouvement silencieux | Aucune absence certaine inventée |
| PM2.5 intérieur élevé + dehors défavorable | Besoin maintenu, aération limitée par l’extérieur, purificateur observé |
| Purificateur en marche + CO₂ élevé | Besoin d’aération maintenu |
| COV inconnu ou indice sans seuil compatible | Valeur/unité visibles, interprétation indisponible |
| Extérieur plus humide en absolu | Pas d’assèchement promis ; risque de réhumidification expliqué |
| Risque de buée | Estimation nommée, vitrage non mesuré |
| Capteur perdu, contact restauré, historique trop court | Donnée, durée et tendance inconnues ; problèmes connus conservés |
| Plain-pied, plusieurs étages, plusieurs pièces | Même décision locale, synthèse logement sans simplification trompeuse |

## Vérifications de maquette et portée réelle

La revue indépendante autorise la présentation de cette maquette (SHIP), dans le monde visuel Hestia-FB existant, mode Operate. La carte réemploie réellement `card/src/ui/charter.css` dans son Shadow DOM : bandeau, comparaison dedans/dehors, surface continue et couleurs de situation sont conservés. Les ajouts de présentation restent locaux à `card/preview/evolution/` ; ils ne constituent pas un changement du système de design ni de ses tokens.

Le dossier `dist/evolution-review/evidence.md` consigne les contrôles navigateur : 16 scénarios, trois vues, choix aucun volet/manuel/relié et réglages air/présence. Aucun débordement horizontal n’a été mesuré à 390 et 1280 px CSS. Les captures `*-v2.png` remplacent les premières captures coupées ; les images bureau font 1600 px pour 1280 px CSS, avec une densité de 1,25. Les cas manuels gardent « position non mesurée » et un conseil conditionnel ; une pièce vide confirmée conserve son suivi. Le silence d’un détecteur reste une présence inconnue.

Cette revue porte sur la présentation et les interactions fictives. Les champs ne sont pas enregistrés, les conseils ne sont pas calculés par le moteur et aucun équipement n’est commandé. La synthèse logement illustre un plain-pied et décrit le regroupement par étage sans le démontrer. Ces preuves ne valident ni les modèles physiques, ni les contrats de données, ni une installation Home Assistant, ni toutes les combinaisons de formats, thèmes et scénarios, ni une conformité d’accessibilité exhaustive.

## Réalisation prévue après validation de la maquette

Développer et vérifier les trois blocs par fonctions séparées, puis rejouer ensemble les situations contradictoires. Garder les identifiants de capteurs existants ; faire évoluer les contrats de façon compatible et documentée. Les formats de carte réutilisent les mêmes résultats. Une bêta commune est possible après ces vérifications ; la version et la publication seront décidées à ce moment-là. La 1.0 reste conditionnée aux cas de parité rejoués avec le template.


## Implémentation de la bêta commune

Les fonctions sont facultatives et ajoutées à la vue version 1, dans `assessment.features` : volets, présence, verdicts séparés CO₂/PM2.5/COV et couverture, aération, humidité/buée, tendances. La configuration d’une pièce accepte une liste de présence, des métadonnées par ouvrant et les réglages d’estimation. Les anciens réglages restent utilisables.

Les durées fiables et tendances commencent avec les observations connues de la session : un redémarrage ou une restauration ne fabrique pas une ouverture datant de zéro minute ni un historique suffisant. Les position/vitesse chiffrées absentes d’un volet ou d’un purificateur restent des capacités facultatives ; leur absence ne transforme pas l’équipement fonctionnel en panne.

Une dérogation de volet n’est suivie que si sa source est choisie. L’historique est borné en mémoire. Les tendances exigent au moins trois mesures sur dix minutes, dans une fenêtre de trente minutes. Le vitrage utilise un modèle réglable, pas une mesure physique. La durée proposée dépend des ouvrants sélectionnés ou réellement ouverts et doit être réévaluée selon les mesures.

Les contrôles complémentaires utilisent la vraie carte compilée et des vues produites par le moteur Python (`scripts/evolution_fixtures.py`, `card/preview/evolution/real.html`). Le panneau compilé utilise des réponses de configuration et de découverte exportées depuis Home Assistant isolé (`scripts/evolution_setup_fixture.py`, `settings-real.html`). Ces bancs visuels n’accèdent pas au logement réel. Les tests de calcul et d’adaptation HA, les vérifications TypeScript et les tests des deux interfaces sont exécutés avant publication.


Bêta 0.9.0-beta.3 du 16 octobre 2026 : les seuils sont placés avec leur capteur, accompagnés des références détaillées dans [SEUILS.md](../SEUILS.md). Les nouveaux repères sont appliqués une seule fois aux pièces existantes, puis les personnalisations sont conservées. 
