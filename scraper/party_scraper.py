"""Scrapes partywiseresult-{STATE_CODE}.htm — full party list per state."""

import logging
from dataclasses import dataclass

from scraper.base import BaseScraper
from constants import STATES_BY_CODE, StateConfig

logger = logging.getLogger(__name__)


@dataclass
class PartyResultRow:
    state_code: str
    party_name: str
    abbreviation: str
    won: int
    leading: int
    total: int


class PartyResultScraper(BaseScraper):
    """Scrape full party-wise results for a given state."""

    def scrape_state(self, state: StateConfig) -> list[PartyResultRow]:
        path = f"partywiseresult-{state.code}.htm"
        stage_path = self.raw_data_dir / state.code / "partywiseresult.html"
        html = self.fetch_and_stage(path, stage_path)
        rows = self._parse(html, state.code)
        logger.info(
            "PartyResultScraper [%s]: %d parties", state.name, len(rows)
        )
        return rows

    def scrape_all(self) -> list[PartyResultRow]:
        all_rows: list[PartyResultRow] = []
        for state in STATES_BY_CODE.values():
            all_rows.extend(self.scrape_state(state))
        return all_rows

    def _parse(self, html: str, state_code: str) -> list[PartyResultRow]:
        soup = self.parse(html)
        rows: list[PartyResultRow] = []

        table = soup.find("table")
        if not table:
            logger.warning("No table found for state %s", state_code)
            return rows

        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            cells = [td.get_text(strip=True) for td in tds]

            # Expected: [full_party_name - ABBR, won_count, leading_count, total_count]
            # OR:       [full_party_name - ABBR | won | leading | total]
            raw_name = cells[0]
            try:
                won = int(cells[1])
                leading = int(cells[2])
                total = int(cells[3])
            except (ValueError, IndexError):
                continue

            # Extract abbreviation from "Full Name - ABBR"
            name, abbr = self._split_name_abbr(raw_name)
            rows.append(
                PartyResultRow(
                    state_code=state_code,
                    party_name=name,
                    abbreviation=abbr,
                    won=won,
                    leading=leading,
                    total=total,
                )
            )

        return rows

    @staticmethod
    def _split_name_abbr(raw: str) -> tuple[str, str]:
        """Split 'Bharatiya Janata Party - BJP' into ('Bharatiya Janata Party', 'BJP')."""
        if " - " in raw:
            parts = raw.rsplit(" - ", 1)
            return parts[0].strip(), parts[1].strip()
        return raw.strip(), raw.strip()
