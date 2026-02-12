import logging
import discord

from twitchAPI.twitch import Twitch
from twitchAPI.object.api import Stream

from database import db
from database.models import LiveAlert
from discordbot import bot
from webapp import webapp

logger = logging.getLogger('live-alert')
logger.setLevel(logging.INFO)

_live_alert_first_check = True


def _stream_thumbnail_url(stream: Stream) -> str:
	"""URL de la miniature du stream (preview Twitch)."""
	url = getattr(stream, 'thumbnail_url', None) or ''
	if '{width}' in url or '{height}' in url:
		url = url.replace('{width}', '320').replace('{height}', '180')
	if not url:
		url = f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{stream.user_login}-320x180.jpg"
	return url


def _format_embed_text(text: str, stream: Stream, stream_url: str, thumbnail: str) -> str:
	"""Formate un texte d'embed avec les variables stream."""
	if not text:
		return ''
	try:
		return text.format(
			user_login=stream.user_login or '',
			user_name=stream.user_name or '',
			game_name=getattr(stream, 'game_name', None) or '',
			title=stream.title or '',
			language=getattr(stream, 'language', None) or '',
			stream_url=stream_url,
			thumbnail=thumbnail,
		)
	except KeyError:
		return text


async def checkOnlineStreamer(twitch: Twitch) :
	global _live_alert_first_check
	with webapp.app_context() : 
		alerts : list[LiveAlert] = LiveAlert.query.all()
		streams = await _retreiveStreams(twitch, alerts)
		watch_stream = None
		
		# Récupération du statut du live principal (channel configuré)
		from database.helpers import ConfigurationHelper
		main_channel = ConfigurationHelper().getValue('twitch_channel')
		main_stream = None
		if main_channel:
			main_stream = next((s for s in streams if s.user_login.lower() == main_channel.lower()), None)
		
		# Mise à jour du BOT_STATUS pour la webapp
		if main_stream:
			webapp.config["BOT_STATUS"]["twitch_is_live"] = True
			webapp.config["BOT_STATUS"]["twitch_viewer_count"] = getattr(main_stream, 'viewer_count', 0)
		else:
			webapp.config["BOT_STATUS"]["twitch_is_live"] = False
			webapp.config["BOT_STATUS"]["twitch_viewer_count"] = 0
		
		# Premier check : synchronisation sans notification
		if _live_alert_first_check:
			logger.info('Live Alert: première vérification, synchronisation sans notification')
			for alert in alerts:
				stream = next((s for s in streams if s.user_login == alert.login), None)
				if stream:
					alert.online = True
					if alert.watch_activity and alert.enable:
						watch_stream = stream
				else:
					alert.online = False
			await _updateBotActivity(watch_stream)
			db.session.commit()
			_live_alert_first_check = False
			return
		
		# Vérifications normales ensuite
		for alert in alerts : 
			stream = next((s for s in streams if s.user_login == alert.login), None)
			if stream : 
				logger.info(f'Streamer en ligne : {alert.login}')
				if not alert.online and alert.enable :
					logger.info(f'N\'etait pas en ligne auparavant : {alert.login}')
					await _notifyAlert(alert, stream)
				alert.online = True
				if alert.watch_activity and alert.enable:
					watch_stream = stream
			else :
				logger.info(f'Streamer hors ligne : {alert.login}')
				alert.online = False
		
		await _updateBotActivity(watch_stream)
		db.session.commit()


async def _updateBotActivity(stream: Stream | None):
	if stream:
		logger.info(f'Mise à jour de l\'activité : Regarde le live de {stream.user_name}')
		activity = discord.Streaming(
			name=f'Regarde le live de {stream.user_name}',
			url=f'https://www.twitch.tv/{stream.user_login}'
		)
		await bot.change_presence(status=discord.Status.online, activity=activity)
	else:
		logger.info('Aucun stream à regarder, retour à l\'activité normale')
		# Remettre une humeur aléatoire
		from database.models import Humeur
		import random
		humeurs = Humeur.query.all()
		if humeurs:
			humeur = random.choice(humeurs)
			logger.info(f'Réinitialisation du statut : {humeur.text}')
			await bot.change_presence(status=discord.Status.online, activity=discord.CustomActivity(humeur.text))
		else:
			# Si pas de humeur, remettre un statut par défaut
			await bot.change_presence(status=discord.Status.online, activity=None)

async def _notifyAlert(alert: LiveAlert, stream: Stream):
	stream_url = f'https://www.twitch.tv/{stream.user_login}'
	thumbnail = _stream_thumbnail_url(stream)

	# Message texte optionnel (avant l'embed)
	message_text = None
	if alert.message and alert.message.strip():
		try:
			message_text = alert.message.format(stream)
		except KeyError:
			message_text = alert.message

	# Construction de l'embed Discord
	try:
		embed_color = int(alert.embed_color or '9146FF', 16)
	except ValueError:
		embed_color = 0x9146FF

	embed_title = _format_embed_text(alert.embed_title, stream, stream_url, thumbnail) if alert.embed_title else (stream.title or f"{stream.user_name} est en live")
	embed_description = _format_embed_text(alert.embed_description, stream, stream_url, thumbnail) if alert.embed_description else None

	embed = discord.Embed(
		title=embed_title,
		url=stream_url,
		color=embed_color
	)
	if embed_description:
		embed.description = embed_description

	author_name = _format_embed_text(alert.embed_author_name, stream, stream_url, thumbnail) if alert.embed_author_name else stream.user_name
	user_id = getattr(stream, 'user_id', None)
	author_icon = alert.embed_author_icon or (f"https://static-cdn.jtvnw.net/jtv_user_pictures/{user_id}-profile_image-70x70.png" if user_id else "https://static-cdn.jtvnw.net/ttv-favicon/favicon-32x32.png")
	embed.set_author(name=author_name, icon_url=author_icon)

	if alert.embed_thumbnail and thumbnail:
		embed.set_thumbnail(url=thumbnail)
	if alert.embed_image and thumbnail:
		embed.set_image(url=thumbnail)

	if alert.embed_footer:
		footer_text = _format_embed_text(alert.embed_footer, stream, stream_url, thumbnail)
		if footer_text:
			embed.set_footer(text=footer_text)

	logger.info(f'Envoi de notification live (embed) : {stream.user_login}')
	bot.loop.create_task(_sendMessage(alert.notify_channel, message_text, embed))

async def _sendMessage(channel_id: int, message: str | None, embed: discord.Embed):
	try:
		discord_channel = bot.get_channel(channel_id)
		if not discord_channel:
			logger.error(f"Canal Discord {channel_id} introuvable")
			return
		if message and message.strip():
			await discord_channel.send(content=message, embed=embed)
		else:
			await discord_channel.send(embed=embed)
		logger.info('Notification live envoyée')
	except Exception as e:
		logger.error(f"Erreur lors de l'envoi de la notification live : {e}")

async def _retreiveStreams(twitch: Twitch, alerts: list[LiveAlert]) -> list[Stream]:
	streams: list[Stream] = []
	logger.info(f'Recherche de streams pour : {alerts}')
	async for stream in twitch.get_streams(user_login=[alert.login for alert in alerts]):
		streams.append(stream)
	logger.info(f'Ces streams sont en ligne : {streams}')
	return streams
