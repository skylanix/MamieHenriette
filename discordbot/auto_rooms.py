# discordbot/auto_rooms.py — Auto rooms : message et réactions dans la partie texte du salon vocal (onglet Discussion)
import logging
from typing import Optional

import discord
from discord import Member, VoiceState
from database.helpers import ConfigurationHelper

# (guild_id, owner_id) -> room_data (voice_channel_id, control_message_id, whitelist, blacklist, access_mode)
_rooms: dict[tuple[int, int], dict] = {}

# message_id -> (guild_id, owner_id) pour retrouver la room depuis une réaction
_control_message_ids: dict[int, tuple[int, int]] = {}

# Emoji -> action
REACTIONS = [
	("🔓", "open", "Ouvert"),
	("🔒", "closed", "Fermé"),
	("🛡️", "private", "Privé"),
	("✅", "whitelist", "Liste blanche"),
	("🚫", "blacklist", "Liste noire"),
	("🧹", "purge", "Purge"),
	("👑", "transfer", "Propriété"),
	("🎤", "speak", "Micro"),
	("📹", "stream", "Vidéo"),
	("📝", "status", "Statut"),
]


def _status_display(access_mode: str) -> str:
	"""Cadenas ouvert ou fermé selon si le salon est ouvert ou pas."""
	if access_mode == "open":
		return "🔓 Ouvert"
	if access_mode == "closed":
		return "🔒 Fermé"
	if access_mode == "private":
		return "🔒 Privé"
	return "🔓 Ouvert"


def _status_emoji(access_mode: str) -> str:
	"""Emoji cadenas seul pour le nom du channel."""
	return "🔓" if access_mode == "open" else "🔒"


def _build_control_embed(owner: Member, voice_channel: discord.VoiceChannel, access_mode: str) -> discord.Embed:
	"""Construit l’embed de config avec infos du salon."""
	embed = discord.Embed(
		title="Configuration du salon",
		description=(
			"Voici l’espace de configuration de votre salon vocal. "
			"Utilisez les réactions ci-dessous — seul le propriétaire peut réagir."
		),
		color=discord.Color.blurple()
	)
	members_count = len(voice_channel.members)
	user_limit = voice_channel.user_limit or 0
	limit_text = f"{user_limit} max" if user_limit else "Illimitée"
	members_text = f"{members_count} / {user_limit}" if user_limit else str(members_count)
	bitrate_kbps = (voice_channel.bitrate or 0) // 1000

	embed.add_field(name="Propriétaire", value=owner.mention, inline=True)
	embed.add_field(name="Statut du salon", value=_status_display(access_mode), inline=True)
	embed.add_field(name="Nom du salon", value=voice_channel.name, inline=True)
	embed.add_field(name="Membres", value=members_text, inline=True)
	embed.add_field(name="Limite", value=limit_text, inline=True)
	embed.add_field(name="Bitrate", value=f"{bitrate_kbps} kbps", inline=True)
	embed.add_field(name="Accès", value="🔓 Ouvert · 🔒 Fermé · 🛡️ Privé", inline=False)
	embed.add_field(name="Listes", value="✅ Liste blanche · 🚫 Liste noire", inline=False)
	embed.add_field(name="Actions", value="🧹 Purge · 👑 Propriété · 🎤 Micro · 📹 Vidéo · 📝 Statut", inline=False)
	return embed


def _room_key(guild_id: int, owner_id: int) -> tuple[int, int]:
	return (guild_id, owner_id)


def _get_room(guild_id: int, owner_id: int) -> Optional[dict]:
	return _rooms.get(_room_key(guild_id, owner_id))


def _set_room(guild_id: int, owner_id: int, data: dict):
	_rooms[_room_key(guild_id, owner_id)] = data
	mid = data.get("control_message_id")
	if mid:
		_control_message_ids[mid] = (guild_id, owner_id)


def _del_room(guild_id: int, owner_id: int):
	data = _rooms.pop(_room_key(guild_id, owner_id), None)
	if data and data.get("control_message_id"):
		_control_message_ids.pop(data["control_message_id"], None)


def _find_room_by_channel(guild_id: int, channel_id: int) -> Optional[tuple[int, dict]]:
	for (gid, oid), data in _rooms.items():
		if gid == guild_id and data.get("voice_channel_id") == channel_id:
			return (oid, data)
	return None


