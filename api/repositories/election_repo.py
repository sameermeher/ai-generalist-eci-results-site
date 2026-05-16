"""Repository layer — raw SQLAlchemy queries, no business logic."""

from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import (
    Candidate,
    Constituency,
    ConstituencyResult,
    Election,
    PartyResult,
    State,
    StateSummary,
)


# ---------------------------------------------------------------------------
# Election
# ---------------------------------------------------------------------------


async def get_elections(session: AsyncSession) -> list[Election]:
    result = await session.execute(select(Election).order_by(desc(Election.year)))
    return list(result.scalars().all())


async def get_election_by_id(session: AsyncSession, election_id: int) -> Optional[Election]:
    result = await session.execute(
        select(Election).where(Election.id == election_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


async def get_states(session: AsyncSession, election_id: int) -> list[State]:
    result = await session.execute(
        select(State)
        .where(State.election_id == election_id)
        .order_by(State.name)
    )
    return list(result.scalars().all())


async def get_state_by_code(
    session: AsyncSession, election_id: int, code: str
) -> Optional[State]:
    result = await session.execute(
        select(State).where(State.election_id == election_id, State.code == code)
    )
    return result.scalar_one_or_none()


async def get_state_summary(session: AsyncSession, state_id: int) -> Optional[StateSummary]:
    result = await session.execute(
        select(StateSummary)
        .where(StateSummary.state_id == state_id)
        .options(selectinload(StateSummary.state))
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Party results
# ---------------------------------------------------------------------------


async def get_party_results_for_state(
    session: AsyncSession, state_id: int, election_id: int
) -> list[PartyResult]:
    result = await session.execute(
        select(PartyResult)
        .where(
            PartyResult.state_id == state_id,
            PartyResult.election_id == election_id,
        )
        .options(selectinload(PartyResult.party))
        .order_by(desc(PartyResult.total_seats))
    )
    return list(result.scalars().all())


async def get_all_party_results(
    session: AsyncSession, election_id: int
) -> list[PartyResult]:
    result = await session.execute(
        select(PartyResult)
        .where(PartyResult.election_id == election_id)
        .options(
            selectinload(PartyResult.party),
            selectinload(PartyResult.state),
        )
        .order_by(desc(PartyResult.total_seats))
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Constituencies
# ---------------------------------------------------------------------------


async def get_constituencies_for_state(
    session: AsyncSession,
    state_id: int,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ConstituencyResult], int]:
    base_q = (
        select(ConstituencyResult)
        .join(ConstituencyResult.constituency)
        .where(Constituency.state_id == state_id)
        .options(
            selectinload(ConstituencyResult.constituency),
            selectinload(ConstituencyResult.winner_candidate).selectinload(Candidate.party),
            selectinload(ConstituencyResult.winner_party),
            selectinload(ConstituencyResult.runner_up_candidate).selectinload(Candidate.party),
        )
    )
    if search:
        base_q = base_q.where(Constituency.name.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await session.execute(count_q)).scalar_one()

    result = await session.execute(
        base_q.order_by(Constituency.ac_number).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total


async def get_constituency_detail(
    session: AsyncSession, constituency_id: int
) -> Optional[Constituency]:
    result = await session.execute(
        select(Constituency)
        .where(Constituency.id == constituency_id)
        .options(
            selectinload(Constituency.constituency_result).selectinload(
                ConstituencyResult.winner_candidate
            ).selectinload(Candidate.party),
            selectinload(Constituency.constituency_result).selectinload(
                ConstituencyResult.winner_party
            ),
            selectinload(Constituency.constituency_result).selectinload(
                ConstituencyResult.runner_up_candidate
            ).selectinload(Candidate.party),
            selectinload(Constituency.candidates).selectinload(Candidate.party),
            selectinload(Constituency.candidates).selectinload(Candidate.candidate_result),
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


async def get_top_margins(
    session: AsyncSession, election_id: int, limit: int = 20, bottom: bool = False
) -> list[ConstituencyResult]:
    order = ConstituencyResult.margin if bottom else desc(ConstituencyResult.margin)
    result = await session.execute(
        select(ConstituencyResult)
        .join(ConstituencyResult.constituency)
        .join(Constituency.state)
        .where(
            State.election_id == election_id,
            ConstituencyResult.margin.is_not(None),
        )
        .options(
            selectinload(ConstituencyResult.constituency).selectinload(Constituency.state),
            selectinload(ConstituencyResult.winner_candidate),
            selectinload(ConstituencyResult.winner_party),
        )
        .order_by(order)
        .limit(limit)
    )
    return list(result.scalars().all())
