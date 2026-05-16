"""Parties router — cross-state party-wise results."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories import election_repo as repo
from api.schemas.schemas import CrossStatePartyOut
from db.session import get_async_session

router = APIRouter(prefix="/parties", tags=["parties"])

_DEFAULT_ELECTION = 1


@router.get("/", response_model=list[CrossStatePartyOut])
async def get_all_party_results(
    election_id: int = _DEFAULT_ELECTION,
    session: AsyncSession = Depends(get_async_session),
):
    """Return cross-state party results aggregated by party."""
    rows = await repo.get_all_party_results(session, election_id)

    # Aggregate: {abbreviation: {state_code: seats, ...}}
    agg: dict[str, dict] = {}
    for pr in rows:
        abbr = pr.party.abbreviation
        if abbr not in agg:
            agg[abbr] = {
                "abbreviation": abbr,
                "party_name": pr.party.name,
                "results": {},
                "grand_total": 0,
            }
        agg[abbr]["results"][pr.state.code] = pr.total_seats
        agg[abbr]["grand_total"] += pr.total_seats

    return sorted(agg.values(), key=lambda x: x["grand_total"], reverse=True)
