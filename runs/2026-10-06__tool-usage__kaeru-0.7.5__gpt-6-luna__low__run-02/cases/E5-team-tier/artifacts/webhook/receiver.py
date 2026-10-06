"""Small, fail-closed webhook verification and delivery helpers.

The signing key is read at call time from ``WEBHOOK_SIGNING_KEY`` so importing
this module is safe in tools which do not handle live webhook traffic. In
production, pass the provider's timestamp as ``timestamp`` and sign
``timestamp + b"." + payload`` to limit replay of captured requests.
"""

import hashlib
import hmac
import os
import random
import time


MAX_ATTEMPTS = 3
MAX_PAYLOAD_BYTES = 1_048_576
DEFAULT_TIMESTAMP_TOLERANCE = 300
DEFAULT_BACKOFF_BASE = 0.1
DEFAULT_BACKOFF_MAX = 2.0


def _key(signing_key=None):
    if signing_key is None:
        configured = os.environ.get("WEBHOOK_SIGNING_KEY")
        if not configured:
            return None
        signing_key = configured
    if isinstance(signing_key, str):
        signing_key = signing_key.encode("utf-8")
    if not isinstance(signing_key, bytes) or not signing_key:
        return None
    return signing_key


def _signature_bytes(signature):
    if isinstance(signature, bytes):
        try:
            signature = signature.decode("ascii")
        except UnicodeDecodeError:
            return None
    if not isinstance(signature, str):
        return None
    signature = signature.strip()
    if signature.startswith("sha256="):
        signature = signature[7:]
    # Keep a single canonical representation; compare_digest then compares
    # equal-length ASCII strings in constant time.
    if len(signature) != 64 or any(c not in "0123456789abcdefABCDEF" for c in signature):
        return None
    return signature.lower()


def valid_signature(
    payload,
    signature,
    *,
    signing_key=None,
    timestamp=None,
    tolerance=DEFAULT_TIMESTAMP_TOLERANCE,
    now=None,
):
    """Return whether an HMAC-SHA256 signature matches the exact body bytes.

    With ``timestamp``, the signed bytes are ``<timestamp>.<payload>`` and the
    timestamp must be within ``tolerance`` seconds of ``now``. Without it, the
    legacy body-only HMAC format is checked for compatibility.
    """
    key = _key(signing_key)
    supplied = _signature_bytes(signature)
    if key is None or supplied is None or not isinstance(payload, bytes):
        return False

    signed_payload = payload
    if timestamp is not None:
        if isinstance(timestamp, bytes):
            try:
                timestamp = timestamp.decode("ascii")
            except UnicodeDecodeError:
                return False
        if not isinstance(timestamp, str) or not timestamp.isascii() or not timestamp.isdigit():
            return False
        try:
            timestamp_seconds = int(timestamp)
        except (TypeError, ValueError):
            return False
        if tolerance < 0:
            return False
        current_time = time.time() if now is None else now
        if abs(current_time - timestamp_seconds) > tolerance:
            return False
        signed_payload = timestamp.encode("ascii") + b"." + payload

    expected = hmac.new(key, signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def receive(
    payload,
    signature,
    deliver,
    *,
    signing_key=None,
    timestamp=None,
    require_timestamp=True,
    timestamp_tolerance=DEFAULT_TIMESTAMP_TOLERANCE,
    max_attempts=MAX_ATTEMPTS,
    backoff_base=DEFAULT_BACKOFF_BASE,
    backoff_max=DEFAULT_BACKOFF_MAX,
    retry_if=None,
    sleep=time.sleep,
    jitter=random.uniform,
):
    """Verify then deliver a webhook body, retrying delivery failures.

    ``deliver`` must implement idempotency using the provider event ID; a
    network failure after its side effect may otherwise cause duplicate work.
    Supply ``retry_if`` to limit retries to transient delivery errors.
    """
    if not isinstance(payload, bytes):
        raise TypeError("payload must be the exact request body as bytes")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("payload too large")
    if require_timestamp and timestamp is None:
        raise ValueError("timestamp is required")
    if not valid_signature(
        payload,
        signature,
        signing_key=signing_key,
        timestamp=timestamp,
        tolerance=timestamp_tolerance,
    ):
        raise ValueError("invalid signature")
    if not callable(deliver):
        raise TypeError("deliver must be callable")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")
    if backoff_base < 0 or backoff_max < 0:
        raise ValueError("backoff values must be non-negative")

    for attempt in range(max_attempts):
        try:
            return deliver(payload)
        except Exception as error:
            if attempt == max_attempts - 1 or (retry_if is not None and not retry_if(error)):
                raise
            ceiling = min(backoff_base * (2 ** attempt), backoff_max)
            delay = jitter(ceiling / 2, ceiling) if ceiling else 0
            sleep(max(0, delay))
