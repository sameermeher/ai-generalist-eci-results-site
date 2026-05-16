"""Constituencies router — list and detail views."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories import election_repo as repo
from api.schemas.schemas import ConstituencyDetailOut
from db.session import get_async_session

router = APIRouter(prefix="/constituencies", tags=["constituencies"])

_DEFAULT_ELECTION = 1


@router.get("/", response_model=dict)
async def list_constituencies(
    state_code: str,
    election_id: int = _DEFAULT_ELECTION,
    search: Optional[str] = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    state = await repo.get_state_by_code(session, election_id, state_code.upper())
    if not state:
        raise HTTPException(status_code=404, detail=f"State '{state_code}' not found")

    offset = (page - 1) * page_size
    items, total = await repo.get_constituencies_for_state(
        session, state.id, search=search, limit=page_size, offset=offset
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{constituency_id}", response_model=ConstituencyDetailOut)
async def get_constituency_detail(
    constituency_id: int, session: AsyncSession = Depends(get_async_session)
):
    constituency = await repo.get_constituency_detail(session, constituency_id)
    if not constituency:
        raise HTTPException(status_code=404, detail="Constituency not found")

    # Build candidate result list sorted by votes desc
    candidate_results = []
    for cand in sorted(
        constituency.candidates,
        key=lambda c: (c.candidate_result.votes if c.candidate_result else 0),
        reverse=True,
    ):
        cr = cand.candidate_result
        candidate_results.append(
            {
                "candidate": cand,
                "votes": cr.votes if cr else 0,
                "position": cr.position if cr else None,
                "is_winner": cr.is_winner if cr else False,
                "vote_percentage": cr.vote_percentage if cr else None,
            }
        )

    return ConstituencyDetailOut(
        constituency=constituency,
        result=constituency.constituency_result,
        candidates=candidate_results,
    )
