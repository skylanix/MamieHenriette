from datetime import datetime
from database import db
from flask_login import UserMixin

# Rôles par défaut (niveau 0 à 5) — seed en base via migration
ROLE_ORDER = [
	"viewer_twitch",
	"utilisateur_discord",
	"moderateur_discord",
	"expert_discord",
	"moderateur_twitch",
	"super_administrateur",
]

def role_level(role_name: str) -> int:
	"""Retourne le niveau du rôle depuis la table webapp_role (-1 si inconnu)."""
	if not role_name:
		return -1
	r = WebappRole.query.filter_by(name=role_name).first()
	return r.level if r else -1

class WebappRole(db.Model):
	__tablename__ = "webapp_role"
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), unique=True, nullable=False)
	level = db.Column(db.Integer, nullable=False, default=0)
	description = db.Column(db.String(256), nullable=True)
	color = db.Column(db.String(7), nullable=True, default="#6B7280")  # Couleur hexadécimale pour l'affichage
	icon = db.Column(db.String(32), nullable=True)  # Nom d'icône (ex: 'user', 'shield', 'crown')

class PagePermission(db.Model):
	__tablename__ = "webapp_page_permission"
	id = db.Column(db.Integer, primary_key=True)
	page_key = db.Column(db.String(64), unique=True, nullable=False)
	min_level = db.Column(db.Integer, nullable=False, default=0)
	write_level = db.Column(db.Integer, nullable=True)
	category = db.Column(db.String(32), nullable=True, default="general")  # Catégorie: 'general', 'moderation', 'content', 'config'
	description = db.Column(db.String(256), nullable=True)  # Description de la page

class WebappUser(db.Model, UserMixin):
	__tablename__ = "webapp_user"
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(64), unique=True, nullable=False)
	email = db.Column(db.String(256), unique=True, nullable=False)
	password_hash = db.Column(db.String(256), nullable=False)
	role = db.Column(db.String(64), nullable=False, default="viewer_twitch")
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

	def get_level(self) -> int:
		return role_level(self.role)

	def has_role_at_least(self, min_role: str) -> bool:
		return self.get_level() >= role_level(min_role)

	def has_level_at_least(self, level: int) -> bool:
		return self.get_level() >= level

	def has_any_role(self, roles: list) -> bool:
		return self.role in roles

class Configuration(db.Model): 
	key = db.Column(db.String(32), primary_key=True)
	value = db.Column(db.String(512))

