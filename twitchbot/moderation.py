import re
import logging
from datetime import datetime

from twitchAPI.twitch import Twitch
from twitchAPI.chat import ChatMessage

from database import db
from database.models import TwitchAnnouncement, TwitchModerationLog, TwitchBannedWord
from webapp import webapp

logger = logging.getLogger('twitch-moderation')
logger.setLevel(logging.INFO)

last_multitwitch: str = None
games_disabled: bool = False


def _log_action(action: str, moderator: str, target: str = None, details: str = None):
    with webapp.app_context():
        log = TwitchModerationLog(
            action=action,
            moderator=moderator,
            target=target,
            details=details,
            created_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()


def _is_moderator(msg: ChatMessage) -> bool:
    return msg.user.mod or msg.user.name.lower() == msg.room.name.lower()


async def _get_broadcaster_id(twitch: Twitch, channel: str) -> str:
    async for user in twitch.get_users(logins=[channel]):
        return user.id
    return None


async def _get_user_id(twitch: Twitch, username: str) -> str:
    async for user in twitch.get_users(logins=[username]):
        return user.id
    return None


async def _get_moderator_id(twitch: Twitch) -> str:
    async for user in twitch.get_users():
        return user.id
    return None


async def timeout_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    if len(args) < 1:
        await msg.reply("Usage: !timeout <viewer> [minutes] [raison]")
        return
    
    viewer = args[0].lstrip('@')
    duration = 180  # 3 minutes par défaut
    reason = "Timeout"
    
    # Si args[1] est un nombre, c'est la durée, sinon c'est la raison
    if len(args) >= 2:
        try:
            duration = int(args[1]) * 60
            # Tout ce qui suit est la raison
            if len(args) >= 3:
                reason = ' '.join(args[2:])
        except ValueError:
            # args[1] n'est pas un nombre, donc tout depuis args[1] est la raison
            reason = ' '.join(args[1:])
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    user_id = await _get_user_id(twitch, viewer)
    
    if user_id:
        await twitch.ban_user(broadcaster_id, moderator_id, user_id, reason=reason, duration=duration)
        # Log avec durée et raison
        log_details = f"{duration}s - {reason}"
        _log_action("timeout", msg.user.name, viewer, log_details)
        logger.info(f'{viewer} timeout pour {duration}s par {msg.user.name} - Raison: {reason}')


async def ban_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    if len(args) < 1:
        await msg.reply("Usage: !ban <viewer1> [viewer2] ...")
        return
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    for viewer in args[:5]:
        viewer = viewer.lstrip('@')
        user_id = await _get_user_id(twitch, viewer)
        if user_id:
            await twitch.ban_user(broadcaster_id, moderator_id, user_id, reason="Ban")
            _log_action("ban", msg.user.name, viewer)
            logger.info(f'{viewer} banni par {msg.user.name}')


async def unban_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    if len(args) < 1:
        await msg.reply("Usage: !unban <viewer1> [viewer2] ...")
        return
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    for viewer in args[:5]:
        viewer = viewer.lstrip('@')
        user_id = await _get_user_id(twitch, viewer)
        if user_id:
            await twitch.unban_user(broadcaster_id, moderator_id, user_id)
            _log_action("unban", msg.user.name, viewer)
            logger.info(f'{viewer} débanni par {msg.user.name}')


async def clean_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    if len(args) >= 1:
        viewer = args[0].lstrip('@')
        user_id = await _get_user_id(twitch, viewer)
        if user_id:
            await twitch.delete_chat_messages(broadcaster_id, moderator_id, user_id=user_id)
            _log_action("clean", msg.user.name, viewer)
            logger.info(f'Messages de {viewer} supprimés par {msg.user.name}')
    else:
        await twitch.delete_chat_messages(broadcaster_id, moderator_id)
        _log_action("clean", msg.user.name, None, "Chat complet")
        logger.info(f'Chat nettoyé par {msg.user.name}')


async def shieldmode_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    if len(args) < 1:
        await msg.reply("Usage: !shieldmode <on/off>")
        return
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    is_active = args[0].lower() == "on"
    await twitch.update_shield_mode_status(broadcaster_id, moderator_id, is_active)
    _log_action("shieldmode", msg.user.name, None, "on" if is_active else "off")
    logger.info(f'Shield mode {"activé" if is_active else "désactivé"} par {msg.user.name}')


async def settitle_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply("Usage: !settitle <titre>")
        return
    
    title = parts[1]
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    
    await twitch.modify_channel_information(broadcaster_id, title=title)
    _log_action("settitle", msg.user.name, None, title)
    logger.info(f'Titre changé en "{title}" par {msg.user.name}')


async def setgame_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply("Usage: !setgame <jeu>")
        return
    
    game_name = parts[1]
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    
    game_id = None
    async for game in twitch.get_games(names=[game_name]):
        game_id = game.id
        break
    
    if game_id:
        await twitch.modify_channel_information(broadcaster_id, game_id=game_id)
        _log_action("setgame", msg.user.name, None, game_name)
        logger.info(f'Jeu changé en "{game_name}" par {msg.user.name}')
    else:
        await msg.reply(f"Jeu '{game_name}' introuvable")


async def subon_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    await twitch.update_chat_settings(broadcaster_id, moderator_id, subscriber_mode=True)
    _log_action("subon", msg.user.name)
    logger.info(f'Mode abonnés activé par {msg.user.name}')


async def suboff_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    await twitch.update_chat_settings(broadcaster_id, moderator_id, subscriber_mode=False)
    _log_action("suboff", msg.user.name)
    logger.info(f'Mode abonnés désactivé par {msg.user.name}')


async def follon_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    duration = 10
    if len(args) >= 1:
        try:
            duration = int(args[0])
        except ValueError:
            duration = 10
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    await twitch.update_chat_settings(broadcaster_id, moderator_id, follower_mode=True, follower_mode_duration=duration)
    _log_action("follon", msg.user.name, None, f"{duration}min")
    logger.info(f'Mode followers ({duration}min) activé par {msg.user.name}')


async def folloff_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    await twitch.update_chat_settings(broadcaster_id, moderator_id, follower_mode=False)
    _log_action("folloff", msg.user.name)
    logger.info(f'Mode followers désactivé par {msg.user.name}')


async def emoteon_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    await twitch.update_chat_settings(broadcaster_id, moderator_id, emote_mode=True)
    _log_action("emoteon", msg.user.name)
    logger.info(f'Mode emote activé par {msg.user.name}')


async def emoteoff_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    
    await twitch.update_chat_settings(broadcaster_id, moderator_id, emote_mode=False)
    _log_action("emoteoff", msg.user.name)
    logger.info(f'Mode emote désactivé par {msg.user.name}')


async def multitwitch_command(msg: ChatMessage, twitch: Twitch):
    global last_multitwitch
    
    args = msg.text.split()[1:]
    
    if len(args) == 0:
        if last_multitwitch:
            await msg.reply(last_multitwitch)
        return
    
    if not _is_moderator(msg):
        return
    
    if args[0].lower() == "reset":
        last_multitwitch = None
        logger.info(f'MultiTwitch reset par {msg.user.name}')
        return
    
    if args[0].lower() == "auto":
        broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
        async for channel in twitch.get_channel_information(broadcaster_id):
            title = channel.title
            mentions = re.findall(r'@(\w+)', title)
            if mentions:
                channels = [msg.room.name] + mentions
                last_multitwitch = f"https://multitwitch.live/{'/'.join(channels)}"
                await msg.reply(last_multitwitch)
            return
        return
    
    channels = []
    for arg in args:
        if arg == "@":
            channels.append(msg.room.name)
        else:
            channels.append(arg.lstrip('@'))
    
    last_multitwitch = f"https://multitwitch.live/{'/'.join(channels)}"
    await msg.reply(last_multitwitch)
    logger.info(f'MultiTwitch créé par {msg.user.name}: {last_multitwitch}')


async def ann_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    if len(args) < 2:
        await msg.reply("Usage: !ann <alias> <on/off/toggle>")
        return
    
    alias = args[0]
    action = args[1].lower()
    
    with webapp.app_context():
        announcement = TwitchAnnouncement.query.filter_by(name=alias).first()
        if not announcement:
            await msg.reply(f"Annonce '{alias}' introuvable")
            return
        
        if action == "on":
            announcement.enable = True
        elif action == "off":
            announcement.enable = False
        elif action == "toggle":
            announcement.enable = not announcement.enable
        else:
            await msg.reply("Action invalide: on/off/toggle")
            return
        
        db.session.commit()
        status = "activée" if announcement.enable else "désactivée"
        logger.info(f'Annonce {alias} {status} par {msg.user.name}')
        await msg.reply(f"Annonce '{alias}' {status}")


async def no_game_command(msg: ChatMessage, twitch: Twitch):
    global games_disabled
    
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    if len(args) < 1:
        await msg.reply("Usage: !no_game <on/off>")
        return
    
    action = args[0].lower()
    
    if action == "on":
        games_disabled = True
        logger.info(f'Jeux désactivés par {msg.user.name}')
        await msg.reply("Jeux désactivés")
    elif action == "off":
        games_disabled = False
        logger.info(f'Jeux activés par {msg.user.name}')
        await msg.reply("Jeux activés")


def are_games_disabled() -> bool:
    return games_disabled


async def check_message_for_banned_words(msg: ChatMessage, twitch: Twitch) -> bool:
    """
    Vérifie si le message contient des mots interdits.
    Retourne True si le message est valide, False s'il doit être bloqué.
    """
    # Modérateurs et broadcaster exemptés
    if msg.user.mod or msg.user.name.lower() == msg.room.name.lower():
        return True
    
    with webapp.app_context():
        banned_words = TwitchBannedWord.query.filter_by(enabled=True).all()
        if not banned_words:
            return True
        
        message_lower = msg.text.lower()
        
        for banned_word_entry in banned_words:
            word = banned_word_entry.word.lower()
            # Recherche du mot dans le message (mot entier ou partie de mot)
            if word in message_lower:
                # Bloquer le message
                broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
                moderator_id = await _get_moderator_id(twitch)
                user_id = await _get_user_id(twitch, msg.user.name)
                
                # Timeout de l'utilisateur
                if user_id and banned_word_entry.timeout_duration > 0:
                    try:
                        await twitch.ban_user(
                            broadcaster_id, 
                            moderator_id, 
                            user_id, 
                            reason=f"Mot interdit: {banned_word_entry.word}", 
                            duration=banned_word_entry.timeout_duration
                        )
                    except Exception as e:
                        logger.error(f"Erreur timeout mot interdit: {e}")
                
                # Suppression du message
                try:
                    await twitch.delete_chat_messages(broadcaster_id, moderator_id, message_id=msg.id)
                except Exception as e:
                    logger.error(f"Erreur suppression message mot interdit: {e}")
                
                # Log
                _log_action("banned_word", "AutoMod", msg.user.name, f"Mot: {banned_word_entry.word}")
                logger.info(f"Mot interdit détecté de {msg.user.name}: {banned_word_entry.word}")
                
                return False
    
    return True
