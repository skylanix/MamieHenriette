import asyncio
import logging

from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, ChatEvent, ChatMessage, EventData

from database.helpers import ConfigurationHelper
from database.models import Commande


def _user_has_twitch_permission(msg: ChatMessage, required: str) -> bool:
	"""Vérifie si l'utilisateur a le niveau de permission requis (viewer, sub, vip, moderator)."""
	if not required or required == 'viewer':
		return True
	is_broadcaster = msg.user.name.lower() == msg.room.name.lower()
	is_mod = msg.user.mod or is_broadcaster
	if required == 'moderator':
		return is_mod
	if required == 'vip':
		return msg.user.vip or is_mod
	if required == 'sub':
		return msg.user.subscriber or msg.user.vip or is_mod
	return True
from twitchbot.live_alert import checkOnlineStreamer
from twitchbot.announcements import checkAndSendAnnouncements, incrementMessageCount
from twitchbot import moderation
from twitchbot import link_filter
from twitchbot import event_notifications
from webapp import webapp

USER_SCOPE = [
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.MODERATOR_MANAGE_BANNED_USERS,
    AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES,
    AuthScope.MODERATOR_MANAGE_CHAT_SETTINGS,
    AuthScope.MODERATOR_MANAGE_SHIELD_MODE,
    AuthScope.CHANNEL_MANAGE_BROADCAST,
    AuthScope.MODERATOR_READ_FOLLOWERS,
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS,  # EventSub channel.subscribe (notifs sub)
]


async def _onReady(ready_event: EventData):
	logging.info('Bot Twitch prêt')
	with webapp.app_context():
		channel = ConfigurationHelper().getValue('twitch_channel')
		webapp.config["BOT_STATUS"]["twitch_connected"] = True
		webapp.config["BOT_STATUS"]["twitch_channel_name"] = channel
		await ready_event.chat.join_room(channel)
		# EventSub (follow, sub, raid) : besoin du broadcaster_id
		try:
			from twitchAPI.helper import first
			user = await first(twitchBot.twitch.get_users(logins=[channel]))
			if user:
				twitchBot._eventsub = event_notifications.create_eventsub(twitchBot.twitch, asyncio.get_event_loop())
				asyncio.create_task(event_notifications.register_eventsub_handlers(twitchBot._eventsub, user.id, ready_event.chat, channel))
		except Exception as e:
			logging.warning('EventSub non démarré: %s', e)
	asyncio.get_event_loop().create_task(twitchBot._checkOnlineStreamers())
	asyncio.get_event_loop().create_task(twitchBot._runAnnouncements())
	asyncio.get_event_loop().create_task(twitchBot._checkClips())


async def _onMessage(msg: ChatMessage):
	logging.info(f'Dans {msg.room.name}, {msg.user.name} a dit : {msg.text}')
	incrementMessageCount()
	
	# Stocker le message dans BOT_STATUS pour l'affichage web
	with webapp.app_context():
		from datetime import datetime
		message_data = {
			'username': msg.user.name,
			'text': msg.text,
			'timestamp': datetime.now().isoformat(),
			'is_mod': msg.user.mod,
			'is_subscriber': msg.user.subscriber,
			'is_vip': msg.user.vip,
			'color': getattr(msg.user, 'color', None) or '#9146FF'
		}
		messages = webapp.config["BOT_STATUS"]["twitch_chat_messages"]
		messages.append(message_data)
		# Limiter à 100 messages
		if len(messages) > 100:
			messages.pop(0)
	
	if not await link_filter.check_message_for_links(msg, twitchBot.twitch):
		return
	if not await moderation.check_message_for_banned_words(msg, twitchBot.twitch):
		return
	await _handleCustomCommand(msg)


async def _handleCustomCommand(msg: ChatMessage):
	if not msg.text.startswith('!'):
		return
	trigger = msg.text.split()[0].lower()
	with webapp.app_context():
		# Vérifier si les commandes Twitch sont activées globalement
		if not ConfigurationHelper().getValue('twitch_commands_enable'):
			return
		commande = Commande.query.filter_by(trigger=trigger, twitch_enable=True).first()
		if commande:
			permission = commande.twitch_permission or 'viewer'
			if not _user_has_twitch_permission(msg, permission):
				return  # Pas de réponse = l'utilisateur n'a pas la permission
			response = commande.response.replace('{user}', msg.user.name)
			await msg.reply(response)


async def _helloCommand(msg: ChatMessage):
	await msg.reply(f'Bonjour {msg.user.name}')


def _isConfigured():
	helper = ConfigurationHelper()
	return (helper.getValue('twitch_client_id') is not None and 
			helper.getValue('twitch_client_secret') is not None and 
			helper.getValue('twitch_access_token') is not None and 
			helper.getValue('twitch_refresh_token') is not None and 
			helper.getValue('twitch_channel') is not None)


