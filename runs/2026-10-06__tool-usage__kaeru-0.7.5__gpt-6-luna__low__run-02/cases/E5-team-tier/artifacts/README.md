# Webhook receiver

`webhook/receiver.py` is a small helper for verifying and delivering webhook
request bodies. The HTTP server should pass the exact raw body bytes; parsing
and re-serializing JSON before verification will invalidate signatures.

## Configuration

Set `WEBHOOK_SIGNING_KEY` to the provider's secret through the deployment's
secret manager. There is no built-in development key: if the key is absent,
verification fails closed. Do not log the key, signature, or full billing
payload.

Signatures are lowercase or uppercase hex HMAC-SHA256 values, optionally
prefixed with `sha256=`. For replay protection, include the provider timestamp
when calling `receive`: the signed message is the ASCII timestamp, a period,
then the exact body (`timestamp + b"." + payload`). `receive` requires this
timestamp by default and checks that it is within five minutes of the receiver
clock. For a temporary legacy migration, `require_timestamp=False` permits
body-only HMAC, but that removes replay protection.

```python
from webhook.receiver import receive

result = receive(
    raw_body,
    signature_header,
    deliver_billing_event,
    timestamp=timestamp_header,
    retry_if=is_transient_delivery_error,
)
```

`receive` rejects non-byte bodies and bodies larger than 1 MiB. It attempts
delivery up to three times with exponential backoff and jitter. Configure
`max_attempts`, `backoff_base`, and `backoff_max` for deployment needs. Use
`retry_if` to retry only transient failures. The delivery handler must record
and deduplicate the provider's event ID in durable storage: retries cannot
provide exactly-once effects, and a repeated provider delivery may happen
after a successful side effect whose acknowledgement was lost.
