"""ETL pipeline — orchestrates scrape → transform → load phases.

Usage:
    python -m etl.pipeline                     # run full pipeline
    python -m etl.pipeline --phase scrape      # scrape only (stages raw HTML)
    python -m etl.pipeline --phase load        # load from staged HTML (no re-scrape)
    python -m etl.pipeline --state S03         # run only for Assam
    python -m etl.pipeline --no-candidates     # skip slow candidate-detail scraping
"""

import argparse
import logging
from collections import defaultdict


from config import settings
from constants import STATES_BY_CODE
from db.session import sync_engine
from db.models import Base
from etl.loaders.db_loader import DBLoader
from etl.transforms.constituency_transform import transform_candidates, transform_constituencies
from etl.transforms.party_transform import transform_party_rows
from scraper.candidate_scraper import CandidateScraper
from scraper.constituency_scraper import ConstituencyScraper
from scraper.party_scraper import PartyResultScraper

log = logging.getLogger(__name__)


def create_tables() -> None:
    """Create all tables if they don't exist (dev / first-run convenience)."""
    log.info("Ensuring database tables exist...")
    Base.metadata.create_all(sync_engine)
    log.info("Tables ready.")


def run_scrape(state_codes: list[str], scrape_candidates: bool) -> dict:
    """Scrape raw data and return structured dicts."""
    raw_data_dir = settings.raw_data_path
    party_rows_all = []
    constituency_rows_all = []
    candidate_rows_all = []

    states = [STATES_BY_CODE[c] for c in state_codes if c in STATES_BY_CODE]

    with PartyResultScraper(raw_data_dir=raw_data_dir) as ps:
        for state in states:
            log.info("Scraping party results: %s", state.name)
            party_rows_all.extend(ps.scrape_state(state))

    # Build full-name → abbreviation lookup from partywise data so the
    # constituency scraper can resolve abbreviations (ECI constituency pages
    # only show the full party name, not the abbreviation).
    name_to_abbr: dict[str, str] = {
        row.party_name: row.abbreviation for row in party_rows_all
    }

    with ConstituencyScraper(raw_data_dir=raw_data_dir) as cs:
        for state in states:
            log.info("Scraping constituencies: %s", state.name)
            constituency_rows_all.extend(
                cs.scrape_state(state, name_to_abbr=name_to_abbr)
            )

    if scrape_candidates:
        with CandidateScraper(raw_data_dir=raw_data_dir) as cands:
            for row in constituency_rows_all:
                candidate_rows_all.extend(cands.scrape_constituency(row))

    return {
        "party_rows": party_rows_all,
        "constituency_rows": constituency_rows_all,
        "candidate_rows": candidate_rows_all,
    }


def run_load(scraped: dict) -> None:
    """Transform and load all scraped data into the database."""
    party_rows = scraped["party_rows"]
    constituency_rows = scraped["constituency_rows"]
    candidate_rows = scraped["candidate_rows"]

    # Transform
    parties, party_results = transform_party_rows(party_rows)
    constituency_dicts = transform_constituencies(constituency_rows)
    extra_parties, candidate_dicts = transform_candidates(candidate_rows)

    # Merge party lists (avoid duplicates)
    all_party_abbrs = {p["abbreviation"] for p in parties}
    for ep in extra_parties:
        if ep["abbreviation"] not in all_party_abbrs:
            parties.append(ep)

    # Group constituency dicts by state for summary
    constituency_dict_by_state: dict[str, list[dict]] = defaultdict(list)
    for d in constituency_dicts:
        constituency_dict_by_state[d["state_code"]].append(d)

    with DBLoader() as loader:
        election_id = loader.ensure_election()
        state_ids = loader.ensure_states(election_id)
        party_ids = loader.upsert_parties(parties)
        loader.upsert_party_results(party_results, state_ids, party_ids, election_id)
        constituency_ids = loader.upsert_constituencies(constituency_dicts, state_ids)
        candidate_ids = loader.upsert_candidates(candidate_dicts, constituency_ids, party_ids)
        loader.upsert_constituency_results(
            constituency_dicts, constituency_ids, party_ids, candidate_ids
        )
        loader.upsert_state_summaries(state_ids, constituency_dict_by_state)

    log.info("ETL pipeline complete.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="ECI Election Results ETL Pipeline")
    parser.add_argument(
        "--phase",
        choices=["scrape", "load", "all"],
        default="all",
        help="Pipeline phase to run",
    )
    parser.add_argument(
        "--state",
        type=str,
        default=None,
        help="Run only for this state code (e.g. S03). Default: all 5 states.",
    )
    parser.add_argument(
        "--no-candidates",
        action="store_true",
        help="Skip individual candidate detail page scraping.",
    )
    args = parser.parse_args()

    state_codes = [args.state] if args.state else list(STATES_BY_CODE.keys())

    create_tables()

    if args.phase in ("scrape", "all"):
        scraped = run_scrape(state_codes, scrape_candidates=not args.no_candidates)
    else:
        log.warning("--phase=load without prior scrape — attempting from staged files")
        scraped = run_scrape(state_codes, scrape_candidates=not args.no_candidates)

    if args.phase in ("load", "all"):
        run_load(scraped)


if __name__ == "__main__":
    main()
