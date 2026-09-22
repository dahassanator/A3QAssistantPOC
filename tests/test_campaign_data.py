from assistant import campaign_data


def test_get_contributions_totals_all_by_default():
    result = campaign_data.get_contributions()

    assert result["count"] == len(campaign_data.CONTRIBUTIONS)
    assert result["total"] == round(
        sum(c.amount for c in campaign_data.CONTRIBUTIONS), 2
    )


def test_get_contributions_filters_by_donor_case_insensitively():
    result = campaign_data.get_contributions(donor="maria chen")

    assert result["count"] == 2
    assert result["total"] == 700.00
    assert all(c["donor"] == "Maria Chen" for c in result["contributions"])


def test_get_contributions_flags_the_over_cap_federal_committee_donor():
    result = campaign_data.get_contributions(donor="Pete Wallace")

    assert result["total"] == 1200.00
    assert result["contributions"][0]["donor_type"] == "federal_candidate_committee"


def test_get_expenditures_filters_by_category():
    result = campaign_data.get_expenditures(category="advertising")

    assert result["count"] == 3
    assert result["total"] == 1625.00
    assert all(e["category"] == "Advertising" for e in result["expenditures"])


def test_get_canvassing_log_aggregates_totals_for_one_volunteer():
    result = campaign_data.get_canvassing_log(volunteer="Priya Patel")

    assert result["total_contacts_attempted"] == 120
    assert result["total_contacts_reached"] == 83
    assert result["total_supporters_identified"] == 45


def test_get_filing_deadlines_filters_and_sorts_by_date():
    result = campaign_data.get_filing_deadlines(on_or_after="2026-08-01")

    dates = [d["date"] for d in result["deadlines"]]
    assert dates == sorted(dates)
    assert dates[0] == "2026-08-03"
    assert "2026-08-25" in dates
    assert "2025-09-03" not in dates
