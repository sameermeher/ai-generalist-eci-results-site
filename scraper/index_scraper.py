"""Scrapes index.htm — state-level top-5 party overview."""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


@dataclass
class PartyTally:
    abbreviation: str
    won: int = 0
    leading: int = 0


@dataclass
class StateOverview:
    state_name: str
    state_code: str
    total_ac: int
    ac_reported: int
    top_parties: list[PartyTally] = field(default_factory=list)
    party_wise_url: Optional[str] = None
    statewise_url: Optional[str] = None


class IndexScraper(BaseScraper):
    """Scrape index.htm and extract per-state party tallies."""

    def scrape(self) -> list[StateOverview]:
        stage_path = self.raw_data_dir / "index.html"
        html = self.fetch_and_stage("index.htm", stage_path)
        return self._parse(html)

    def _parse(self, html: str) -> list[StateOverview]:
        soup = self.parse(html)
        results: list[StateOverview] = []

        # Each state is in a section containing "Status of Top Five Parties"
        # and an AC count like "Assembly Constituencies123* /126"
        sections = soup.find_all("div", class_=lambda c: c and "status" in c.lower())
        if not sections:
            # Fallback: locate by heading text pattern
            sections = self._find_state_sections(soup)

        for section in sections:
            overview = self._parse_section(section)
            if overview:
                results.append(overview)

        logger.info("IndexScraper: found %d states", len(results))
        return results

    def _find_state_sections(self, soup) -> list:
        """Find sections that contain party tally tables."""
        tables = soup.find_all("table")
        sections = []
        for tbl in tables:
            header_text = " ".join(
                th.get_text(strip=True) for th in tbl.find_all("th")
            ).lower()
            if "parties" in header_text and "leading" in header_text and "won" in header_text:
                # The enclosing container holds state info
                sections.append(tbl.find_parent())
        return sections

    def _parse_section(self, section) -> Optional[StateOverview]:
        text = section.get_text(" ", strip=True)

        # State code via Details link: partywiseresult-S03.htm
        details_link = section.find("a", href=re.compile(r"partywiseresult-(\w+)\.htm"))
        if not details_link:
            return None
        href = details_link["href"]
        code_match = re.search(r"partywiseresult-(\w+)\.htm", href)
        if not code_match:
            return None
        state_code = code_match.group(1)

        # Statewise link
        statewise_link = section.find("a", href=re.compile(r"statewise\w+\.htm"))
        statewise_url = statewise_link["href"] if statewise_link else None

        # Total AC from text like "Assembly Constituencies126* /126"
        ac_match = re.search(r"Assembly\s+Constituencies\s*(\d+)\*?\s*/\s*(\d+)", text)
        ac_reported = int(ac_match.group(1)) if ac_match else 0
        total_ac = int(ac_match.group(2)) if ac_match else 0

        # State name — look for h4/h5/h6 heading
        state_name = ""
        for tag in ("h4", "h5", "h6", "h3", "h2"):
            heading = section.find(tag)
            if heading:
                heading_text = heading.get_text(strip=True)
                if heading_text and len(heading_text) > 2:
                    state_name = heading_text
                    break

        # Party rows from table
        top_parties: list[PartyTally] = []
        tbl = section.find("table")
        if tbl:
            for row in tbl.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) >= 3:
                    abbr = cells[0]
                    try:
                        leading = int(cells[1])
                        won = int(cells[2])
                        top_parties.append(PartyTally(abbreviation=abbr, won=won, leading=leading))
                    except ValueError:
                        continue

        return StateOverview(
            state_name=state_name,
            state_code=state_code,
            total_ac=total_ac,
            ac_reported=ac_reported,
            top_parties=top_parties,
            party_wise_url=href,
            statewise_url=statewise_url,
        )
