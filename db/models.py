"""SQLAlchemy ORM models for the election results database."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Core lookup tables
# ---------------------------------------------------------------------------


class Election(Base):
    """Represents a single election event (e.g. AC General May 2026)."""

    __tablename__ = "elections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    election_type: Mapped[str] = mapped_column(String(50), nullable=False, default="AC_GENERAL")
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    election_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # relationships
    states: Mapped[list["State"]] = relationship("State", back_populates="election")
    party_results: Mapped[list["PartyResult"]] = relationship(
        "PartyResult", back_populates="election"
    )

    __table_args__ = (UniqueConstraint("name", "year", name="uq_election_name_year"),)


class State(Base):
    """A state/UT participating in an election."""

    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    election_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("elections.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_ac: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # relationships
    election: Mapped["Election"] = relationship("Election", back_populates="states")
    constituencies: Mapped[list["Constituency"]] = relationship(
        "Constituency", back_populates="state"
    )
    party_results: Mapped[list["PartyResult"]] = relationship(
        "PartyResult", back_populates="state"
    )
    state_summary: Mapped[Optional["StateSummary"]] = relationship(
        "StateSummary", back_populates="state", uselist=False
    )

    __table_args__ = (UniqueConstraint("election_id", "code", name="uq_state_election_code"),)


class Party(Base):
    """Global party registry — deduped across all states/elections."""

    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # relationships
    candidates: Mapped[list["Candidate"]] = relationship("Candidate", back_populates="party")
    party_results: Mapped[list["PartyResult"]] = relationship(
        "PartyResult", back_populates="party"
    )

    __table_args__ = (UniqueConstraint("abbreviation", name="uq_party_abbreviation"),)


class Constituency(Base):
    """An assembly constituency (AC) within a state."""

    __tablename__ = "constituencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("states.id", ondelete="CASCADE"), nullable=False
    )
    ac_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    constituency_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="GENERAL"
    )  # GENERAL / SC / ST

    # relationships
    state: Mapped["State"] = relationship("State", back_populates="constituencies")
    candidates: Mapped[list["Candidate"]] = relationship(
        "Candidate", back_populates="constituency"
    )
    constituency_result: Mapped[Optional["ConstituencyResult"]] = relationship(
        "ConstituencyResult", back_populates="constituency", uselist=False
    )

    __table_args__ = (
        UniqueConstraint("state_id", "ac_number", name="uq_constituency_state_ac"),
        Index("ix_constituency_state_id", "state_id"),
    )


# ---------------------------------------------------------------------------
# Candidate & result tables
# ---------------------------------------------------------------------------


class Candidate(Base):
    """A candidate contesting in a specific constituency."""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    constituency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("constituencies.id", ondelete="CASCADE"), nullable=False
    )
    party_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("parties.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    serial_number: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # relationships
    constituency: Mapped["Constituency"] = relationship(
        "Constituency", back_populates="candidates"
    )
    party: Mapped[Optional["Party"]] = relationship("Party", back_populates="candidates")
    candidate_result: Mapped[Optional["CandidateResult"]] = relationship(
        "CandidateResult", back_populates="candidate", uselist=False
    )

    __table_args__ = (
        UniqueConstraint(
            "constituency_id", "name", "serial_number", name="uq_candidate_constituency_name"
        ),
        Index("ix_candidate_constituency_id", "constituency_id"),
        Index("ix_candidate_party_id", "party_id"),
    )


class CandidateResult(Base):
    """Vote totals and ranking for a single candidate in a constituency."""

    __tablename__ = "candidate_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    votes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    position: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    is_winner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vote_percentage: Mapped[Optional[float]] = mapped_column(nullable=True)

    # relationships
    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="candidate_result"
    )

    __table_args__ = (Index("ix_candidate_result_candidate_id", "candidate_id"),)


class ConstituencyResult(Base):
    """Aggregated result per constituency: winner, margin, rounds, status."""

    __tablename__ = "constituency_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    constituency_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("constituencies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    winner_candidate_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True
    )
    winner_party_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("parties.id", ondelete="SET NULL"), nullable=True
    )
    runner_up_candidate_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True
    )
    runner_up_party_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("parties.id", ondelete="SET NULL"), nullable=True
    )
    margin: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    rounds_counted: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    total_rounds: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    total_votes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # relationships
    constituency: Mapped["Constituency"] = relationship(
        "Constituency", back_populates="constituency_result"
    )
    winner_candidate: Mapped[Optional["Candidate"]] = relationship(
        "Candidate", foreign_keys=[winner_candidate_id]
    )
    winner_party: Mapped[Optional["Party"]] = relationship(
        "Party", foreign_keys=[winner_party_id]
    )
    runner_up_candidate: Mapped[Optional["Candidate"]] = relationship(
        "Candidate", foreign_keys=[runner_up_candidate_id]
    )

    __table_args__ = (Index("ix_constituency_result_constituency_id", "constituency_id"),)


class PartyResult(Base):
    """Party-level aggregated result per state per election."""

    __tablename__ = "party_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    election_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("elections.id", ondelete="CASCADE"), nullable=False
    )
    state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("states.id", ondelete="CASCADE"), nullable=False
    )
    party_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False
    )
    won: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    leading: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total_seats: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    vote_share: Mapped[Optional[float]] = mapped_column(nullable=True)

    # relationships
    election: Mapped["Election"] = relationship("Election", back_populates="party_results")
    state: Mapped["State"] = relationship("State", back_populates="party_results")
    party: Mapped["Party"] = relationship("Party", back_populates="party_results")

    __table_args__ = (
        UniqueConstraint(
            "election_id", "state_id", "party_id", name="uq_party_result_election_state_party"
        ),
        Index("ix_party_result_state_election", "state_id", "election_id"),
        Index("ix_party_result_party_election", "party_id", "election_id"),
    )


class StateSummary(Base):
    """High-level summary per state — seats declared vs total, timestamp."""

    __tablename__ = "state_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("states.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    total_ac: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    ac_declared: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # relationships
    state: Mapped["State"] = relationship("State", back_populates="state_summary")
