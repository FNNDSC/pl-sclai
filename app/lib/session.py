from datetime import datetime
import uuid


def sessionID_generate(title: str = "") -> str:
    """
    Generate a unique session ID in the format YYYYMMDDHHmmSSmmm-<uuid>[-<title>].

    :param title: Optional title to include in the session ID.
    :return: A session ID string.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
    unique_id = uuid.uuid4().hex
    session_id = f"{timestamp}-{unique_id}"
    if title:
        session_id += f"-{title}"
    return session_id
