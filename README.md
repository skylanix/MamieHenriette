
# 👵 Mamie Henriette - Discord Status Bot 🤖

## 📖 Description

Mamie Henriette est un bot Discord intelligent qui change automatiquement de statut, surveillant et gérant votre serveur avec une touche d'humour et de caractère.

## ✨ Fonctionnalités

- Changement cyclique automatique des statuts
- Configuration flexible via variables d'environnement
- Gestion des erreurs et logging
- Support multi-statuts Discord
- Déploiement simplifié avec Docker
- 📊 Surveillance optionnelle avec Zabbix

## 🛠 Prérequis

- Docker et Docker Compose
- Compte Discord et Token du bot
- (Optionnel) Serveur Zabbix pour la surveillance

## 📦 Installation

1. Clonez le dépôt
```bash
git clone https://git.favrep.ch/lapatatedouce/MamieHenrriette
cd MamieHenrriette
```

2. Copiez le fichier de configuration
```bash
cp .env.example .env
```

3. Éditez le fichier `.env` avec vos paramètres
```bash
nano .env
```

4. Démarrez le conteneur Docker

**Mode développement (avec logs):**
```bash
docker-compose up --build
```

**Mode production (en arrière-plan):**
```bash
docker-compose up --build -d
```

**Voir les logs:**
```bash
docker-compose logs -f discord-bot
```

**Arrêter le conteneur:**
```bash
docker-compose down
```

## 🔧 Configuration

### Variables d'environnement principales

- `TOKEN`: Votre token Discord (obligatoire)
- `STATUS`: Statut initial (défaut: online)
- `INTERVAL`: Intervalle de changement de statut (défaut: 3600 secondes)

### 📊 Configuration Zabbix (optionnelle)

- `ENABLE_ZABBIX`: Activer la surveillance Zabbix (défaut: false)
- `ZABBIX_SERVER`: Adresse du serveur Zabbix
- `ZABBIX_HOSTNAME`: Nom d'hôte pour identifier le bot
- `ZABBIX_PORT`: Port d'exposition Zabbix (défaut: 10050)

#### Métriques surveillées par Zabbix

- Statut du bot Discord
- Temps de fonctionnement (uptime)
- Utilisation mémoire
- Erreurs et avertissements dans les logs
- Connectivité à Discord

#### Activation de Zabbix

Dans votre fichier `.env` :
```bash
ENABLE_ZABBIX=true
ZABBIX_SERVER=votre-serveur-zabbix.com
ZABBIX_HOSTNAME=MamieHenriette
```

### Fichier `statuts.txt`

Créez un fichier `statuts.txt` avec vos statuts, un par ligne.

Exemple :
```
Surveiller le serveur
Mamie est là !
En mode supervision
```

## 📋 Dépendances

- discord.py==2.3.2
- python-dotenv==1.0.0

---

# 🖥️ Installation environnement de développement

## Installation des dépendances système

```bash
sudo apt install python3 python3-pip
```

## Création de l'environnement Python local

Dans le dossier du projet :

```bash
python3 -m venv .venv
```

Puis activer l'environnement :

```bash
source .venv/bin/activate
```

## Installation des dépendances Python

```bash
pip install -r requirements.txt
```

## Exécution

```bash
python3 run-web.py
```

# Structure du projet

```
.
|-- database : module de connexion à la BDD
|   |-- __init.py__
|   |-- models.py : contient les pojo représentant chaque table
|   |-- schema.sql : contient un scrip sql d'initialisation de la bdd, celui-ci doit être réentrant
|
|-- discordbot : module de connexion à discord
|   |-- __init.py__
|
|-- webapp : module du site web d'administration
|   |-- static : Ressource fixe directement accessible par le navigateir
|   |   |-- css
|   |   |-- ...
|   |
|   |-- template : Fichier html
|   |   |-- template.html : structure globale du site
|   |   |-- commandes.html : page de gestion des commandes
|   |   |-- ...
|   |
|   |-- __init.py__
|   |-- index.py : controller de la page d'acceuil
|   |-- commandes.py : controller de gestion des commandes
|   |-- ...
|
|-- run-web.py : launcher
```