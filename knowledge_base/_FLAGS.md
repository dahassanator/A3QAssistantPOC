---
title: "Knowledge Base Flags"
source: "Compiled during the build of this knowledge base"
description: "Every file with a known caveat, what the caveat is, and what it could cause the chatbot to get wrong"
converted: 2026-09-22
---

# Knowledge Base Flags

93 files total. This lists only the ones with something worth knowing. Anything not listed here was converted cleanly from a source PDF or from verbatim statutory text and has no known issue.

Flags are grouped by what kind of problem they'd cause if nobody knew about them.

---

## 1. Accuracy risks

These could make the chatbot give a confidently wrong answer.

### `ethics_law/36-25-14_filing_of_statement_of_economic_interests.md`

The statute says the Statement of Economic Interests salary threshold is $75,000. The number actually in force is $106,000, effective January 1, 2026.

Both are correct in their own way, which is what makes it dangerous. The $75,000 is the base figure written into the law in 2012, and the same subsection directs the Ethics Commission to raise it every January for inflation. Years of adjustments got it to $106,000.

What this means: the statutory number is never the number to quote a filer. If someone asks "do I have to file?", the answer depends on the Commission's current notice, not on the statute text. The file carries a warning at the bottom saying this, but the $75,000 still appears twice in the body, so retrieval can surface it.

Related files that carry the right number: `ethics_commission/sei_who_must_file_2026.md`.

### `sos_guidance/independent_candidate_ballot_access_2026.md`

This Secretary of State guide says an independent candidate must file the Statement of Economic Interests within 5 days of submitting the ballot access petition.

Ala. Code § 36-25-15(a) says the deadline is not more than 5 days after the date of the first primary election.

These are not the same rule. They often land close together, because the petition is due by primary day anyway, but they can diverge. The statute controls, and the Ethics Commission is the agency that administers the filing.

Files involved: `ethics_law/36-25-15_candidates_statement_of_economic_interests.md` has the controlling text, and `ethics_commission/sei_candidate_filing_requirements.md` describes the conflict.

### `sos_guidance/sos_minimum_qualifications_for_public_office.md`

This came from a web page, not a PDF, and it was retrieved through a tool that passes pages through a summarizing model. It was never verified against an authoritative copy.

The table looks complete, all offices and all 28 footnotes, but nothing confirms that every age, residency period and term limit survived intact. Spot-check a few rows against the live page before anyone relies on this for a qualification decision.

Source: https://www.sos.alabama.gov/alabama-votes/candidates/qualifications-public-office

### `sos_guidance/ballot_access_petitions_rule_820-2-4-.05.md`

The source PDF is a scan with no text layer, so this was read with OCR (software that reads text off an image). OCR makes mistakes, especially on numbers and stamped text.

The rule's substance came through clearly, but this is the only file in the knowledge base where individual characters could be wrong. Worth one read against the original.

### `fcpa_statute/17-5-13_printed_material_must_bear_identification.md`

This one is not a conversion error. The statute itself contains a stale cross-reference.

§ 17-5-13 points to "Section 17-5-2(a)(5)" for the definition of identification. That definition actually sits at § 17-5-2(a)(8) today. The Legislature renumbered the definitions and never fixed the pointer.

The text is reproduced exactly as printed, with a note explaining the mismatch. If the chatbot follows the cross-reference literally it will land on the wrong definition.

---

## 2. Citations that will fail to resolve

The chatbot will see a section number, search for it, and find nothing.

### All five files in `ag_opinions/`, plus `ethics_law/36-25-5`, `36-25-13`, and `36-25-19`

These use the pre-2006 numbering for the Fair Campaign Practices Act, which was Title 17 Chapter 22A before it was renumbered to Chapter 5 in 2006.

So an opinion analyzing the legislative blackout discusses § 17-22A-7, while the statute file in this knowledge base is named for § 17-5-7. Same provision, different name.

The mapping is simple: **17-22A-x means 17-5-x.** Every affected file has a note saying so, but it is worth teaching the chatbot this as a general rule rather than relying on per-file notes, because this numbering shows up across Alabama sources generally.

### `fcpa_statute/17-5-18_repealed.md` and `ethics_law/36-25-1.2_repealed.md`

Both sections were repealed and have no active text. They are kept in the knowledge base on purpose, so that if someone cites them the chatbot can say "that was repealed, here is what replaced it" instead of finding nothing and going silent.

§ 17-5-18 was repealed in 2013. Penalties now live in § 17-5-19 and § 17-5-19.1.
§ 36-25-1.2 was repealed in 2019 and replaced by § 36-25-1.3.

### `ag_opinions/AGO_2002-040_legislator_running_for_federal_office_during_session.md`

Numbered 2002-040 but dated October 24, 2001. Alabama's opinion numbering does not always match the year of issuance. If the chatbot cites a date it should use the one printed on the opinion, not the one implied by the number.

---

