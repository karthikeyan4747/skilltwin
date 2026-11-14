"""Screenshot validation: allowlisted formats, size cap, verified decode, re-encoded in memory."""

import base64
import binascii
import io

from PIL import Image, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG"}
MAX_DIMENSION = 1024


class InvalidImageError(ValueError):
    """The upload is not an allowed, decodable image within limits."""


def sanitize_screenshot(data_b64: str, max_bytes: int) -> str:
    """Return a re-encoded JPEG (base64) of at most MAX_DIMENSION px; never written to disk."""
    try:
        raw = base64.b64decode(data_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidImageError("not base64") from exc
    if len(raw) > max_bytes:
        raise InvalidImageError("too large")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise InvalidImageError("format not allowed")
            probe.verify()
        with Image.open(io.BytesIO(raw)) as image:
            rgb = image.convert("RGB")
            rgb.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
            out = io.BytesIO()
            rgb.save(out, format="JPEG", quality=80)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidImageError("could not decode") from exc
    return base64.b64encode(out.getvalue()).decode("ascii")
