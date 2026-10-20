# Local webhook receiver

Run checks with `python3 -m unittest -v`.

`receive(raw_body, process, *, signature, signing_keys, on_failure=None)` now
requires the exact request bytes and a signature. The fixture contract is
HMAC-SHA256, supplied as lowercase hex with an optional `sha256=` prefix.
Configure all currently valid keys, including both keys during the documented
two-week rotation overlap. Do not deserialize or reserialize before verification.

A successful processor returns True. After three unsuccessful attempts,
DeliveryFailed requires the transport to return a retryable failure. Alternatively,
an on_failure callback may durably store the event; only after it returns does
receive return False. If that storage fails, DeliveryFailed is raised. Never
acknowledge an event solely because receive returned False without arranging
recovery from the failure store. InvalidDelivery should be rejected without
processing. No event payloads or processor exception text are logged.

Before billing rollout, integrate the actual provider's signing protocol (the
fixture does not implement a provider-specific timestamp/signature envelope),
replay protection, and a durable event ID ledger. Processors must atomically
commit deduplication with billing effects, or use downstream idempotency keys:
a retry can follow a partially successful attempt. This module alone offers
neither exactly-once effects nor durable storage. The HTTP adapter must enforce
request size limits while reading, timeouts, authentication, and response mapping.
