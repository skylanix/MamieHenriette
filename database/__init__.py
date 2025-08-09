from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
from webapp import webapp

webapp.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(webapp)

with webapp.app_context():
    with open('database/schema.sql', 'r') as f:
        sql_script = f.read()
    db.session.execute(text(sql_script))
    db.session.commit()
