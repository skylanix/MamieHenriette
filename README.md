Voici le README.md pour votre projet :

# 👵 Mamie Henrriette - Discord Status Bot 🤖

## 📖 Description

Mamie Henrriette est un bot Discord intelligent qui change automatiquement de statut, surveillant et gérant votre serveur avec une touche d'humour et de caractère.

## ✨ Fonctionnalités

- Changement cyclique automatique des statuts
- Configuration flexible via variables d'environnement
- Gestion des erreurs et logging
- Support multi-statuts Discord
- Déploiement simplifié avec Docker

## 🛠 Prérequis

- Docker
- Compte Discord et Token du bot

## 📦 Installation

1. Clonez le dépôt
```bash
git clone https://git.favrep.ch/lapatatedouce/MamieHenrriette
cd MamieHenrriette
```

2. Conteneur Docker

```bash
docker-compose up --build
```

## 🔧 Configuration

### Variables d'environnement

- `TOKEN`: Votre token Discord (obligatoire)
- `STATUS`: Statut initial (défaut: online)
- `INTERVAL`: Intervalle de changement de statut (défaut: 60 secondes)

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



# Installation poste de dev
## installation des dépendences systeme 
~~~
sudo apt install python3 python3-pip p
~~~

## creation de l'environnement python locale
Dans le projet
~~~
python3 -m venv .venv
~~~

Puis activer l'environnement : 
~~~
source .venv/bin/activate
~~~

## installation des dépendences python 

~~~
pip install -r requirements.txt
~~~

## execution

~~~
TOKEN=truc python3 bot.py
~~~