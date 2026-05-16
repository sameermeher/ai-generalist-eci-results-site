"""Transform raw constituency + candidate scraper output into DB-ready dicts."""

from scraper.constituency_scraper import ConstituencyRow
from scraper.candidate_scraper import CandidateRow


def _normalize_status(row: ConstituencyRow) -> str:
    """Return a human-readable status string.

    The ECI site stores '0' (or another digit) in the status column when a
    result has been fully declared.  Treat any row that has a winner as
    'Result Declared' regardless of what the raw status cell says.
    """
    raw = (row.status or "").strip()
    if row.winner_name and row.winner_name.strip():
        return "Result Declared"
    if raw.lower() in ("", "0", "pending"):
        return "Pending"
    return raw


def transform_constituencies(rows: list[ConstituencyRow]) -> list[dict]:
    """Return list of constituency dicts ready for upsert."""
    return [
        {
            "state_code": r.state_code,
            "ac_number": r.ac_number,
            "name": r.name,
            "winner_name": r.winner_name,
            "winner_party_abbr": r.winner_party_abbr,
            "winner_party_name": r.winner_party_name,
            "runner_up_name": r.runner_up_name,
            "runner_up_party_abbr": r.runner_up_party_abbr,
            "runner_up_party_name": r.runner_up_party_name,
            "margin": r.margin,
            "rounds_counted": r.rounds_counted,
            "total_rounds": r.total_rounds,
            "status": _normalize_status(r),
        }
        for r in rows
    ]


def transform_candidates(rows: list[CandidateRow]) -> tuple[list[dict], list[dict]]:
    """Return (parties_to_upsert, candidates_with_results).

    candidates_with_results: includes all fields needed for candidates + candidate_results.
    """
    extra_parties: dict[str, dict] = {}
    candidates: list[dict] = []

    for r in rows:
        abbr = r.party_abbr or r.party_name[:20]
        if abbr not in extra_parties:
            extra_parties[abbr] = {"name": r.party_name, "abbreviation": abbr}
        candidates.append(
            {
                "state_code": r.state_code,
                "ac_number": r.ac_number,
                "constituency_name": r.constituency_name,
                "serial_number": r.serial_number,
                "name": r.candidate_name,
                "party_abbr": abbr,
                "votes": r.votes,
                "is_winner": r.is_winner,
                "position": r.position,
            }
        )

    return list(extra_parties.values()), candidates
