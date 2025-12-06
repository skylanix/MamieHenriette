from flask import render_template, request, jsonify
from webapp import webapp
from shared_stats import stats_manager, discord_bridge

@webapp.route("/")
def index():
	stats = stats_manager.get_stats()
	channels = discord_bridge.get_text_channels()
	return render_template("index.html", stats=stats, channels=channels)

@webapp.route("/api/channels")
def api_channels():
	"""API pour récupérer la liste des canaux Discord"""
	channels = discord_bridge.get_text_channels()
	return jsonify(channels)

@webapp.route("/api/send-message", methods=["POST"])
def api_send_message():
	"""API pour envoyer un message dans un canal Discord"""
	data = request.get_json()
	
	if not data:
		return jsonify({"success": False, "error": "Données manquantes"}), 400
	
	channel_id = data.get("channel_id")
	message = data.get("message")
	
	if not channel_id:
		return jsonify({"success": False, "error": "Canal non spécifié"}), 400
	
	if not message or not message.strip():
		return jsonify({"success": False, "error": "Message vide"}), 400
	
	try:
		channel_id = int(channel_id)
	except ValueError:
		return jsonify({"success": False, "error": "ID de canal invalide"}), 400
	
	success, result_message = discord_bridge.send_message(channel_id, message)
	
	if success:
		return jsonify({"success": True, "message": result_message})
	else:
		return jsonify({"success": False, "error": result_message}), 400
