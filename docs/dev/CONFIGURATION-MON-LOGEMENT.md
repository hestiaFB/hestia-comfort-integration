# Configuration Mon logement — validation locale

Validation de la version 0.3.0-beta.3 avant publication. Elle n’a pas été installée sur le Home Assistant de production.

La page est fournie par l’intégration : onglet **Confort** du panneau commun **Hestia-FB** de la barre latérale. Elle propose le Salon en premier, puis les pièces Home Assistant. La carte ouvre directement la pièce concernée. Une pièce se règle en six étapes : Température et humidité, Fenêtres et portes, CO₂, Chauffage, Pièce et confort, Récapitulatif ; on peut revenir à chacune avant d'enregistrer. Un cadre repliable « À quoi sert cet onglet ? » explique chaque étape. L'extérieur se règle à part, une fois pour toutes les pièces : sa source (Hestia Weather ou vos propres capteurs), ses mesures par cadre, puis la qualité de l'air (Atmo France, Hestia Weather ou aucune) et sa zone.

Les sources présentent valeur, pièce et provenance. Une référence de température ou humidité définie dans Home Assistant est privilégiée. Plusieurs candidats restent à choisir ; une absence facultative peut rester vide. Les alias vers une autre pièce, sources calculées, portes ambiguës et rôle extérieur demandent une confirmation explicite. L’affectation d’une station à une pièce ne détermine pas le rôle de chacune de ses mesures.

Les données extérieures sont communes uniquement pour les pièces qui activent cette option. Les configurations existantes conservent leurs sources. La pluie utilise une intensité actuelle, pas un cumul. L’indice ATMO quotidien peut déclencher une précaution, mais ne constitue pas une observation actuelle de l’air aux fenêtres. Les anciens signaux binaires sélectionnés restent identifiés comme tels, sauf diagnostics incompatibles.

Les sauvegardes sont réservées aux administrateurs, vérifiées côté intégration et protégées contre un écrasement lorsque la configuration change dans une autre session. Aucun équipement n’est commandé.

## Vérifications

- 62 tests Python : moteur, adaptation HA, configuration, provenance, absence et ambiguïté, diagnostics, références HA, sauvegarde et restrictions administrateur.
- 3 tests du modèle d’interface et compilation du module intégré ; 11 tests de carte et compilation du fichier distribué.
- Instance HA locale isolée, données fictives : activation initiale, barre latérale, fichier intégré servi, découverte, sauvegarde commune, ajout de pièce, lecture réelle du moteur et suppression du CO₂ sans changer l’identité de la pièce.
- Navigation réelle depuis la carte vers `/hestia/confort/<pièce>` ; annulation du brouillon depuis la page sans enregistrer.
- Interface HA locale : modification du Salon, maintien des champs vides, contacts et récapitulatif, enregistrement effectif depuis la page.
- Aperçu reproduisant les cas Cuisine et station avec données fictives : étapes jusqu’à l’enregistrement, portes de réfrigérateur et alias CO₂ non sélectionnés, pluie et ATMO lisibles, thèmes et largeur mobile.

Ces tests ne valident pas une prochaine installation HACS ni toutes les stations réelles. L’aperçu `http://127.0.0.1:8766/preview/setup/` ne contacte pas l’installation réelle.
