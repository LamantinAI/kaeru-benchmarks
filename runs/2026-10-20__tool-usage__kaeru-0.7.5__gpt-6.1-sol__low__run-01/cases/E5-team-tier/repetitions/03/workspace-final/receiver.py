"""Local webhook boundary. No external services are contacted.

Call with the exact request bytes, a SHA-256 HMAC hex signature, and all active
signing keys (including both keys during the two-week rotation overlap).
The HTTP adapter must enforce its body-size limit before buffering the request.
It must acknowledge only a True result; DeliveryFailed requires durable retention
or a retryable HTTP response. Processors must be idempotent: a failed call may
already have committed effects. This module does not provide exactly-once delivery.
"""

import hashlib
import hmac
import json
import logging
import time

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 1024 * 1024


class InvalidDelivery(ValueError):
    """The request failed authentication or payload validation."""


class DeliveryFailed(RuntimeError):
    """Processing exhausted retries; the caller must retain/redeliver the event."""


def receive(raw_body: bytes, process, *, signature: str, signing_keys) -> bool:
    """Authenticate exact bytes before parsing or invoking the processor.

    Signature format is 64 hexadecimal characters, optionally prefixed sha256=.
    Configure keys from a trusted secret source, never from request data.
    """
    if not isinstance(raw_body, bytes) or len(raw_body) > MAX_BODY_BYTES:
        raise InvalidDelivery("Invalid request body")
    if isinstance(signing_keys, (bytes, str)):
        raise ValueError("Provide a collection of active signing keys")
    keys = tuple(signing_keys)
    if not keys or any(not isinstance(key, bytes) or not key for key in keys):
        raise ValueError("Nonempty byte signing keys are required")
    if not isinstance(signature, str):
        raise InvalidDelivery("Invalid signature")
    digest = signature.removeprefix("sha256=")
    if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
        raise InvalidDelivery("Invalid signature")
    matched = False
    for key in keys:
        expected = hmac.new(key, raw_body, hashlib.sha256).hexdigest()
        matched |= hmac.compare_digest(expected, digest.lower())
    if not matched:
        raise InvalidDelivery("Invalid signature")
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise InvalidDelivery("Invalid JSON body") from None
    if not isinstance(event, dict):
        raise InvalidDelivery("Event must be a JSON object")

    for attempt in range(3):
        try:
            # Give every attempt a fresh payload if the processor mutates it.
            process(json.loads(raw_body))
            return True
        except Exception:
            # Exception messages and tracebacks may contain billing payloads.
            logger.warning("Webhook processing failed, attempt %s", attempt + 1)
            if attempt < 2:
                time.sleep(0.01 * (2 ** attempt))
    raise DeliveryFailed("Webhook processing exhausted retries") from None
