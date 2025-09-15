import discord
from discord.ext import commands
from datetime import datetime, date, time
from database import db
from database.models import Averto

class CommandesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name='averto', description='Donner un avertissement à un utilisateur')
    @discord.app_commands.describe(
        user='L\'utilisateur à avertir',
        reason='La raison de l\'avertissement'
    )
    async def averto(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        required_role_ids = [ID ROLE DISCORD, ID ROLE DISCORD]
        
        if not any(role.id in required_role_ids for role in interaction.user.roles):
            await interaction.response.send_message("Vous n'avez pas les permissions nécessaires pour utiliser cette commande.", ephemeral=True)
            return

        now = datetime.now()
        current_date = now.date()
        current_time = now.time()

        averto = Averto(
            user_id=str(user.id),
            date=current_date,
            time=current_time,
            sanctioned_by=str(interaction.user.id),
            reason=reason
        )

        db.session.add(averto)
        db.session.commit()

        embed = discord.Embed(
            title="⚠️ Avertissement donné",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Utilisateur", value=user.mention, inline=True)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
        embed.add_field(name="Raison", value=reason, inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CommandesCog(bot))
