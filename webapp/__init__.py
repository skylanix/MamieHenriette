from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# import os

# file_path = os.path.abspath(os.getcwd())+"/todo.db"

webapp = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+file_path
# db = SQLAlchemy(app)

from webapp import routes