from loguru import logger


def notify(bot, channel, text):
    """Debug notification."""
    logger.debug(f"Sending to channel {channel['hook_url']}: {text}")
