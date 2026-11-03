# Versions du moteur de conseil

Le moteur de conseil (`custom_components/hestia_comfort/advisor/`) a son propre numéro, à part de celui de l'intégration : `VERSION` dans `advisor/__init__.py`.

Il est écrit dans chaque instantané, dans le journal des conseils, dans les avis « Ce conseil ne va pas » et dans le rapport de chaque nuit. Le panneau l'affiche dans « Versions et liens ». On sait ainsi, conseil par conseil, quelle version l'a donné, et on peut comparer avant et après une amélioration.

## La règle

- **Majeur** : une nouvelle génération du moteur ; les jumeaux appris ne sont pas repris, ils sont réappris.
- **Mineur** : un geste, une règle ou une façon de décider qui change des conseils.
- **Correctif** : une correction qui ne change que le conseil qui était faux.

Chaque changement du moteur monte son numéro et ajoute une ligne ci-dessous, la plus récente en haut.

## Historique

### 3.0.0 — 3 novembre 2026

Le moteur entre dans l'intégration (étape C de `PASSAGE-CONFORT-3.md`). Il reprend tout ce qui a été mis au point au labo depuis le 31 octobre :

- conseils par comparaison de gestes simulés sur les jumeaux de chaque pièce (chaleur, humidité, CO₂, particules, COV) ;
- interdits de sécurité : pluie, rafales, vigilance, absence, gel ;
- la plage suit le thermostat, le poêle simulé, « Coupez le poêle » quand la consigne est dépassée trop longtemps ;
- durées de 5 en 5 min, « Laissez ouvert encore N min », source du moment, air traversant ;
- conseil gardé au moins 30 min tant qu'il aide, pas d'appareil conseillé la nuit ;
- « Bon à savoir » : le soleil en une ligne, seulement quand il compte ;
- apprentissage de chaque nuit, avec les fenêtres recalées sur les vraies ouvertures ;
- un geste « plus tard » dit son heure (« Aérez 15 min vers 13 h 50 »).
