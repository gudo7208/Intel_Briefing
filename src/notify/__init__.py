"""
通知模块 - 支持多渠道推送情报简报。
目前支持: Telegram Bot, Discord Webhook
"""
from src.notify.base import NotifyProvider
from src.notify.telegram_bot import TelegramNotifier
from src.notify.discord_webhook import DiscordNotifier

__all__ = ["NotifyProvider", "TelegramNotifier", "DiscordNotifier"]
