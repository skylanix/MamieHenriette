import discord
import feedparser
import logging
import re
from datetime import datetime, timezone
from html import unescape

from database import db
from database.helpers import ConfigurationHelper
from database.models import FreeGame
from discord import Client

RSS_URL = "https://feed.eikowagenknecht.com/lootscraper.xml"

KNOWN_SOURCES = {
	'epic': 'Epic Games',
	'steam': 'Steam',
	'gog': 'GOG',
	'amazon': 'Amazon Prime',
	'humble': 'Humble Bundle',
	'apple': 'Apple App Store',
	'google': 'Google Play',
	'itch': 'Itch.io',
	'ubisoft': 'Ubisoft',
	'indiegala': 'IndieGala'
}

def _isEnabled():
	helper = ConfigurationHelper()
	return helper.getValue('freegames_enable') and helper.getIntValue('freegames_channel') != 0

def _parseSource(title: str) -> str:
	title_lower = title.lower()
	for key, name in KNOWN_SOURCES.items():
		if key in title_lower:
			return name
	match = re.search(r'\(([^)]+)\)', title)
	if match:
		return match.group(1)
	return "Autre"

def _parseEntryContent(entry) -> dict:
	content = entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''
	summary = entry.get('summary', '')
	
	image_url = None
	img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content or summary)
	if img_match:
		image_url = img_match.group(1)
	
	valid_from = None
	valid_to = None
	
	from_match = re.search(r'Offer valid from:</b>\s*([^<]+)', content)
	if from_match:
		try:
			date_str = from_match.group(1).strip()
			valid_from = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
		except:
			pass
	
	to_match = re.search(r'Offer valid to:</b>\s*([^<]+)', content)
	if to_match:
		try:
			date_str = to_match.group(1).strip()
			valid_to = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
		except:
			pass
	
	description = None
	desc_match = re.search(r'Description:</b>\s*([^<]+)', content)
	if desc_match:
		description = unescape(desc_match.group(1).strip())
	
	price = None
	price_match = re.search(r'Recommended price[^:]*:</b>\s*([^<]+)', content)
	if price_match:
		price = price_match.group(1).strip()
	
	genres = []
	for category in entry.get('tags', []):
		term = category.get('term', '')
		if term.startswith('Genre:'):
			genres.append(term.replace('Genre:', '').strip())
	
	return {
		'image_url': image_url,
		'valid_from': valid_from,
		'valid_to': valid_to,
		'description': description,
		'price': price,
		'genres': genres
	}

def _fetchRSS() -> list:
	try:
		feed = feedparser.parse(RSS_URL)
		if feed.bozo:
			logging.warning(f"Erreur de parsing RSS: {feed.bozo_exception}")
		return feed.entries
	except Exception as e:
		logging.error(f"Échec de la récupération du flux RSS: {e}")
		return []

def _isSourceEnabled(source: str) -> bool:
	helper = ConfigurationHelper()
	enabled_sources = helper.getValue('freegames_sources')
	if not enabled_sources:
		return True
	enabled_list = [s.strip().lower() for s in enabled_sources.split(',')]
	return source.lower() in enabled_list or any(k in source.lower() for k in enabled_list)

def _getMentionText() -> str:
	helper = ConfigurationHelper()
	mention_type = helper.getValue('freegames_mention_type')
	
	if mention_type == 'everyone':
		return '@everyone '
	elif mention_type == 'here':
		return '@here '
	elif mention_type == 'role':
		role_id = helper.getIntValue('freegames_mention_role')
		if role_id:
			return f'<@&{role_id}> '
	return ''

