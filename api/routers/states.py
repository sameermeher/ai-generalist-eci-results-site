"""States router — summaries and party breakdowns per state."""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories import election_repo as repo
from api.schemas.schemas import StateDetailOut, StateOut
from db.session import get_async_session

router = APIRouter(prefix="/states", tags=["states"])

_DEFAULT_ELECTION = 1  # override via query param once multi-election is needed


@router.get("/", response_model=list[StateOut])
async def list_states(
    election_id: int = _DEFAULT_ELECTION,
    session: AsyncSession = Depends(get_async_session),
):
    return await repo.get_states(session, election_id)


@router.get("/{state_code}", response_model=StateDetailOut)
async def get_state_detail(
    state_code: str,
    election_id: int = _DEFAULT_ELECTION,
    session: AsyncSession = Depends(get_async_session),
):
    state = await repo.get_state_by_code(session, election_id, state_code.upper())
    if not state:
        raise HTTPException(status_code=404, detail=f"State '{state_code}' not found")

    summary = await repo.get_state_summary(session, state.id)
    party_results = await repo.get_party_results_for_state(session, state.id, election_id)

    return StateDetailOut(
        state=state,
        summary=summary,
        party_results=party_results,
    )
