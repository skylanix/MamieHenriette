import asyncio
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
	try:
		await asyncio.wait_for(bot.get_channel(channel).send(message), timeout=30.0)
		logger.info(f'Notification envoyée')
	except asyncio.TimeoutError:
		logger.error(f'Timeout lors de l\'envoi de notification live alert')
	except Exception as e:
		logger.error(f'Erreur lors de l\'envoi de notification live alert : {e}')

async def _retreiveStreams(twitch: Twitch, alerts : list[LiveAlert]) -> list[Stream] : 
	streams : list[Stream] = []
	logger.info(f'Recherche de streams pour : {alerts}')
	try:
		async for stream in asyncio.wait_for(twitch.get_streams(user_login = [alert.login for alert in alerts]), timeout=30.0):
			streams.append(stream)
		logger.info(f'Ces streams sont en ligne : {streams}')
	except asyncio.TimeoutError:
		logger.error('Timeout lors de la récupération des streams Twitch')
	except Exception as e:
		logger.error(f'Erreur lors de la récupération des streams Twitch : {e}')
	return streams

