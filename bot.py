import discord
import json
import random
import asyncio
import logging
import os

class DiscordStatusBot:
    def __init__(self):
        # Configuration des logs
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
        
        # Charger la configuration à partir des variables d'environnement
        self.config = self.charger_configuration()
        if not self.config:
            logging.error("Impossible de charger la configuration")
            exit(1)
        
        # Configuration des intents
        intents = discord.Intents.default()
        intents.message_content = False
        
        # Création du client
        self.client = discord.Client(intents=intents)
        
        # Événements
        self.setup_events()

    def charger_configuration(self):
        """Chargement de la configuration à partir des variables d'environnement"""
        config = {
            'token': os.getenv('TOKEN'),
            'status': os.getenv('STATUS', 'online'),
            'interval': int(os.getenv('INTERVAL', 60))
        }
        
        if not config['token']:
            logging.error("Token non fourni")
            return None
        
        return config

    def charger_statuts(self):
        """Chargement des statuts depuis le fichier"""
        try:
            with open('/app/statuts.txt', 'r', encoding='utf-8') as fichier:
                return [ligne.strip() for ligne in fichier.readlines() if ligne.strip()]
        except FileNotFoundError:
            logging.error("Fichier de statuts non trouvé")
            return []

    def setup_events(self):
        """Configuration des événements du bot"""
        @self.client.event
        async def on_ready():
            logging.info(f'Bot connecté : {self.client.user}')
            self.client.loop.create_task(self.changer_statut())

    # Déplacez changer_statut à l'extérieur de setup_events
    async def changer_statut(self):
        """Changement cyclique du statut"""
        await self.client.wait_until_ready()
        statuts = self.charger_statuts()
        if not statuts:
            logging.warning("Aucun statut disponible")
            return

        # Mapping des status Discord
        status_mapping = {
            'online': discord.Status.online,
            'idle': discord.Status.idle,
            'dnd': discord.Status.dnd,
            'invisible': discord.Status.invisible
        }

        # Récupérer le status depuis la configuration
        status_discord = status_mapping.get(self.config.get('status', 'online'), discord.Status.online)

        while not self.client.is_closed():
            try:
                # Sélection du statut
                statut = random.choice(statuts)
                
                # Changement de statut avec custom activity
                await self.client.change_presence(
                    status=status_discord, 
                    activity=discord.CustomActivity(name=statut)
                )
                logging.info(f"Statut changé : {statut}")
                
                # Délai entre les changements
                await asyncio.sleep(self.config.get('interval', 60))
            except Exception as e:
                logging.error(f"Erreur lors du changement de statut : {e}")
                await asyncio.sleep(30)  # Attente en cas d'erreur

    def executer(self):
        """Lancement du bot"""
        try:
            if self.config and 'token' in self.config:
                self.client.run(self.config['token'])
            else:
                logging.error("Token non trouvé dans la configuration")
        except discord.LoginFailure:
            logging.error("Échec de connexion - Vérifiez votre token")
        except Exception as e:
            logging.error(f"Erreur lors du lancement : {e}")

def main():
    bot = DiscordStatusBot()
    bot.executer()

if __name__ == "__main__":
    main()