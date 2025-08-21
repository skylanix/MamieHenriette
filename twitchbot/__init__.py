
import asyncio
import logging

from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, ChatEvent, ChatMessage, EventData

CLIENT_ID= 'TODO'
CLIENT_SECRET='TODO'

USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

CHANNEL = "#TODO"

ACCESS_TOKEN = 'TODO'
REFRESH_TOKEN = 'TODO'


async def _onReady(ready_event: EventData):
	logging.info('Twitch bot ready')
	await ready_event.chat.join_room(CHANNEL)

async def _onMessage(msg: ChatMessage):
	print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')

async def _helloCommand(msg: ChatMessage):
	await msg.reply(f'Bonjour {msg.user.name}')

class TwitchBot() : 

	async def _connect(self):
		self.twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)
		await self.twitch.set_user_authentication(ACCESS_TOKEN, USER_SCOPE, REFRESH_TOKEN)
		self.chat = await Chat(self.twitch)
		self.chat.register_event(ChatEvent.READY, _onReady)
		self.chat.register_event(ChatEvent.MESSAGE, _onMessage)
		# chat.register_event(ChatEvent.SUB, on_sub)
		self.chat.register_command('hello', _helloCommand)
		self.chat.start()
	
	def begin(self): 
		asyncio.run(self._connect())

	# je sais pas encore comment appeller ca
	async def _close(self):
		self.chat.stop()
		await self.twitch.close()

twitchBot = TwitchBot()

