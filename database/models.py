from database import db

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
	message = db.Column(db.String(2000))

class Message(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	enable = db.Column(db.Boolean, default=False)
	text = db.Column(db.String(256))
	periodicity = db.Column(db.Integer)

class Commande(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	discord_enable = db.Column(db.Boolean, default=True)
	twitch_enable = db.Column(db.Boolean, default=True)
	trigger = db.Column(db.String(32), unique=True)
	response = db.Column(db.String(2000))

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

class AntiCheatCache(db.Model):
	__tablename__ = 'anticheat_cache'
	steam_id = db.Column(db.String(32), primary_key=True)
	game_name = db.Column(db.String(256))
	status = db.Column(db.String(32))
	anticheats = db.Column(db.String(512))
	reference = db.Column(db.String(512))
	notes = db.Column(db.String(1024))
	updated_at = db.Column(db.DateTime)

class FreeGame(db.Model):
	__tablename__ = 'free_game'
	id = db.Column(db.Integer, primary_key=True)
	entry_id = db.Column(db.String(512), unique=True)
	title = db.Column(db.String(512))
	source = db.Column(db.String(64))
	url = db.Column(db.String(2048))
	image_url = db.Column(db.String(2048))
	description = db.Column(db.Text)
	valid_from = db.Column(db.DateTime)
	valid_to = db.Column(db.DateTime)
	notified = db.Column(db.Boolean, default=False)
	notified_at = db.Column(db.DateTime)
	created_at = db.Column(db.DateTime)

class DiscordInvite(db.Model):
	__tablename__ = 'discord_invite'
	code = db.Column(db.String(32), primary_key=True)
	guild_id = db.Column(db.String(64), nullable=False)
	channel_id = db.Column(db.String(64), nullable=False)
	channel_name = db.Column(db.String(256))
	inviter_id = db.Column(db.String(64))
	inviter_name = db.Column(db.String(256))
	uses = db.Column(db.Integer, default=0)
	max_uses = db.Column(db.Integer, default=0)
	max_age = db.Column(db.Integer, default=0)
	temporary = db.Column(db.Boolean, default=False)
	created_at = db.Column(db.DateTime)
	expires_at = db.Column(db.DateTime)
	revoked = db.Column(db.Boolean, default=False)
	last_sync = db.Column(db.DateTime)

class YoutubeAlert(db.Model):
	__tablename__ = 'youtube_alert'
	id = db.Column(db.Integer, primary_key=True)
	enable = db.Column(db.Boolean, default=True)
	channel_id = db.Column(db.String(64), unique=True)
	channel_name = db.Column(db.String(256))
	notify_channel = db.Column(db.Integer)
	message = db.Column(db.String(2000))
	last_video_id = db.Column(db.String(64))

