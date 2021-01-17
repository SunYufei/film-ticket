from datetime import datetime, timedelta, timezone


def utc_now():
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    utc8 = timezone(timedelta(hours=8))
    return now.astimezone(utc8)
