import re

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def is_valid_uuid(value: str) -> bool:
    import uuid
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """Strips path components and keeps only safe characters."""
    import os
    name = os.path.basename(filename)
    return re.sub(r"[^\w.\-]", "_", name)
