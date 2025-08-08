from webapp import db

class Message(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	enable = db.Column(db.Boolean, default=False)
	text = db.Column(db.String(200))
	# en seconde
	periodicity = db.Column(db.Integer)
