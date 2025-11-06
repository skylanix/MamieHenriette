import asyncio
import logging
import time
import os
import discord
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from database import db
from database.helpers import ConfigurationHelper
from database.models import ModerationEvent
from discord import Message

def _get_local_tz():
	tz_name = os.environ.get('APP_TZ') or os.environ.get('TZ') or 'Europe/Paris'
	try:
		return ZoneInfo(tz_name)
	except Exception:
		try:
			return datetime.now().astimezone().tzinfo or timezone.utc
		except Exception:
			return timezone.utc

def _to_local(dt: datetime) -> datetime | None:
	if not dt:
		return None
	if dt.tzinfo is None:
		# Assume stored in UTC if naive
		dt = dt.replace(tzinfo=timezone.utc)
	return dt.astimezone(_get_local_tz())

def get_staff_role_ids():
	staff_roles = ConfigurationHelper().getValue('moderation_staff_role_ids')
	if staff_roles:
		return [int(role_id.strip()) for role_id in staff_roles.split(',') if role_id.strip()]
	staff_role_old = ConfigurationHelper().getValue('moderation_staff_role_id')
	if staff_role_old:
		return [int(staff_role_old)]
	return []

def has_staff_role(user_roles):
	staff_role_ids = get_staff_role_ids()
	if not staff_role_ids:
		return False
	return any(role.id in staff_role_ids for role in user_roles)

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

async def safe_delete_message(message: Message):
	try:
		await message.delete()
	except:
		pass

async def send_access_denied(channel):
	embed = discord.Embed(
		title="❌ Accès refusé",
		description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
		color=discord.Color.red()
	)
	await channel.send(embed=embed)

async def send_user_not_found(channel):
	embed = discord.Embed(
		title="❌ Erreur",
		description="Utilisateur introuvable. Vérifiez la mention ou l'ID Discord.",
		color=discord.Color.red()
	)
	await channel.send(embed=embed)

async def parse_target_user_and_reason(message, bot, parts: list):
	if message.mentions:
		target_user = message.mentions[0]
		reason = parts[2] if len(parts) > 2 else "Sans raison"
		return target_user, reason
	
	try:
		user_id = int(parts[1])
		target_user = await bot.fetch_user(user_id)
		reason = parts[2] if len(parts) > 2 else "Sans raison"
		return target_user, reason
	except (ValueError, discord.NotFound):
		return None, None

async def send_warning_usage(channel):
	embed = discord.Embed(
		title="📋 Utilisation de la commande",
		description="**Syntaxe :** `!averto @utilisateur [raison]` ou `!averto <id> [raison]`",
		color=discord.Color.blue()
	)
	embed.add_field(name="Exemples", value="• `!averto @User Spam dans le chat`\n• `!warn 123456789012345678 Comportement inapproprié`\n• `!av @User`", inline=False)
	embed.add_field(name="Aliases", value="`!averto`, `!av`, `!avertissement`, `!warn`", inline=False)
	await channel.send(embed=embed)

def create_warning_event(target_user, reason: str, staff_member):
	event = ModerationEvent(
		type='warning',
		username=target_user.name,
		discord_id=str(target_user.id),
		created_at=datetime.now(timezone.utc),
		reason=reason,
		staff_id=str(staff_member.id),
		staff_name=staff_member.name
	)
	db.session.add(event)
	_commit_with_retry()

def _commit_with_retry(max_retries: int = 5, base_delay: float = 0.1):
	attempt = 0
	while True:
		try:
			db.session.commit()
			return
		except Exception as e:
			msg = str(e)
			if 'database is locked' in msg.lower() and attempt < max_retries:
				db.session.rollback()
				delay = base_delay * (2 ** attempt)
				time.sleep(delay)
				attempt += 1
				continue
			db.session.rollback()
			raise

