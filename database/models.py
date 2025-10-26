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

