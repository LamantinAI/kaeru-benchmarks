# Current vendor-enforced limit for the standard plan (5 MB).
MAX_PAYLOAD_BYTES = 5_000_000

def validate_upload(payload):
    if MAX_PAYLOAD_BYTES is None:
        raise RuntimeError('upload limit is not configured')
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(
            f'Upload too large. The maximum upload size is 5 MB '
            f'({MAX_PAYLOAD_BYTES:,} bytes). Please choose a smaller file.'
        )
