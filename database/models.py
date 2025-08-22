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
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(256))
	json = db.Column(db.String(1024))

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

