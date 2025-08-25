# MamieHenriette 👵

**Bot multi-plateformes pour Discord, Twitch et YouTube Live**

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités](#fonctionnalités)
  - [Discord](#discord)
  - [Twitch](#twitch)
  - [YouTube Live](#youtube-live-en-développement)
  - [Interface d'administration](#interface-dadministration)
  - [Surveillance](#surveillance)
- [Installation](#installation)
  - [Prérequis](#prérequis)
  - [Création du bot Discord](#création-du-bot-discord)
  - [Démarrage rapide](#démarrage-rapide)
  - [Commandes Docker utiles](#commandes-docker-utiles)
  - [Mise à jour](#mise-à-jour)
- [Configuration avancée](#configuration-avancée)
  - [Variables d'environnement](#variables-denvironnement)
  - [Interface d'administration](#interface-dadministration-1)
- [Architecture du projet](#architecture-du-projet)
  - [Structure des modules](#structure-des-modules)
  - [Composants principaux](#composants-principaux)
- [Spécifications techniques](#spécifications-techniques)
  - [Base de données (SQLite)](#base-de-données-sqlite)
  - [Architecture multi-thread](#architecture-multi-thread)
  - [Dépendances principales](#dépendances-principales)
- [Développement](#développement)
  - [Installation locale](#installation-locale)
  - [Contribution](#contribution)

## Vue d'ensemble

Mamie Henriette est un bot intelligent open-source développé spécifiquement pour la communauté de [STEvE](https://www.facebook.com/ChaineSTEvE) sur [YouTube](https://www.youtube.com/@513v3), [Twitch](https://www.twitch.tv/chainesteve) et [Discord](https://discord.com/invite/UwAPqMJnx3).

> ⚠️ **Statut** : En cours de développement

### Caractéristiques principales

- Interface web d'administration complète
- Gestion multi-plateformes (Discord opérationnel, Twitch intégré, YouTube Live en développement)
- Système de notifications automatiques
- Base de données intégrée pour la persistance
- Surveillance optionnelle avec Zabbix *(non testée)*

## Fonctionnalités

### Discord
- **Statuts dynamiques** : Rotation automatique des humeurs (10 min)
- **Notifications Humble Bundle** : Surveillance et alertes automatiques (30 min)
- **Commandes personnalisées** : Gestion via interface web
- **Recherche ProtonDB** : Commande `!protondb <nom_du_jeu>` pour vérifier la compatibilité Linux/Steam Deck
- **Modération** : Outils intégrés

### Twitch
- **Chat bot** : Commandes et interactions automatiques

### YouTube Live *(en développement)*
- **Chat bot** : Modération et commandes
- **Événements** : Notifications de diffusion

### Interface d'administration
- **Dashboard** : Vue d'ensemble et statistiques
- **Configuration** : Tokens, paramètres des plateformes, configuration ProtonDB
- **Gestion des humeurs** : Création et modification des statuts
- **Commandes** : Édition des commandes personnalisées
- **Modération** : Outils de gestion communautaire

### Surveillance
- **Zabbix Agent 2** : Monitoring avancé *(non testé)*
- **Métriques** : Santé du bot et uptime

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
   - **Important activez les intents** :
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
```

```bash
cd MamieHenriette
```

```bash
# 2. Lancer avec Docker
docker compose up --build -d
```

> ⚠️ **Important** : Après configuration via l'interface web http://localhost:5000, **redémarrez le conteneur** pour que les changements soient pris en compte :
> ```bash
> docker compose restart MamieHenriette
> ```

### Commandes Docker utiles

```bash
# Logs en temps réel
docker compose logs -f MamieHenriette
```

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

## Configuration avancée

### Variables d'environnement

```yaml
environment:
  - ENABLE_ZABBIX=false     # Surveillance (non testée)
  - ZABBIX_SERVER=localhost
  - ZABBIX_HOSTNAME=MamieHenriette
```

### Interface d'administration

| Section | Fonction |
|---------|----------|
| **Configurations** | Tokens Discord/Twitch, paramètres généraux et configuration ProtonDB |
| **Humeurs** | Gestion des statuts Discord |
| **Commandes** | Commandes personnalisées multi-plateformes |
| **Messages** | Messages automatiques et notifications |
| **Modération** | Outils de gestion communautaire |

## Architecture du projet

### Structure des modules

```
├── database/          # Couche données
│   ├── models.py      # Modèles ORM
│   ├── helpers.py     # Utilitaires BDD
│   └── schema.sql     # Structure initiale
│
├── discordbot/        # Module Discord
│   └── __init__.py    # Bot et handlers
│
├── twitchbot/         # Module Twitch  
│   └── __init__.py    # Bot Twitch et handlers
│
├── protondb/          # Module ProtonDB
│   └── __init__.py    # API Algolia et recherche compatibilité
│
└── webapp/            # Interface d'administration
    ├── static/        # Assets statiques
    ├── templates/     # Vues HTML
    └── *.py           # Contrôleurs par section
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
- **Configuration** : Paramètres et tokens
- **Humeur** : Statuts Discord rotatifs
- **Message** : Messages périodiques *(planifié)*
- **GameBundle** : Historique Humble Bundle

### Architecture multi-thread
- **Thread 1** : Interface web Flask (port 5000)
- **Thread 2** : Bot Discord et tâches automatisées
- **Thread 3** : Bot Twitch et gestion du chat

### Dépendances principales
```
discord.py>=2.3.2         # API Discord
flask>=2.3.2              # Interface web
flask-sqlalchemy>=3.0.3   # ORM SQLAlchemy
requests>=2.32.4          # Client HTTP
waitress>=3.0.2           # Serveur WSGI
algoliasearch>=4          # API ProtonDB/SteamDB
twitchAPI>=4.5.0          # API Twitch
python-dotenv==1.0.0      # Variables d'environnement
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

---

*Mamie Henriette vous surveille ! 👵👀*
