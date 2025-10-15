import asyncio
import discord
import logging
import random

from database import db
from database.helpers import ConfigurationHelper
from database.models import Configuration, Humeur, Commande
from discord import Message, TextChannel, Member
from discordbot.humblebundle import checkHumbleBundleAndNotify
from discordbot.command import handle_warning_command, handle_remove_warning_command, handle_list_warnings_command, handle_ban_command, handle_kick_command, handle_unban_command
from discordbot.welcome import sendWelcomeMessage, sendLeaveMessage, updateInviteCache
from protondb import searhProtonDb

class DiscordBot(discord.Client):
	async def on_ready(self):
		logging.info(f'Connecté en tant que {self.user} (ID: {self.user.id})')
		for c in self.get_all_channels() :
			logging.info(f'{c.id} {c.name}')
		
		for guild in self.guilds:
			await updateInviteCache(guild)
		
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

	def getAllTextChannel(self) -> list[TextChannel]:
		channels = []
		for channel in self.get_all_channels():
			if isinstance(channel, TextChannel):
				channels.append(channel)
		return channels


	def begin(self) : 
		token = Configuration.query.filter_by(key='discord_token').first()
		if token :
			self.run(token.value)
		else :
			logging.error('Aucun token Discord configuré. Le bot ne peut pas être démarré')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True
bot = DiscordBot(intents=intents)

# https://discordpy.readthedocs.io/en/stable/quickstart.html
@bot.event
async def on_message(message: Message):
	if message.author == bot.user:
		return
	if not message.content.startswith('!'):
		return
	command_name = message.content.split()[0]
	
	if ConfigurationHelper().getValue('moderation_enable'):
		if command_name in ['!averto', '!av', '!avertissement', '!warn']:
			await handle_warning_command(message, bot)
			return

		if command_name in ['!delaverto', '!removewarn', '!unwarn']:
			await handle_remove_warning_command(message, bot)
			return

		if command_name in ['!listevent', '!listwarn', '!warnings']:
			await handle_list_warnings_command(message, bot)
			return
	
	if ConfigurationHelper().getValue('moderation_ban_enable'):
		if command_name == '!ban':
			await handle_ban_command(message, bot)
			return
		
		if command_name == '!unban':
			await handle_unban_command(message, bot)
			return
	
	if ConfigurationHelper().getValue('moderation_kick_enable'):
		if command_name == '!kick':
			await handle_kick_command(message, bot)
			return
	
	commande = Commande.query.filter_by(discord_enable=True, trigger=command_name).first()
	if commande:
		try:
			await message.channel.send(commande.response, suppress_embeds=True)
			return
		except Exception as e:
			logging.error(f'Échec de l\'exécution de la commande Discord : {e}')

	if(ConfigurationHelper().getValue('proton_db_enable_enable') and message.content.find('!protondb')==0) :
		if (message.content.find('<@')>0) :
			mention = message.content[message.content.find('<@'):]
		else :
			mention = message.author.mention
		name = message.content.replace('!protondb', '').replace(f'{mention}', '').strip();
		games = searhProtonDb(name)
		if (len(games)==0) :
			msg = f'{mention} Je n\'ai pas trouvé de jeux correspondant à **{name}**. Es-tu sûr que le jeu est disponible sur Steam ?'
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
			logging.error(f'Échec de l\'envoi du message ProtonDB : {e}')

@bot.event
async def on_member_join(member: Member):
	await sendWelcomeMessage(bot, member)

@bot.event
async def on_member_remove(member: Member):
	await sendLeaveMessage(bot, member)

@bot.event
async def on_invite_create(invite):
	await updateInviteCache(invite.guild)

@bot.event
async def on_invite_delete(invite):
	await updateInviteCache(invite.guild)

