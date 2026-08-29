"""Packaged, curated US ETF research universe."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UniverseMember(BaseModel):
    """One explicitly selected symbol and its research purpose."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=12)
    role: str = Field(min_length=1, max_length=300)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class ResearchUniverse(BaseModel):
    """Versioned symbol membership, independent from mutable market observations."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    universe_id: str = Field(min_length=1, max_length=100)
    universe_version: str = Field(min_length=1, max_length=100)
    members: list[UniverseMember] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_symbols(self) -> ResearchUniverse:
        symbols = self.symbols
        if len(symbols) != len(set(symbols)):
            raise ValueError("Research universe symbols must be unique.")
        return self

    @property
    def symbols(self) -> list[str]:
        return [member.symbol for member in self.members]


def load_research_universe(path: Path | None = None) -> ResearchUniverse:
    """Load the packaged baseline or a caller-supplied versioned universe JSON."""

    if path is None:
        payload = (
            files("etf_advisor.research").joinpath("universe_v1.json").read_text(encoding="utf-8")
        )
    else:
        payload = path.read_text(encoding="utf-8")
    return ResearchUniverse.model_validate(json.loads(payload))