class Humeur(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	enable = db.Column(db.Boolean, default=True)
	text = db.Column(db.String(256))

class GameAlias(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	alias = db.Column(db.String(32))
	name = db.Column(db.String(256))

class GameBundle(db.Model):
	url = db.Column(db.String(2048), primary_key=True)
	name = db.Column(db.String(256))
	json = db.Column(db.String(2048))

class LiveAlert(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	enable = db.Column(db.Boolean, default=True)
	online = db.Column(db.Boolean, default=False)
	login = db.Column(db.String(128))
	notify_channel = db.Column(db.Integer)
	message = db.Column(db.String(2000))  # message optionnel avant l'embed
	watch_activity = db.Column(db.Boolean, default=False)
	# Personnalisation de l'embed Discord (comme YouTube)
	embed_title = db.Column(db.String(256))
	embed_description = db.Column(db.String(2000))
	embed_color = db.Column(db.String(8), default='9146FF')  # violet Twitch
	embed_footer = db.Column(db.String(2048))
	embed_author_name = db.Column(db.String(256))
	embed_author_icon = db.Column(db.String(512))
	embed_thumbnail = db.Column(db.Boolean, default=True)
	embed_image = db.Column(db.Boolean, default=True)

class TwitchAnnouncement(db.Model):
	__tablename__ = 'twitch_announcement'
	id = db.Column(db.Integer, primary_key=True)
	enable = db.Column(db.Boolean, default=True)
	name = db.Column(db.String(64))
	text = db.Column(db.String(500))
	periodicity = db.Column(db.Integer, default=10)
	min_chat_messages = db.Column(db.Integer, default=0)
	last_sent = db.Column(db.DateTime, nullable=True)

# Niveaux de permission Twitch pour les commandes personnalisées : viewer, sub, vip, moderator
class Commande(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	discord_enable = db.Column(db.Boolean, default=True)
	twitch_enable = db.Column(db.Boolean, default=True)
	trigger = db.Column(db.String(32), unique=True)
	response = db.Column(db.String(2000))
	twitch_permission = db.Column(db.String(16), default='viewer')  # viewer | sub | vip | moderator

class ModerationEvent(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	type = db.Column(db.String(32))
	username = db.Column(db.String(256))
	discord_id = db.Column(db.String(64))
	created_at = db.Column(db.DateTime)
	reason = db.Column(db.String(1024))
	staff_id = db.Column(db.String(64))
	staff_name = db.Column(db.String(256))
	duration = db.Column(db.Integer)


class TwitchModerationLog(db.Model):
	__tablename__ = 'twitch_moderation_log'
	id = db.Column(db.Integer, primary_key=True)
	action = db.Column(db.String(32))
	moderator = db.Column(db.String(256))
	target = db.Column(db.String(256))
	details = db.Column(db.String(512))
	created_at = db.Column(db.DateTime)


class TwitchLinkFilter(db.Model):
	__tablename__ = 'twitch_link_filter'
	id = db.Column(db.Integer, primary_key=True)
	enabled = db.Column(db.Boolean, default=False)
	allow_subscribers = db.Column(db.Boolean, default=True)
	allow_vips = db.Column(db.Boolean, default=True)
	allow_moderators = db.Column(db.Boolean, default=True)
	timeout_duration = db.Column(db.Integer, default=60)
	warning_message = db.Column(db.String(500), default="Les liens ne sont pas autorises dans le chat.")


class TwitchAllowedDomain(db.Model):
	__tablename__ = 'twitch_allowed_domain'
	id = db.Column(db.Integer, primary_key=True)
	domain = db.Column(db.String(256), unique=True)


class TwitchPermit(db.Model):
	__tablename__ = 'twitch_permit'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(256))
	expires_at = db.Column(db.DateTime)


class TwitchAllowedUser(db.Model):
	__tablename__ = 'twitch_allowed_user'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(256), unique=True)

class AntiCheatCache(db.Model):
	__tablename__ = 'anticheat_cache'
	steam_id = db.Column(db.String(32), primary_key=True)
	game_name = db.Column(db.String(256))
	status = db.Column(db.String(32))
	anticheats = db.Column(db.String(512))
	reference = db.Column(db.String(512))
	notes = db.Column(db.String(1024))
	updated_at = db.Column(db.DateTime)


class YouTubeNotification(db.Model):
	__tablename__ = 'youtube_notification'
	id = db.Column(db.Integer, primary_key=True)
	enable = db.Column(db.Boolean, default=True)
	channel_id = db.Column(db.String(128))
	notify_channel = db.Column(db.Integer)
	message = db.Column(db.String(2000))
	video_type = db.Column(db.String(16), default='all')
	last_video_id = db.Column(db.String(128))
	embed_title = db.Column(db.String(256))
	embed_description = db.Column(db.String(2000))
	embed_color = db.Column(db.String(8), default='FF0000')
	embed_footer = db.Column(db.String(2048))
	embed_author_name = db.Column(db.String(256))
	embed_author_icon = db.Column(db.String(512))
	embed_thumbnail = db.Column(db.Boolean, default=True)
	embed_image = db.Column(db.Boolean, default=True)


class FreeLootEntry(db.Model):
	__tablename__ = 'freeloot_entry'
	entry_id = db.Column(db.String(256), primary_key=True)


class TwitchEventNotification(db.Model):
	"""Configuration des notifications par type d'événement (sub, follow, raid, clip)."""
	__tablename__ = 'twitch_event_notification'
	id = db.Column(db.Integer, primary_key=True)
	event_type = db.Column(db.String(32), unique=True, nullable=False)  # sub, follow, raid, clip
	enable = db.Column(db.Boolean, default=True)
	notify_twitch_chat = db.Column(db.Boolean, default=True)
	notify_discord = db.Column(db.Boolean, default=False)
	discord_channel_id = db.Column(db.Integer, nullable=True)
	message_twitch = db.Column(db.String(500), default='')
	message_discord = db.Column(db.String(2000), nullable=True)
	embed_color = db.Column(db.String(8), default='9146FF')
	embed_title = db.Column(db.String(256), nullable=True)
	embed_description = db.Column(db.String(2000), nullable=True)
	embed_thumbnail = db.Column(db.Boolean, default=True)
	last_clip_id = db.Column(db.String(128), nullable=True)  # pour détecter les nouveaux clips


class TwitchBannedWord(db.Model):
	"""Mots interdits dans le chat Twitch."""
	__tablename__ = 'twitch_banned_word'
	id = db.Column(db.Integer, primary_key=True)
	word = db.Column(db.String(256), unique=True, nullable=False)
	enabled = db.Column(db.Boolean, default=True)
	timeout_duration = db.Column(db.Integer, default=60)  # durée du timeout en secondes
	created_at = db.Column(db.DateTime, default=datetime.utcnow)

