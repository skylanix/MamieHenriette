import discord
import asyncio
from datetime import datetime
from database import db
from database.helpers import ConfigurationHelper
from database.models import ModerationEvent
from discord import Message

def get_staff_role_id():
	staff_role = ConfigurationHelper().getValue('moderation_staff_role_id')
	return int(staff_role) if staff_role else 581990740431732738

def get_embed_delete_delay():
	delay = ConfigurationHelper().getValue('moderation_embed_delete_delay')
	return int(delay) if delay else 0

async def delete_after_delay(message):
	delay = get_embed_delete_delay()
	if delay > 0:
		await asyncio.sleep(delay)
		try:
			await message.delete()
		except:
			pass

async def handle_warning_command(message: Message, bot):
	if not any(role.id == get_staff_role_id() for role in message.author.roles):
		embed = discord.Embed(
			title="❌ Accès refusé",
			description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	parts = message.content.split(maxsplit=2)
	
	if len(parts) < 2:
		embed = discord.Embed(
			title="📋 Utilisation de la commande",
			description="**Syntaxe :** `!averto @utilisateur [raison]` ou `!averto <id> [raison]`",
			color=discord.Color.blue()
		)
		embed.add_field(name="Exemples", value="• `!averto @User Spam dans le chat`\n• `!warn 123456789012345678 Comportement inapproprié`\n• `!av @User`", inline=False)
		embed.add_field(name="Aliases", value="`!averto`, `!av`, `!avertissement`, `!warn`", inline=False)
		await message.channel.send(embed=embed)
		return
	
	target_user = None
	if message.mentions:
		target_user = message.mentions[0]
		reason = parts[2] if len(parts) > 2 else "Sans raison"
	else:
		try:
			user_id = int(parts[1])
			target_user = await bot.fetch_user(user_id)
			reason = parts[2] if len(parts) > 2 else "Sans raison"
		except (ValueError, discord.NotFound):
			embed = discord.Embed(
				title="❌ Erreur",
				description="Utilisateur introuvable. Vérifiez la mention ou l'ID Discord.",
				color=discord.Color.red()
			)
			await message.channel.send(embed=embed)
			return
	
	if not target_user:
		embed = discord.Embed(
			title="❌ Erreur",
			description="Impossible de trouver l'utilisateur.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	event = ModerationEvent(
		type='warning',
		username=target_user.name,
		discord_id=str(target_user.id),
		created_at=datetime.utcnow(),
		reason=reason,
		staff_id=str(message.author.id),
		staff_name=message.author.name
	)
	db.session.add(event)
	db.session.commit()
	
	embed = discord.Embed(
		title="⚠️ Sanction",
		description=f"L'utilisateur **{target_user.name}** (`@{target_user.name}`) a été **averti**.",
		color=discord.Color.orange()
	)
	if reason != "Sans raison":
		embed.add_field(name="Raison", value=reason, inline=False)
	
	sent_message = await message.channel.send(embed=embed)
	await message.delete()
	asyncio.create_task(delete_after_delay(sent_message))

async def handle_remove_warning_command(message: Message, bot):
	if not any(role.id == get_staff_role_id() for role in message.author.roles):
		embed = discord.Embed(
			title="❌ Accès refusé",
			description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	parts = message.content.split(maxsplit=1)
	
	if len(parts) < 2:
		embed = discord.Embed(
			title="📋 Utilisation de la commande",
			description="**Syntaxe :** `!delaverto <id>`",
			color=discord.Color.blue()
		)
		embed.add_field(name="Exemples", value="• `!delaverto 5`\n• `!removewarn 12`", inline=False)
		embed.add_field(name="Aliases", value="`!delaverto`, `!removewarn`, `!delwarn`", inline=False)
		await message.channel.send(embed=embed)
		return
	
	try:
		event_id = int(parts[1])
	except ValueError:
		embed = discord.Embed(
			title="❌ Erreur",
			description="L'ID doit être un nombre entier.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	event = ModerationEvent.query.filter_by(id=event_id).first()
	
	if not event:
		embed = discord.Embed(
			title="❌ Erreur",
			description=f"Aucun événement de modération trouvé avec l'ID `{event_id}`.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	username = event.username
	event_type = event.type
	
	db.session.delete(event)
	db.session.commit()
	
	embed = discord.Embed(
		title="✅ Événement supprimé",
		description=f"L'événement de type **{event_type}** pour **{username}** (ID: {event_id}) a été supprimé.",
		color=discord.Color.green(),
		timestamp=datetime.utcnow()
	)
	embed.add_field(name="🛡️ Modérateur", value=f"{message.author.name}\n`{message.author.id}`", inline=True)
	embed.set_footer(text="Mamie Henriette")
	
	await message.channel.send(embed=embed)
	await message.delete()

async def handle_list_warnings_command(message: Message, bot):
	if not any(role.id == get_staff_role_id() for role in message.author.roles):
		embed = discord.Embed(
			title="❌ Accès refusé",
			description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	parts = message.content.split(maxsplit=1)
	user_filter = None
	
	if len(parts) > 1 and message.mentions:
		user_filter = str(message.mentions[0].id)
	
	if user_filter:
		events = ModerationEvent.query.filter_by(discord_id=user_filter).order_by(ModerationEvent.created_at.desc()).all()
	else:
		events = ModerationEvent.query.order_by(ModerationEvent.created_at.desc()).all()
	
	if not events:
		embed = discord.Embed(
			title="📋 Liste des événements",
			description="Aucun événement de modération trouvé.",
			color=discord.Color.blue()
		)
		await message.channel.send(embed=embed)
		return
	
	page = 0
	per_page = 5
	max_page = (len(events) - 1) // per_page
	
	def create_embed(page_num):
		start = page_num * per_page
		end = start + per_page
		page_events = events[start:end]
		
		embed = discord.Embed(
			title="📋 Liste des événements de modération",
			description=f"Total : {len(events)} événement(s)",
			color=discord.Color.blue(),
			timestamp=datetime.utcnow()
		)
		
		for event in page_events:
			date_str = event.created_at.strftime('%d/%m/%Y %H:%M') if event.created_at else 'N/A'
			embed.add_field(
				name=f"ID {event.id} - {event.type.upper()} - {event.username}",
				value=f"**Discord ID:** `{event.discord_id}`\n**Date:** {date_str}\n**Raison:** {event.reason}\n**Staff:** {event.staff_name}",
				inline=False
			)
		
		embed.set_footer(text=f"Page {page_num + 1}/{max_page + 1}")
		return embed
	
	msg = await message.channel.send(embed=create_embed(page))
	
	if max_page > 0:
		await msg.add_reaction('⬅️')
		await msg.add_reaction('➡️')
	await msg.add_reaction('❌')
	
	def check(reaction, user):
		return user == message.author and str(reaction.emoji) in ['⬅️', '➡️', '❌'] and reaction.message.id == msg.id
	
	while True:
		try:
			reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
			
			if str(reaction.emoji) == '❌':
				await msg.delete()
				break
			elif str(reaction.emoji) == '➡️' and page < max_page:
				page += 1
				await msg.edit(embed=create_embed(page))
			elif str(reaction.emoji) == '⬅️' and page > 0:
				page -= 1
				await msg.edit(embed=create_embed(page))
			
			await msg.remove_reaction(reaction, user)
		except:
			break
	
	if msg:
		try:
			await msg.clear_reactions()
		except:
			pass
	
	await message.delete()

async def handle_ban_command(message: Message, bot):
	if not any(role.id == get_staff_role_id() for role in message.author.roles):
		embed = discord.Embed(
			title="❌ Accès refusé",
			description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	parts = message.content.split(maxsplit=2)
	
	if len(parts) < 2:
		embed = discord.Embed(
			title="📋 Utilisation de la commande",
			description="**Syntaxe :** `!ban @utilisateur [raison]` ou `!ban <id> [raison]`",
			color=discord.Color.blue()
		)
		embed.add_field(name="Exemples", value="• `!ban @User Spam répété`\n• `!ban 123456789012345678 Comportement toxique`", inline=False)
		await message.channel.send(embed=embed)
		return
	
	target_user = None
	if message.mentions:
		target_user = message.mentions[0]
		reason = parts[2] if len(parts) > 2 else "Sans raison"
	else:
		try:
			user_id = int(parts[1])
			target_user = await bot.fetch_user(user_id)
			reason = parts[2] if len(parts) > 2 else "Sans raison"
		except (ValueError, discord.NotFound):
			embed = discord.Embed(
				title="❌ Erreur",
				description="Utilisateur introuvable. Vérifiez la mention ou l'ID Discord.",
				color=discord.Color.red()
			)
			await message.channel.send(embed=embed)
			return
	
	if not target_user:
		embed = discord.Embed(
			title="❌ Erreur",
			description="Impossible de trouver l'utilisateur.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	member = message.guild.get_member(target_user.id)
	joined_days = None
	if member and member.joined_at:
		delta = datetime.utcnow() - member.joined_at.replace(tzinfo=None)
		joined_days = delta.days
	
	try:
		await message.guild.ban(target_user, reason=reason)
	except discord.Forbidden:
		embed = discord.Embed(
			title="❌ Erreur",
			description="Je n'ai pas les permissions nécessaires pour bannir cet utilisateur.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	event = ModerationEvent(
		type='ban',
		username=target_user.name,
		discord_id=str(target_user.id),
		created_at=datetime.utcnow(),
		reason=reason,
		staff_id=str(message.author.id),
		staff_name=message.author.name
	)
	db.session.add(event)
	db.session.commit()
	
	embed = discord.Embed(
		title="⚠️ Sanction",
		description=f"L'utilisateur **{target_user.name}** (`@{target_user.name}`) a été **banni**.",
		color=discord.Color.red()
	)
	embed.add_field(name="ID Discord", value=f"`{target_user.id}`", inline=False)
	if joined_days is not None:
		embed.add_field(name="Membre depuis", value=f"{joined_days} jour{'s' if joined_days > 1 else ''}", inline=False)
	if reason != "Sans raison":
		embed.add_field(name="Raison", value=reason, inline=False)
	
	sent_message = await message.channel.send(embed=embed)
	await message.delete()
	asyncio.create_task(delete_after_delay(sent_message))

async def handle_kick_command(message: Message, bot):
	if not any(role.id == get_staff_role_id() for role in message.author.roles):
		embed = discord.Embed(
			title="❌ Accès refusé",
			description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	parts = message.content.split(maxsplit=2)
	
	if len(parts) < 2 or not message.mentions:
		embed = discord.Embed(
			title="📋 Utilisation de la commande",
			description="**Syntaxe :** `!kick @utilisateur [raison]`",
			color=discord.Color.blue()
		)
		embed.add_field(name="Exemples", value="• `!kick @User Spam dans le chat`\n• `!kick @User Comportement inapproprié`", inline=False)
		await message.channel.send(embed=embed)
		return
	
	target_member = message.mentions[0]
	reason = parts[2] if len(parts) > 2 else "Sans raison"
	
	member_obj = message.guild.get_member(target_member.id)
	if not member_obj:
		embed = discord.Embed(
			title="❌ Erreur",
			description="L'utilisateur n'est pas membre du serveur.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	joined_days = None
	if member_obj.joined_at:
		delta = datetime.utcnow() - member_obj.joined_at.replace(tzinfo=None)
		joined_days = delta.days
	
	try:
		await message.guild.kick(member_obj, reason=reason)
	except discord.Forbidden:
		embed = discord.Embed(
			title="❌ Erreur",
			description="Je n'ai pas les permissions nécessaires pour expulser cet utilisateur.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	event = ModerationEvent(
		type='kick',
		username=target_member.name,
		discord_id=str(target_member.id),
		created_at=datetime.utcnow(),
		reason=reason,
		staff_id=str(message.author.id),
		staff_name=message.author.name
	)
	db.session.add(event)
	db.session.commit()
	
	embed = discord.Embed(
		title="⚠️ Sanction",
		description=f"L'utilisateur **{target_member.name}** (`@{target_member.name}`) a été **expulsé**.",
		color=discord.Color.orange()
	)
	if joined_days is not None:
		embed.add_field(name="Membre depuis", value=f"{joined_days} jour{'s' if joined_days > 1 else ''}", inline=False)
	if reason != "Sans raison":
		embed.add_field(name="Raison", value=reason, inline=False)
	
	sent_message = await message.channel.send(embed=embed)
	await message.delete()
	asyncio.create_task(delete_after_delay(sent_message))

async def handle_unban_command(message: Message, bot):
	if not any(role.id == get_staff_role_id() for role in message.author.roles):
		embed = discord.Embed(
			title="❌ Accès refusé",
			description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	parts = message.content.split(maxsplit=2)
	
	if len(parts) < 2:
		embed = discord.Embed(
			title="📋 Utilisation de la commande",
			description="**Syntaxe :** `!unban <discord_id>` ou `!unban #<sanction_id> [raison]`",
			color=discord.Color.blue()
		)
		embed.add_field(name="Exemples", value="• `!unban 123456789012345678`\n• `!unban #5 Appel accepté`", inline=False)
		await message.channel.send(embed=embed)
		return
	
	reason = parts[2] if len(parts) > 2 else "Sans raison"
	target_user = None
	discord_id = None
	
	if parts[1].startswith('#'):
		try:
			sanction_id = int(parts[1][1:])
			event = ModerationEvent.query.filter_by(id=sanction_id, type='ban').first()
			if not event:
				embed = discord.Embed(
					title="❌ Erreur",
					description=f"Aucune sanction de ban trouvée avec l'ID #{sanction_id}.",
					color=discord.Color.red()
				)
				await message.channel.send(embed=embed)
				return
			discord_id = event.discord_id
			try:
				target_user = await bot.fetch_user(int(discord_id))
			except discord.NotFound:
				pass
		except ValueError:
			embed = discord.Embed(
				title="❌ Erreur",
				description="ID de sanction invalide.",
				color=discord.Color.red()
			)
			await message.channel.send(embed=embed)
			return
	else:
		try:
			discord_id = parts[1]
			target_user = await bot.fetch_user(int(discord_id))
		except (ValueError, discord.NotFound):
			embed = discord.Embed(
				title="❌ Erreur",
				description="ID Discord invalide ou utilisateur introuvable.",
				color=discord.Color.red()
			)
			await message.channel.send(embed=embed)
			return
	
	try:
		await message.guild.unban(discord.Object(id=int(discord_id)), reason=reason)
	except discord.NotFound:
		embed = discord.Embed(
			title="❌ Erreur",
			description="Cet utilisateur n'est pas banni.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	except discord.Forbidden:
		embed = discord.Embed(
			title="❌ Erreur",
			description="Je n'ai pas les permissions nécessaires pour débannir cet utilisateur.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return
	
	username = target_user.name if target_user else f"ID: {discord_id}"
	
	event = ModerationEvent(
		type='unban',
		username=username,
		discord_id=discord_id,
		created_at=datetime.utcnow(),
		reason=reason,
		staff_id=str(message.author.id),
		staff_name=message.author.name
	)
	db.session.add(event)
	db.session.commit()
	
	embed = discord.Embed(
		title="⚠️ Sanction",
		description=f"L'utilisateur **{username}** (`@{username}`) a été **débanni**.",
		color=discord.Color.green()
	)
	if reason != "Sans raison":
		embed.add_field(name="Raison", value=reason, inline=False)
	
	sent_message = await message.channel.send(embed=embed)
	await message.delete()
	asyncio.create_task(delete_after_delay(sent_message))