async def send_warning_confirmation(channel, target_user, reason: str, original_message: Message):
	embed = discord.Embed(
		title="⚠️ Sanction",
		description=f"L'utilisateur **{target_user.name}** (`@{target_user.name}`) a été **averti**.",
		color=discord.Color.orange()
	)
	if reason != "Sans raison":
		embed.add_field(name="Raison", value=reason, inline=False)
	
	sent_message = await channel.send(embed=embed)
	await safe_delete_message(original_message)
	asyncio.create_task(delete_after_delay(sent_message))

async def handle_warning_command(message: Message, bot):
	parts = message.content.split(maxsplit=2)
	if not has_staff_role(message.author.roles):
		await send_access_denied(message.channel)
	elif len(parts) < 2:
		await send_warning_usage(message.channel)
	else:
		target_user, reason = await parse_target_user_and_reason(message, bot, parts)
		if not target_user:
			await send_user_not_found(message.channel)
		else:
			await _process_warning_success(message, target_user, reason)

async def _process_warning_success(message: Message, target_user, reason: str):
	create_warning_event(target_user, reason, message.author)
	await send_warning_confirmation(message.channel, target_user, reason, message)

async def send_remove_warning_usage(channel):
	embed = discord.Embed(
		title="📋 Utilisation de la commande",
		description="**Syntaxe :** `!delaverto <id>`",
		color=discord.Color.blue()
	)
	embed.add_field(name="Exemples", value="• `!delaverto 5`\n• `!removewarn 12`", inline=False)
	embed.add_field(name="Aliases", value="`!delaverto`, `!removewarn`, `!delwarn`", inline=False)
	await channel.send(embed=embed)

async def send_invalid_event_id(channel):
	embed = discord.Embed(
		title="❌ Erreur",
		description="L'ID doit être un nombre entier.",
		color=discord.Color.red()
	)
	await channel.send(embed=embed)

async def send_event_not_found(channel, event_id: int):
	embed = discord.Embed(
		title="❌ Erreur",
		description=f"Aucun événement de modération trouvé avec l'ID `{event_id}`.",
		color=discord.Color.red()
	)
	await channel.send(embed=embed)

def delete_moderation_event(event: ModerationEvent):
	db.session.delete(event)
	db.session.commit()

async def send_event_deleted_confirmation(channel, event: ModerationEvent, moderator, original_message: Message):
	embed = discord.Embed(
		title="✅ Événement supprimé",
		description=f"L'événement de type **{event.type}** pour **{event.username}** (ID: {event.id}) a été supprimé.",
		color=discord.Color.green(),
		timestamp=datetime.now(timezone.utc)
	)
	embed.add_field(name="🛡️ Modérateur", value=f"{moderator.name}\n`{moderator.id}`", inline=True)
	embed.set_footer(text="Mamie Henriette")
	
	await channel.send(embed=embed)
	await safe_delete_message(original_message)

async def handle_remove_warning_command(message: Message, bot):
	if not has_staff_role(message.author.roles):
		await send_access_denied(message.channel)
		return
	
	parts = message.content.split(maxsplit=1)
	
	if len(parts) < 2:
		await send_remove_warning_usage(message.channel)
		return
	
	try:
		event_id = int(parts[1])
	except ValueError:
		await send_invalid_event_id(message.channel)
		return
	
	event = ModerationEvent.query.filter_by(id=event_id).first()
	
	if not event:
		await send_event_not_found(message.channel, event_id)
		return
	
	delete_moderation_event(event)
	await send_event_deleted_confirmation(message.channel, event, message.author, message)

def get_moderation_events(user_filter: str = None):
	if user_filter:
		return ModerationEvent.query.filter_by(discord_id=user_filter).order_by(ModerationEvent.created_at.desc()).all()
	return ModerationEvent.query.order_by(ModerationEvent.created_at.desc()).all()

async def send_no_events_found(channel):
	embed = discord.Embed(
		title="📋 Liste des événements",
		description="Aucun événement de modération trouvé.",
		color=discord.Color.blue()
	)
	await channel.send(embed=embed)

