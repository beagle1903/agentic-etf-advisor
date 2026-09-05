"""Replaceable boundary for nondeterministic audit identifier generation."""

from collections.abc import Callable
from uuid import uuid4

type IdentifierFactory = Callable[[], str]


def random_identifier() -> str:
    """Generate an opaque UUID at an explicit application boundary."""
    return str(uuid4())
