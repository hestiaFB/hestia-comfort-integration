# Notes techniques

Pour les développeurs. Le guide pour les utilisateurs est [ici](../guide.md).

## Tests et compilation

- Tests Python : Python 3.14, `pip install -r requirements-test.txt`, puis `python -m unittest discover -s tests -p 'test_*.py'`.
- Types : `pip install mypy`, puis `python -m mypy --follow-imports=silent --ignore-missing-imports custom_components/hestia_comfort/api.py custom_components/hestia_comfort/recorder_history.py custom_components/hestia_comfort/room/constants.py` (les fichiers déjà typés ; la liste grandit avec eux).
- Le coordinateur d’une pièce (`coordinator.py`) garde son cycle de vie et son calcul ; ses parties sont dans `room/` : `learning.py` (apprentissage, historique, statistiques), `volume.py` (même air), `presence.py`, `sun.py`, `airings.py` (aérations suivies, COV), `readings.py` (lecture des capteurs), `constants.py`.
- Panneau : `cd frontend && npm ci && npm run validate` (produit `custom_components/hestia_comfort/frontend/panel.js`).
- Carte : `cd card && npm ci && npm run validate` (produit `custom_components/hestia_comfort/frontend/hestia-comfort-card.js`).
- Chargement des cartes : `cd card && npx playwright install chromium firefox && HESTIA_TEST_FIREFOX=1 npm run test:loading`. Vérifie les cartes logement et pièce, et leur éditeur, avant et après l’initialisation de Home Assistant, sur deux onglets, avec cache et rechargement.

## Bancs visuels

Données fictives, aucune connexion à un Home Assistant réel :

- `card/preview/refonte/` : la vraie carte compilée, nourrie par des situations calculées par le moteur Python (`scenes.py` → `scenes.json`) ;
- `card/preview/formats/` : les formats de carte ;
- `card/preview/card.html`, `floors.html`, `floor-settings.html` : carte, étages, réglage d’un étage ;
- `frontend/tests/hub-harness.mjs` : le panneau Hestia-FB (Accueil, Confort, Weather).

Les images de `docs/images/` viennent de ces bancs.

## Traduire

Hestia Confort parle français et anglais. Le français est écrit dans le code ; chaque autre langue est un dictionnaire « phrase française → traduction ». Pour ajouter une langue, traduisez ces fichiers en partant de l’anglais :

| Fichier | Ce qu’il traduit |
| --- | --- |
| `card/src/i18n/en.ts` | Les cartes et le bilan |
| `frontend/i18n-en.ts` et `frontend/socle/i18n-en.ts` | Le panneau Hestia-FB |
| `custom_components/hestia_comfort/engine/i18n_en.py` | Les conseils et les textes calculés pour la carte et le panneau |
| `custom_components/hestia_comfort/translations/en.json` | L’assistant de Paramètres et les noms des entités |

Les valeurs des entités restent en français : elles servent aux automatisations. Les tests vérifient qu’aucune phrase n’est oubliée et que les `{noms}` entre accolades sont gardés.

Pas à l’aise avec ces fichiers ? [Ouvrez une demande « Traduction »](https://github.com/hestiaFB/hestia-comfort-integration/issues/new?title=Traduction%20%3A%20) : on vous envoie la liste des phrases, et on s’occupe du reste.

## Interfaces

- API WebSocket v1 en lecture : `hestia_comfort/entries`, `hestia_comfort/view`, `hestia_comfort/subscribe`, `hestia_comfort/home_subscribe`.
- Entités par pièce : situation, geste, raison, chauffage observé, couverture des données (identifiant interne `<entrée>_<clé>`).
- Hestia Weather : `weather_link.py` lit son API publique (station, prévisions, `air()` depuis Weather 2.5.7).

## Notes de conception

| Note | Sujet |
| --- | --- |
| [CONFIGURATION-MON-LOGEMENT.md](CONFIGURATION-MON-LOGEMENT.md) | Le panneau « Mon logement » (0.3) |
| [ETAGES.md](ETAGES.md) | Logement et étages, données publiées (0.6) |
| [CHARGEMENT-CARTES.md](CHARGEMENT-CARTES.md) | Chargement fiable des cartes (0.6) |
| [BLOCS-7-8-9.md](BLOCS-7-8-9.md) | Soleil et volets, aération fine, air et présence : périmètre et limites (0.9) |
| [IMPLEMENTATION-7-8-9.md](IMPLEMENTATION-7-8-9.md) | Contrat de travail des blocs 7 à 9 |

Ces notes datent de leur version : elles ne décrivent pas toujours l’état actuel.
