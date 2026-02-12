# Notifications d'événements Twitch (sub, follow, raid, clip) : chat + Discord
import asyncio
import logging
from typing import Any

import discord
from twitchAPI.chat import Chat
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.object.eventsub import (
	ChannelFollowEvent,
	ChannelRaidEvent,
	ChannelSubscribeEvent,
)
from twitchAPI.twitch import Twitch

from database import db
from database.models import TwitchEventNotification
from webapp import webapp

logger = logging.getLogger("twitch-events")


def _format_message(template: str, **kwargs: Any) -> str:
	if not template:
		return ""
	for k, v in (kwargs or {}).items():
		template = template.replace("{" + k + "}", str(v or ""))
	return template


async def _send_twitch(chat: Chat, channel: str, text: str) -> None:
	if not text or not chat:
		return
	try:
		await chat.send_message(channel, text[:500])
	except Exception as e:
		logger.error("Envoi chat Twitch événement: %s", e)


def _schedule_discord_send(channel_id: int, content: str | None, embed: discord.Embed | None) -> None:
	"""Planifie l'envoi sur le canal Discord (sans bloquer le loop Twitch)."""
	from discordbot import bot
	try:
		ch = bot.get_channel(channel_id)
		if not ch:
			logger.warning("Canal Discord %s introuvable", channel_id)
			return
		payload = content if content else embed
		if not payload:
			return
		asyncio.run_coroutine_threadsafe(
			ch.send(content=content, embed=embed) if (content and embed) else ch.send(content=content or None, embed=embed if not content else None),
			bot.loop,
		)
	except Exception as e:
		logger.error("Envoi Discord événement: %s", e)


async def _handle_follow(data: ChannelFollowEvent, chat: Chat, channel: str) -> None:
	with webapp.app_context():
		cfg = TwitchEventNotification.query.filter_by(event_type="follow", enable=True).first()
		if not cfg:
			return
		ev = data.event
		user = getattr(ev, "user_name", None) or getattr(ev, "user_login", "")
		user_login = getattr(ev, "user_login", user)
		msg = _format_message(
			cfg.message_twitch or "Merci {user} pour le follow !",
			user=user_login,
			user_name=user,
		)
		if cfg.notify_twitch_chat and msg:
			await _send_twitch(chat, channel, msg)
		if cfg.notify_discord and cfg.discord_channel_id:
			content = _format_message(cfg.message_discord or "", user=user_login, user_name=user)
			try:
				embed_color = int(cfg.embed_color or "9146FF", 16)
			except ValueError:
				embed_color = 0x9146FF
			embed = discord.Embed(
				title=_format_message(cfg.embed_title or "Nouveau follow", user=user_login, user_name=user),
				description=cfg.embed_description or f"{user} suit maintenant la chaîne.",
				color=embed_color,
			)
			_schedule_discord_send(cfg.discord_channel_id, content.strip() or None, embed)


async def _handle_subscribe(data: ChannelSubscribeEvent, chat: Chat, channel: str) -> None:
	with webapp.app_context():
		cfg = TwitchEventNotification.query.filter_by(event_type="sub", enable=True).first()
		if not cfg:
			return
		ev = data.event
		user = getattr(ev, "user_name", None) or getattr(ev, "user_login", "")
		user_login = getattr(ev, "user_login", user)
		msg = _format_message(
			cfg.message_twitch or "Merci {user} pour l'abonnement !",
			user=user_login,
			user_name=user,
		)
		if cfg.notify_twitch_chat and msg:
			await _send_twitch(chat, channel, msg)
		if cfg.notify_discord and cfg.discord_channel_id:
			content = _format_message(cfg.message_discord or "", user=user_login, user_name=user)
			try:
				embed_color = int(cfg.embed_color or "9146FF", 16)
			except ValueError:
				embed_color = 0x9146FF
			embed = discord.Embed(
				title=_format_message(cfg.embed_title or "Nouvel abonnement", user=user_login, user_name=user),
				description=cfg.embed_description or f"Merci à {user} pour l'abonnement !",
				color=embed_color,
			)
			_schedule_discord_send(cfg.discord_channel_id, content.strip() or None, embed)


