Webhook receiver fixture
========================

Run checks with `python3 -m unittest -v`.

Use `receive_signed(raw_body, signature, process, signing_keys=[current, previous])`
at the authentication boundary. Keys are nonempty bytes; the signature is a bare
HMAC-SHA256 hex digest over the original body. Both keys are accepted during the
required two-week rotation overlap. Remove the previous key after that overlap.
`receive` is for already authenticated dictionaries only.

Successful processing returns True. Exhausted processing now raises DeliveryFailed
instead of returning False and dropping the event. Update callers accordingly:
return a retryable HTTP failure, or durably enqueue the delivery before acknowledging.
InvalidDelivery means authentication or payload validation failed. Configuration
errors raise ValueError. Logs omit exception messages and payloads.

Before billing deployment, connect this fixture to the actual sender's signature
protocol (including timestamp/replay validation where supplied), enforce body limits
while reading HTTP requests, and configure secrets securely. There is no HTTP server,
durable inbox, deduplication store, or billing processor in this workspace. The
processor must enforce event-id uniqueness transactionally with its billing updates;
retries can otherwise repeat effects after a partial failure. Verify those integrations
and crash/restart behavior before relying on this for billing.
