"""Pydantic v2 response schemas (DTOs) for all API endpoints."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Base / shared
# ---------------------------------------------------------------------------


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(OrmBase):
    total: int
    page: int
    page_size: int
    items: list


# ---------------------------------------------------------------------------
# Election
# ---------------------------------------------------------------------------


class ElectionOut(OrmBase):
    id: int
    name: str
    election_type: str
    year: int
    election_date: Optional[date]


# ---------------------------------------------------------------------------
# State / Party
# ---------------------------------------------------------------------------


class PartyOut(OrmBase):
    id: int
    name: str
    abbreviation: str


class PartyResultOut(OrmBase):
    party: PartyOut
    won: int
    leading: int
    total_seats: int
    vote_share: Optional[float]


class StateOut(OrmBase):
    id: int
    code: str
    name: str
    total_ac: int


class StateSummaryOut(OrmBase):
    state: StateOut
    total_ac: int
    ac_declared: int
    last_updated: Optional[datetime]


class StateDetailOut(OrmBase):
    state: StateOut
    summary: Optional[StateSummaryOut]
    party_results: list[PartyResultOut]


# ---------------------------------------------------------------------------
# Constituency
# ---------------------------------------------------------------------------


class CandidateBriefOut(OrmBase):
    id: int
    name: str
    party: Optional[PartyOut]


class ConstituencyOut(OrmBase):
    id: int
    ac_number: int
    name: str
    constituency_type: str


class ConstituencyResultOut(OrmBase):
    constituency: ConstituencyOut
    winner: Optional[CandidateBriefOut]
    winner_party: Optional[PartyOut]
    runner_up: Optional[CandidateBriefOut]
    margin: Optional[int]
    rounds_counted: Optional[int]
    total_rounds: Optional[int]
    status: str
    total_votes: Optional[int]


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


class CandidateResultOut(OrmBase):
    candidate: CandidateBriefOut
    votes: int
    position: Optional[int]
    is_winner: bool
    vote_percentage: Optional[float]


class ConstituencyDetailOut(OrmBase):
    constituency: ConstituencyOut
    result: Optional[ConstituencyResultOut]
    candidates: list[CandidateResultOut]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class CrossStatePartyOut(BaseModel):
    abbreviation: str
    party_name: str
    results: dict[str, int]   # {state_code: total_seats}
    grand_total: int


class MarginOut(BaseModel):
    state_name: str
    constituency_name: str
    winner_name: str
    winner_party: str
    margin: int
    status: str
