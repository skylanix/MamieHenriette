from flask import Flask, render_template
from webapp import webapp

@webapp.route("/")
def index():
    return render_template("index.html")
