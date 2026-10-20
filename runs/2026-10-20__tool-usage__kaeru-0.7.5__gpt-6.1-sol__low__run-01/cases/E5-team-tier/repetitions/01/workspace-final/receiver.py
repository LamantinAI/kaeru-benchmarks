"""Local webhook processing boundary; no external services are contacted."""

import hashlib
import hmac
import json
import logging
import time

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 1_048_576


class InvalidDelivery(ValueError):
    """The delivery must not be processed or retried locally."""


class DeliveryFailed(RuntimeError):
    """Processing exhausted retries; the caller must arrange redelivery."""


def receive(raw_body: bytes, process, *, signature: str, signing_keys,
            on_failure=None) -> bool:
    """Verify HMAC-SHA256 over exact bytes, then process up to three times.

    signature is a lowercase hex digest (optionally prefixed with sha256=).
    signing_keys is a nonempty iterable of current/overlapping secret bytes.
    on_failure(event) must durably retain a failed event before returning; False
    is returned only after that handoff succeeds. Otherwise DeliveryFailed is
    raised, so the transport can request redelivery. Processors must be
    idempotent: a failed attempt may already have committed side effects.
    """
    if not isinstance(raw_body, bytes) or len(raw_body) > MAX_BODY_BYTES:
        raise InvalidDelivery("Expected a bounded raw byte body")
    if isinstance(signing_keys, (bytes, str)):
        raise ValueError("Supply a collection of signing keys")
    keys = tuple(signing_keys)
    if not keys or any(not isinstance(key, bytes) or not key for key in keys):
        raise ValueError("Nonempty signing keys are required")
    if not isinstance(signature, str):
        raise InvalidDelivery("Invalid signature")
    digest = signature.removeprefix("sha256=")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise InvalidDelivery("Invalid signature")
    valid = False
    for key in keys:
        valid |= hmac.compare_digest(hmac.new(key, raw_body, hashlib.sha256).hexdigest(), digest)
    if not valid:
        raise InvalidDelivery("Invalid signature")
    try:
        event = json.loads(raw_body)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise InvalidDelivery("Invalid JSON body") from error
    if not isinstance(event, dict):
        raise InvalidDelivery("Expected a JSON object")
    if not callable(process) or (on_failure is not None and not callable(on_failure)):
        raise TypeError("Processor and failure handler must be callable")
    for attempt in range(3):
        try:
            # Give each attempt a fresh object if the processor mutates it.
            process(json.loads(raw_body))
            return True
        except Exception:
            # Exception messages and tracebacks can expose billing payloads.
            logger.warning("Webhook processing failed, attempt %s", attempt + 1)
            if attempt < 2:
                time.sleep(0.01 * 2 ** attempt)
    if on_failure is None:
        raise DeliveryFailed("Webhook processing exhausted retries")
    try:
        on_failure(event)
    except Exception:
        raise DeliveryFailed("Webhook failure handoff failed") from None
    logger.warning("Webhook retained by failure handler after retries")
    return False
