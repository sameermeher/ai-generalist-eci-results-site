"""Unit tests for scrapers using mocked HTML."""


from scraper.party_scraper import PartyResultScraper
from scraper.constituency_scraper import ConstituencyScraper


# ---------------------------------------------------------------------------
# Fixtures — minimal HTML that mirrors ECI page structure
# ---------------------------------------------------------------------------

PARTY_TABLE_HTML = """
<html><body>
<table>
  <tr><td>Bharatiya Janata Party - BJP</td><td>82</td><td>0</td><td>82</td></tr>
  <tr><td>Indian National Congress - INC</td><td>19</td><td>0</td><td>19</td></tr>
  <tr><td>Bodoland Peoples Front - BOPF</td><td>10</td><td>0</td><td>10</td></tr>
</table>
</body></html>
"""

CONSTITUENCY_TABLE_HTML = """
<html><body>
<table>
  <tr>
    <td>ABHAYAPURI</td><td>16</td>
    <td>BHUPEN ROY</td><td>Bharatiya Janata Party i</td>
    <td>PRADIP SARKAR</td><td>Indian National Congress i</td>
    <td>58926</td><td>18/18</td><td>Result Declared</td>
  </tr>
  <tr>
    <td>ALGAPUR-KATLICHERRA</td><td>122</td>
    <td>ZUBAIR ANAM MAZUMDER</td><td>Indian National Congress i</td>
    <td>ZAKIR HUSSAIN LASKAR</td><td>Asom Gana Parishad i</td>
    <td>105448</td><td>26/26</td><td>Result Declared</td>
  </tr>
</table>
</body></html>
"""


# ---------------------------------------------------------------------------
# Party scraper tests
# ---------------------------------------------------------------------------

class TestPartyResultScraper:
    def test_parse_returns_correct_row_count(self):
        scraper = PartyResultScraper.__new__(PartyResultScraper)
        rows = scraper._parse(PARTY_TABLE_HTML, "S03")
        assert len(rows) == 3

    def test_parse_bjp_won(self):
        scraper = PartyResultScraper.__new__(PartyResultScraper)
        rows = scraper._parse(PARTY_TABLE_HTML, "S03")
        bjp = next(r for r in rows if r.abbreviation == "BJP")
        assert bjp.won == 82
        assert bjp.total == 82

    def test_split_name_abbr_with_dash(self):
        name, abbr = PartyResultScraper._split_name_abbr("Bharatiya Janata Party - BJP")
        assert name == "Bharatiya Janata Party"
        assert abbr == "BJP"

    def test_split_name_abbr_no_dash(self):
        name, abbr = PartyResultScraper._split_name_abbr("Independent")
        assert name == "Independent"
        assert abbr == "Independent"


# ---------------------------------------------------------------------------
# Constituency scraper tests
# ---------------------------------------------------------------------------

class TestConstituencyScraper:
    def test_parse_returns_correct_row_count(self):
        scraper = ConstituencyScraper.__new__(ConstituencyScraper)
        rows = scraper._parse(CONSTITUENCY_TABLE_HTML, "S03")
        assert len(rows) == 2

    def test_parse_first_row_values(self):
        scraper = ConstituencyScraper.__new__(ConstituencyScraper)
        rows = scraper._parse(CONSTITUENCY_TABLE_HTML, "S03")
        r = rows[0]
        assert r.name == "ABHAYAPURI"
        assert r.ac_number == 16
        assert r.winner_name == "BHUPEN ROY"
        assert r.margin == 58926
        assert r.rounds_counted == 18
        assert r.total_rounds == 18
        assert r.status == "Result Declared"

    def test_winner_party_abbr_extracted(self):
        scraper = ConstituencyScraper.__new__(ConstituencyScraper)
        rows = scraper._parse(CONSTITUENCY_TABLE_HTML, "S03")
        assert rows[0].winner_party_abbr == "Bharatiya Janata Party"  # no " - ABBR" present

    def test_parse_rounds(self):
        assert ConstituencyScraper._parse_rounds("18/18") == (18, 18)
        assert ConstituencyScraper._parse_rounds("26/26") == (26, 26)
        assert ConstituencyScraper._parse_rounds("0/0") == (0, 0)
        assert ConstituencyScraper._parse_rounds("") == (0, 0)
