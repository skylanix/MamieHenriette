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
	if _tableEmpty('game_bundle', cursor) and _tableExists('game_bundle_old', cursor):
		logging.info("remplir game_bundle avec game_bundle_old")
		bundles = cursor.execute('SELECT * FROM game_bundle_old').fetchall()
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

	if _tableExists('commande', cursor) and not _tableHaveColumn('commande', 'twitch_permission', cursor):
		try:
			cursor.execute("ALTER TABLE commande ADD COLUMN twitch_permission VARCHAR(16) DEFAULT 'viewer'")
			logging.info("Colonne twitch_permission ajoutée à commande")
		except Exception as e:
			logging.warning(f"Colonne commande.twitch_permission: {e}")


def _doAddColumnMigrations(cursor: Cursor):
	"""Migrations d'ajout de colonnes. Exécutées à part pour ne pas dépendre du script principal."""
	if _tableExists('commande', cursor) and not _tableHaveColumn('commande', 'twitch_permission', cursor):
		try:
			cursor.execute("ALTER TABLE commande ADD COLUMN twitch_permission VARCHAR(16) DEFAULT 'viewer'")
			logging.info("Colonne twitch_permission ajoutée à commande")
		except Exception as e:
			logging.warning(f"Colonne commande.twitch_permission: {e}")
	if _tableExists('live_alert', cursor) and not _tableHaveColumn('live_alert', 'watch_activity', cursor):
		try:
			cursor.execute("ALTER TABLE live_alert ADD COLUMN watch_activity BOOLEAN NOT NULL DEFAULT 0")
			logging.info("Colonne watch_activity ajoutée à live_alert")
		except Exception as e:
			logging.warning(f"Colonne live_alert.watch_activity: {e}")

	# Colonnes embed pour live_alert (message par défaut en embed)
	if _tableExists('live_alert', cursor):
		live_alert_embed_columns = [
			('embed_title', 'VARCHAR(256)'),
			('embed_description', 'VARCHAR(2000)'),
			('embed_color', 'VARCHAR(8) DEFAULT "9146FF"'),
			('embed_footer', 'VARCHAR(2048)'),
			('embed_author_name', 'VARCHAR(256)'),
			('embed_author_icon', 'VARCHAR(512)'),
			('embed_thumbnail', 'BOOLEAN DEFAULT 1'),
			('embed_image', 'BOOLEAN DEFAULT 1'),
		]
		for col_name, col_type in live_alert_embed_columns:
			if not _tableHaveColumn('live_alert', col_name, cursor):
				try:
					cursor.execute(f'ALTER TABLE live_alert ADD COLUMN {col_name} {col_type}')
					logging.info(f"Colonne {col_name} ajoutée à live_alert")
				except Exception as e:
					logging.warning(f"Colonne live_alert.{col_name}: {e}")

	# Table twitch_event_notification + seed des 4 types
	if not _tableExists('twitch_event_notification', cursor):
		try:
			cursor.execute("""
				CREATE TABLE twitch_event_notification (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					event_type VARCHAR(32) UNIQUE NOT NULL,
					enable BOOLEAN NOT NULL DEFAULT 1,
					notify_twitch_chat BOOLEAN NOT NULL DEFAULT 1,
					notify_discord BOOLEAN NOT NULL DEFAULT 0,
					discord_channel_id INTEGER NULL,
					message_twitch VARCHAR(500) NOT NULL DEFAULT '',
					message_discord VARCHAR(2000) NULL,
					embed_color VARCHAR(8) DEFAULT '9146FF',
					embed_title VARCHAR(256) NULL,
					embed_description VARCHAR(2000) NULL,
					embed_thumbnail BOOLEAN NOT NULL DEFAULT 1,
					last_clip_id VARCHAR(128) NULL
				)
			""")
			logging.info("Table twitch_event_notification créée")
		except Exception as e:
			logging.warning(f"Table twitch_event_notification: {e}")
	if _tableExists('twitch_event_notification', cursor) and _tableEmpty('twitch_event_notification', cursor):
		for ev in ('sub', 'follow', 'raid', 'clip'):
			try:
				cursor.execute(
					"INSERT INTO twitch_event_notification (event_type, message_twitch) VALUES (?, ?)",
					(ev, 'Merci {user} !' if ev != 'raid' else 'Bienvenue aux viewers de {from_broadcaster_name} !'),
				)
			except Exception as e:
				logging.warning(f"Seed twitch_event_notification {ev}: {e}")

	# Table webapp_user (auth)
	if not _tableExists('webapp_user', cursor):
		try:
			cursor.execute("""
				CREATE TABLE webapp_user (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					username VARCHAR(64) UNIQUE NOT NULL,
					email VARCHAR(256) UNIQUE NOT NULL,
					password_hash VARCHAR(256) NOT NULL,
					role VARCHAR(64) NOT NULL DEFAULT 'viewer_twitch',
					created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
				)
			""")
			logging.info("Table webapp_user créée")
		except Exception as e:
			logging.warning(f"Table webapp_user: {e}")

	# Tables webapp_role et webapp_page_permission
	if not _tableExists('webapp_role', cursor):
		try:
			cursor.execute("""
				CREATE TABLE webapp_role (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name VARCHAR(64) UNIQUE NOT NULL,
					level INTEGER NOT NULL DEFAULT 0
				)
			""")
			logging.info("Table webapp_role créée")
		except Exception as e:
			logging.warning(f"Table webapp_role: {e}")
	if not _tableExists('webapp_page_permission', cursor):
		try:
			cursor.execute("""
				CREATE TABLE webapp_page_permission (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					page_key VARCHAR(64) UNIQUE NOT NULL,
					min_level INTEGER NOT NULL DEFAULT 0,
					write_level INTEGER NULL
				)
			""")
			logging.info("Table webapp_page_permission créée")
		except Exception as e:
			logging.warning(f"Table webapp_page_permission: {e}")