## 3. Provenance and freshness

Nothing here is wrong as far as I know. These are files where it is worth knowing where the text came from or how old it is.

### `sos_guidance/municipal_election_fcpa_calendar_2026.md`

Two things. First, the PDF's own title block says "FCPA Filing Calendar / 2025 Municipal Elections", but the election it covers is the Municipal General Election on August 25, 2026. The file is named 2026 and carries a note explaining the mismatch.

Second, this is still web-sourced. Unlike the state calendar, it was never verified against the actual PDF.

### `sos_guidance/independent_candidate_petition_form.md`

Web-sourced, never verified against the PDF. It is also a blank form rather than a guidance document, and it is dated Revised 12.2.2019, making it the oldest item in the knowledge base.

### `sos_guidance/campaign_advertisement_guidelines_2024.md` and `sos_guidance/online_filing_system_guidelines_2024.md`

Both are the 2024 editions. The Secretary of State has not published 2026 versions as far as I could find, so these are current in the sense that they are the latest available, but they were written for a previous election cycle.

The ad guidelines PDF is also a two-column landscape layout. A plain text extraction scrambles the reading order, so this one was extracted column by column to keep the sentences in the right sequence.

### `sos_guidance/2026_fcpa_filing_calendar.md`

Marked Revised 6.4.2025. This one was verified: the PDF Hassan uploaded turned out to be byte-identical to the copy already converted, so there is no newer revision hiding somewhere.

### `ethics_commission/ethics_commission_role_in_fcpa.md`

This is the only file in the knowledge base that is not a source document. I wrote it, pulling together material from § 17-5-19.1, § 17-5-19.2, § 36-25-4(b), the PAC Filing Guidelines and AG Opinion 2000-088.

It exists because staff routinely assume the Secretary of State handles everything about campaign finance, and that is not right. But it is a synthesis, so if it ever conflicts with a source document, the source document wins. The file says this inside.

### `ethics_commission/sei_who_must_file_2026.md`

Carries the correct current threshold of $106,000, but that number changes every January. Anything built on this file should expect to refresh it annually.

---

## 4. Deliberately excluded

### The Ethics Commission's SEI instructions PDF

Still live at https://ethics-form.alabama.gov/instructions/form_sei_inst.pdf, and deliberately left out of this knowledge base.

It says the salary threshold is $50,000, cites § 17-22A-2 which was renumbered twenty years ago, and refers to the 2007 reporting year throughout. Adding it would give the chatbot a plausible-looking official document containing several wrong numbers, which is worse than not having instructions at all.

If someone wants SEI instructions in the knowledge base later, get a current version from the Commission directly rather than using what is posted.

---

## 5. Open question

Not a flag on any particular file, a gap in what the sources actually say.

§ 36-25-14(a) lists specific job titles that must file a Statement of Economic Interests, including police chiefs, fire chiefs, school principals and chief municipal clerks. But § 36-25-14(b) says that employees earning below the threshold are not required to file, "unless otherwise required by law."

So it is unclear from the text alone whether a police chief earning $80,000 has to file. The Ethics Commission's "Who Must File" notice lists those job titles without resolving it either way.

If this matters for the chatbot, it is a question for sei@ethics.alabama.gov rather than something to infer.

---

## Quick reference

| File | Flag |
|---|---|
| `ethics_law/36-25-14_...` | Says $75,000; real threshold is $106,000 |
| `sos_guidance/independent_candidate_ballot_access_2026.md` | SEI deadline conflicts with § 36-25-15 |
| `sos_guidance/sos_minimum_qualifications_for_public_office.md` | Web-sourced via summarizer, unverified |
| `sos_guidance/ballot_access_petitions_rule_820-2-4-.05.md` | OCR of a scan |
| `fcpa_statute/17-5-13_...` | Statute's own cross-reference is stale |
| `ag_opinions/` (all 5) | Pre-2006 numbering: 17-22A-x means 17-5-x |
| `ethics_law/36-25-5`, `36-25-13`, `36-25-19` | Same pre-2006 numbering |
| `ag_opinions/AGO_2002-040_...` | Numbered 2002, dated 2001 |
| `fcpa_statute/17-5-18_repealed.md` | Repealed, kept for citation resolution |
| `ethics_law/36-25-1.2_repealed.md` | Repealed, kept for citation resolution |
| `sos_guidance/municipal_election_fcpa_calendar_2026.md` | PDF title says 2025; web-sourced |
| `sos_guidance/independent_candidate_petition_form.md` | Web-sourced, 2019 form |
| `sos_guidance/campaign_advertisement_guidelines_2024.md` | 2024 edition; two-column layout |
| `sos_guidance/online_filing_system_guidelines_2024.md` | 2024 edition |
| `ethics_commission/ethics_commission_role_in_fcpa.md` | Written by Claude, not a source document |
| `ethics_commission/sei_who_must_file_2026.md` | Threshold changes every January |
