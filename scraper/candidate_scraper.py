"""Scrapes individual constituency candidate-level detail pages.

The URL pattern for candidate detail pages is not confirmed from static page
inspection alone. This scraper attempts common ECI patterns and follows links
found in constituency list pages (ConstituencyRow.detail_url).
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from scraper.base import BaseScraper
from scraper.constituency_scraper import ConstituencyRow

logger = logging.getLogger(__name__)


@dataclass
class CandidateRow:
    state_code: str
    ac_number: int
    constituency_name: str
    serial_number: Optional[int]
    candidate_name: str
    party_name: str
    party_abbr: str
    votes: int
    is_winner: bool
    position: Optional[int]


class CandidateScraper(BaseScraper):
    """Scrape candidate-level data from constituency detail pages."""

    # Known URL patterns to probe — ordered by likelihood
    _URL_PATTERNS = [
        "ConstituencyWise{state_code}{ac_number:02d}.htm",
        "ConstituencyWise{state_code}{ac_number:03d}.htm",
        "AcResult-{state_code}{ac_number:02d}.htm",
        "AcResult-{state_code}{ac_number:03d}.htm",
    ]

    def scrape_constituency(
        self, row: ConstituencyRow
    ) -> list[CandidateRow]:
        """Try all URL patterns to fetch candidate detail for one constituency."""
        state_code = row.state_code
        ac = row.ac_number

        # 1. Try URL discovered from constituency list page links
        if row.detail_url:
            candidate_rows = self._try_url(row.detail_url, state_code, ac, row.name)
            if candidate_rows:
                return candidate_rows

        # 2. Try known URL patterns
        for pattern in self._URL_PATTERNS:
            path = pattern.format(state_code=state_code, ac_number=ac)
            candidate_rows = self._try_url(path, state_code, ac, row.name)
            if candidate_rows:
                return candidate_rows

        logger.warning(
            "No candidate detail page found for %s AC-%d", state_code, ac
        )
        return []

    def _try_url(
        self, path: str, state_code: str, ac_number: int, constituency_name: str
    ) -> list[CandidateRow]:
        stage_path = (
            self.raw_data_dir / state_code / "candidates" / f"ac_{ac_number:03d}.html"
        )
        try:
            html = self.fetch_and_stage(path, stage_path)
            rows = self._parse(html, state_code, ac_number, constituency_name)
            if rows:
                logger.info(
                    "CandidateScraper [%s AC-%d]: %d candidates via %s",
                    state_code, ac_number, len(rows), path,
                )
                return rows
        except Exception as exc:
            logger.debug("URL %s failed: %s", path, exc)
            # Remove zero-byte staged file if fetch failed
            if stage_path.exists() and stage_path.stat().st_size == 0:
                stage_path.unlink(missing_ok=True)
        return []

    def _parse(
        self, html: str, state_code: str, ac_number: int, constituency_name: str
    ) -> list[CandidateRow]:
        soup = self.parse(html)
        rows: list[CandidateRow] = []

        table = soup.find("table")
        if not table:
            return rows

        position = 0
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            cells = [td.get_text(strip=True) for td in tds]

            # Typical columns: Serial No | Candidate Name | Party | Votes | ...
            serial_num: Optional[int] = None
            candidate_name = ""
            party_raw = ""
            votes = 0

            try:
                serial_num = int(cells[0])
            except ValueError:
                pass

            if len(cells) >= 4:
                candidate_name = cells[1] if serial_num is not None else cells[0]
                party_raw = cells[2] if serial_num is not None else cells[1]
                votes_raw = cells[3] if serial_num is not None else cells[2]
                try:
                    votes = int(votes_raw.replace(",", ""))
                except ValueError:
                    continue
            else:
                continue

            if not candidate_name:
                continue

            party_name, party_abbr = self._extract_party(party_raw)
            position += 1

            rows.append(
                CandidateRow(
                    state_code=state_code,
                    ac_number=ac_number,
                    constituency_name=constituency_name,
                    serial_number=serial_num,
                    candidate_name=candidate_name.strip(),
                    party_name=party_name,
                    party_abbr=party_abbr,
                    votes=votes,
                    is_winner=(position == 1),
                    position=position,
                )
            )

        # Sort descending by votes; winner = most votes
        rows.sort(key=lambda r: r.votes, reverse=True)
        for i, r in enumerate(rows, start=1):
            r.position = i
            r.is_winner = i == 1

        return rows

    @staticmethod
    def _extract_party(raw: str) -> tuple[str, str]:
        cleaned = re.sub(r"\s+i\s*$", "", raw, flags=re.IGNORECASE).strip()
        if " - " in cleaned:
            parts = cleaned.rsplit(" - ", 1)
            return parts[0].strip(), parts[1].strip()
        return cleaned, cleaned
