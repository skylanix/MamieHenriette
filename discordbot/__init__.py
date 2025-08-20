import asyncio
import datetime
import discord
import json
import logging
import random
import requests

from database import db
from database.helpers import ConfigurationHelper
from database.models import Configuration, GameBundle, Humeur, Commande
from protondb import searhProtonDb
from discord import Message


class DiscordBot(discord.Client):
	async def on_ready(self):
		logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
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
					logging.info(f'changement de status {humeur.text}')
					await self.change_presence(status = discord.Status.online,  activity = discord.CustomActivity(humeur.text))
			# 10 minutes TODO à rendre configurable
			await asyncio.sleep(10*60)

	async def updateHumbleBundle(self):
		while not self.is_closed():
			if ConfigurationHelper().getValue('humble_bundle_enable') and ConfigurationHelper().getIntValue('humble_bundle_channel') != 0 :
				response = requests.get("http://hexas.shionn.org/humble-bundle/json", headers={ "Content-Type": "application/json" })
				if response.status_code == 200:
					bundle = response.json()
					if GameBundle.query.filter_by(id=bundle['id']).first() == None :
						choice = bundle['choices'][0]
						date = datetime.datetime.fromtimestamp(bundle['endDate']/1000,datetime.UTC).strftime("%d %B %Y")
						message = f"@here **Humble Bundle** propose un pack de jeu [{bundle['name']}]({bundle['url']}) contenant :\n"
						for game in choice["games"]:
							message += f"- {game}\n"
						message += f"Pour {choice['price']}€, disponible jusqu'au {date}."
						await self.get_channel(ConfigurationHelper().getIntValue('humble_bundle_channel')).send(message)
						db.session.add(GameBundle(id=bundle['id'], name=bundle['name'], json = json.dumps(bundle)))
						db.session.commit()
				else:
					logging.error(f"Erreur de connexion {response.status_code}")
			else: 
				logging.info('Humble bundle est désactivé')
			# toute les 30 minutes
			await asyncio.sleep(30*60)

	def begin(self) : 
		token = Configuration.query.filter_by(key='discord_token').first()
		if token :
			self.run(token.value)
		else :
			logging.error('pas de token on ne lance pas discord')

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
		
