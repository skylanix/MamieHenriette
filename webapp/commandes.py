from flask import render_template
from webapp import webapp

@webapp.route("/commandes")
def commandes():
    return render_template("commandes.html")