async def _handle_raid(data: ChannelRaidEvent, chat: Chat, channel: str) -> None:
	with webapp.app_context():
		cfg = TwitchEventNotification.query.filter_by(event_type="raid", enable=True).first()
		if not cfg:
			return
		ev = data.event
		from_broadcaster = getattr(ev, "from_broadcaster_user_name", None) or getattr(ev, "from_broadcaster_user_login", "")
		viewers = getattr(ev, "viewers", 0)
		msg = _format_message(
			cfg.message_twitch or "Bienvenue aux {viewers} viewers de {from_broadcaster_name} !",
			from_broadcaster_name=from_broadcaster,
			viewers=viewers,
		)
		if cfg.notify_twitch_chat and msg:
			await _send_twitch(chat, channel, msg)
		if cfg.notify_discord and cfg.discord_channel_id:
			content = _format_message(
				cfg.message_discord or "",
				from_broadcaster_name=from_broadcaster,
				viewers=viewers,
			)
			try:
				embed_color = int(cfg.embed_color or "9146FF", 16)
			except ValueError:
				embed_color = 0x9146FF
			embed = discord.Embed(
				title=_format_message(
					cfg.embed_title or "Raid reçu",
					from_broadcaster_name=from_broadcaster,
					viewers=viewers,
				),
				description=cfg.embed_description or f"{from_broadcaster} a raid avec {viewers} viewers !",
				color=embed_color,
			)
			_schedule_discord_send(cfg.discord_channel_id, content.strip() or None, embed)


async def notify_clip(
	chat: Chat | None,
	channel: str,
	*,
	user: str,
	title: str,
	url: str,
	thumbnail_url: str,
	clip_id: str,
) -> None:
	"""Appelé quand un nouveau clip est détecté (polling)."""
	with webapp.app_context():
		cfg = TwitchEventNotification.query.filter_by(event_type="clip", enable=True).first()
		if not cfg:
			return
		msg_twitch = _format_message(
			cfg.message_twitch or "Nouveau clip par {user} : {title} {url}",
			user=user,
			title=title,
			url=url,
		)
		if cfg.notify_twitch_chat and chat and msg_twitch:
			await _send_twitch(chat, channel, msg_twitch)
		if cfg.notify_discord and cfg.discord_channel_id:
			content = _format_message(
				cfg.message_discord or "",
				user=user,
				title=title,
				url=url,
				thumbnail_url=thumbnail_url or "",
			)
			try:
				embed_color = int(cfg.embed_color or "9146FF", 16)
			except ValueError:
				embed_color = 0x9146FF
			embed = discord.Embed(
				title=_format_message(cfg.embed_title or "Nouveau clip", user=user, title=title),
				url=url,
				description=cfg.embed_description or title,
				color=embed_color,
			)
			if cfg.embed_thumbnail and thumbnail_url:
				embed.set_thumbnail(url=thumbnail_url)
			_schedule_discord_send(cfg.discord_channel_id, content.strip() or None, embed)
		cfg.last_clip_id = clip_id
		db.session.commit()


def create_eventsub(twitch: Twitch, callback_loop: asyncio.AbstractEventLoop) -> EventSubWebsocket:
	"""Crée et démarre le client EventSub. Les callbacks seront exécutés sur `callback_loop`."""
	eventsub = EventSubWebsocket(twitch, callback_loop=callback_loop)
	eventsub.start()
	return eventsub


async def register_eventsub_handlers(
	eventsub: EventSubWebsocket,
	broadcaster_id: str,
	chat: Chat,
	channel: str,
) -> None:
	"""Enregistre follow, sub, raid sur l'EventSub. À appeler dans les 10 s après start()."""
	
	# Définir les callbacks comme des wrappers explicites
	async def on_follow(data: ChannelFollowEvent) -> None:
		try:
			await _handle_follow(data, chat, channel)
		except Exception as e:
			logger.error("Erreur handler follow: %s", e)

	async def on_subscribe(data: ChannelSubscribeEvent) -> None:
		try:
			await _handle_subscribe(data, chat, channel)
		except Exception as e:
			logger.error("Erreur handler subscribe: %s", e)

	async def on_raid(data: ChannelRaidEvent) -> None:
		try:
			await _handle_raid(data, chat, channel)
		except Exception as e:
			logger.error("Erreur handler raid: %s", e)

	# Chaque souscription est tentée séparément : si le token n'a pas channel:read:subscriptions,
	# seule "sub" échouera ; follow et raid restent actifs.
	subscriptions_ok = 0
	
	try:
		await eventsub.listen_channel_follow_v2(broadcaster_id, broadcaster_id, on_follow)
		logger.info("EventSub: follow enregistré ✓")
		subscriptions_ok += 1
	except Exception as e:
		logger.error("EventSub follow: %s", e)
	
	try:
		await eventsub.listen_channel_subscribe(broadcaster_id, on_subscribe)
		logger.info("EventSub: subscribe enregistré ✓")
		subscriptions_ok += 1
	except Exception as e:
		logger.warning("EventSub subscribe (nécessite scope channel:read:subscriptions): %s", e)
	
	try:
		await eventsub.listen_channel_raid(to_broadcaster_user_id=broadcaster_id, callback=on_raid)
		logger.info("EventSub: raid enregistré ✓")
		subscriptions_ok += 1
	except Exception as e:
		logger.error("EventSub raid: %s", e)
	
	if subscriptions_ok == 0:
		logger.error("EventSub: AUCUNE souscription n'a réussi ! Le WebSocket va se fermer.")
	else:
		logger.info(f"EventSub: {subscriptions_ok}/3 souscriptions actives")
