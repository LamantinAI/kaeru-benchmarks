# Current vendor-confirmed standard-plan limit, in bytes (5 MB).
MAX_PAYLOAD_BYTES = 5_000_000

def validate_upload(payload):
    if MAX_PAYLOAD_BYTES is None:
        raise RuntimeError('upload limit is not configured')
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(
            f'Upload is too large. The maximum size is 5 MB '
            f'({MAX_PAYLOAD_BYTES:,} bytes). Please choose a smaller file.'
        )