def create_events_list_embed(events: list, page_num: int, per_page: int):
	start = page_num * per_page
	end = start + per_page
	page_events = events[start:end]
	max_page = (len(events) - 1) // per_page
	
	embed = discord.Embed(
		title="📋 Liste des événements de modération",
		description=f"Total : {len(events)} événement(s)",
		color=discord.Color.blue(),
		timestamp=datetime.now(timezone.utc)
	)
	
	for event in page_events:
		local_dt = _to_local(event.created_at)
		date_str = local_dt.strftime('%d/%m/%Y %H:%M') if local_dt else 'N/A'
		embed.add_field(
			name=f"ID {event.id} - {event.type.upper()} - {event.username}",
			value=f"**Discord ID:** `{event.discord_id}`\n**Date:** {date_str}\n**Raison:** {event.reason}\n**Staff:** {event.staff_name}",
			inline=False
		)
	
	embed.set_footer(text=f"Page {page_num + 1}/{max_page + 1}")
	return embed

async def add_pagination_reactions(msg, max_page: int):
	if max_page > 0:
		await msg.add_reaction('⬅️')
		await msg.add_reaction('➡️')
	await msg.add_reaction('❌')

async def handle_pagination_loop(msg, bot, message_author, events: list, per_page: int):
	page = 0
	max_page = (len(events) - 1) // per_page
	
	def check(reaction, user):
		return user == message_author and str(reaction.emoji) in ['⬅️', '➡️', '❌'] and reaction.message.id == msg.id
	
	while True:
		try:
			reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
			
			if str(reaction.emoji) == '❌':
				await msg.delete()
				break
			elif str(reaction.emoji) == '➡️' and page < max_page:
				page += 1
				await msg.edit(embed=create_events_list_embed(events, page, per_page))
			elif str(reaction.emoji) == '⬅️' and page > 0:
				page -= 1
				await msg.edit(embed=create_events_list_embed(events, page, per_page))
			
			await msg.remove_reaction(reaction, user)
		except:
			break
	
	try:
		await msg.clear_reactions()
	except:
		pass

async def handle_list_warnings_command(message: Message, bot):
	if not has_staff_role(message.author.roles):
		await send_access_denied(message.channel)
		return
	
	parts = message.content.split(maxsplit=1)
	user_filter = str(message.mentions[0].id) if len(parts) > 1 and message.mentions else None
	
	events = get_moderation_events(user_filter)
	
	if not events:
		await send_no_events_found(message.channel)
		return
	
	per_page = 5
	max_page = (len(events) - 1) // per_page
	
	msg = await message.channel.send(embed=create_events_list_embed(events, 0, per_page))
	await add_pagination_reactions(msg, max_page)
	await handle_pagination_loop(msg, bot, message.author, events, per_page)
	await safe_delete_message(message)

async def handle_ban_command(message: Message, bot):
	parts = message.content.split(maxsplit=2)
	if not has_staff_role(message.author.roles):
		await send_access_denied(message.channel)
	elif len(parts) < 2:
		await _send_ban_usage(message.channel)
	else:
		target_user, reason = await _parse_ban_target_and_reason(message, bot, parts)
		if not target_user:
			await _send_user_not_found_for_ban(message.channel)
		else:
			await _process_ban_success(message, target_user, reason)

async def _send_ban_usage(channel):
	embed = discord.Embed(
		title="📋 Utilisation de la commande",
		description="**Syntaxe :** `!ban @utilisateur [raison]` ou `!ban <id> [raison]`",
		color=discord.Color.blue()
	)
	embed.add_field(name="Exemples", value="• `!ban @User Spam répété`\n• `!ban 123456789012345678 Comportement toxique`", inline=False)
	await channel.send(embed=embed)

async def _parse_ban_target_and_reason(message: Message, bot, parts: list):
	if message.mentions:
		return message.mentions[0], (parts[2] if len(parts) > 2 else "Sans raison")
	try:
		user_id = int(parts[1])
		user = await bot.fetch_user(user_id)
		return user, (parts[2] if len(parts) > 2 else "Sans raison")
	except (ValueError, discord.NotFound):
		return None, None

