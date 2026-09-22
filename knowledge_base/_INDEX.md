---
title: "Knowledge Base Index"
source: "Assembled for the A3Q Assistant Alabama FCPA compliance chatbot"
description: "What is in this knowledge base, where each file came from, and what is still missing"
converted: 2026-09-18
---

# Knowledge Base Index

92 source documents plus this index. Every file has a YAML header at the top with its title, source, description and (where known) the URL it came from, so the chatbot can cite where an answer came from.

## Secretary of State guidance

| File | What it covers | As-of |
|---|---|---|
| sos_guidance/candidate_filing_guidelines_2026.md | How candidates qualify, appoint a principal campaign committee, and file | 2026 |
| sos_guidance/pac_filing_guidelines_2026.md | The PAC version: registration, reports, amendments, dissolution, prohibited transfers | Version 1-21-2026 |
| sos_guidance/2026_fcpa_filing_calendar.md | Every deadline in the 2026 state election cycle, as a date/activity table | Revised 6.4.2025 |
| sos_guidance/municipal_election_fcpa_calendar_2026.md | Deadlines for the Aug 25, 2026 municipal election | Revised 9/18/2025 |
| sos_guidance/legislative_blackout_period_2026.md | When legislative and statewide candidates may not accept contributions | 2026 session |
| sos_guidance/campaign_advertisement_guidelines_2024.md | Disclaimers, exceptions, penalties, electioneering disclosure | 2024 |
| sos_guidance/online_filing_system_guidelines_2024.md | How to register and file in the online system | 2024 |
| sos_guidance/alabama_fcpa_system_faq.md | Short FAQ for the filing portal | current |
| sos_guidance/fcpa_user_guide_tyler_technologies_v1.md | The full 48-page portal manual from Tyler Technologies | v1.0 |
| sos_guidance/sos_minimum_qualifications_for_public_office.md | Age, residency, citizenship, terms and term limits by office | current |
| sos_guidance/independent_candidate_ballot_access_2026.md | Petition route to the ballot, signature counts, deadlines | Revised 11/14/2025 |
| sos_guidance/independent_candidate_petition_form.md | The blank petition form and its required wording | Revised 12.2.2019 |
| sos_guidance/ballot_access_petitions_rule_820-2-4-.05.md | The administrative rule on petition format (OCR of a scanned PDF) | 2018 |

## The law itself

`fcpa_statute/` holds all 32 sections of the Fair Campaign Practices Act, Code of Alabama 1975, Title 17, Chapter 5, one file per section, verbatim, each with its History note. The guidance documents above cite these sections constantly, so the chatbot can now quote the actual law instead of only a guide's description of it.

The sections campaign staff ask about most: 17-5-2 (definitions), 17-5-4 (principal campaign committee, 5-day rule), 17-5-4.1 (municipal $1,000 exemption), 17-5-7 (what funds may be spent on, the session blackout), 17-5-8 (the report schedule), 17-5-8.1 (the $20,000 contribution report), 17-5-12 (ad disclaimers), 17-5-15 (PAC-to-PAC ban), 17-5-16.1 (AI deepfakes), 17-5-19 and 17-5-19.1 (criminal and civil penalties).

## Attorney General opinions

`ag_opinions/` holds the five opinions the guidance documents cite, in full. These are the authorities behind rules the guides state without explaining:

| File | Answers |
|---|---|
| AGO_94-00228 | Why the blackout starts at 12:01 a.m., and that an unwanted contribution returned to the donor is not a reportable accepted contribution |
| AGO_94-00227 | That "paid for by" satisfies the disclaimer, and that a complete address means street or PO box, city and state; also who can be prosecuted |
| AGO_95-00218 | Why McIntyre v. Ohio did not wipe out Alabama's identification requirement |
| AGO_2000-088 | Why a sitting legislator running for county office is not covered by the blackout |
| AGO_2002-040 | Why a sitting legislator running for federal office is not covered by the blackout |

These are scans and the text comes from their OCR layer. They also use the pre-2006 section numbers (§ 17-22A-x), which were renumbered to § 17-5-x in 2006; each file carries a note mapping the old numbers to the current ones.

## Alabama Ethics Commission

`ethics_commission/` covers the Statement of Economic Interests, which candidates must file with the Ethics Commission rather than the Secretary of State, plus a summary of which campaign finance questions the Ethics Commission rather than the Secretary of State answers.

Two things to watch here. The salary threshold for appointed officials and employees is now $106,000, effective January 1, 2026; older Ethics Commission documents still on their website say $50,000 or $75,000, and the old SEI instructions PDF was deliberately left out of this knowledge base for that reason. And the Ethics Commission and the Secretary of State state the independent candidate's SEI deadline differently; the discrepancy is flagged inside `sei_candidate_filing_requirements.md`.

## The Ethics Law

`ethics_law/` holds all 38 sections of the Code of Ethics for Public Officials, Employees, Etc., Code of Alabama 1975, Title 36, Chapter 25, one file per section, verbatim.

This is the FCPA's sibling statute, and a candidate is subject to both. The FCPA governs campaign money; the Ethics Law governs conflicts of interest, gifts, lobbying and the Statement of Economic Interests. Several things campaign staff will ask about live only here:

- § 36-25-14 and § 36-25-15 are the SEI requirements, including the rule that a candidate who does not file is removed from the ballot.
- § 36-25-4(b) is the statutory basis for the Ethics Commission's authority over the FCPA: approving its forms, issuing FCPA advisory opinions, and reviewing civil penalties under § 17-5-19.2.
- § 36-25-6 says contributions may not be converted to personal use, a one-sentence rule that sits outside the FCPA entirely.
- § 36-25-12 bars a candidate for Commissioner of Agriculture and Industries from accepting contributions from businesses the department regulates. Nothing in Title 17 says this.
- § 36-25-5.2 requires candidates and their spouses to report government employment or contracts to the Commission within 30 days.
- § 36-25-1(34)b.1 is the seam between the two statutes: a contribution properly reported under the FCPA is not a "thing of value" for gift purposes.

Note on the salary threshold: § 36-25-14 states $75,000, but the same subsection directs the Commission to adjust it each January for inflation. That is how the current figure became $106,000. The $75,000 in the statute is a base, not the number to quote a filer; the file carries a warning saying so.

Several sections still cite the pre-2006 numbering for the FCPA (§ 17-22A-x). Those files carry notes mapping the old numbers to the current § 17-5-x.

## Notes on fidelity

The PDFs were converted with text extraction. Three needed extra handling: the ballot access rule was a scan with no text layer and was read with OCR, so check it against the original if something reads oddly; the campaign advertisement guidelines are a two-column landscape layout and were extracted column by column so the reading order is right; the two calendars were rebuilt as tables so each deadline stays attached to its date.

The web sources (the qualifications page and all 70 statute sections) were retrieved through a fetching tool that passes pages through a small summarizing model. The statute text was requested verbatim and spot-checked, but for anything a decision turns on, confirm against the source URL in the file header.

Three files were first built from that web route and have since been rebuilt or verified against the actual PDF: the PAC filing guidelines (verified word for word), the independent candidate ballot access guide (rebuilt from the PDF), and the 2026 state filing calendar (the PDF turned out to be byte-identical to the copy already converted). The municipal calendar and the petition form are still web-sourced.

## Still missing

- The Secretary of State's administrative rules for elections beyond rule 820-2-4-.05.
- The blank SEI form. Only the instructions and the filing rules are here, not the form itself.
