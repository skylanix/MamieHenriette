from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
from webapp import webapp

webapp.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(webapp)

with webapp.app_context():
	with open('database/schema.sql', 'r') as f:
		sql = f.read()
		connection = db.session.connection().connection
		try:
			cursor = connection.cursor()
			cursor.executescript(sql)
			cursor.close()
		finally:
			connection.close()
