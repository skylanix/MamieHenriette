from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

webapp = Flask(__name__)
webapp.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(webapp)

from webapp import routes

with webapp.app_context():
    with open('schema.sql', 'r') as f:
        sql_script = f.read()
    db.session.execute(text(sql_script))
    db.session.commit()
