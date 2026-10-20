MAX_PAYLOAD_BYTES = None

def validate_upload(payload):
    if MAX_PAYLOAD_BYTES is None:
        raise RuntimeError('upload limit is not configured')
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError('upload too large')
