"""Scrapes statewise{STATE_CODE}{PAGE}.htm — paginated constituency results."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from scraper.base import BaseScraper
from constants import STATES_BY_CODE, StateConfig

logger = logging.getLogger(__name__)


@dataclass
class ConstituencyRow:
    state_code: str
    ac_number: int
    name: str
    winner_name: str
    winner_party_abbr: str
    winner_party_name: str
    runner_up_name: str
    runner_up_party_abbr: str
    runner_up_party_name: str
    margin: int
    rounds_counted: int
    total_rounds: int
    status: str
    detail_url: Optional[str] = None  # constituency-level candidate page if found


class ConstituencyScraper(BaseScraper):
    """Scrape all paginated constituency result pages for a state."""

    def scrape_state(
        self,
        state: StateConfig,
        name_to_abbr: Optional[dict[str, str]] = None,
    ) -> list[ConstituencyRow]:
        all_rows: list[ConstituencyRow] = []
        for page in range(1, state.statewise_pages + 1):
            path = f"statewise{state.code}{page}.htm"
            stage_path = self.raw_data_dir / state.code / f"statewise_p{page}.html"
            try:
                html = self.fetch_and_stage(path, stage_path)
            except Exception as exc:
                # 404 means we've gone past the last page — stop quietly
                if "404" in str(exc) or "Not Found" in str(exc):
                    logger.info(
                        "ConstituencyScraper [%s] page %d returned 404 — stopping.",
                        state.name, page,
                    )
                    break
                raise
            rows = self._parse(html, state.code, name_to_abbr or {})
            all_rows.extend(rows)
            logger.info(
                "ConstituencyScraper [%s] page %d/%d: %d rows",
                state.name,
                page,
                state.statewise_pages,
                len(rows),
            )
        return all_rows

    def scrape_all(
        self, name_to_abbr: Optional[dict[str, str]] = None
    ) -> list[ConstituencyRow]:
        all_rows: list[ConstituencyRow] = []
        for state in STATES_BY_CODE.values():
            all_rows.extend(self.scrape_state(state, name_to_abbr=name_to_abbr))
        return all_rows

    def _parse(
        self,
        html: str,
        state_code: str,
        name_to_abbr: dict[str, str],
    ) -> list[ConstituencyRow]:
        soup = self.parse(html)
        rows: list[ConstituencyRow] = []
        table = soup.find("table")
        if not table:
            logger.warning("No table found in statewise page for %s", state_code)
            return rows

        for tr in table.find_all("tr"):
            # Use recursive=False so nested <td> elements inside party tooltip
            # sub-tables are NOT counted as row columns.
            tds = tr.find_all("td", recursive=False)
            if len(tds) < 8:
                continue

            # Direct-child column layout (9 columns):
            # 0: CONSTITUENCY_NAME
            # 1: AC_NUMBER
            # 2: WINNER_NAME
            # 3: WINNER_PARTY cell (nested <table> — first inner <td> = clean name)
            # 4: RUNNER_UP_NAME
            # 5: RUNNER_UP_PARTY cell (same structure)
            # 6: MARGIN (votes)
            # 7: ROUNDS (e.g. "18/18")
            # 8: STATUS

            try:
                constituency_name = tds[0].get_text(strip=True)
                ac_number = int(tds[1].get_text(strip=True))
            except (ValueError, IndexError):
                continue

            winner_name = tds[2].get_text(strip=True) if len(tds) > 2 else ""
            winner_party_name = self._party_name_from_cell(tds[3]) if len(tds) > 3 else ""
            runner_up_name = tds[4].get_text(strip=True) if len(tds) > 4 else ""
            runner_up_party_name = self._party_name_from_cell(tds[5]) if len(tds) > 5 else ""
            margin_raw = tds[6].get_text(strip=True) if len(tds) > 6 else "0"
            rounds_raw = tds[7].get_text(strip=True) if len(tds) > 7 else "0/0"
            status = tds[8].get_text(strip=True) if len(tds) > 8 else "Pending"

            # Strip "(i)" notation used on ECI site for incumbent indicator
            winner_name = re.sub(r"\s*\(i\)\s*$", "", winner_name, flags=re.IGNORECASE).strip()
            runner_up_name = re.sub(r"\s*\(i\)\s*$", "", runner_up_name, flags=re.IGNORECASE).strip()

            # Resolve party abbreviations via lookup (built from partywise pages)
            winner_party_abbr = name_to_abbr.get(winner_party_name, winner_party_name)
            runner_up_party_abbr = name_to_abbr.get(runner_up_party_name, runner_up_party_name)

            try:
                margin = int(margin_raw.replace(",", ""))
            except ValueError:
                margin = 0

            rounds_counted, total_rounds = self._parse_rounds(rounds_raw)

            # Look for detail page link on winner td
            detail_url: Optional[str] = None
            winner_td = tds[2] if len(tds) > 2 else None
            if winner_td:
                link = winner_td.find("a", href=True)
                if link:
                    detail_url = link["href"]

            rows.append(
                ConstituencyRow(
                    state_code=state_code,
                    ac_number=ac_number,
                    name=constituency_name,
                    winner_name=winner_name,
                    winner_party_abbr=winner_party_abbr,
                    winner_party_name=winner_party_name,
                    runner_up_name=runner_up_name,
                    runner_up_party_abbr=runner_up_party_abbr,
                    runner_up_party_name=runner_up_party_name,
                    margin=margin,
                    rounds_counted=rounds_counted,
                    total_rounds=total_rounds,
                    status=status,
                    detail_url=detail_url,
                )
            )

        return rows

    @staticmethod
    def _party_name_from_cell(td) -> str:
        """Extract the clean party name from a party <td>.

        The ECI party cell contains a nested <table> where the first inner
        <td> holds the plain party name.  If no nested table exists, fall
        back to the cell's own text.
        """
        inner_td = td.find("td")
        if inner_td:
            return inner_td.get_text(strip=True)
        return td.get_text(strip=True)

    @staticmethod
    def _parse_rounds(raw: str) -> tuple[int, int]:
        """Parse '18/18' → (18, 18)."""
        m = re.match(r"(\d+)\s*/\s*(\d+)", raw.strip())
        if m:
            return int(m.group(1)), int(m.group(2))
        try:
            v = int(raw.strip())
            return v, v
        except ValueError:
            return 0, 0
