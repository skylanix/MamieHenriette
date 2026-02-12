import re
import logging
from datetime import datetime, timedelta

from twitchAPI.twitch import Twitch
from twitchAPI.chat import ChatMessage

from database import db
from database.models import TwitchLinkFilter, TwitchAllowedDomain, TwitchPermit, TwitchAllowedUser
from twitchbot.moderation import _log_action, _get_broadcaster_id, _get_moderator_id, _get_user_id, _is_moderator
from webapp import webapp

logger = logging.getLogger('twitch-link-filter')
logger.setLevel(logging.INFO)

URL_REGEX = re.compile(r'https?://[^\s]+|(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?')


def _get_filter_config():
    """Retourne un dictionnaire avec la config du filtre de liens"""
    with webapp.app_context():
        config = TwitchLinkFilter.query.first()
        if not config:
            config = TwitchLinkFilter(enabled=False)
            db.session.add(config)
            db.session.commit()
        # Retourner un dict pour éviter DetachedInstanceError
        return {
            'enabled': config.enabled,
            'allow_subscribers': config.allow_subscribers,
            'allow_vips': config.allow_vips,
            'allow_moderators': config.allow_moderators,
            'timeout_duration': config.timeout_duration,
            'warning_message': config.warning_message
        }


def _get_allowed_domains():
    with webapp.app_context():
        return [d.domain.lower() for d in TwitchAllowedDomain.query.all()]


def _is_user_whitelisted(username: str) -> bool:
    with webapp.app_context():
        return TwitchAllowedUser.query.filter_by(username=username.lower()).first() is not None


def _has_valid_permit(username: str) -> bool:
    with webapp.app_context():
        permit = TwitchPermit.query.filter_by(username=username.lower()).first()
        if permit and permit.expires_at > datetime.now():
            return True
        if permit and permit.expires_at <= datetime.now():
            db.session.delete(permit)
            db.session.commit()
        return False


def _extract_domain(url: str) -> str:
    url = url.lower()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    return url.split('/')[0]


def _is_domain_allowed(url: str, allowed_domains: list) -> bool:
    domain = _extract_domain(url)
    for allowed in allowed_domains:
        if domain == allowed or domain.endswith('.' + allowed):
            return True
    return False


async def check_message_for_links(msg: ChatMessage, twitch: Twitch) -> bool:
    config = _get_filter_config()
    
    if not config['enabled']:
        return True
    
    if config['allow_moderators'] and (msg.user.mod or msg.user.name.lower() == msg.room.name.lower()):
        return True
    
    if config['allow_vips'] and msg.user.vip:
        return True
    
    if config['allow_subscribers'] and msg.user.subscriber:
        return True
    
    if _is_user_whitelisted(msg.user.name):
        return True
    
    urls = URL_REGEX.findall(msg.text)
    if not urls:
        return True
    
    if _has_valid_permit(msg.user.name):
        with webapp.app_context():
            permit = TwitchPermit.query.filter_by(username=msg.user.name.lower()).first()
            if permit:
                db.session.delete(permit)
                db.session.commit()
        return True
    
    allowed_domains = _get_allowed_domains()
    for url in urls:
        if not _is_domain_allowed(url, allowed_domains):
            await _handle_unauthorized_link(msg, twitch, config, url)
            return False
    
    return True


async def _handle_unauthorized_link(msg: ChatMessage, twitch: Twitch, config: dict, url: str):
    broadcaster_id = await _get_broadcaster_id(twitch, msg.room.name)
    moderator_id = await _get_moderator_id(twitch)
    user_id = await _get_user_id(twitch, msg.user.name)
    
    if user_id and config['timeout_duration'] > 0:
        try:
            await twitch.ban_user(broadcaster_id, moderator_id, user_id, reason="Lien non autorise", duration=config['timeout_duration'])
        except Exception as e:
            logger.error(f"Erreur timeout link filter: {e}")
    
    try:
        await twitch.delete_chat_messages(broadcaster_id, moderator_id, message_id=msg.id)
    except Exception as e:
        logger.error(f"Erreur suppression message: {e}")
    
    if config['warning_message']:
        await msg.reply(config['warning_message'])
    
    _log_action("link_blocked", "AutoMod", msg.user.name, _extract_domain(url))
    logger.info(f"Lien bloque de {msg.user.name}: {url}")


async def permit_command(msg: ChatMessage, twitch: Twitch):
    if not _is_moderator(msg):
        return
    
    args = msg.text.split()[1:]
    if len(args) < 1:
        await msg.reply("Usage: !permit <viewer> [minutes]")
        return
    
    username = args[0].lstrip('@').lower()
    duration = 60
    if len(args) >= 2:
        try:
            duration = int(args[1]) * 60
        except ValueError:
            duration = 60
    
    expires_at = datetime.now() + timedelta(seconds=duration)
    
    with webapp.app_context():
        existing = TwitchPermit.query.filter_by(username=username).first()
        if existing:
            existing.expires_at = expires_at
        else:
            permit = TwitchPermit(username=username, expires_at=expires_at)
            db.session.add(permit)
        db.session.commit()
    
    _log_action("permit", msg.user.name, username, f"{duration}s")
    await msg.reply(f"@{username} peut poster un lien pendant {duration // 60} minute(s)")
    logger.info(f"Permit accorde a {username} par {msg.user.name}")
