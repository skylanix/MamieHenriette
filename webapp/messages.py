from flask import render_template
from webapp import webapp

@webapp.route("/messages")
def messages():
	return render_template("messages.html")