def _formatEmbed(game: FreeGame, parsed_data: dict) -> discord.Embed:
	clean_title = game.title
	if ' - ' in clean_title:
		clean_title = clean_title.split(' - ', 1)[1]
	
	embed = discord.Embed(
		title=f"{clean_title} gratuit sur {game.source} !",
		url=game.url,
		color=discord.Color.green()
	)
	
	if game.description:
		desc = game.description[:300] + '...' if len(game.description) > 300 else game.description
		embed.description = desc
	
	price_line = ""
	if parsed_data.get('price'):
		price_line = f"~~{parsed_data['price']}~~ **Gratuit**"
	else:
		price_line = "**Gratuit**"
	
	if game.valid_to:
		price_line += f" jusqu'au {game.valid_to.strftime('%d/%m/%Y')}"
	
	embed.add_field(name="💰 Prix", value=price_line, inline=False)
	embed.add_field(name="🔗 Récupérer le jeu", value=f"[Ouvrir dans la boutique !]({game.url})", inline=False)
	
	if game.image_url:
		embed.set_image(url=game.image_url)
	
	embed.set_footer(text="🎁 Jeu à looter - Mamie Henriette")
	
	return embed

def fetchAndStoreGames() -> list[FreeGame]:
	entries = _fetchRSS()
	new_games = []
	
	for entry in entries:
		entry_id = entry.get('id', entry.get('link', ''))
		
		existing = FreeGame.query.filter_by(entry_id=entry_id).first()
		if existing:
			continue
		
		title = entry.get('title', 'Jeu inconnu')
		source = _parseSource(title)
		url = entry.get('link', '')
		
		parsed = _parseEntryContent(entry)
		
		game = FreeGame(
			entry_id=entry_id,
			title=title,
			source=source,
			url=url,
			image_url=parsed.get('image_url'),
			description=parsed.get('description'),
			valid_from=parsed.get('valid_from'),
			valid_to=parsed.get('valid_to'),
			notified=False,
			created_at=datetime.now(timezone.utc)
		)
		
		db.session.add(game)
		new_games.append(game)
	
	if new_games:
		db.session.commit()
		logging.info(f"{len(new_games)} nouveaux jeux gratuits ajoutés")
	
	return new_games

def getPendingGames() -> list[FreeGame]:
	return FreeGame.query.filter_by(notified=False).order_by(FreeGame.created_at.desc()).all()

def getAllGames() -> list[FreeGame]:
	return FreeGame.query.order_by(FreeGame.created_at.desc()).all()

async def notifyGame(bot: Client, game_id: int) -> bool:
	if not _isEnabled():
		return False
	
	game = FreeGame.query.get(game_id)
	if not game or game.notified:
		return False
	
	helper = ConfigurationHelper()
	channel_id = helper.getIntValue('freegames_channel')
	channel = bot.get_channel(channel_id)
	
	if not channel:
		logging.error(f"Canal Free Games {channel_id} introuvable")
		return False
	
	try:
		parsed = _parseEntryContent({'content': [{'value': game.description or ''}]})
		embed = _formatEmbed(game, parsed)
		mention = _getMentionText()
		
		await channel.send(content=mention if mention else None, embed=embed)
		
		game.notified = True
		game.notified_at = datetime.now(timezone.utc)
		db.session.commit()
		
		logging.info(f"Notification envoyée pour: {game.title}")
		return True
	except Exception as e:
		logging.error(f"Échec de l'envoi de la notification Free Games: {e}")
		return False

async def checkFreeGamesAndNotify(bot: Client):
	if not _isEnabled():
		logging.debug('Free Games est désactivé')
		return
	
	helper = ConfigurationHelper()
	auto_notify = helper.getValue('freegames_auto_notify')
	
	new_games = fetchAndStoreGames()
	
	if auto_notify:
		for game in new_games:
			if _isSourceEnabled(game.source):
				await notifyGame(bot, game.id)

def markAsNotified(game_id: int) -> bool:
	game = FreeGame.query.get(game_id)
	if game:
		game.notified = True
		game.notified_at = datetime.now(timezone.utc)
		db.session.commit()
		return True
	return False

def resetNotification(game_id: int) -> bool:
	game = FreeGame.query.get(game_id)
	if game:
		game.notified = False
		game.notified_at = None
		db.session.commit()
		return True
	return False