class TwitchBot():
	_eventsub = None

	async def _connect(self):
		with webapp.app_context():
			if _isConfigured():
				try:
					helper = ConfigurationHelper()
					self.twitch = await Twitch(helper.getValue('twitch_client_id'), helper.getValue('twitch_client_secret'))
					await self.twitch.set_user_authentication(helper.getValue('twitch_access_token'), USER_SCOPE, helper.getValue('twitch_refresh_token'))
					self.chat = await Chat(self.twitch)
					self.chat.register_event(ChatEvent.READY, _onReady)
					self.chat.register_event(ChatEvent.MESSAGE, _onMessage)
					self.chat.register_command('hello', _helloCommand)
					self._register_moderation_commands()
					self.chat.start()
				except Exception as e:
					logging.error(f'Échec de l\'authentification Twitch : {e}')
			else:
				logging.info("Twitch n'est pas configuré")

	def _register_moderation_commands(self):
		# Créer des wrappers async pour chaque commande
		async def cmd_timeout(msg): await moderation.timeout_command(msg, self.twitch)
		async def cmd_ban(msg): await moderation.ban_command(msg, self.twitch)
		async def cmd_unban(msg): await moderation.unban_command(msg, self.twitch)
		async def cmd_clean(msg): await moderation.clean_command(msg, self.twitch)
		async def cmd_shieldmode(msg): await moderation.shieldmode_command(msg, self.twitch)
		async def cmd_settitle(msg): await moderation.settitle_command(msg, self.twitch)
		async def cmd_setgame(msg): await moderation.setgame_command(msg, self.twitch)
		async def cmd_subon(msg): await moderation.subon_command(msg, self.twitch)
		async def cmd_suboff(msg): await moderation.suboff_command(msg, self.twitch)
		async def cmd_follon(msg): await moderation.follon_command(msg, self.twitch)
		async def cmd_folloff(msg): await moderation.folloff_command(msg, self.twitch)
		async def cmd_emoteon(msg): await moderation.emoteon_command(msg, self.twitch)
		async def cmd_emoteoff(msg): await moderation.emoteoff_command(msg, self.twitch)
		async def cmd_ann(msg): await moderation.ann_command(msg, self.twitch)
		async def cmd_no_game(msg): await moderation.no_game_command(msg, self.twitch)
		async def cmd_multitwitch(msg): await moderation.multitwitch_command(msg, self.twitch)
		async def cmd_permit(msg): await link_filter.permit_command(msg, self.twitch)

		self.chat.register_command('kick', cmd_timeout)
		self.chat.register_command('to', cmd_timeout)
		self.chat.register_command('timeout', cmd_timeout)
		self.chat.register_command('tm', cmd_timeout)
		self.chat.register_command('ban', cmd_ban)
		self.chat.register_command('unban', cmd_unban)
		self.chat.register_command('clean', cmd_clean)
		self.chat.register_command('shieldmode', cmd_shieldmode)
		self.chat.register_command('settitle', cmd_settitle)
		self.chat.register_command('setgame', cmd_setgame)
		self.chat.register_command('setcateg', cmd_setgame)
		self.chat.register_command('subon', cmd_subon)
		self.chat.register_command('suboff', cmd_suboff)
		self.chat.register_command('follon', cmd_follon)
		self.chat.register_command('folloff', cmd_folloff)
		self.chat.register_command('emoteon', cmd_emoteon)
		self.chat.register_command('emoteoff', cmd_emoteoff)
		self.chat.register_command('ann', cmd_ann)
		self.chat.register_command('no_game', cmd_no_game)
		self.chat.register_command('multitwitch', cmd_multitwitch)
		self.chat.register_command('permit', cmd_permit)

	async def _checkOnlineStreamers(self):
		while True:
			try:
				await checkOnlineStreamer(self.twitch)
			except Exception as e:
				logging.error(f'Erreur check streamers online : {e}')
			await asyncio.sleep(5 * 60)

	async def _runAnnouncements(self):
		with webapp.app_context():
			channel = ConfigurationHelper().getValue('twitch_channel')
		while True:
			try:
				await checkAndSendAnnouncements(self.chat, channel, self.twitch)
			except Exception as e:
				logging.error(f'Erreur envoi annonces : {e}')
			await asyncio.sleep(2 * 60)  # Vérification toutes les 2 min pour limiter le spam

	async def _checkClips(self):
		"""Vérifie le clip le plus récent (polling) et notifie si nouveau."""
		with webapp.app_context():
			channel = ConfigurationHelper().getValue('twitch_channel')
		if not channel:
			return
		from twitchAPI.helper import first
		try:
			user = await first(self.twitch.get_users(logins=[channel]))
			if not user:
				return
		except Exception:
			return
		while True:
			try:
				with webapp.app_context():
					from database.models import TwitchEventNotification
					cfg = TwitchEventNotification.query.filter_by(event_type='clip', enable=True).first()
				if not cfg:
					await asyncio.sleep(120)
					continue
				clip = await first(self.twitch.get_clips(broadcaster_id=user.id, first=1))
				if not clip:
					await asyncio.sleep(120)
					continue
				if cfg.last_clip_id is None:
					with webapp.app_context():
						from database import db
						cfg = TwitchEventNotification.query.filter_by(event_type='clip', enable=True).first()
						if cfg:
							cfg.last_clip_id = clip.id
							db.session.commit()
				elif clip.id != cfg.last_clip_id:
					with webapp.app_context():
						await event_notifications.notify_clip(
								self.chat,
								channel,
								user=getattr(clip, 'creator_name', None) or getattr(clip, 'user_name', '') or clip.id,
								title=getattr(clip, 'title', '') or 'Clip',
								url=getattr(clip, 'url', '') or f'https://clips.twitch.tv/{clip.id}',
								thumbnail_url=getattr(clip, 'thumbnail_url', '') or '',
								clip_id=clip.id,
							)
			except Exception as e:
				logging.error('Erreur check clips: %s', e)
			await asyncio.sleep(120)

	def begin(self):
		asyncio.run(self._connect())

	async def _close(self):
		self.chat.stop()
		await self.twitch.close()


twitchBot = TwitchBot()
