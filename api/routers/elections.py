"""Elections router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories import election_repo as repo
from api.schemas.schemas import ElectionOut
from db.session import get_async_session

router = APIRouter(prefix="/elections", tags=["elections"])


@router.get("/", response_model=list[ElectionOut])
async def list_elections(session: AsyncSession = Depends(get_async_session)):
    return await repo.get_elections(session)


@router.get("/{election_id}", response_model=ElectionOut)
async def get_election(
    election_id: int, session: AsyncSession = Depends(get_async_session)
):
    election = await repo.get_election_by_id(session, election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    return election
