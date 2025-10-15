from flask import render_template, request, redirect, url_for
from webapp import webapp
from database import db
from database.models import ModerationEvent

@webapp.route("/moderation")
def moderation():
	events = ModerationEvent.query.order_by(ModerationEvent.created_at.desc()).all()
	return render_template("moderation.html", events=events)

@webapp.route("/moderation/update/<int:event_id>", methods=['POST'])
def update_moderation_event(event_id):
	event = ModerationEvent.query.get_or_404(event_id)
	event.reason = request.form.get('reason')
	db.session.commit()
	return redirect(url_for('moderation'))

@webapp.route("/moderation/delete/<int:event_id>")
def delete_moderation_event(event_id):
	event = ModerationEvent.query.get_or_404(event_id)
	db.session.delete(event)
	db.session.commit()
	return redirect(url_for('moderation'))

