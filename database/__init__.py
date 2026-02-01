import logging
import json
import os
from sqlalchemy import event
from sqlalchemy.engine import Engine

from flask_sqlalchemy import SQLAlchemy
from sqlite3 import Cursor, Connection
from webapp import webapp


basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
webapp.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "database.db")}'
# Options moteur pour améliorer la concurrence SQLite
webapp.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
	'connect_args': {
		'check_same_thread': False,
		'timeout': 30
	},
}
webapp.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(webapp)

# PRAGMA pour SQLite (WAL, busy timeout)
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
	try:
		cursor = dbapi_connection.cursor()
		cursor.execute("PRAGMA journal_mode=WAL;")
		cursor.execute("PRAGMA synchronous=NORMAL;")
		cursor.execute("PRAGMA busy_timeout=30000;")
		cursor.close()
	except Exception:
		pass

def _tableExists(table_name: str, cursor: Cursor) -> bool:
	cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
	return cursor.fetchone() is not None

def _tableHaveColumn(table_name:str, column_name:str, cursor:Cursor) -> bool:
	if not _tableExists(table_name, cursor):
		return False
	cursor.execute(f'PRAGMA table_info({table_name})')
	columns = cursor.fetchall()
	return any(col[1] == column_name for col in columns)

def _tableEmpty(table:str, cursor:Cursor) -> bool:
	return cursor.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0

def _renameTable(old_name:str, new_name:str, cursor:Cursor) : 
	cursor.execute(f'ALTER TABLE {old_name} RENAME TO {new_name}')

def _dropTable(table_name:str, cursor:Cursor) : 
	cursor.execute(f'DROP TABLE {table_name}')

def _doPreImportMigration(cursor:Cursor):
	if _tableHaveColumn('game_bundle', 'id', cursor) :
		logging.info("Table game_bundle détécté, rennomage en game_bundle_old")
		_renameTable('game_bundle', 'game_bundle_old', cursor)

def _doPostImportMigration(cursor:Cursor):
	if _tableEmpty('game_bundle', cursor) :
		logging.info("remplir game_bundle avec game_bundle_old")
		bundles = cursor.execute(f'SELECT * FROM game_bundle_old').fetchall()
		for bundle in bundles : 
			name = bundle[1]
			json_data = json.loads(bundle[2])
			url = json_data['url']
			logging.info(f'import du bundle {name}, {url}')
			cursor.execute('INSERT INTO game_bundle(url, name, json) VALUES (?, ?, ?)', (url, name, json.dumps(json_data)))
		logging.info("suppression de la table temporaire game_bundle_old")
		_dropTable('game_bundle_old', cursor)

	if _tableExists('youtube_notification', cursor):
		embed_columns = [
			('embed_title', 'VARCHAR(256)'),
			('embed_description', 'VARCHAR(2000)'),
			('embed_color', 'VARCHAR(8) DEFAULT "FF0000"'),
			('embed_footer', 'VARCHAR(2048)'),
			('embed_author_name', 'VARCHAR(256)'),
			('embed_author_icon', 'VARCHAR(512)'),
			('embed_thumbnail', 'BOOLEAN DEFAULT 1'),
			('embed_image', 'BOOLEAN DEFAULT 1'),
		]
		for col_name, col_type in embed_columns:
			if not _tableHaveColumn('youtube_notification', col_name, cursor):
				try:
					cursor.execute(f'ALTER TABLE youtube_notification ADD COLUMN {col_name} {col_type}')
					logging.info(f"Colonne {col_name} ajoutée à youtube_notification")
				except Exception as e:
					logging.warning(f"Colonne youtube_notification.{col_name}: {e}")

with webapp.app_context():
	with open('database/schema.sql', 'r') as f:
		sql = f.read()
		connection : Connection = db.session.connection().connection
		try:
			cursor : Cursor = connection.cursor()
			_doPreImportMigration(cursor)
			cursor.executescript(sql)
			_doPostImportMigration(cursor)
			connection.commit()
			cursor.close()
		except Exception as e:
			logging.error(f"lors de l'import de la bdd : {e}")
		finally:
			connection.close()
