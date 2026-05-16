"""ECI state constants — codes, names, AC counts, and page counts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StateConfig:
    code: str          # e.g. "S03"
    name: str          # e.g. "Assam"
    total_ac: int      # total assembly constituencies
    statewise_pages: int  # number of paginated constituency pages


STATES: list[StateConfig] = [
    StateConfig(code="S03", name="Assam",       total_ac=126, statewise_pages=10),
    StateConfig(code="S11", name="Kerala",      total_ac=140, statewise_pages=10),
    StateConfig(code="S22", name="Tamil Nadu",  total_ac=234, statewise_pages=15),
    StateConfig(code="S25", name="West Bengal", total_ac=294, statewise_pages=20),
    StateConfig(code="U07", name="Puducherry",  total_ac=30,  statewise_pages=5),
]

STATES_BY_CODE: dict[str, StateConfig] = {s.code: s for s in STATES}

ELECTION_NAME = "General Election to Assembly Constituencies: May 2026"
ELECTION_YEAR = 2026
ECI_BASE_URL = "https://results.eci.gov.in/ResultAcGenMay2026"
