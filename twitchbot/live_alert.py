import logging

from twitchAPI.twitch import Twitch
from twitchAPI.object.api import Stream

from database import db
from database.models import LiveAlert
from discordbot import bot
from webapp import webapp

logger = logging.getLogger('live-alert')
logger.setLevel(logging.INFO)


async def checkOnlineStreamer(twitch: Twitch) :
	with webapp.app_context() : 
		alerts : list[LiveAlert] = LiveAlert.query.all()
		streams = await _retreiveStreams(twitch, alerts)
		for alert in alerts : 
			stream = next((s for s in streams if s.user_login == alert.login), None)
			if stream : 
				logger.info(f'Streamer en ligne : {alert.login}')
				if not alert.online and alert.enable :
					logger.info(f'N\'etait pas en ligne auparavant : {alert.login}')
					await _notifyAlert(alert, stream)
				alert.online = True
			else :
				logger.info(f'Streamer hors ligne : {alert.login}')
				alert.online = False
		db.session.commit()

async def _notifyAlert(alert : LiveAlert, stream : Stream):
	message : str = alert.message.format(stream)
	logger.info(f'Message de notification : {message}')
	bot.loop.create_task(_sendMessage(alert.notify_channel, message))

async def _sendMessage(channel : int, message : str) : 
	logger.info(f'Envoi de notification : {message}')
	await bot.get_channel(channel).send(message)
	logger.info(f'Notification envoyé')

async def _retreiveStreams(twitch: Twitch, alerts : list[LiveAlert]) -> list[Stream] : 
	streams : list[Stream] = []
	logger.info(f'Recherche de streams pour : {alerts}')
	async for stream in twitch.get_streams(user_login = [alert.login for alert in alerts]):
		streams.append(stream)
	logger.info(f'Ces streams sont en ligne : {streams}')
	return streams