def _doSeedAuth(cursor: Cursor):
	"""Seed rôles par défaut et permissions des pages si vides."""
	from database.models import ROLE_ORDER
	if not _tableExists('webapp_role', cursor):
		return
	if cursor.execute("SELECT COUNT(*) FROM webapp_role").fetchone()[0] > 0:
		return
	default_roles = [
		("viewer_twitch", 0),
		("utilisateur_discord", 1),
		("moderateur_discord", 2),
		("expert_discord", 3),
		("moderateur_twitch", 4),
		("super_administrateur", 5),
	]
	for name, level in default_roles:
		try:
			cursor.execute("INSERT INTO webapp_role (name, level) VALUES (?, ?)", (name, level))
		except Exception as e:
			logging.warning(f"Seed role {name}: {e}")
	logging.info("Rôles par défaut insérés")

	if not _tableExists('webapp_page_permission', cursor):
		return
	if cursor.execute("SELECT COUNT(*) FROM webapp_page_permission").fetchone()[0] > 0:
		return
	# page_key, min_level, write_level (NULL = même que min_level)
	default_pages = [
		("index", 0, None),
		("configurations", 5, 5),
		("commandes", 1, 2),
		("humeurs", 1, 2),
		("live_alert", 0, 4),
		("announcements", 0, 4),
		("twitch_moderation", 0, 4),
		("link_filter", 0, 4),
		("twitch_events", 0, 4),
		("youtube", 1, 2),
		("protondb", 1, 2),
		("freeloot", 1, 2),
		("moderation", 1, 2),
		("users", 5, 5),
		("settings", 5, 5),
	]
	for page_key, min_level, wl in default_pages:
		try:
			cursor.execute(
				"INSERT INTO webapp_page_permission (page_key, min_level, write_level) VALUES (?, ?, ?)",
				(page_key, min_level, wl),
			)
		except Exception as e:
			logging.warning(f"Seed page {page_key}: {e}")
	logging.info("Permissions pages par défaut insérées")

	# Inscriptions activées par défaut
	if _tableExists("configuration", cursor):
		try:
			cursor.execute(
				"INSERT OR IGNORE INTO configuration (key, value) VALUES ('registration_enabled', 'true')"
			)
		except Exception as e:
			logging.warning(f"Config registration_enabled: {e}")


with webapp.app_context():
	with open('database/schema.sql', 'r') as f:
		sql = f.read()
	connection: Connection = db.session.connection().connection
	try:
		cursor = connection.cursor()
		_doPreImportMigration(cursor)
		cursor.executescript(sql)
		_doPostImportMigration(cursor)
		connection.commit()
	except Exception as e:
		logging.error(f"lors de l'import de la bdd : {e}")
	finally:
		try:
			cursor = connection.cursor()
			_doAddColumnMigrations(cursor)
			_doSeedAuth(cursor)
			connection.commit()
		except Exception as e:
			logging.warning(f"migrations colonnes : {e}")
		connection.close()
