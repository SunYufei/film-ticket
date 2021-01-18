from datetime import datetime, timedelta, timezone

utc8 = timezone(timedelta(hours=8))


def utc_now():
    return datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(utc8)


def log(log_type: str, content):
    print(f'[{log_type}]\t{content}')
