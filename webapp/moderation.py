from flask import render_template, request, redirect, url_for
from webapp import webapp
from webapp.auth import require_page, can_write_page
from database import db
from database.models import ModerationEvent

def _top_sanctioned():
	return (
		db.session.query(
			ModerationEvent.discord_id,
			db.func.max(ModerationEvent.username).label("username"),
			db.func.count(ModerationEvent.id).label("count"),
		)
		.group_by(ModerationEvent.discord_id)
		.order_by(db.func.count(ModerationEvent.id).desc())
		.limit(3)
		.all()
	)

def _top_moderators():
	return (
		db.session.query(
			ModerationEvent.staff_id,
			db.func.max(ModerationEvent.staff_name).label("staff_name"),
			db.func.count(ModerationEvent.id).label("count"),
		)
		.group_by(ModerationEvent.staff_id)
		.order_by(db.func.count(ModerationEvent.id).desc())
		.limit(3)
		.all()
	)

@webapp.route("/moderation")
@require_page("moderation")
def moderation():
	events = ModerationEvent.query.order_by(ModerationEvent.created_at.desc()).all()
	top_sanctioned = _top_sanctioned()
	top_moderators = _top_moderators()
	return render_template(
		"moderation.html",
		events=events,
		event=None,
		top_sanctioned=top_sanctioned,
		top_moderators=top_moderators,
	)

@webapp.route("/moderation/edit/<int:event_id>")
@require_page("moderation")
def open_edit_moderation_event(event_id):
	event = ModerationEvent.query.get_or_404(event_id)
	events = ModerationEvent.query.order_by(ModerationEvent.created_at.desc()).all()
	top_sanctioned = _top_sanctioned()
	top_moderators = _top_moderators()
	return render_template(
		"moderation.html",
		events=events,
		event=event,
		top_sanctioned=top_sanctioned,
		top_moderators=top_moderators,
	)

@webapp.route("/moderation/update/<int:event_id>", methods=['POST'])
@require_page("moderation")
def update_moderation_event(event_id):
	if not can_write_page("moderation"):
		return render_template("403.html"), 403
	event = ModerationEvent.query.get_or_404(event_id)
	event.reason = request.form.get('reason')
	db.session.commit()
	return redirect(url_for('moderation'))

@webapp.route("/moderation/delete/<int:event_id>")
@require_page("moderation")
def delete_moderation_event(event_id):
	if not can_write_page("moderation"):
		return render_template("403.html"), 403
	event = ModerationEvent.query.get_or_404(event_id)
	db.session.delete(event)
	db.session.commit()
	return redirect(url_for('moderation'))

