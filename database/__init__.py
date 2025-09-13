from flask_sqlalchemy import SQLAlchemy
from webapp import webapp
import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
webapp.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "database.db")}'
db = SQLAlchemy(webapp)

def migrate_game_bundle_if_needed():
	"""Migre la table game_bundle si elle a l'ancienne structure (id comme clé primaire)"""
	try:
		connection = db.session.connection().connection
		cursor = connection.cursor()
		
		cursor.execute("PRAGMA table_info(game_bundle)")
		columns = cursor.fetchall()
		
		if columns:
			has_id_primary = any(col[1] == 'id' and col[5] == 1 for col in columns)
			
			if has_id_primary:
				print("Migration de game_bundle: ancienne structure détectée")
				cursor.execute("DROP TABLE game_bundle")
				connection.commit()
				print("Ancienne table game_bundle supprimée")
		
		cursor.close()
	except Exception as e:
		print(f"Erreur lors de la vérification de migration: {e}")

with webapp.app_context():
	migrate_game_bundle_if_needed()
	
	with open('database/schema.sql', 'r') as f:
		sql = f.read()
		connection = db.session.connection().connection
		try:
			cursor = connection.cursor()
			cursor.executescript(sql)
			cursor.close()
		finally:
			connection.close()
