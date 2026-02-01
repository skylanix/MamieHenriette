import logging
from datetime import datetime, timedelta

from twitchAPI.chat import Chat

from database import db
from database.models import TwitchAnnouncement
from webapp import webapp

logger = logging.getLogger('twitch-announcements')
logger.setLevel(logging.INFO)


async def checkAndSendAnnouncements(chat: Chat, channel: str):
	"""
	Vérifie et envoie les annonces dont la périodicité est écoulée.
	Appelé périodiquement par le bot Twitch.
	"""
	with webapp.app_context():
		announcements: list[TwitchAnnouncement] = TwitchAnnouncement.query.filter_by(enable=True).all()
		now = datetime.now()
		
		for announcement in announcements:
			if _shouldSend(announcement, now):
				try:
					await _sendAnnouncement(chat, channel, announcement)
					announcement.last_sent = now
					db.session.commit()
					logger.info(f'Annonce envoyée : {announcement.name}')
				except Exception as e:
					logger.error(f'Erreur lors de l\'envoi de l\'annonce "{announcement.name}": {e}')


def _shouldSend(announcement: TwitchAnnouncement, now: datetime) -> bool:
	"""
	Vérifie si une annonce doit être envoyée basée sur sa périodicité.
	"""
	if announcement.last_sent is None:
		return True
	
	time_since_last = now - announcement.last_sent
	periodicity_delta = timedelta(minutes=announcement.periodicity)
	
	return time_since_last >= periodicity_delta


async def _sendAnnouncement(chat: Chat, channel: str, announcement: TwitchAnnouncement):
	"""
	Envoie une annonce dans le chat Twitch.
	"""
	await chat.send_message(channel, announcement.text)
