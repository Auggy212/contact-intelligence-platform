from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def billing_period(dt: datetime | None = None) -> str:
    """Returns a YYYY-MM string for the billing period of the given datetime."""
    d = dt or now_utc()
    return d.strftime("%Y-%m")


def is_future(dt: datetime) -> bool:
    return dt > now_utc()
