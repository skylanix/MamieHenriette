from flask import render_template
from webapp import webapp
# from database import db
# from database.message import Message

@webapp.route("/")
def index():
    # message = Message(text="bla bla", periodicity = 3600)
    # db.session.add(message)
    # db.session.commit()
    return render_template("index.html")