async def _send_user_not_found_for_ban(channel):
	embed = discord.Embed(
		title="❌ Erreur",
		description="Utilisateur introuvable. Vérifiez la mention ou l'ID Discord.",
		color=discord.Color.red()
	)
	await channel.send(embed=embed)

def _create_ban_event(target_user, reason: str, staff_member):
	event = ModerationEvent(
		type='ban',
		username=target_user.name,
		discord_id=str(target_user.id),
        created_at=datetime.now(timezone.utc),
		reason=reason,
		staff_id=str(staff_member.id),
		staff_name=staff_member.name
	)
	db.session.add(event)
	_commit_with_retry()
	return event

async def _process_ban_success(message: Message, target_user, reason: str):
	member = message.guild.get_member(target_user.id)
	joined_days = None
	if member and member.joined_at:
		delta = datetime.now(timezone.utc) - (member.joined_at if member.joined_at.tzinfo else member.joined_at.replace(tzinfo=timezone.utc))
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

	event = _create_ban_event(target_user, reason, message.author)

	embed = discord.Embed(
		title="⚠️ Sanction",
		description=f"L'utilisateur **{target_user.name}** (`@{target_user.name}`) a été **banni**.",
		color=discord.Color.red()
	)
	embed.add_field(name="ID Discord", value=f"`{target_user.id}`", inline=False)
	if joined_days is not None:
		embed.add_field(name="Membre depuis", value=format_days_to_age(joined_days), inline=False)
	if reason != "Sans raison":
		embed.add_field(name="Raison", value=reason, inline=False)

	sent_message = await message.channel.send(embed=embed)
	await safe_delete_message(message)
	asyncio.create_task(delete_after_delay(sent_message))
async def handle_unban_command(message: Message, bot):
	parts = message.content.split(maxsplit=2)
	if not has_staff_role(message.author.roles):
		await send_access_denied(message.channel)
	elif len(parts) < 2:
		await _send_unban_usage(message.channel)
	else:
		target_user, discord_id, reason = await _parse_unban_target_and_reason(message, bot, parts)
		if not discord_id:
			await _send_unban_invalid_id(message.channel)
		else:
			await _process_unban_success(message, bot, target_user, discord_id, reason)

async def _send_unban_usage(channel):
	embed = discord.Embed(
		title="📋 Utilisation de la commande",
		description="**Syntaxe :** `!unban <discord_id>` ou `!unban #<sanction_id> [raison]`",
		color=discord.Color.blue()
	)
	embed.add_field(name="Exemples", value="• `!unban 123456789012345678`\n• `!unban #5 Appel accepté`", inline=False)
	await channel.send(embed=embed)

async def _parse_unban_target_and_reason(message: Message, bot, parts: list):
	reason = parts[2] if len(parts) > 2 else "Sans raison"
	target_user = None
	discord_id = None
	if parts[1].startswith('#'):
		try:
			sanction_id = int(parts[1][1:])
			evt = ModerationEvent.query.filter_by(id=sanction_id, type='ban').first()
			if not evt:
				return None, None, reason
			discord_id = evt.discord_id
			try:
				target_user = await bot.fetch_user(int(discord_id))
			except discord.NotFound:
				pass
		except ValueError:
			return None, None, reason
	else:
		try:
			discord_id = parts[1]
			target_user = await bot.fetch_user(int(discord_id))
		except (ValueError, discord.NotFound):
			return None, None, reason
	return target_user, discord_id, reason

async def _send_unban_invalid_id(channel):
	embed = discord.Embed(
		title="❌ Erreur",
		description="ID Discord invalide ou utilisateur introuvable.",
		color=discord.Color.red()
	)
	await channel.send(embed=embed)

