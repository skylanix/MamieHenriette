
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, ChatEvent, ChatMessage, EventData

CLIENT_ID= 'TODO'
CLIENT_SECRET='TODO'

USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

CHANNEL = "#TODO"

ACCESS_TOKEN = 'TODO'
REFRESH_TOKEN = 'TODO'


async def on_ready(ready_event: EventData):
	print('Bot is ready for work, joining channels')
	await ready_event.chat.join_room(CHANNEL)

async def on_message(msg: ChatMessage):
	print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')

async def start() : 
	twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)

	# auth = UserAuthenticator(twitch, USER_SCOPE, url='todo')
	# print(f'{auth.return_auth_url()}')
	# token, refresh_token = await auth.authenticate( use_browser=False)
	# token, refresh_token = await auth.authenticate()
	# print(f'{token} :: {refresh_token}')
	
	await twitch.set_user_authentication(ACCESS_TOKEN, USER_SCOPE, REFRESH_TOKEN)
	# await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)

	chat = await Chat(twitch)
	chat.register_event(ChatEvent.READY, on_ready)
	chat.register_event(ChatEvent.MESSAGE, on_message)
	# chat.register_event(ChatEvent.SUB, on_sub)
	# chat.register_command('reply', test_command)
	chat.start()

	try:
		input('press ENTER to stop\n')
	finally:
		# now we can close the chat bot and the twitch api client
		chat.stop()
		await twitch.close()