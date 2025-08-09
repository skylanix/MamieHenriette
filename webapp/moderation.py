from flask import render_template
from webapp import webapp

@webapp.route("/moderation")
def moderation():
    return render_template("moderation.html")