async def _process_unban_success(message: Message, bot, target_user, discord_id: str, reason: str):
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
	create = ModerationEvent(
		type='unban',
		username=username,
		discord_id=discord_id,
		created_at=datetime.now(timezone.utc),
		reason=reason,
		staff_id=str(message.author.id),
		staff_name=message.author.name
	)
	db.session.add(create)
	_commit_with_retry()

	try:
		asyncio.create_task(_send_unban_invite(message, bot, target_user, discord_id))
	except:
		pass

	embed = discord.Embed(
		title="⚠️ Sanction",
		description=f"L'utilisateur **{username}** (`@{username}`) a été **débanni**.",
		color=discord.Color.green()
	)
	if reason != "Sans raison":
		embed.add_field(name="Raison", value=reason, inline=False)
	
	sent_message = await message.channel.send(embed=embed)
	await safe_delete_message(message)
	asyncio.create_task(delete_after_delay(sent_message))

async def _send_unban_invite(message: Message, bot, target_user, discord_id: str):
	try:
		user_obj = target_user or await bot.fetch_user(int(discord_id))
		channel = None
		try:
			channel_id = ConfigurationHelper().getIntValue('welcome_channel_id')
			if channel_id:
				channel = bot.get_channel(channel_id) or message.guild.get_channel(channel_id)
		except:
			pass
		if not channel:
			me = message.guild.me or message.guild.get_member(bot.user.id)
			for ch in message.guild.text_channels:
				try:
					perms = ch.permissions_for(me) if me else None
					if not perms or not perms.create_instant_invite:
						continue
					channel = ch
					break
				except:
					continue
		if not channel:
			channel = message.guild.system_channel or message.channel
		invite = None
		try:
			invite = await channel.create_invite(max_age=86400, max_uses=1, unique=True, reason='Invitation automatique après débannissement')
		except Exception as e:
			logging.warning(f"[UNBAN] Échec création d'invitation sur #{channel and channel.name}: {e}")
			return
		if user_obj and invite:
			try:
				msg = f"Tu as été débanni de {message.guild.name}. Voici une invitation pour revenir : {invite.url}"
				await user_obj.send(msg)
			except Exception as e:
				logging.warning(f"[UNBAN] Impossible d'envoyer un MP à {user_obj} ({user_obj.id}): {e}")
				try:
					await message.author.send(f"Impossible d'envoyer un MP à {user_obj} pour l'unban. Voici l'invitation à lui transmettre : {invite.url}")
				except:
					pass
	except:
		pass

async def handle_ban_list_command(message: Message, bot):
	if not has_staff_role(message.author.roles):
		embed = discord.Embed(
			title="❌ Accès refusé",
			description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
			color=discord.Color.red()
		)
		await message.channel.send(embed=embed)
		return

	# Récupérer la liste des bannis
	bans = []
	try:
		async for entry in message.guild.bans(limit=None):
			bans.append(entry)
	except TypeError:
		try:
			bans = await message.guild.bans()
		except Exception:
			bans = []
	except Exception:
		bans = []

	if not bans:
		embed = discord.Embed(
			title="🔨 Utilisateurs bannis",
			description="Aucun utilisateur banni sur ce serveur.",
			color=discord.Color.blue()
		)
		msg = await message.channel.send(embed=embed)
		asyncio.create_task(delete_after_delay(msg))
		await safe_delete_message(message)
		return

	page = 0
	per_page = 10
	max_page = (len(bans) - 1) // per_page

	def create_banlist_embed(page_num: int):
		start = page_num * per_page
		end = start + per_page
		page_bans = bans[start:end]
		embed = discord.Embed(
			title="🔨 Utilisateurs bannis",
			description=f"Total : {len(bans)} utilisateur(s) banni(s)",
			color=discord.Color.red(),
			timestamp=datetime.now(timezone.utc)
		)
		for entry in page_bans:
			user = entry.user
			reason = entry.reason or 'Sans raison'
			embed.add_field(
				name=f"{user.name} ({user.id})",
				value=f"Raison: {reason}",
				inline=False
			)
		embed.set_footer(text=f"Page {page_num + 1}/{max_page + 1}")
		return embed

	msg = await message.channel.send(embed=create_banlist_embed(page))
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
				await msg.edit(embed=create_banlist_embed(page))
			elif str(reaction.emoji) == '⬅️' and page > 0:
				page -= 1
				await msg.edit(embed=create_banlist_embed(page))
			await msg.remove_reaction(reaction, user)
		except Exception:
			break

	try:
		await msg.clear_reactions()
	except Exception:
		pass

	await safe_delete_message(message)

