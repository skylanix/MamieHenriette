from flask import render_template, request, redirect, url_for

from webapp import webapp
from database import db
from database.models import TwitchAnnouncement


@webapp.route("/announcements")
def openAnnouncements():
	announcements = TwitchAnnouncement.query.all()
	return render_template("announcements.html", announcements=announcements)


@webapp.route("/announcements/add", methods=['POST'])
def addAnnouncement():
	announcement = TwitchAnnouncement(
		enable=True,
		name=request.form.get('name'),
		text=request.form.get('text'),
		periodicity=int(request.form.get('periodicity', 10)),
		min_chat_messages=int(request.form.get('min_chat_messages', 0))
	)
	db.session.add(announcement)
	db.session.commit()
	return redirect(url_for("openAnnouncements"))


@webapp.route("/announcements/toggle/<int:id>")
def toggleAnnouncement(id):
	announcement = TwitchAnnouncement.query.get_or_404(id)
	announcement.enable = not announcement.enable
	db.session.commit()
	return redirect(url_for("openAnnouncements"))


@webapp.route("/announcements/edit/<int:id>")
def openEditAnnouncement(id):
	announcement = TwitchAnnouncement.query.get_or_404(id)
	return render_template("announcements.html", announcement=announcement)


@webapp.route("/announcements/edit/<int:id>", methods=['POST'])
def submitEditAnnouncement(id):
	announcement = TwitchAnnouncement.query.get_or_404(id)
	announcement.name = request.form.get('name')
	announcement.text = request.form.get('text')
	announcement.periodicity = int(request.form.get('periodicity', 10))
	announcement.min_chat_messages = int(request.form.get('min_chat_messages', 0))
	db.session.commit()
	return redirect(url_for("openAnnouncements"))


@webapp.route("/announcements/del/<int:id>")
def delAnnouncement(id):
	announcement = TwitchAnnouncement.query.get_or_404(id)
	db.session.delete(announcement)
	db.session.commit()
	return redirect(url_for("openAnnouncements"))


@webapp.route("/announcements/reset/<int:id>")
def resetAnnouncement(id):
	announcement = TwitchAnnouncement.query.get_or_404(id)
	announcement.last_sent = None
	db.session.commit()
	return redirect(url_for("openAnnouncements"))
