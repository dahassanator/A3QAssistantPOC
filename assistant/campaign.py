"""The single fictional campaign this POC serves.

This is a placeholder stub for ticket #2 (walking skeleton). Full mock
campaign data (contributions, expenditures, canvassing log, filing
deadlines) is built in ticket #5.
"""


def get_default_campaign_context() -> dict:
    return {
        "state": "Alabama",
        "office": "Mayoral",
        "campaign_name": "Placeholder Campaign",
    }