async def handle_staff_help_command(message: Message, bot):
	is_staff = has_staff_role(message.author.roles)
	
	embed = discord.Embed(
		title="📚 Aide - Commandes disponibles",
		description="Liste de toutes les commandes disponibles",
		color=discord.Color.blurple(),
		timestamp=datetime.now(timezone.utc)
	)
	embed.set_thumbnail(url=bot.user.display_avatar.url)
	embed.set_footer(text=f"Demandé par {message.author.name}")

	public_commands = []
	
	if ConfigurationHelper().getValue('proton_db_enable_enable'):
		public_commands.append(
			"**🎮 ProtonDB**\n"
			"• `!protondb <nom du jeu>` ou `!pdb <nom du jeu>`\n"
			"Recherche un jeu sur ProtonDB pour vérifier sa compatibilité Linux\n"
			"Ex: `!pdb Elden Ring`"
		)
	
	from database.models import Commande
	custom_commands = Commande.query.filter_by(discord_enable=True).all()
	if custom_commands:
		commands_list = []
		for cmd in custom_commands:
			commands_list.append(f"• `{cmd.trigger}`")
		custom_text = "\n".join(commands_list[:10])
		if len(custom_commands) > 10:
			custom_text += f"\n*... et {len(custom_commands) - 10} autres*"
		public_commands.append(f"**🤖 Commandes personnalisées**\n{custom_text}")
	
	if public_commands:
		for cmd_text in public_commands:
			embed.add_field(name="\u200b", value=cmd_text, inline=False)
	else:
		embed.add_field(
			name="📝 Commandes publiques",
			value="Aucune commande publique configurée pour le moment.",
			inline=False
		)
	
	if is_staff:
		embed.add_field(
			name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
			value="**🛠️ COMMANDES STAFF**",
			inline=False
		)
		
		if ConfigurationHelper().getValue('moderation_enable'):
			value = (
				"• `!averto @utilisateur raison`\n"
				"  *Alias: !warn, !av, !avertissement*\n"
				"• `!delaverto id`\n"
				"  *Alias: !removewarn, !delwarn*\n"
				"• `!warnings` ou `!warnings @utilisateur`\n"
				"  *Alias: !listevent, !listwarn*\n"
				"Exemples:\n"
				"`!averto @User Spam dans le chat`\n"
				"`!delaverto 12`\n"
				"`!warnings @User`"
			)
			embed.add_field(name="⚠️ Avertissements", value=value, inline=False)
			embed.add_field(
				name="🔎 Inspection",
				value=("• `!inspect @utilisateur` ou `!inspect id`\n"
						"Affiche les infos détaillées et l'historique de modération\n"
						"Ex: `!inspect @User`"),
				inline=False
			)

		if ConfigurationHelper().getValue('moderation_ban_enable'):
			value = (
				"• `!ban @utilisateur raison`\n"
				"  Bannit définitivement un utilisateur\n"
				"• `!unban discord_id` ou `!unban #sanction_id raison`\n"
				"  Révoque le ban et envoie une invitation\n"
				"• `!banlist`\n"
				"  Affiche la liste des utilisateurs bannis\n"
				"Exemples:\n"
				"`!ban @User Comportement toxique répété`\n"
				"`!unban 123456789012345678 Erreur de modération`\n"
				"`!unban #5 Appel accepté`"
			)
			embed.add_field(name="🔨 Bannissement", value=value, inline=False)

		if ConfigurationHelper().getValue('moderation_kick_enable'):
			value = (
				"• `!kick @utilisateur raison`\n"
				"  Expulse temporairement un utilisateur du serveur\n"
				"Exemple: `!kick @User Spam de liens`"
			)
			embed.add_field(name="👢 Expulsion", value=value, inline=False)

	try:
		sent = await message.channel.send(embed=embed)
		if is_staff:
			asyncio.create_task(delete_after_delay(sent))
	except Exception:
		pass
	await safe_delete_message(message)

