import discord
from datetime import datetime
from database import db
from database.models import Warning
from discord import Message

STAFF_ROLE_ID = 581990740431732738

async def handle_warning_command(message: Message, bot):
	if not any(role.id == STAFF_ROLE_ID for role in message.author.roles):
		return
	
	parts = message.content.split(maxsplit=2)
	
	if len(parts) < 2 or not message.mentions:
		return
	
	target_user = message.mentions[0]
	reason = parts[2] if len(parts) > 2 else "Sans raison"
	
	warning = Warning(
		username=target_user.name,
		discord_id=str(target_user.id),
		created_at=datetime.utcnow(),
		reason=reason,
		staff_id=str(message.author.id),
		staff_name=message.author.name
	)
	db.session.add(warning)
	db.session.commit()
	
	embed = discord.Embed(
		title="⚠️ Avertissement",
		description=f"{target_user.mention} a reçu un avertissement de la part de l'équipe de modération",
		color=discord.Color.red(),
		timestamp=datetime.utcnow()
	)
	embed.add_field(name="👤 Utilisateur", value=f"{target_user.name}\n`{target_user.id}`", inline=True)
	#embed.add_field(name="🛡️ Modérateur", value=f"{message.author.name}\n`{message.author.id}`", inline=True)
	embed.add_field(name="📝 Raison", value=reason, inline=False)
	embed.set_footer(text="Mamie Henriette")
	
	await message.channel.send(embed=embed)
	await message.delete()
