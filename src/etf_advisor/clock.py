"""Replaceable clock boundary for nondeterministic wall-clock reads."""

from collections.abc import Callable
from datetime import UTC, datetime

type Clock = Callable[[], datetime]


def system_utc_now() -> datetime:
    """Read the system clock in UTC at an explicit application boundary."""

    return datetime.now(UTC)
