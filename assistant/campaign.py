"""The single fictional campaign this POC serves.

Its records (contributions, expenditures, canvassing log, filing
deadlines) live in `assistant/campaign_data.py`.
"""


def get_default_campaign_context() -> dict:
    return {
        "state": "Alabama",
        "office": "Mayor",
        "candidate_name": "Danielle Ruiz",
        "campaign_name": "Ruiz for Mayor",
        "town": "Cedar Bend, Alabama",
        "election_date": "2026-08-25",
        "as_of_date": "2026-07-15",
    }
