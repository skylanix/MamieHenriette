import logging
import json
import os

from flask_sqlalchemy import SQLAlchemy
from sqlite3 import Cursor, Connection
from webapp import webapp


basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
webapp.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "database.db")}'
db = SQLAlchemy(webapp)

def _tableHaveColumn(table_name:str, column_name:str, cursor:Cursor) -> bool: 
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
