from flask import render_template
from webapp import webapp
from database.models import ModerationEvent

@webapp.route("/")
def index():
	status = webapp.config["BOT_STATUS"]
	sanctions_count = ModerationEvent.query.count()
	return render_template(
		"index.html",
		discord_connected=status["discord_connected"],
		discord_guild_count=status["discord_guild_count"],
		sanctions_count=sanctions_count,
		twitch_connected=status["twitch_connected"],
		twitch_channel_name=status["twitch_channel_name"],
	)
