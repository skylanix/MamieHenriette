-- Migration: Ajout de la table twitch_banned_word
-- Date: 2026-02-10
-- Description: Permet de gérer les mots interdits dans le chat Twitch

CREATE TABLE IF NOT EXISTS `twitch_banned_word` (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	`word` VARCHAR(256) UNIQUE NOT NULL,
	`enabled` BOOLEAN NOT NULL DEFAULT TRUE,
	`timeout_duration` INTEGER NOT NULL DEFAULT 60,
	`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
