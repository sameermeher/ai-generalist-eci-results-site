"""Idempotent database loader — upserts all scraped data into Neon DB."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from constants import ELECTION_NAME, ELECTION_YEAR, STATES_BY_CODE
from db.models import (
    Candidate,
    CandidateResult,
    Constituency,
    ConstituencyResult,
    Election,
    Party,
    PartyResult,
    State,
    StateSummary,
)
from db.session import get_sync_session

logger = logging.getLogger(__name__)


class DBLoader:
    """Loads transformed data into PostgreSQL using idempotent upserts."""

    def __init__(self, session: Session | None = None) -> None:
        self._owned = session is None
        self.session: Session = session or get_sync_session()

    def close(self) -> None:
        if self._owned:
            self.session.close()

    def __enter__(self) -> "DBLoader":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Top-level entry points
    # ------------------------------------------------------------------

    def ensure_election(self) -> int:
        """Create or fetch the election record. Returns election_id."""
        stmt = select(Election).where(
            Election.name == ELECTION_NAME, Election.year == ELECTION_YEAR
        )
        election = self.session.execute(stmt).scalar_one_or_none()
        if not election:
            election = Election(
                name=ELECTION_NAME,
                election_type="AC_GENERAL",
                year=ELECTION_YEAR,
            )
            self.session.add(election)
            self.session.flush()
            logger.info("Created election: %s", ELECTION_NAME)
        return election.id

    def ensure_states(self, election_id: int) -> dict[str, int]:
        """Create or fetch state records. Returns {state_code: state_id}."""
        result: dict[str, int] = {}
        for cfg in STATES_BY_CODE.values():
            stmt = select(State).where(
                State.election_id == election_id, State.code == cfg.code
            )
            state = self.session.execute(stmt).scalar_one_or_none()
            if not state:
                state = State(
                    election_id=election_id,
                    code=cfg.code,
                    name=cfg.name,
                    total_ac=cfg.total_ac,
                )
                self.session.add(state)
                self.session.flush()
                logger.info("Created state: %s (%s)", cfg.name, cfg.code)
            result[cfg.code] = state.id
        self.session.commit()
        return result

    def upsert_parties(self, party_dicts: list[dict]) -> dict[str, int]:
        """Upsert parties. Returns {abbreviation: party_id}."""
        if not party_dicts:
            return {}
        stmt = (
            pg_insert(Party)
            .values(party_dicts)
            .on_conflict_do_update(
                index_elements=["abbreviation"],
                set_={"name": pg_insert(Party).excluded.name},
            )
            .returning(Party.id, Party.abbreviation)
        )
        rows = self.session.execute(stmt).fetchall()
        self.session.commit()
        result = {row.abbreviation: row.id for row in rows}
        logger.info("Upserted %d parties", len(result))
        return result

    def upsert_party_results(
        self,
        party_result_dicts: list[dict],
        state_ids: dict[str, int],
        party_ids: dict[str, int],
        election_id: int,
    ) -> None:
        """Upsert party_results rows."""
        rows = []
        for d in party_result_dicts:
            state_id = state_ids.get(d["state_code"])
            party_id = party_ids.get(d["abbreviation"])
            if not state_id or not party_id:
                logger.warning("Skipping party result — missing state/party: %s", d)
                continue
            rows.append(
                {
                    "election_id": election_id,
                    "state_id": state_id,
                    "party_id": party_id,
                    "won": d["won"],
                    "leading": d["leading"],
                    "total_seats": d["total_seats"],
                }
            )
        if not rows:
            return
        stmt = (
            pg_insert(PartyResult)
            .values(rows)
            .on_conflict_do_update(
                index_elements=["election_id", "state_id", "party_id"],
                set_={
                    "won": pg_insert(PartyResult).excluded.won,
                    "leading": pg_insert(PartyResult).excluded.leading,
                    "total_seats": pg_insert(PartyResult).excluded.total_seats,
                },
            )
        )
        self.session.execute(stmt)
        self.session.commit()
        logger.info("Upserted %d party_results rows", len(rows))

    def upsert_constituencies(
        self, constituency_dicts: list[dict], state_ids: dict[str, int]
    ) -> dict[tuple[str, int], int]:
        """Upsert constituencies. Returns {(state_code, ac_number): constituency_id}."""
        rows = []
        meta: list[tuple[str, int]] = []  # (state_code, ac_number) in same order
        for d in constituency_dicts:
            state_id = state_ids.get(d["state_code"])
            if not state_id:
                continue
            rows.append(
                {
                    "state_id": state_id,
                    "ac_number": d["ac_number"],
                    "name": d["name"],
                    "constituency_type": d.get("constituency_type", "GENERAL"),
                }
            )
            meta.append((d["state_code"], d["ac_number"]))
        if not rows:
            return {}

        stmt = (
            pg_insert(Constituency)
            .values(rows)
            .on_conflict_do_update(
                index_elements=["state_id", "ac_number"],
                set_={"name": pg_insert(Constituency).excluded.name},
            )
            .returning(Constituency.id, Constituency.state_id, Constituency.ac_number)
        )
        db_rows = self.session.execute(stmt).fetchall()
        self.session.commit()

        # Build a (state_id → state_code) reverse map for the return dict
        state_code_by_id = {v: k for k, v in state_ids.items()}
        result = {
            (state_code_by_id[r.state_id], r.ac_number): r.id for r in db_rows
        }
        logger.info("Upserted %d constituencies", len(result))
        return result

    def upsert_constituency_results(
        self,
        constituency_dicts: list[dict],
        constituency_ids: dict[tuple[str, int], int],
        party_ids: dict[str, int],
        candidate_ids: dict[tuple[int, str], int],  # (constituency_id, name) → id
    ) -> None:
        """Upsert constituency_results (winner, margin, rounds, status)."""
        rows = []
        for d in constituency_dicts:
            key = (d["state_code"], d["ac_number"])
            c_id = constituency_ids.get(key)
            if not c_id:
                continue
            winner_party_id = party_ids.get(d["winner_party_abbr"])
            runner_party_id = party_ids.get(d["runner_up_party_abbr"])
            winner_cand_id = candidate_ids.get((c_id, d["winner_name"]))
            runner_cand_id = candidate_ids.get((c_id, d["runner_up_name"]))
            rows.append(
                {
                    "constituency_id": c_id,
                    "winner_candidate_id": winner_cand_id,
                    "winner_party_id": winner_party_id,
                    "runner_up_candidate_id": runner_cand_id,
                    "runner_up_party_id": runner_party_id,
                    "margin": d["margin"],
                    "rounds_counted": d["rounds_counted"],
                    "total_rounds": d["total_rounds"],
                    "status": d["status"],
                    "updated_at": datetime.utcnow(),
                }
            )
        if not rows:
            return
        stmt = (
            pg_insert(ConstituencyResult)
            .values(rows)
            .on_conflict_do_update(
                index_elements=["constituency_id"],
                set_={
                    "winner_candidate_id": pg_insert(ConstituencyResult).excluded.winner_candidate_id,
                    "winner_party_id": pg_insert(ConstituencyResult).excluded.winner_party_id,
                    "runner_up_candidate_id": pg_insert(ConstituencyResult).excluded.runner_up_candidate_id,
                    "runner_up_party_id": pg_insert(ConstituencyResult).excluded.runner_up_party_id,
                    "margin": pg_insert(ConstituencyResult).excluded.margin,
                    "rounds_counted": pg_insert(ConstituencyResult).excluded.rounds_counted,
                    "total_rounds": pg_insert(ConstituencyResult).excluded.total_rounds,
                    "status": pg_insert(ConstituencyResult).excluded.status,
                    "updated_at": pg_insert(ConstituencyResult).excluded.updated_at,
                },
            )
        )
        self.session.execute(stmt)
        self.session.commit()
        logger.info("Upserted %d constituency_results rows", len(rows))

    def upsert_candidates(
        self,
        candidate_dicts: list[dict],
        constituency_ids: dict[tuple[str, int], int],
        party_ids: dict[str, int],
    ) -> dict[tuple[int, str], int]:
        """Upsert candidates + candidate_results. Returns {(constituency_id, name): id}."""
        if not candidate_dicts:
            return {}

        # --- Candidates ---
        cand_rows = []
        for d in candidate_dicts:
            key = (d["state_code"], d["ac_number"])
            c_id = constituency_ids.get(key)
            if not c_id:
                continue
            cand_rows.append(
                {
                    "constituency_id": c_id,
                    "party_id": party_ids.get(d["party_abbr"]),
                    "name": d["name"],
                    "serial_number": d.get("serial_number"),
                }
            )

        if not cand_rows:
            return {}

        stmt = (
            pg_insert(Candidate)
            .values(cand_rows)
            .on_conflict_do_update(
                index_elements=["constituency_id", "name", "serial_number"],
                set_={"party_id": pg_insert(Candidate).excluded.party_id},
            )
            .returning(Candidate.id, Candidate.constituency_id, Candidate.name)
        )
        db_rows = self.session.execute(stmt).fetchall()
        self.session.commit()

        # Build lookup
        cand_id_map: dict[tuple[int, str], int] = {
            (r.constituency_id, r.name): r.id for r in db_rows
        }

        # --- CandidateResults ---
        cr_rows = []
        for d in candidate_dicts:
            key = (d["state_code"], d["ac_number"])
            c_id = constituency_ids.get(key)
            if not c_id:
                continue
            cand_id = cand_id_map.get((c_id, d["name"]))
            if not cand_id:
                continue
            cr_rows.append(
                {
                    "candidate_id": cand_id,
                    "votes": d["votes"],
                    "position": d.get("position"),
                    "is_winner": d.get("is_winner", False),
                }
            )

        if cr_rows:
            stmt2 = (
                pg_insert(CandidateResult)
                .values(cr_rows)
                .on_conflict_do_update(
                    index_elements=["candidate_id"],
                    set_={
                        "votes": pg_insert(CandidateResult).excluded.votes,
                        "position": pg_insert(CandidateResult).excluded.position,
                        "is_winner": pg_insert(CandidateResult).excluded.is_winner,
                    },
                )
            )
            self.session.execute(stmt2)
            self.session.commit()

        logger.info("Upserted %d candidates", len(cand_id_map))
        return cand_id_map

    def upsert_state_summaries(
        self,
        state_ids: dict[str, int],
        constituency_dict_by_state: dict[str, list[dict]],
    ) -> None:
        """Compute and upsert state_summary from constituency data.

        ac_declared is derived from the actual count of ConstituencyResult rows
        already committed to the DB for each state, so it is always accurate
        regardless of what the scraped status text contains.
        """
        from sqlalchemy import text as sa_text

        rows = []
        for state_code, state_id in state_ids.items():
            cfg = STATES_BY_CODE.get(state_code)
            if not cfg:
                continue
            # Count constituencies that have a result row in the DB
            ac_declared = self.session.execute(
                sa_text(
                    "SELECT COUNT(*) FROM constituency_results cr "
                    "JOIN constituencies c ON c.id = cr.constituency_id "
                    "WHERE c.state_id = :sid"
                ),
                {"sid": state_id},
            ).scalar() or 0
            rows.append(
                {
                    "state_id": state_id,
                    "total_ac": cfg.total_ac,
                    "ac_declared": ac_declared,
                    "last_updated": datetime.utcnow(),
                }
            )
        if not rows:
            return
        stmt = (
            pg_insert(StateSummary)
            .values(rows)
            .on_conflict_do_update(
                index_elements=["state_id"],
                set_={
                    "total_ac": pg_insert(StateSummary).excluded.total_ac,
                    "ac_declared": pg_insert(StateSummary).excluded.ac_declared,
                    "last_updated": pg_insert(StateSummary).excluded.last_updated,
                },
            )
        )
        self.session.execute(stmt)
        self.session.commit()
        logger.info("Upserted state summaries for %d states", len(state_ids))
