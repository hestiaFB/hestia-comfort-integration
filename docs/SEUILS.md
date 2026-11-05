# Repères d’interprétation — 16 octobre 2026

Livré dans la bêta 0.9.0-beta.3. Le capteur, ses seuils modifiables et « Pourquoi ces valeurs ? » partagent le même cadre. La plage de température et l’humidité restent dans Température et humidité ; CO₂, PM2.5, COV et délai de présence dans Air et présence. Réglages / autres conserve l’identité de la pièce et les paramètres transversaux. L’aide sur les cartes reste une évolution ultérieure.

| Mesure | Proposition Hestia-FB | Justification et portée |
|---|---|---|
| CO₂ | 800 / 1 000 / 1 500 ppm | Le HCSP donne un objectif de renouvellement d’air à 800 et une valeur d’action rapide à 1 500 dans les ERP. Hestia-FB adapte ces repères au logement et choisit 1 000 comme palier intermédiaire ; ce n’est pas une certification de qualité de l’air. |
| PM2.5 | 15 µg/m³ | Repère opérationnel Hestia-FB sur la mesure reçue, inspiré de la moyenne OMS sur 24 heures. Le moteur ne calcule pas cette moyenne : un pic ne démontre pas un dépassement de l’exposition journalière. |
| Humidité haute | 60 % | Borne haute de la plage 40–60 % conseillée par l’ADEME ; l’aération dépend aussi de l’air extérieur. |
| COV IKEA VINDSTYRKA identifiée | indice 150 | Exemple de déclenchement d’une action donné par Sensirion, repris par Hestia-FB. L’indice relatif se réajuste à son historique ; 100 n’atteste pas un air sain, et 150 n’est pas une limite sanitaire. |
| Autres COV | Pas de seuil automatique sans profil reconnu | Une unité ne suffit pas à identifier un fabricant, un mélange de gaz ou sa calibration. Les seuils personnels existants sont conservés ; aucune conversion générique indice/concentration. |

Sources primaires consultées :

- [HCSP, avis du 21 janvier 2022](https://www.hcsp.fr/hcspi/Explore.cgi/avisrapportsdomaine?clefr=1154).
- [OMS, lignes directrices 2021](https://www.who.int/fr/news-room/questions-and-answers/item/who-global-air-quality-guidelines).
- [ADEME, Respirer un air sain chez soi](https://agirpourlatransition.ademe.fr/particuliers/proteger-sante/eviter-polluants/respirer-air-sain-chez-soi).
- [Sensirion, What is Sensirion’s VOC Index?](https://sensirion.com/en/media/documents/02232963/6294E043/Info_Note_VOC_Index.pdf).
- [UBA / AIR, limites d’interprétation des COV totaux](https://www.umweltbundesamt.de/en/topics/health/commissions-working-groups/german-committee-on-indoor-air-guide-values).

## Migration et personnalisation

À la demande de Frank, les nouveaux repères CO₂/PM2.5/humidité remplacent aussi ceux des pièces existantes. Cette opération se produit une seule fois au chargement de chaque pièce, avant le coordinateur et son écouteur de modifications. `air_reference_version: 1` est persisté dans les options. Les températures personnelles, sources, ouvrants et autres réglages sont conservés. Un indice COV 150 n’est appliqué qu’au profil IKEA identifié, avec l’unité exacte. Le chemin MQTT peut fonctionner avant restauration de l’état grâce à la propriété technique explicite et au modèle d’appareil.

Les sauvegardes suivantes conservent le marqueur ; une valeur personnalisée ou un seuil COV volontairement vidé n’est pas rétabli à chaque redémarrage. Le choix d’un autre capteur COV réinitialise le seuil et propose celui du modèle uniquement s’il est reconnu. Une unité modifiée invalide le seuil précédent. Les boutons « Utiliser… » restent disponibles pour revenir aux repères proposés.

Les paramètres sans référence sanitaire restent explicitement des choix Hestia-FB : plage personnelle 20–24 °C l’hiver et jusqu’à 26 °C l’été (passage progressif selon la température extérieure des 7 derniers jours), présence 5 minutes, rafales 45 km/h, gel 1 °C, soleil de façade estimé 250 W/m², faible lumière 100 lux, facteur de vitrage modélisé 0,7, ancienneté maximale des mesures numériques 30 minutes. Ces explications ne leur attribuent pas une origine officielle inventée.
