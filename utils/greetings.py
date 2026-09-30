"""Time-of-day greetings for Beamers Farm's Nigeria-based business context."""

from datetime import datetime
from zoneinfo import ZoneInfo

NIGERIA_TZ = ZoneInfo("Africa/Lagos")


def time_of_day_greeting(now=None):
    """Return a greeting using West Africa Time, not the visitor's device clock."""
    current = (now or datetime.now(NIGERIA_TZ)).astimezone(NIGERIA_TZ)
    if current.hour < 12:
        return "Good morning"
    if current.hour < 18:
        return "Good afternoon"
    return "Good evening"
