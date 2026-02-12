import logging
from datetime import datetime, timedelta

from twitchAPI.chat import Chat
from twitchAPI.twitch import Twitch

from database import db
from database.models import TwitchAnnouncement
from webapp import webapp

logger = logging.getLogger('twitch-announcements')
logger.setLevel(logging.INFO)

# Délai minimum entre deux annonces (quelle qu'elles soient) pour éviter le spam
MIN_DELAY_BETWEEN_ANNOUNCEMENTS_MINUTES = 5

_message_count: int = 0
_last_announcement_index: int = -1  # Pour la rotation round-robin


def incrementMessageCount():
	global _message_count
	_message_count += 1


def _getAndResetMessageCount() -> int:
	global _message_count
	count = _message_count
	_message_count = 0
	return count


async def _is_channel_live(twitch: Twitch, channel: str) -> bool:
	"""Vérifie si la chaîne Twitch est actuellement en live."""
	try:
		async for _ in twitch.get_streams(user_login=[channel]):
			return True
	except Exception as e:
		logger.warning(f'Impossible de vérifier le statut live de {channel}: {e}')
	return False


async def checkAndSendAnnouncements(chat: Chat, channel: str, twitch: Twitch):
	"""
	Envoie une annonce en rotation parmi celles dont la périodicité est écoulée,
	uniquement si la chaîne est en live et qu'il y a assez d'activité dans le chat.
	Appelé périodiquement par le bot Twitch.
	"""
	global _last_announcement_index
	
	with webapp.app_context():
		if not await _is_channel_live(twitch, channel):
			return

		announcements: list[TwitchAnnouncement] = TwitchAnnouncement.query.filter_by(enable=True).order_by(TwitchAnnouncement.id).all()
		if not announcements:
			return

		now = datetime.now()

		# Ne pas envoyer si une annonce (quelle qu'elle soit) a été envoyée récemment
		last_any = max((a.last_sent for a in announcements if a.last_sent), default=None)
		if last_any and (now - last_any) < timedelta(minutes=MIN_DELAY_BETWEEN_ANNOUNCEMENTS_MINUTES):
			return

		# Filtrer les annonces dont la périodicité est écoulée
		due = [a for a in announcements if _shouldSend(a, now)]
		if not due:
			return

		# Rotation round-robin : chercher la prochaine annonce après la dernière envoyée
		announcement = _selectNextAnnouncement(due, announcements)
		if not announcement:
			return

		# Vérifier le nombre minimum de messages dans le chat
		message_count = _getAndResetMessageCount()
		if message_count < announcement.min_chat_messages:
			logger.debug(f'Annonce "{announcement.name}" ignorée : seulement {message_count} messages (minimum requis : {announcement.min_chat_messages})')
			return

		try:
			await _sendAnnouncement(chat, channel, announcement)
			announcement.last_sent = now
			_last_announcement_index = announcements.index(announcement)
			db.session.commit()
			logger.info(f'Annonce envoyée : {announcement.name} (après {message_count} messages)')
		except Exception as e:
			logger.error(f'Erreur lors de l\'envoi de l\'annonce "{announcement.name}": {e}')


def _selectNextAnnouncement(due: list[TwitchAnnouncement], all_announcements: list[TwitchAnnouncement]) -> TwitchAnnouncement | None:
	"""
	Sélectionne la prochaine annonce selon un système de rotation round-robin.
	Cherche la première annonce éligible après la dernière envoyée.
	"""
	global _last_announcement_index
	
	if not due:
		return None
	
	# Si c'est la première annonce ou si l'index est invalide, prendre la première de la liste
	if _last_announcement_index == -1 or _last_announcement_index >= len(all_announcements):
		return due[0]
	
	# Chercher la prochaine annonce éligible après la dernière envoyée
	start_index = _last_announcement_index + 1
	
	# Parcourir depuis l'index suivant jusqu'à la fin, puis revenir au début
	for i in range(len(all_announcements)):
		idx = (start_index + i) % len(all_announcements)
		announcement = all_announcements[idx]
		if announcement in due:
			return announcement
	
	# Fallback : retourner la première annonce éligible
	return due[0]


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
