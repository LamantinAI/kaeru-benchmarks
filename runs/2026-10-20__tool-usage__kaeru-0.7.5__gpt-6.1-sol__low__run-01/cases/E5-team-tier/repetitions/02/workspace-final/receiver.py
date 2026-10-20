"""Local webhook processing fixture. No external services are contacted.

The HTTP adapter must pass the original body bytes to receive_signed, map
DeliveryFailed to a retryable non-2xx response, and acknowledge only success.
Processors must be idempotent: a failed call may already have had side effects.
"""

from copy import deepcopy
import hashlib
import hmac
import json
import logging
import time

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 1024 * 1024


class DeliveryFailed(RuntimeError):
    """Processing exhausted retries; the delivery must remain retryable."""


class InvalidDelivery(ValueError):
    """The delivery is unauthenticated or malformed."""


def receive_signed(body: bytes, signature: str, process, *, signing_keys) -> bool:
    """Verify HMAC-SHA256 hex over raw bytes against all active rotation keys.

    This fixture's signature contract is a bare 64-character hexadecimal digest.
    The HTTP adapter must implement the sender's actual header/signing protocol.
    Configure both current and previous keys throughout the rotation overlap.
    """
    keys = tuple(signing_keys)
    if not keys or any(not isinstance(key, bytes) or not key for key in keys):
        raise ValueError("Nonempty signing keys must be configured as bytes")
    if not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES:
        raise InvalidDelivery("Invalid body or body too large")
    if not isinstance(signature, str) or len(signature) != 64:
        raise InvalidDelivery("Invalid signature")
    try:
        supplied = bytes.fromhex(signature)
    except ValueError:
        raise InvalidDelivery("Invalid signature") from None
    valid = False
    for key in keys:
        valid |= hmac.compare_digest(hmac.digest(key, body, hashlib.sha256), supplied)
    if not valid:
        raise InvalidDelivery("Invalid signature")
    try:
        event = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        raise InvalidDelivery("Invalid JSON") from None
    if not isinstance(event, dict):
        raise InvalidDelivery("Event must be a JSON object")
    return receive(event, process)


def receive(event: dict, process) -> bool:
    """Process an already authenticated event, or raise for upstream retry.

    Each attempt receives a fresh copy so processor mutations cannot corrupt
    retries. No event payloads or exception text are written to logs.
    """
    if not isinstance(event, dict):
        raise InvalidDelivery("Event must be a dictionary")
    original = deepcopy(event)
    for attempt in range(3):
        try:
            process(deepcopy(original))
            return True
        except Exception as exc:
            logger.warning("Webhook processing failed, attempt %s", attempt + 1)
            if attempt == 2:
                raise DeliveryFailed("Webhook processing exhausted retries") from exc
            time.sleep(0.01 * (2 ** attempt))
