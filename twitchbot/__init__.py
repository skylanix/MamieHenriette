
import asyncio
import logging

from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, ChatEvent, ChatMessage, EventData

from database.helpers import ConfigurationHelper

from webapp import webapp

USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

async def _onReady(ready_event: EventData):
	logging.info('Twitch bot ready')
	with webapp.app_context():
		await ready_event.chat.join_room(ConfigurationHelper().getValue('twitch_channel'))

async def _onMessage(msg: ChatMessage):
	logging.info(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')

# commande qui repond "bonjour" a "!hello"
async def _helloCommand(msg: ChatMessage):
	await msg.reply(f'Bonjour {msg.user.name}')

def _isConfigured() -> bool: 
	helper = ConfigurationHelper()
	return helper.getValue('twitch_client_id') != None and helper.getValue('twitch_client_secret') != None and helper.getValue('twitch_access_token') != None and helper.getValue('twitch_refresh_token') != None and helper.getValue('twitch_channel') != None

class TwitchBot() : 

	async def _connect(self):
		with webapp.app_context():
			if _isConfigured() : 
				try : 
					helper = ConfigurationHelper()
					self.twitch = await Twitch(helper.getValue('twitch_client_id'), helper.getValue('twitch_client_secret'))
					await self.twitch.set_user_authentication(helper.getValue('twitch_access_token'), USER_SCOPE, helper.getValue('twitch_refresh_token'))
					self.chat = await Chat(self.twitch)
					self.chat.register_event(ChatEvent.READY, _onReady)
					self.chat.register_event(ChatEvent.MESSAGE, _onMessage)
					# chat.register_event(ChatEvent.SUB, on_sub)
					self.chat.register_command('hello', _helloCommand)
					self.chat.start()
				except Exception as e: 
					logging.error(f'Échec de l\'authentification Twitch. Vérifiez vos identifiants et redémarrez après correction : {e}')
			else: 
				logging.info("Twitch n'est pas configuré")
	
	def begin(self): 
		asyncio.run(self._connect())

	# je sais pas encore comment appeller ca
	async def _close(self):
		self.chat.stop()
		await self.twitch.close()

twitchBot = TwitchBot()

