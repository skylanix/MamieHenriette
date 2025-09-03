from twitchAPI.twitch import Twitch
from twitchAPI.object.api import Stream

from database import db
from database.models import LiveAlert
from discordbot import bot
from webapp import webapp


async def checkOnlineStreamer(twitch: Twitch) :
	with webapp.app_context() : 
		alerts : list[LiveAlert] = LiveAlert.query.all()
		streams = await _retreiveStreams(twitch, alerts)
		for alert in alerts : 
			stream = next((s for s in streams if s.user_login == alert.login), None)
			if stream : 
				if not alert.online and alert.enable :
					await _notifyAlert(alert, stream)
				alert.online = True
			else :
				alert.online = False
		db.session.commit()

async def _notifyAlert(alert : LiveAlert, stream : Stream):
	message : str = alert.message.format(stream)
	bot.loop.create_task(_sendMessage(alert.notify_channel, message))

async def _sendMessage(channel : int, message : str) : 
	await bot.get_channel(channel).send(message)

async def _retreiveStreams(twitch: Twitch, alerts : list[LiveAlert]) -> list[Stream] : 
	streams : list[Stream] = []
	async for stream in twitch.get_streams(user_login = [alert.login for alert in alerts]):
		streams.append(stream)
	return streams

