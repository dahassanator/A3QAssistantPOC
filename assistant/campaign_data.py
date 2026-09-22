"""Mock structured data for the single fictional campaign this POC serves.

In production this would be the platform's real database, queried by real
backend functions - never embedded into a vector store, since the model
needs exact figures (sums, filters), not semantic retrieval. This module
stands in for that database: plain Python records, queried by plain
functions. The orchestrator exposes those functions to Claude as tools
(see `assistant/orchestrator.py`), the same integration shape a real
platform API would slot into later.

The filing deadlines below are the real dates from
`knowledge_base/sos_guidance/municipal_election_fcpa_calendar_2026.md` for
the August 25, 2026 municipal election cycle, so a question that combines
this campaign's own schedule with the cited statute stays internally
consistent. One contribution (from a federal candidate's committee) is
deliberately set above the $1,000 cap in Ala. Code § 17-5-15.1, so that
statute/data combined questions have a real violation to catch instead of
only a clean bill of health.
"""

from dataclasses import asdict, dataclass


@dataclass
class Contribution:
    donor: str
    donor_type: str  # "individual", "pac", or "federal_candidate_committee"
    amount: float
    date: str  # YYYY-MM-DD


@dataclass
class Expenditure:
    payee: str
    category: str
    amount: float
    date: str  # YYYY-MM-DD


@dataclass
class CanvassingEntry:
    date: str  # YYYY-MM-DD
    volunteer: str
    contacts_attempted: int
    contacts_reached: int
    supporters_identified: int


@dataclass
class FilingDeadline:
    date: str  # YYYY-MM-DD
    description: str
    citation: str | None = None


CONTRIBUTIONS = [
    Contribution("Maria Chen", "individual", 500.00, "2025-09-10"),
    Contribution("James O'Donnell", "individual", 250.00, "2025-09-15"),
    Contribution("Cedar Bend Rotary Club PAC", "pac", 750.00, "2025-10-01"),
    Contribution("Pete Wallace for Congress Committee", "federal_candidate_committee", 1200.00, "2025-10-05"),
    Contribution("Sarah Whitfield", "individual", 100.00, "2025-11-02"),
    Contribution("Tom Baxter", "individual", 1000.00, "2026-01-15"),
    Contribution("Linda Park", "individual", 300.00, "2026-03-20"),
    Contribution("Cedar Bend Rotary Club PAC", "pac", 250.00, "2026-06-10"),
    Contribution("Maria Chen", "individual", 200.00, "2026-07-01"),
]

EXPENDITURES = [
    Expenditure("Print Shop AL", "Printing", 450.00, "2025-09-20"),
    Expenditure("FB Ads Co", "Advertising", 600.00, "2025-10-10"),
    Expenditure("Campaign HQ Rent", "Office", 800.00, "2025-11-05"),
    Expenditure("Yard Signs Inc", "Advertising", 325.00, "2026-02-14"),
    Expenditure("Volunteer Cookout Catering", "Events", 150.00, "2026-04-01"),
    Expenditure("Local Radio Station", "Advertising", 700.00, "2026-06-15"),
    Expenditure("Campaign HQ Rent", "Office", 800.00, "2026-07-30"),
]

CANVASSING_LOG = [
    CanvassingEntry("2025-10-04", "Priya Patel", 40, 28, 15),
    CanvassingEntry("2025-10-11", "Priya Patel", 35, 22, 10),
    CanvassingEntry("2025-11-01", "Marcus Lee", 50, 30, 18),
    CanvassingEntry("2026-03-14", "Priya Patel", 45, 33, 20),
    CanvassingEntry("2026-06-20", "Marcus Lee", 60, 40, 25),
    CanvassingEntry("2026-07-25", "Ana Torres", 30, 20, 12),
]

FILING_DEADLINES = [
    FilingDeadline("2025-09-03", "August monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2025-10-02", "September monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2025-11-04", "October monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2025-12-02", "November monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2026-01-05", "December monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2026-02-03", "January monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2026-03-03", "February monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2026-04-02", "March monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2026-05-04", "April monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2026-06-02", "May monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2026-07-02", "June monthly report due", "§ 17-5-8(a)(1)"),
    FilingDeadline("2026-08-03", "1st weekly report due", "§ 17-5-8(a)(2)"),
    FilingDeadline("2026-08-10", "2nd weekly report due", "§ 17-5-8(a)(2)"),
    FilingDeadline("2026-08-17", "3rd weekly report due", "§ 17-5-8(a)(2)"),
    FilingDeadline("2026-08-24", "4th weekly report due", "§ 17-5-8(a)(2)"),
    FilingDeadline("2026-08-25", "Municipal Election Day", None),
    FilingDeadline("2026-12-23", "Last day to raise funds to retire campaign debt", "§ 17-5-7(b)(3)"),
    FilingDeadline("2026-12-31", "Close books for the 2026 Annual Report", "§ 17-5-8(b)"),
    FilingDeadline("2027-01-31", "2026 Annual Report due", "§ 17-5-8(b)"),
]


def get_contributions(donor: str | None = None) -> dict:
    matches = [
        c for c in CONTRIBUTIONS if donor is None or donor.lower() in c.donor.lower()
    ]
    return {
        "total": round(sum(c.amount for c in matches), 2),
        "count": len(matches),
        "contributions": [asdict(c) for c in matches],
    }


def get_expenditures(category: str | None = None) -> dict:
    matches = [
        e
        for e in EXPENDITURES
        if category is None or category.lower() == e.category.lower()
    ]
    return {
        "total": round(sum(e.amount for e in matches), 2),
        "count": len(matches),
        "expenditures": [asdict(e) for e in matches],
    }


def get_canvassing_log(volunteer: str | None = None) -> dict:
    matches = [
        c
        for c in CANVASSING_LOG
        if volunteer is None or volunteer.lower() in c.volunteer.lower()
    ]
    return {
        "total_contacts_attempted": sum(c.contacts_attempted for c in matches),
        "total_contacts_reached": sum(c.contacts_reached for c in matches),
        "total_supporters_identified": sum(c.supporters_identified for c in matches),
        "entries": [asdict(c) for c in matches],
    }


def get_filing_deadlines(on_or_after: str | None = None) -> dict:
    matches = [
        d for d in FILING_DEADLINES if on_or_after is None or d.date >= on_or_after
    ]
    return {"deadlines": [asdict(d) for d in sorted(matches, key=lambda d: d.date)]}
