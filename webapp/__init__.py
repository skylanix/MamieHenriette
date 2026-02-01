from flask import Flask

webapp = Flask(__name__)

# État des bots (mis à jour par les bots, lu par le panneau)
webapp.config["BOT_STATUS"] = {
	"discord_connected": False,
	"discord_guild_count": 0,
	"twitch_connected": False,
	"twitch_channel_name": None,
}

from webapp import commandes, configurations, index, humeurs, protondb, live_alert, twitch_auth, moderation, youtube
