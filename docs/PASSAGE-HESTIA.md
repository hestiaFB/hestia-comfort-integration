# Mise à jour bloquée : « changed its domain from niak_comfort to hestia_comfort »

*English below.*

Depuis la 2.0, le nom technique de Hestia Confort est `hestia_comfort` (avant : `niak_comfort`).
Le Marketplace de Home Assistant (2026.11 et plus récent) refuse une mise à jour qui change ce nom. Il affiche :

> The update could not be started: hestiaFB/hestia-comfort-integration changed its domain from niak_comfort to hestia_comfort, uninstall it and install it again.

**Ne supprimez pas l'intégration** dans Paramètres → Appareils et services : vos pièces, réglages et apprentissages partiraient avec.
Il suffit de changer le dossier. Tout le reste est repris seul.

## Ce qu'il faut

- Un accès aux fichiers de Home Assistant : l'extension **File editor**, **Studio Code Server**, ou un partage **Samba**.
- Cinq minutes, et deux redémarrages.

## Les étapes

1. **Faites une sauvegarde** : Paramètres → Système → Sauvegardes.
2. **Supprimez le dossier** `/config/custom_components/niak_comfort`.
   - Seulement ce dossier. Ne touchez pas à `/config/.storage`.
3. **Redémarrez Home Assistant.**
   - Le Marketplace voit que l'ancien dossier n'est plus là et ne bloque plus.
   - Une réparation « intégration introuvable » peut apparaître pour Niak Confort : laissez-la, elle partira seule.
4. **Paramètres → Marketplace → Hestia Confort → Télécharger** (la dernière version).
5. **Redémarrez Home Assistant.**
6. **Paramètres → Appareils et services → Ajouter une intégration → Hestia Confort.**
   - Hestia Confort retrouve votre installation et la reprend : rien n'est créé en double.
   - Le message « Votre installation a été reprise sous le nouveau nom » s'affiche.
7. Ouvrez **Hestia-FB → Accueil** : l'encart « Passage au nom Hestia » montre chaque étape, puis s'en va.

## Ce qui est gardé

- Vos pièces, réglages, apprentissages, historiques et statistiques.
- Le nom de vos entités : vos automatisations et tableaux de bord continuent de marcher.
- Les automatisations, scripts, scènes et tableaux de bord faits dans l'interface sont mis à jour.
- Ce qui est écrit à la main en YAML n'est jamais modifié : une réparation dans **Paramètres** liste les fichiers et les lignes à changer.

## Vous avez aussi Hestia Weather ?

Faites la même chose pour lui, dans la foulée : dossier `niak_weather`, puis **Hestia Weather** dans le Marketplace.
La liaison entre les deux suit d'elle-même.

## Ça ne marche pas ?

- **« Ajouter une intégration » propose de créer une nouvelle pièce** : l'ancienne installation n'a pas été trouvée. Arrêtez-vous là et ouvrez une issue : ne créez pas de nouvelle pièce.
- **Le Marketplace refuse encore** : vérifiez que le dossier `niak_comfort` a bien disparu, puis redémarrez.
- **Vous avez supprimé l'intégration par erreur** : restaurez la sauvegarde de l'étape 1.

Dans tous les cas, [ouvrez une issue](https://github.com/hestiaFB/hestia-comfort-integration/issues/new) avec le journal de Home Assistant (Paramètres → Système → Journaux, filtre `hestia`).

---

## English

Since 2.0, Hestia Confort's technical name is `hestia_comfort` (formerly `niak_comfort`). Home Assistant's Marketplace (2026.11 and later) refuses an update that changes it.

**Do not delete the integration** in Settings → Devices & services: your rooms, settings and learning would go with it.

1. Make a backup (Settings → System → Backups).
2. Delete the folder `/config/custom_components/niak_comfort` (File editor, Studio Code Server or Samba). Nothing else.
3. Restart Home Assistant. A repair saying Niak Confort is not found may show: leave it.
4. Settings → Marketplace → Hestia Confort → Download (latest version).
5. Restart Home Assistant.
6. Settings → Devices & services → Add integration → Hestia Confort. It finds your installation and carries it over: nothing is set up twice.
7. Open Hestia-FB → Home: the « Moving to the Hestia name » box shows each step.

Your rooms, settings, learning, history, statistics and entity names are kept. If « Add integration » offers to set up a new room instead, stop there and open an issue.
