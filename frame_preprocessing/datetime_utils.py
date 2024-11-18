from datetime import datetime

import pytz


class DatetimeUtils:
    """
    """

    @staticmethod
    def is_in_daylight_savings(timestamp_s: int, timezone_str: str) -> bool:
        """
        """
        date_time = datetime.fromtimestamp(timestamp_s)
        timezone = pytz.timezone(timezone_str)
        try:
            timezone_aware_date = timezone.localize(date_time, is_dst=None)
            return timezone_aware_date.tzinfo._dst.seconds != 0
        except pytz.exceptions.AmbiguousTimeError:
            # This happens in the exact hour when daylight savings switch occurs
            # We will consider these frames as not in daylight savings
            return False