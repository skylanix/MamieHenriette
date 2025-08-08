from flask import Flask, render_template
from webapp import webapp, db
from webapp.models import Message

@webapp.route("/")
def index():
    # message = Message(text="bla bla", periodicity = 3600)
    # db.session.add(message)
    # db.session.commit()
    return render_template("index.html")
