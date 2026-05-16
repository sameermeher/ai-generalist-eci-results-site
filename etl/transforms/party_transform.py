"""Transform raw party scraper output into DB-ready dicts."""

from scraper.party_scraper import PartyResultRow


def transform_party_rows(
    rows: list[PartyResultRow],
) -> tuple[list[dict], list[dict]]:
    """Return (parties_to_upsert, party_results_to_upsert).

    parties_to_upsert: [{name, abbreviation}]
    party_results_to_upsert: [{state_code, abbreviation, won, leading, total_seats}]
    """
    parties: dict[str, dict] = {}  # keyed by abbreviation
    party_results: list[dict] = []

    for row in rows:
        abbr = row.abbreviation or row.party_name[:20]
        if abbr not in parties:
            parties[abbr] = {"name": row.party_name, "abbreviation": abbr}
        party_results.append(
            {
                "state_code": row.state_code,
                "abbreviation": abbr,
                "won": row.won,
                "leading": row.leading,
                "total_seats": row.total,
            }
        )

    return list(parties.values()), party_results
