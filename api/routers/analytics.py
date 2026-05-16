"""Analytics router — margins, summaries, cross-state insights."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories import election_repo as repo
from api.schemas.schemas import MarginOut
from db.session import get_async_session

router = APIRouter(prefix="/analytics", tags=["analytics"])

_DEFAULT_ELECTION = 1


@router.get("/top-margins", response_model=list[MarginOut])
async def top_margins(
    election_id: int = _DEFAULT_ELECTION,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Top N constituencies by winning margin (largest wins)."""
    rows = await repo.get_top_margins(session, election_id, limit=limit, bottom=False)
    return [_to_margin_out(r) for r in rows]


@router.get("/closest-contests", response_model=list[MarginOut])
async def closest_contests(
    election_id: int = _DEFAULT_ELECTION,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Top N constituencies by smallest winning margin (tightest races)."""
    rows = await repo.get_top_margins(session, election_id, limit=limit, bottom=True)
    return [_to_margin_out(r) for r in rows]


@router.get("/state-summaries", response_model=list[dict])
async def all_state_summaries(
    election_id: int = _DEFAULT_ELECTION,
    session: AsyncSession = Depends(get_async_session),
):
    """Summary of declared vs total ACs for all states."""
    states = await repo.get_states(session, election_id)
    out = []
    for state in states:
        summary = await repo.get_state_summary(session, state.id)
        out.append(
            {
                "state_code": state.code,
                "state_name": state.name,
                "total_ac": state.total_ac,
                "ac_declared": summary.ac_declared if summary else 0,
                "last_updated": summary.last_updated.isoformat() if summary and summary.last_updated else None,
            }
        )
    return out


def _to_margin_out(r) -> MarginOut:
    return MarginOut(
        state_name=r.constituency.state.name if r.constituency and r.constituency.state else "",
        constituency_name=r.constituency.name if r.constituency else "",
        winner_name=r.winner_candidate.name if r.winner_candidate else "",
        winner_party=r.winner_party.abbreviation if r.winner_party else "",
        margin=r.margin or 0,
        status=r.status,
    )
