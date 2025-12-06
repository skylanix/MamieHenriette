import logging
import feedparser
from dataclasses import dataclass
from datetime import datetime

from database import db
from database.models import YoutubeAlert
from webapp import webapp

logger = logging.getLogger('youtube-alert')
logger.setLevel(logging.INFO)

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


@dataclass
class YoutubeVideo:
	video_id: str
	title: str
	author: str
	link: str
	published: datetime
	thumbnail: str


def _fetch_latest_video(channel_id: str) -> YoutubeVideo | None:
	feed_url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
	try:
		feed = feedparser.parse(feed_url)
		if feed.entries:
			entry = feed.entries[0]
			video_id = entry.yt_videoid
			return YoutubeVideo(
				video_id=video_id,
				title=entry.title,
				author=entry.author,
				link=entry.link,
				published=datetime(*entry.published_parsed[:6]),
				thumbnail=f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
			)
	except Exception as e:
		logger.error(f"Erreur lors de la récupération du flux RSS pour {channel_id}: {e}")
	return None


def _get_channel_name(channel_id: str) -> str | None:
	feed_url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
	try:
		feed = feedparser.parse(feed_url)
		if feed.feed and hasattr(feed.feed, 'author'):
			return feed.feed.author
		if feed.entries:
			return feed.entries[0].author
	except Exception as e:
		logger.error(f"Erreur lors de la récupération du nom de chaîne pour {channel_id}: {e}")
	return None


async def checkNewVideos(bot):
	with webapp.app_context():
		alerts: list[YoutubeAlert] = YoutubeAlert.query.filter_by(enable=True).all()
		
		for alert in alerts:
			logger.info(f"Vérification de la chaîne : {alert.channel_name or alert.channel_id}")
			video = _fetch_latest_video(alert.channel_id)
			
			if video:
				if not alert.channel_name:
					alert.channel_name = video.author
				
				if alert.last_video_id != video.video_id:
					logger.info(f"Nouvelle vidéo détectée : {video.title}")
					
					if alert.last_video_id is not None:
						await _notifyAlert(bot, alert, video)
					
					alert.last_video_id = video.video_id
			else:
				logger.warning(f"Impossible de récupérer les vidéos pour {alert.channel_id}")
		
		db.session.commit()


async def _notifyAlert(bot, alert: YoutubeAlert, video: YoutubeVideo):
	try:
		message = alert.message.format(video)
		logger.info(f"Message de notification : {message}")
		bot.loop.create_task(_sendMessage(bot, alert.notify_channel, message))
	except Exception as e:
		logger.error(f"Erreur lors du formatage du message : {e}")


async def _sendMessage(bot, channel: int, message: str):
	logger.info(f"Envoi de notification : {message}")
	channel_obj = bot.get_channel(channel)
	if channel_obj:
		await channel_obj.send(message)
		logger.info("Notification envoyée")
	else:
		logger.error(f"Canal Discord non trouvé : {channel}")
