import asyncio
import discord
import logging
import random

from database import db
from database.helpers import ConfigurationHelper
from database.models import Configuration, Humeur, Commande
from discord import Message
from discordbot.humblebundle import checkHumbleBundleAndNotify
from protondb import searhProtonDb

class DiscordBot(discord.Client):
	async def on_ready(self):
		logging.info(f'Connecté en tant que {self.user} (ID: {self.user.id})')
		for c in self.get_all_channels() :
			logging.info(f'{c.id} {c.name}')
		
		self.loop.create_task(self.updateStatus())
		self.loop.create_task(self.updateHumbleBundle())
	
	async def updateStatus(self):
		while not self.is_closed():
			humeurs = Humeur.query.all()
			if len(humeurs)>0 :
				humeur = random.choice(humeurs)
				if humeur != None: 
					logging.info(f'Changement de statut : {humeur.text}')
					await self.change_presence(status = discord.Status.online,  activity = discord.CustomActivity(humeur.text))
			# 10 minutes TODO à rendre configurable
			await asyncio.sleep(10*60)

	async def updateHumbleBundle(self):
		while not self.is_closed():
			await checkHumbleBundleAndNotify(self)
			# toutes les 30 minutes
			await asyncio.sleep(30*60)

	def begin(self) : 
		token = Configuration.query.filter_by(key='discord_token').first()
		if token :
			self.run(token.value)
		else :
			logging.error('Pas de token, on ne lance pas Discord')

intents = discord.Intents.default()
intents.message_content = True
bot = DiscordBot(intents=intents)

# https://discordpy.readthedocs.io/en/stable/quickstart.html
@bot.event
async def on_message(message: Message):
	if message.author == bot.user:
		return
	if not message.content.startswith('!'):
		return
	command_name = message.content.split()[0]
	commande = Commande.query.filter_by(discord_enable=True, trigger=command_name).first()
	if commande:
		try:
			await message.channel.send(commande.response, suppress_embeds=True)
			return
		except Exception as e:
			logging.error(e)

	if(ConfigurationHelper().getValue('proton_db_enable_enable') and message.content.find('!protondb')==0) :
		if (message.content.find('<@')>0) :
			mention = message.content[message.content.find('<@'):]
		else :
			mention = message.author.mention
		name = message.content.replace('!protondb', '').replace(f'{mention}', '').strip();
		games = searhProtonDb(name)
		if (len(games)==0) :
			msg = f'{mention} Je n\'ai pas trouvé de jeux correspondant à **{name}**'
		else :
			msg = f'{mention} J\'ai trouvé {len(games)} jeux :\n'
			ite = iter(games)
			while (game := next(ite, None)) is not None and len(msg) < 1850 :
				msg += f'- [{game.get('name')}](https://www.protondb.com/app/{game.get('id')}) classé **{game.get('tier')}**\n'
			rest = sum(1 for _ in ite)
			if (rest > 0): 
				msg += f'- et encore {rest} autres jeux'
		try : 
			await message.channel.send(msg, suppress_embeds=True)
		except Exception as e:
			logging.error(e)
		