async def handle_kick_command(message: Message, bot):
	parts = message.content.split(maxsplit=2)
	if not has_staff_role(message.author.roles):
		await send_access_denied(message.channel)
	elif len(parts) < 2 or not message.mentions:
		await _send_kick_usage(message.channel)
	else:
		target_member = message.mentions[0]
		reason = parts[2] if len(parts) > 2 else "Sans raison"
		await _process_kick_success(message, target_member, reason)

async def _send_kick_usage(channel):
	embed = discord.Embed(
		title="📋 Utilisation de la commande",
		description="**Syntaxe :** `!kick @utilisateur [raison]`",
		color=discord.Color.blue()
	)
	embed.add_field(name="Exemples", value="• `!kick @User Spam dans le chat`\n• `!kick @User Comportement inapproprié`", inline=False)
	await channel.send(embed=embed)

async def _process_kick_success(message: Message, target_member, reason: str):
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
		delta = datetime.now(timezone.utc) - (member_obj.joined_at if member_obj.joined_at.tzinfo else member_obj.joined_at.replace(tzinfo=timezone.utc))
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
	create = ModerationEvent(
		type='kick',
		username=target_member.name,
		discord_id=str(target_member.id),
		created_at=datetime.now(timezone.utc),
		reason=reason,
		staff_id=str(message.author.id),
		staff_name=message.author.name
	)
	db.session.add(create)
	_commit_with_retry()
	embed = discord.Embed(
		title="⚠️ Sanction",
		description=f"L'utilisateur **{target_member.name}** (`@{target_member.name}`) a été **expulsé**.",
		color=discord.Color.orange()
	)
	if joined_days is not None:
		embed.add_field(name="Membre depuis", value=format_days_to_age(joined_days), inline=False)
	if reason != "Sans raison":
		embed.add_field(name="Raison", value=reason, inline=False)
	sent_message = await message.channel.send(embed=embed)
	await safe_delete_message(message)
	asyncio.create_task(delete_after_delay(sent_message))

def format_days_to_age(days: int) -> str:
	if days >= 365:
		years = days // 365
		remaining_days = days % 365
		if remaining_days > 0:
			return f"{years} an{'s' if years > 1 else ''} et {remaining_days} jour{'s' if remaining_days > 1 else ''}"
		return f"{years} an{'s' if years > 1 else ''}"
	return f"{days} jour{'s' if days > 1 else ''}"

async def get_member_join_info(guild, member_id: int):
	member = guild.get_member(member_id)
	if not member or not member.joined_at:
		return None, None
	
	join_date = member.joined_at
	days_on_server = (datetime.now(timezone.utc) - join_date).days
	return join_date, days_on_server

def get_account_age(user):
	if not user.created_at:
		return None
	account_age = (datetime.now(timezone.utc) - user.created_at).days
	return account_age

def get_user_moderation_history(discord_id: str):
	events = ModerationEvent.query.filter_by(discord_id=discord_id).order_by(ModerationEvent.created_at.desc()).all()
	
	warnings = [e for e in events if e.type == 'warning']
	kicks = [e for e in events if e.type == 'kick']
	bans = [e for e in events if e.type == 'ban']
	
	return warnings, kicks, bans

async def send_inspect_usage(channel):
	embed = discord.Embed(
		title="📋 Utilisation de la commande",
		description="**Syntaxe :** `!inspect @utilisateur` ou `!inspect <id>`",
		color=discord.Color.blue()
	)
	embed.add_field(name="Exemples", value="• `!inspect @User`\n• `!inspect 123456789012345678`", inline=False)
	await channel.send(embed=embed)

async def parse_target_user(message: Message, bot, parts: list):
	if message.mentions:
		return message.mentions[0]
	
	try:
		user_id = int(parts[1])
		return await bot.fetch_user(user_id)
	except (ValueError, discord.NotFound):
		return None

