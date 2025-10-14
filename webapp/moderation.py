from flask import render_template
from webapp import webapp
from database.models import Warning

@webapp.route("/moderation")
def moderation():
	warnings = Warning.query.order_by(Warning.created_at.desc()).all()
	return render_template("moderation.html", warnings=warnings)

