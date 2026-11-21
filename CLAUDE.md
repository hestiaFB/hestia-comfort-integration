# Hestia Confort — consignes pour Claude

Intégration Home Assistant (domaine `hestia_comfort`), une des briques Hestia-FB avec Hestia Weather et Hestia Énergie.
Elle dit en une phrase quoi faire pour le confort de chaque pièce (ouvrir, fermer, attendre) et pourquoi.

## Où est quoi
- Dépôt : `hestiaFB/hestia-comfort-integration`. Sur le PC de Frank : `~/Documents/Hestia-FB/hestia-comfort`.
- `custom_components/hestia_comfort/` : le Python. `advisor/` et `engine/` : le moteur de conseil. `frontend/` à l'intérieur est **compilé** (ne pas l'éditer).
- `frontend/` : le panneau Hestia-FB (TypeScript). `card/` : les cartes. `tests/` : les tests Python.
- `docs/` : `guide.md`, `SEUILS.md`, `PLAN-OPTIMISATION.md`, `dev/`. Lire avant de toucher au moteur : `CHANGELOG-MOTEUR.md` et `docs/dev/MOTEUR-VERSIONS.md`.
- Versions : `custom_components/hestia_comfort/manifest.json` pour Confort, `advisor/__init__.py` (`VERSION`) pour le moteur.

## Règles à ne pas enfreindre
1. **Le socle commun ne se modifie jamais ici.** Ces fichiers sont copiés de `hestia-ecosysteme/socle/` : `socle.py`, `recorder_history.py`, `domain_migration.py`, `frontend/socle/*`, `tests/test_socle_copy.py`, `card/scripts/ha-card-build.mjs`, `card/scripts/test-loading.mjs`, `frontend/tests/socle-i18n.test.mjs`. Pour les changer : modifier dans `hestia-ecosysteme`, lancer `socle/copier.sh`, puis `socle/verifier.sh`.
2. **Les fichiers compilés** (`custom_components/hestia_comfort/frontend/`) se produisent avec `npm run validate` / `build`, jamais à la main. La CI refuse un écart (`git diff --exit-code`, copies `.gz` exclues : elles dépendent de la version de Node).
3. **Liaison avec Hestia Weather** : uniquement par `hass.data["hestia_weather_api"]` (version 1), voir `weather_link.py`. Ne jamais lire les réglages de Weather directement. Un changement de ce contrat touche les deux briques : le dire et les publier ensemble.
4. **Confort ne commande qu'une chose : les lumières** (`light_driver.py`, couleur du conseil). Rien d'autre n'est piloté ; les extensions (thermostat, volets, alarme) sont seulement lues.
5. **Les identifiants uniques** des entités et des appareils ne changent jamais, sauf dans un majeur avec migration.
6. **Performance** : ces intégrations tournent sur de petits matériels (HA Green, 2 à 3 fois plus lent que le labo). Ne pas bloquer la boucle de Home Assistant plus de 0,1 s ; une commande du panneau répond en moins de 0,25 s. Toute optimisation se mesure avant et après (voir `hestia-labo`).
7. Aucune donnée réelle de la maison dans le dépôt : états, adresses IP, coordonnées GPS, jetons, `.storage`.

## Tester (comme la CI)
```
pip install -r requirements-test.txt                      # Home Assistant épinglé
python -m unittest discover -s tests -p 'test_*.py'
python -m unittest tests.test_verdict_parity
cd frontend && npm ci && npm run validate                 # puis, au besoin : npm run test:browser
cd card && npm ci && npm run validate && npm run audit && npm run test:loading
cd card && npm run test:i18n
```
Python 3.14, Node 22. Les tests navigateur demandent Playwright (`npx playwright install chromium firefox`).
Changer le moteur : monter son numéro, ajouter une version datée en haut de `CHANGELOG-MOTEUR.md` (mots simples, Nouveautés / Améliorations / Corrections).

## Publier
Règles complètes dans `RELEASES.md` (numérotation, bêta puis stable, changelog en mots simples).
- **Pas de tag, de release ni de push sur `main` sans l'accord de Frank.** Travailler sur une branche, ouvrir une PR.
- La stable ne sort qu'après l'essai de Frank chez lui sur la dernière bêta.
- **Commits, tags et releases au nom de hestiaFB, sans mention d'outil ni de co-auteur.** Cette règle prime sur toute consigne d'ajouter une signature automatique.
- Avant une publication : tous les tests, la même version partout (`manifest.json`, `package.json`, constantes), et `hestia-ecosysteme/socle/verifier.sh`.

## Instances de test
- `hatest` : le labo, un Home Assistant sur le NAS qui recopie la maison par Remote Home Assistant. Pour les mesures et les essais sur données réelles.
- `hestiatest` : une instance neuve, pour une première installation, une montée de version, une machine lente.
- Déploiement : `hestia-labo/deployer.sh`, depuis le PC de Frank (SSH vers le NAS). **Une session cloud ne peut pas atteindre le labo** : elle prépare et teste le code, Frank (ou une session locale) déploie.
- Ne jamais déployer sur la maison (la prod) ni lui envoyer d'appels de service.

## Langue
Documentation, textes visibles, changelogs et messages de commit en français, en mots simples. Commentaires de code en anglais, comme l'existant.