def create_inspect_embed(user, member, join_date, days_on_server, account_age, warnings, kicks, bans, invite_info):
	embed = discord.Embed(
		title=f"🔍 Inspection de {user.name}",
		color=discord.Color.blue(),
		timestamp=datetime.now(timezone.utc)
	)
	
	embed.set_thumbnail(url=user.display_avatar.url)
	embed.add_field(name="👤 Utilisateur", value=f"{user.mention}\n`{user.id}`", inline=True)
	
	if account_age is not None:
		embed.add_field(
			name="📅 Compte créé",
			value=f"{_to_local(user.created_at).strftime('%d/%m/%Y')}\n({format_days_to_age(account_age)})",
			inline=True
		)
	
	if member and join_date:
		embed.add_field(
			name="📥 Rejoint le serveur",
			value=f"{_to_local(join_date).strftime('%d/%m/%Y à %H:%M')}\n({format_days_to_age(days_on_server)})",
			inline=True
		)
	
	if invite_info:
		embed.add_field(name="🎫 Invitation", value=invite_info, inline=True)
	else:
		embed.add_field(name="🎫 Invitation", value="Inconnue", inline=True)
	
	warning_text = f"⚠️ **{len(warnings)}** avertissement{'s' if len(warnings) > 1 else ''}"
	kick_text = f"👢 **{len(kicks)}** expulsion{'s' if len(kicks) > 1 else ''}"
	ban_text = f"🔨 **{len(bans)}** ban{'s' if len(bans) > 1 else ''}"
	
	mod_history = f"{warning_text}\n{kick_text}\n{ban_text}"
	
	if warnings or kicks or bans:
		embed.add_field(name="📋 Historique de modération", value=mod_history, inline=False)
		
		if warnings:
			recent_warnings = warnings[:3]
			warnings_detail = "\n".join([
				f"• ID {w.id} - {_to_local(w.created_at).strftime('%d/%m/%Y')} - {w.reason[:50]}{'...' if len(w.reason) > 50 else ''}"
				for w in recent_warnings
			])
			if len(warnings) > 3:
				warnings_detail += f"\n*... et {len(warnings) - 3} autre(s)*"
			embed.add_field(name="⚠️ Derniers avertissements", value=warnings_detail, inline=False)
	else:
		embed.add_field(name="✅ Historique de modération", value="Aucun incident", inline=False)
	
	embed.set_footer(text="Mamie Henriette")
	return embed

async def get_invite_info_for_user(bot, guild, user_id: int):
	try:
		from discordbot.welcome import invite_cache
		
		audit_logs = [entry async for entry in guild.audit_logs(limit=100, action=discord.AuditLogAction.member_join)]
		
		for entry in audit_logs:
			if entry.target and entry.target.id == user_id:
				if hasattr(entry, 'extra') and entry.extra:
					return f"Code: `{entry.extra}`"
		
		return None
	except:
		return None

async def handle_inspect_command(message: Message, bot):
	if not has_staff_role(message.author.roles):
		await send_access_denied(message.channel)
		return
	
	parts = message.content.split(maxsplit=1)
	
	if len(parts) < 2:
		await send_inspect_usage(message.channel)
		return
	
	target_user = await parse_target_user(message, bot, parts)
	
	if not target_user:
		await send_user_not_found(message.channel)
		return
	
	member = message.guild.get_member(target_user.id)
	join_date, days_on_server = await get_member_join_info(message.guild, target_user.id)
	account_age = get_account_age(target_user)
	warnings, kicks, bans = get_user_moderation_history(str(target_user.id))
	invite_info = await get_invite_info_for_user(bot, message.guild, target_user.id)
	
	embed = create_inspect_embed(
		target_user,
		member,
		join_date,
		days_on_server,
		account_age,
		warnings,
		kicks,
		bans,
		invite_info
	)
	
	await message.channel.send(embed=embed)
	await safe_delete_message(message)

