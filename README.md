# MamieHenriette 👵

**Bot multi-plateformes pour Discord, Twitch et YouTube Live**


## Vue d'ensemble

Mamie Henriette est un bot intelligent open-source développé spécifiquement pour la communauté de [STEvE](https://www.facebook.com/ChaineSTEvE) sur [YouTube](https://www.youtube.com/@513v3), [Twitch](https://www.twitch.tv/chainesteve) et [Discord](https://discord.com/invite/UwAPqMJnx3).

> ⚠️ **Statut** : En cours de développement

### Caractéristiques principales

- Interface web d'administration complète
- Gestion multi-plateformes (Discord, Twitch, YouTube Live)
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

### Twitch *(en développement)*
- **Chat bot** : Commandes et interactions
- **Événements live** : Notifications de stream

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
   - **Important** : Activez les "Privileged Gateway Intents" :
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

### Configuration

1. **Interface web** : Accédez à http://localhost
2. **Token Discord** : Section "Configurations"
3. **ProtonDB** : Configurer l'API Algolia dans "Configurations" pour activer `!protondb`
4. **Humeurs** : Définir les statuts du bot
5. **Canaux** : Configurer les notifications

> ⚠️ **Important** : Après avoir configuré le token Discord, les humeurs et autres fonctionnalités via l'interface web, **redémarrez le conteneur** pour que les changements soient pris en compte :
> ```bash
> docker compose restart mamiehenriette
> ```

### Commandes Docker utiles

```bash
# Logs en temps réel
docker compose logs -f mamiehenriette
```

```bash
# Logs d'un conteneur en cours d'exécution
docker logs -f mamiehenriette
```

```bash
# Redémarrer
docker compose restart mamiehenriette
```

```bash
# Arrêter
docker compose down
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
| **Configurations** | Tokens, paramètres généraux et configuration ProtonDB |
| **Humeurs** | Gestion des statuts Discord |
| **Commandes** | Commandes personnalisées |
| **Modération** | Outils de gestion |

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

### Dépendances principales
```
discord.py         # API Discord
flask              # Interface web
requests           # Client HTTP
waitress           # Serveur WSGI
algoliasearch      # API ProtonDB/SteamDB
```

## Développement

### Installation locale
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run-web.py
```

### Contribution
1. Fork du projet
2. Branche feature
3. Pull Request

---

*Mamie Henriette vous surveille ! 👵👀*