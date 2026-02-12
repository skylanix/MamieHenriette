import os
from flask import Flask
from flask_login import LoginManager

webapp = Flask(__name__)

# Secret key pour les sessions (Flask-Login)
webapp.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# État des bots (mis à jour par les bots, lu par le panneau)
webapp.config["BOT_STATUS"] = {
	"discord_connected": False,
	"discord_guild_count": 0,
	"twitch_connected": False,
	"twitch_channel_name": None,
	"twitch_is_live": False,
	"twitch_viewer_count": 0,
	"twitch_chat_messages": [],  # Derniers messages du chat (max 100)
}

login_manager = LoginManager()
login_manager.init_app(webapp)
login_manager.login_view = "login"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."

from database.models import WebappUser

@login_manager.user_loader
def load_user(user_id):
	try:
		return WebappUser.query.get(int(user_id))
	except (ValueError, TypeError):
		return None

from webapp import auth, commandes, configurations, index, humeurs, protondb, live_alert, twitch_auth, moderation, youtube, announcements, twitch_moderation, link_filter, twitch_events, users, settings, freeloot

from flask import request, redirect, url_for
from flask_login import current_user

@webapp.context_processor
def inject_user_level():
	from flask_login import current_user
	from database.helpers import ConfigurationHelper
	reg = ConfigurationHelper().getValue("registration_enabled")
	registration_enabled = reg not in (None, "", "false", "0", "no", "off")
	return {
		"current_user_level": current_user.get_level() if current_user.is_authenticated else -1,
		"registration_enabled": registration_enabled,
	}

@webapp.before_request
def require_login():
	"""Redirige vers /login si non authentifié (sauf login, register, static, callback Twitch OAuth)."""
	if request.endpoint in (None, "login", "register", "static", "twitchReceiveToken"):
		return
	if not current_user.is_authenticated:
		return redirect(url_for("login", next=request.url))
