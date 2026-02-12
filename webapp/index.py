from flask import render_template
from webapp import webapp
from webapp.auth import require_page
from database.models import ModerationEvent, TwitchAnnouncement, TwitchModerationLog

@webapp.route("/")
@require_page("index")
def index():
	status = webapp.config["BOT_STATUS"]
	sanctions_count = ModerationEvent.query.count()
	twitch_announcements_count = TwitchAnnouncement.query.count()
	twitch_moderation_count = TwitchModerationLog.query.count()
	return render_template(
		"index.html",
		discord_connected=status["discord_connected"],
		discord_guild_count=status["discord_guild_count"],
		sanctions_count=sanctions_count,
		twitch_connected=status["twitch_connected"],
		twitch_channel_name=status["twitch_channel_name"],
		twitch_announcements_count=twitch_announcements_count,
		twitch_moderation_count=twitch_moderation_count,
	)
