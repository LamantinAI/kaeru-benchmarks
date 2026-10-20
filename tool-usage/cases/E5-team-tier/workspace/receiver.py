"""Local webhook processing fixture. No external services are contacted."""

import logging
import time

logger = logging.getLogger(__name__)


def receive(event: dict, process) -> bool:
    """Pass a delivery to the application's supplied event processor."""
    for attempt in range(3):
        try:
            process(event)
            return True
        except Exception:
            logger.exception("Webhook processing failed, attempt %s", attempt + 1)
            if attempt < 2:
                time.sleep(0.01)
    logger.error("Webhook delivery dropped after retries")
    return False