def _find_room_by_message(message_id: int) -> Optional[tuple[int, int, dict]]:
	key = _control_message_ids.get(message_id)
	if not key:
		return None
	guild_id, owner_id = key
	data = _get_room(guild_id, owner_id)
	if not data:
		_control_message_ids.pop(message_id, None)
		return None
	return (guild_id, owner_id, data)


async def _apply_access_mode(channel: discord.VoiceChannel, mode: str, whitelist: set, blacklist: set):
	guild = channel.guild
	everyone = guild.default_role
	overwrites = {}
	everyone_ow = discord.PermissionOverwrite()
	if mode == "open":
		everyone_ow.connect = True
		everyone_ow.view_channel = True
		for uid in blacklist:
			m = guild.get_member(uid)
			if m:
				overwrites[m] = discord.PermissionOverwrite(connect=False, view_channel=True)
	elif mode == "closed":
		everyone_ow.connect = False
		everyone_ow.view_channel = True
		for uid in whitelist:
			m = guild.get_member(uid)
			if m:
				overwrites[m] = discord.PermissionOverwrite(connect=True, view_channel=True)
	elif mode == "private":
		everyone_ow.connect = False
		everyone_ow.view_channel = False
		for uid in whitelist:
			m = guild.get_member(uid)
			if m:
				overwrites[m] = discord.PermissionOverwrite(connect=True, view_channel=True)
	overwrites[everyone] = everyone_ow
	await channel.edit(overwrites=overwrites)


async def _handle_reaction_action(bot: discord.Client, guild_id: int, owner_id: int, action: str, channel):
	"""channel = salon vocal (partie texte / onglet Discussion)."""
	room = _get_room(guild_id, owner_id)
	if not room:
		await channel.send("Ce salon n’existe plus.")
		return
	voice_channel = bot.get_channel(room["voice_channel_id"])
	if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
		await channel.send("Salon vocal introuvable.")
		return

	if action in ("open", "closed", "private"):
		room["access_mode"] = action
		await _apply_access_mode(voice_channel, action, room.get("whitelist", set()), room.get("blacklist", set()))
		# Mettre à jour le cadenas dans le nom du channel
		try:
			base_name = voice_channel.name.rstrip(" 🔓🔒")
			new_name = f"{base_name} {_status_emoji(action)}"
			await voice_channel.edit(name=new_name)
		except discord.HTTPException:
			pass
		await channel.send(f"Accès du salon défini sur **{action}**.")
		# Mettre à jour uniquement le statut (cadenas) dans le message de config
		control_message_id = room.get("control_message_id")
		if control_message_id:
			try:
				msg = await channel.fetch_message(control_message_id)
				if msg.embeds:
					embed = msg.embeds[0].copy()
					for i, f in enumerate(embed.fields):
						if f.name == "Statut du salon":
							embed.set_field_at(i, name="Statut du salon", value=_status_display(action), inline=f.inline)
							break
					else:
						embed.add_field(name="Statut du salon", value=_status_display(action), inline=False)
					await msg.edit(embed=embed)
			except discord.HTTPException:
				pass

	elif action == "whitelist":
		await channel.send("Liste blanche : mentionnez un membre pour l’ajouter/retirer.")

	elif action == "blacklist":
		await channel.send("Liste noire : mentionnez un membre pour l’ajouter/retirer.")

	elif action == "purge":
		whitelist = room.get("whitelist", set())
		kicked = 0
		for member in list(voice_channel.members):
			if member.id == owner_id or member.id in whitelist:
				continue
			try:
				await member.move_to(None)
				kicked += 1
			except discord.HTTPException:
				pass
		await channel.send(f"Purge effectuée : {kicked} membre(s) déconnecté(s).")

	elif action == "transfer":
		await channel.send("Transférer le salon : mentionnez le membre à qui donner la propriété.")

	elif action in ("speak", "stream"):
		everyone = voice_channel.guild.default_role
		overwrites = dict(voice_channel.overwrites)
		ow = overwrites.get(everyone) or discord.PermissionOverwrite()
		current = getattr(ow, action)
		setattr(ow, action, not current if current is not None else False)
		overwrites[everyone] = ow
		await voice_channel.edit(overwrites=overwrites)
		label = "Micro" if action == "speak" else "Vidéo"
		await channel.send(f"{label} : {'autorisé' if getattr(ow, action) else 'désactivé'} pour tous.")

	elif action == "status":
		status_text = _status_display(room.get("access_mode", "open"))
		await channel.send(f"Statut du salon : {status_text}\nRépondez avec le nouveau nom du salon pour le modifier.")


