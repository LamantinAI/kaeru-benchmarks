# Current vendor limit on the standard plan: 5 MB (decimal bytes).
MAX_PAYLOAD_BYTES = 5_000_000

def validate_upload(payload):
    if MAX_PAYLOAD_BYTES is None:
        raise RuntimeError('upload limit is not configured')
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError('Upload too large. Maximum upload size is 5 MB (5,000,000 bytes).')
