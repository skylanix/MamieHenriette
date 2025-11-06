# MamieHenriette 👵

**Bot multi-plateformes pour Discord, Twitch et YouTube Live**

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités](#fonctionnalités)
  - [Discord](#discord)
  - [Twitch](#twitch)
  - [YouTube Live](#youtube-live-en-développement)
  - [Interface d'administration](#interface-dadministration)
- [Installation](#installation)
  - [Prérequis](#prérequis)
  - [Création du bot Discord](#création-du-bot-discord)
  - [Démarrage rapide](#démarrage-rapide)
  - [Build local (développement)](#build-local-développement)
  - [Déploiement avec Portainer](#déploiement-avec-portainer)
  - [Volumes persistants](#volumes-persistants)
  - [Commandes Docker utiles](#commandes-docker-utiles)
  - [Mise à jour](#mise-à-jour)
- [Architecture du projet](#architecture-du-projet)
  - [Interface d'administration](#interface-dadministration-1)
  - [Structure des modules](#structure-des-modules)
  - [Composants principaux](#composants-principaux)
- [Spécifications techniques](#spécifications-techniques)
  - [Base de données (SQLite)](#base-de-données-sqlite)
  - [Architecture multi-thread](#architecture-multi-thread)
  - [Monitoring et logging](#monitoring-et-logging)
  - [Dépendances principales](#dépendances-principales)
- [Développement](#développement)
  - [Installation locale](#installation-locale)
  - [Contribution](#contribution)
- [Licence](#licence)

## Vue d'ensemble

Mamie Henriette est un bot intelligent open-source développé spécifiquement pour la communauté de [STEvE](https://www.facebook.com/ChaineSTEvE) sur [YouTube](https://www.youtube.com/@513v3), [Twitch](https://www.twitch.tv/chainesteve) et [Discord](https://discord.com/invite/UwAPqMJnx3).

> ⚠️ **Statut** : En cours de développement

### Caractéristiques principales

- Interface web d'administration complète
- Gestion multi-plateformes (Discord opérationnel, Twitch intégré, YouTube Live en développement)
- Système de notifications automatiques
- Base de données intégrée pour la persistance

## Fonctionnalités

### Discord
- **Statuts dynamiques** : Rotation automatique des humeurs (10 min)
- **Notifications Humble Bundle** : Surveillance et alertes automatiques (30 min)
- **Commandes personnalisées** : Gestion via interface web
- **Recherche ProtonDB** :
  - Commande `!protondb nom_du_jeu` ou `!pdb nom_du_jeu` pour vérifier la compatibilité Linux/Steam Deck
  - Recherche intelligente avec support des alias de jeux
  - Affichage du score de compatibilité, nombre de rapports et lien direct
- **Modération** : Système complet de modération avec historique
  - Avertissements : `!averto`, `!warn`, `!av`, `!avertissement`
  - Gestion des avertissements : `!delaverto`, `!removewarn`, `!delwarn`
  - Liste des événements : `!warnings`, `!listevent`, `!listwarn`
  - Inspection utilisateur : `!inspect` (historique complet, date d'arrivée, compte)
  - Bannissement : `!ban`, `!unban` (avec invitation automatique), `!banlist`
  - Expulsion : `!kick`
  - Aide : `!aide`, `!help`
  - Messages de bienvenue et départ personnalisables
  - Panneau d'administration web pour consulter l'historique

### Twitch
- **Chat bot** : Commandes et interactions automatiques
- **Alertes Live** : 
  - Surveillance automatique des streamers
  - Support jusqu'à 100 chaînes simultanément
  - Notifications Discord avec aperçu du stream
  - Gestion via interface d'administration
  - Détection automatique des débuts/fins de stream

### YouTube Live *(en développement)*
- **Chat bot** : Modération et commandes
- **Événements** : Notifications de diffusion

### Interface d'administration
- **Dashboard** : Vue d'ensemble et statistiques
- **Configuration** : Tokens, paramètres des plateformes, configuration ProtonDB
- **Gestion des humeurs** : Création et modification des statuts
- **Commandes** : Édition des commandes personnalisées
- **Modération** : Outils de gestion communautaire


## Installation

### Prérequis
- [Docker Engine](https://docs.docker.com/engine/install/) ou [Docker Desktop](https://docs.docker.com/desktop/)
- Token Discord pour le bot
- Token Twitch (optionnel) pour les fonctionnalités Twitch

### Création du bot Discord

Avant d'installer MamieHenriette, vous devez créer un bot Discord et obtenir son token :

1. **Accéder au portail développeur** : Rendez-vous sur [Discord Developer Portal](https://discord.com/developers/applications)

2. **Créer une nouvelle application** :
   - Cliquez sur "New Application"
   - Donnez un nom à votre bot (ex: "MmeMichue")
   - Acceptez les conditions et cliquez sur "Create"

3. **Configurer le bot** :
   - Dans le menu latéral, cliquez sur "Bot"
   - Ajoutez une photo de profil et un pseudo à votre bot
   - **Important : activez les intents** :
     - ☑️ Presence Intent
     - ☑️ Server Members Intent 
     - ☑️ Message Content Intent
   - Cliquez sur "Save Changes"

4. **Récupérer le token** :
   - Dans la section "Token", cliquez sur "Reset Token"
   - Copiez le token généré (gardez-le secret !)

5. **Inviter le bot sur votre serveur** :
   - Allez dans "OAuth2" > "URL Generator"
   - Sélectionnez les scopes : `bot` et `applications.commands`
   - Sélectionnez les permissions nécessaires (Administrator recommandé pour simplifier)
   - Utilisez l'URL générée pour inviter le bot sur votre serveur

### Démarrage rapide

```bash
# 1. Cloner le projet
git clone https://github.com/skylanix/MamieHenriette.git
cd MamieHenriette
```

```bash
# 2. Récupérer l'image depuis Docker Hub et lancer
docker compose pull
docker compose up -d
```

> 📝 L'interface web sera accessible sur http://localhost:5000
>
> ⚠️ **Important** : Après configuration via l'interface web, **redémarrez le conteneur** pour que les changements soient pris en compte :
> ```bash
> docker compose restart MamieHenriette
> ```

### Build local (développement)

Si vous souhaitez modifier le code et builder l'image localement :

```bash
# 1. Cloner et accéder au projet
git clone https://github.com/skylanix/MamieHenriette.git
cd MamieHenriette
```

```bash
# 2. Modifier le docker-compose.yml
# Commentez la ligne 'image:' et décommentez la section 'build:' :
```

```yaml
services:
  MamieHenriette:
    container_name: MamieHenriette
    # image: skylanix/mamiehenriette:latest  # ← Commentez cette ligne
    restart: unless-stopped
    build:                                   # ← Décommentez cette lignes
    image: mamiehenriette                    # ← Décommentez cette lignes
    # ... reste de la configuration
```

```bash
# 3. Builder et lancer
docker compose up --build -d
```

### Déploiement avec Portainer

Si vous utilisez Portainer pour gérer vos conteneurs Docker, voici la configuration Docker Compose à utiliser :

```yaml
services:
  mamiehenriette:
    container_name: MamieHenriette
    image: ghcr.io/skylanix/mamiehenriette:latest
    restart: unless-stopped
    environment:
      TZ: Europe/Paris
    volumes:
      # Adaptez ces chemins selon votre configuration
      - ./instance:/app/instance
      - ./logs:/app/logs
    ports:
      - 5000:5000

  watchtower:  # Mise à jour automatique de l'image
    image: containrrr/watchtower:latest
    container_name: watchtower
    restart: unless-stopped
    environment:
      TZ: Europe/Paris
      WATCHTOWER_INCLUDE: "MamieHenriette"
      WATCHTOWER_SCHEDULE: "0 */30 * * * *"  # Vérification toutes les 30 min
      WATCHTOWER_MONITOR_ONLY: "false"
      WATCHTOWER_CLEANUP: "true"
      WATCHTOWER_INCLUDE_RESTARTING: "true"
      # Décommentez pour activer les notifications Discord :
      # WATCHTOWER_NOTIFICATION_URL: "discord://token@id"
      # WATCHTOWER_NOTIFICATIONS: shoutrrr
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  # Décommentez pour accéder à la base de données via interface web (localhost:5001)
  # sqlite-web:
  #   image: ghcr.io/coleifer/sqlite-web:latest
  #   container_name: sqlite_web
  #   ports:
  #     - "5001:8080"
  #   volumes:
  #     - ./instance/database.db:/data/database.db
  #   environment:
  #     - SQLITE_DATABASE=/data/database.db
```

**Étapes dans Portainer :**

1. **Accéder à Portainer** : Ouvrez votre interface Portainer (généralement http://votre-serveur:9000)

2. **Créer une Stack** :
   - Allez dans "Stacks" → "Add stack"
   - Donnez un nom : `MamieHenriette`
   - Collez la configuration ci-dessus dans l'éditeur

3. **Adapter les chemins** :
   - Remplacez `/chemin/vers/instance` par le chemin absolu sur votre serveur (ex: `/opt/containers/MamieHenriette/instance`)
   - Remplacez `/chemin/vers/logs` par le chemin absolu sur votre serveur (ex: `/opt/containers/MamieHenriette/logs`)

4. **Déployer** :
   - Cliquez sur "Deploy the stack"
   - Attendez que le conteneur démarre

5. **Accéder à l'interface** :
   - Ouvrez http://votre-serveur:5000
   - Configurez le bot via l'interface web
   - Redémarrez le conteneur depuis Portainer après configuration

### Volumes persistants
- `./instance/` : Base de données SQLite et configuration
- `./logs/` : Logs applicatifs rotatifs (50MB max par fichier)

### Commandes Docker utiles

```bash
# Logs d'un conteneur en cours d'exécution
docker logs -f MamieHenriette
```

```bash
# Redémarrer
docker compose restart MamieHenriette
```

```bash
# Arrêter
docker compose down
```

### Mise à jour

#### Avec Docker (recommandé)
```bash
# 1. Arrêter les conteneurs
docker compose down

# 2. Récupérer les dernières modifications
git pull origin main

# 3. Mettre à jour l'image Docker
docker compose pull

# 4. Reconstruire et relancer
docker compose up --build -d
```

#### Sans Docker (installation locale)
```bash
# 1. Arrêter l'application
# (Ctrl+C si elle tourne en premier plan)

# 2. Récupérer les modifications
git pull origin main

# 3. Mettre à jour les dépendances
pip install -r requirements.txt

# 4. Relancer
python run-web.py
```

## Architecture du projet

### Interface d'administration

| Section | Fonction |
|---------|----------|
| **Configurations** | Tokens Discord/Twitch, paramètres généraux et configuration ProtonDB |
| **Humeurs** | Gestion des statuts Discord rotatifs |
| **Commandes** | Commandes personnalisées multi-plateformes (Discord/Twitch) |
| **Alertes Live** | Configuration surveillance streamers Twitch avec notifications Discord |
| **Messages** | Messages automatiques et notifications périodiques |
| **Modération** | Outils de gestion communautaire |

### Structure des modules

```
├── database/          # Couche données
│   ├── models.py      # Modèles ORM
│   ├── helpers.py     # Utilitaires BDD
│   └── schema.sql     # Structure initiale
│
├── discordbot/        # Module Discord
│   ├── __init__.py    # Bot et handlers principaux
│   └── humblebundle.py # Surveillance Humble Bundle
│
├── twitchbot/         # Module Twitch  
│   ├── __init__.py    # Bot Twitch et handlers
│   └── live_alert.py  # Surveillance des streams live
│
├── protondb/          # Module ProtonDB
│   └── __init__.py    # API Algolia et recherche compatibilité
│
└── webapp/            # Interface d'administration
    ├── static/        # Assets statiques (CSS, JS, images)
    ├── templates/     # Vues HTML Jinja2
    ├── live_alert.py  # Gestion des alertes Twitch
    ├── twitch_auth.py # Authentification Twitch OAuth
    └── *.py           # Autres contrôleurs par section
```

### Composants principaux

| Fichier | Rôle |
|---------|------|
| `run-web.py` | Point d'entrée principal |
| `start.sh` | Script de démarrage Docker |
| `docker-compose.yml` | Configuration des services |
| `requirements.txt` | Dépendances Python |

## Spécifications techniques

### Base de données (SQLite)
- **Configuration** : Paramètres et tokens des plateformes
- **Humeur** : Statuts Discord rotatifs avec gestion automatique
- **Commande** : Commandes personnalisées multi-plateformes (Discord/Twitch)
- **LiveAlert** : Configuration surveillance streamers Twitch (nom, canal Discord, statut)
- **GameAlias** : Alias pour améliorer les recherches ProtonDB
- **GameBundle** : Historique et notifications Humble Bundle
- **Message** : Messages automatiques périodiques (implémenté)
- **Moderation** : Historique complet des actions de modération (avertissements, bans, kicks, unbans) avec raison, staff et timestamp

### Architecture multi-thread
- **Thread 1** : Interface web Flask (port 5000) avec logging rotatif
- **Thread 2** : Bot Discord et tâches automatisées (humeurs, Humble Bundle)
- **Thread 3** : Bot Twitch et surveillance live streams (vérification 5min)

### Monitoring et logging
- **Healthcheck Docker** : Surveillance processus Python + détection erreurs logs
- **Logs rotatifs** : Fichiers limités à 50MB avec rotation automatique
- **Persistance** : Logs sauvegardés sur l'hôte dans `./logs/`

### Dépendances principales
```
discord.py==2.3.2         # API Discord avec support async
flask>=2.3.2              # Interface web et API REST
flask-sqlalchemy>=3.0.3   # ORM SQLAlchemy pour base de données
flask[async]              # Extensions async pour Flask
requests>=2.32.4          # Client HTTP pour APIs externes
waitress>=3.0.2           # Serveur WSGI de production
algoliasearch>=4,<5       # API ProtonDB via Algolia
twitchAPI>=4.5.0          # API Twitch pour streams et chat
python-dotenv==1.0.0      # Gestion variables d'environnement
aiohttp>=3.7.4,<4         # Client HTTP async (requis par discord.py)
audioop-lts               # Compatibilité audio Python 3.13+
```

## Développement

### Installation locale
```bash
python3 -m venv venv
```
```bash
source venv/bin/activate
```
```bash
pip install -r requirements.txt
```
```bash
python run-web.py
```

### Contribution
1. Fork du projet
2. Branche feature
3. Pull Request

## Licence

    MamieHenriette - Bot multi-plateformes pour Discord, Twitch et YouTube Live
    Copyright (C) 2025 Philippe Favre

    Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le modifier
    selon les termes de la Licence Publique Générale GNU Affero telle que publiée
    par la Free Software Foundation, soit la version 3 de la Licence, ou
    (à votre choix) toute version ultérieure.

    Ce programme est distribué dans l'espoir qu'il sera utile,
    mais SANS AUCUNE GARANTIE ; sans même la garantie implicite de
    COMMERCIALISATION ou d'ADÉQUATION À UN USAGE PARTICULIER. Voir la
    Licence Publique Générale GNU Affero pour plus de détails.

    Vous devriez avoir reçu une copie de la Licence Publique Générale GNU Affero
    avec ce programme. Si ce n'est pas le cas, voir <https://www.gnu.org/licenses/>.

---

*Mamie Henriette vous surveille ! 👵👀*