async def send_control_panel(bot: discord.Client, guild_id: int, owner: Member, voice_channel: discord.VoiceChannel) -> Optional[int]:
	"""Envoie le message de config avec réactions dans la partie texte du salon vocal (onglet Discussion). Seul le proprio peut réagir. Retourne l’id du message."""
	embed = _build_control_embed(owner, voice_channel, "open")

	try:
		# Message dans la partie texte du vocal (onglet Discussion à droite)
		msg = await voice_channel.send(embed=embed)
		for emoji, _action, _label in REACTIONS:
			await msg.add_reaction(emoji)
		return msg.id
	except discord.HTTPException as e:
		logging.error(f"Impossible d’envoyer le panneau Auto Room dans le vocal : {e}")
		return None


async def on_voice_state_update_auto_rooms(bot: discord.Client, member: Member, before: VoiceState, after: VoiceState):
	config = ConfigurationHelper()
	if not config.getValue("auto_rooms_enable"):
		return
	trigger_channel_id = config.getIntValue("auto_rooms_channel_id")
	if not trigger_channel_id:
		return

	guild = member.guild

	if after.channel and after.channel.id == trigger_channel_id:
		category = after.channel.category
		# Nom du salon avec statut (cadenas) à la création
		channel_name = f"Salon de {member.display_name} {_status_emoji('open')}"
		try:
			new_channel = await guild.create_voice_channel(
				name=channel_name,
				category=category,
				reason="Auto room"
			)
			await member.move_to(new_channel)
			control_message_id = await send_control_panel(bot, guild.id, member, new_channel)
			_set_room(guild.id, member.id, {
				"guild_id": guild.id,
				"voice_channel_id": new_channel.id,
				"control_message_id": control_message_id,
				"owner_id": member.id,
				"whitelist": set(),
				"blacklist": set(),
				"access_mode": "open",
			})
			logging.info(f"Auto room créé : {new_channel.name} pour {member.display_name}")
		except discord.HTTPException as e:
			logging.error(f"Erreur création auto room : {e}")

	if before.channel and before.channel.id != trigger_channel_id:
		result = _find_room_by_channel(guild.id, before.channel.id)
		if result:
			owner_id, room = result
			remaining = [m for m in before.channel.members if m.id != member.id]
			if member.id == owner_id:
				_del_room(guild.id, owner_id)
				try:
					await before.channel.delete(reason="Propriétaire parti (auto room)")
				except discord.HTTPException:
					pass
			elif len(remaining) == 0:
				_del_room(guild.id, owner_id)
				try:
					await before.channel.delete(reason="Auto room vide")
				except discord.HTTPException:
					pass


async def on_raw_reaction_add_auto_rooms(bot: discord.Client, payload: discord.RawReactionActionEvent):
	"""Seul le propriétaire peut réagir ; on retire la réaction des autres."""
	if payload.user_id == bot.user.id:
		return
	if not ConfigurationHelper().getValue("auto_rooms_enable"):
		return
	room_info = _find_room_by_message(payload.message_id)
	if not room_info:
		return
	guild_id, owner_id, room = room_info
	if payload.user_id != owner_id:
		try:
			channel = bot.get_channel(payload.channel_id)
			if channel:
				msg = await channel.fetch_message(payload.message_id)
				user = payload.member or await bot.fetch_user(payload.user_id)
				await msg.remove_reaction(payload.emoji, user)
		except discord.HTTPException:
			pass
		return

	emoji_str = str(payload.emoji)
	action = None
	for e, a, _ in REACTIONS:
		if e == emoji_str:
			action = a
			break
	if not action:
		return

	# Canal = salon vocal (le message est dans la partie texte du vocal)
	channel = bot.get_channel(payload.channel_id)
	if not channel or not hasattr(channel, "send"):
		return

	await _handle_reaction_action(bot, guild_id, owner_id, action, channel)

	try:
		msg = await channel.fetch_message(payload.message_id)
		user = payload.member or await bot.fetch_user(payload.user_id)
		await msg.remove_reaction(payload.emoji, user)
	except discord.HTTPException:
		pass
