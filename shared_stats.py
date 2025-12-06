
import threading
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime

@dataclass
class BotStats:
    """Statistiques des bots"""
    # Discord
    discord_connected: bool = False
    discord_guilds: int = 0
    discord_members: int = 0
    discord_channels: int = 0
    discord_bot_name: str = ""
    discord_bot_id: int = 0
    
    # Twitch
    twitch_connected: bool = False
    twitch_channel: str = ""
    
    # Cogs/Fonctionnalités activées
    cogs_enabled: Dict[str, bool] = field(default_factory=dict)
    
    # Dernière mise à jour
    last_update: datetime = None

class StatsManager:
    """Gestionnaire thread-safe des statistiques"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._stats = BotStats()
                    cls._instance._stats_lock = threading.Lock()
        return cls._instance
    
    def update_discord_stats(self, connected: bool = None, guilds: int = None, 
                             members: int = None, channels: int = None,
                             bot_name: str = None, bot_id: int = None):
        """Met à jour les stats Discord"""
        with self._stats_lock:
            if connected is not None:
                self._stats.discord_connected = connected
            if guilds is not None:
                self._stats.discord_guilds = guilds
            if members is not None:
                self._stats.discord_members = members
            if channels is not None:
                self._stats.discord_channels = channels
            if bot_name is not None:
                self._stats.discord_bot_name = bot_name
            if bot_id is not None:
                self._stats.discord_bot_id = bot_id
            self._stats.last_update = datetime.now()
    
    def update_twitch_stats(self, connected: bool = None, channel: str = None):
        """Met à jour les stats Twitch"""
        with self._stats_lock:
            if connected is not None:
                self._stats.twitch_connected = connected
            if channel is not None:
                self._stats.twitch_channel = channel
            self._stats.last_update = datetime.now()
    
    def update_cogs(self, cogs: Dict[str, bool]):
        """Met à jour les cogs activés"""
        with self._stats_lock:
            self._stats.cogs_enabled = cogs.copy()
            self._stats.last_update = datetime.now()
    
    def get_stats(self) -> BotStats:
        """Retourne une copie des stats"""
        with self._stats_lock:
            return BotStats(
                discord_connected=self._stats.discord_connected,
                discord_guilds=self._stats.discord_guilds,
                discord_members=self._stats.discord_members,
                discord_channels=self._stats.discord_channels,
                discord_bot_name=self._stats.discord_bot_name,
                discord_bot_id=self._stats.discord_bot_id,
                twitch_connected=self._stats.twitch_connected,
                twitch_channel=self._stats.twitch_channel,
                cogs_enabled=self._stats.cogs_enabled.copy(),
                last_update=self._stats.last_update
            )


class DiscordBridge:
    """
    Pont de communication entre Flask et le bot Discord.
    Permet d'exécuter des actions Discord depuis Flask de manière thread-safe.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._bot = None
                    cls._instance._loop = None
        return cls._instance
    
    def register_bot(self, bot, loop):
        """Enregistre le bot Discord et sa boucle événementielle"""
        with self._lock:
            self._bot = bot
            self._loop = loop
            logging.info("Bot Discord enregistré dans le bridge")
    
    def is_ready(self) -> bool:
        """Vérifie si le bot est prêt"""
        return self._bot is not None and self._loop is not None and not self._loop.is_closed()
    
    def get_text_channels(self) -> List[Dict]:
        """Retourne la liste des canaux texte disponibles"""
        if not self.is_ready():
            return []
        
        channels = []
        try:
            for guild in self._bot.guilds:
                for channel in guild.text_channels:
                    channels.append({
                        'id': channel.id,
                        'name': channel.name,
                        'guild_name': guild.name,
                        'guild_id': guild.id
                    })
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des canaux: {e}")
        
        return channels
    
    def send_message(self, channel_id: int, message: str) -> tuple[bool, str]:
        """
        Envoie un message dans un canal Discord.
        Retourne (succès, message d'erreur ou de confirmation)
        """
        if not self.is_ready():
            return False, "Le bot Discord n'est pas connecté"
        
        if not message or not message.strip():
            return False, "Le message ne peut pas être vide"
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send_message_async(channel_id, message),
                self._loop
            )
            # Attendre le résultat avec timeout de 10 secondes
            return future.result(timeout=10)
        except asyncio.TimeoutError:
            return False, "Timeout lors de l'envoi du message"
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi du message: {e}")
            return False, f"Erreur: {str(e)}"
    
    async def _send_message_async(self, channel_id: int, message: str) -> tuple[bool, str]:
        """Coroutine interne pour envoyer le message"""
        try:
            channel = self._bot.get_channel(channel_id)
            if not channel:
                return False, "Canal introuvable"
            
            await channel.send(message)
            return True, f"Message envoyé dans #{channel.name}"
        except Exception as e:
            return False, f"Erreur: {str(e)}"

    def sync_invites(self, guild_id: int = None) -> dict:
        """Synchronise les invitations Discord avec la base de données"""
        if not self.is_ready():
            return {'success': False, 'message': "Le bot Discord n'est pas connecté", 'synced': 0}
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._bot.syncInvites(guild_id),
                self._loop
            )
            result = future.result(timeout=30)
            result['success'] = True
            return result
        except asyncio.TimeoutError:
            return {'success': False, 'message': "Timeout lors de la synchronisation", 'synced': 0}
        except Exception as e:
            logging.error(f"Erreur lors de la synchronisation des invitations: {e}")
            return {'success': False, 'message': f"Erreur: {str(e)}", 'synced': 0}

    def revoke_invite(self, invite_code: str) -> dict:
        """Révoque une invitation Discord"""
        if not self.is_ready():
            return {'success': False, 'message': "Le bot Discord n'est pas connecté"}
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._bot.revokeInvite(invite_code),
                self._loop
            )
            return future.result(timeout=10)
        except asyncio.TimeoutError:
            return {'success': False, 'message': "Timeout lors de la révocation"}
        except Exception as e:
            logging.error(f"Erreur lors de la révocation de l'invitation: {e}")
            return {'success': False, 'message': f"Erreur: {str(e)}"}

    def get_invites(self, guild_id: int = None, include_revoked: bool = False) -> list:
        """Récupère les invitations depuis la base de données"""
        if not self.is_ready():
            return []
        
        try:
            return self._bot.getInvites(guild_id, include_revoked)
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des invitations: {e}")
            return []

    def get_guilds(self) -> list:
        """Retourne la liste des guilds"""
        if not self.is_ready():
            return []
        
        try:
            return self._bot.getAllGuilds()
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des guilds: {e}")
            return []


# Instances globales
stats_manager = StatsManager()
discord_bridge = DiscordBridge()

