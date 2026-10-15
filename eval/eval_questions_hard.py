"""Harder eval questions for the retrieval-strategy experiment.

The original 21 questions (eval_questions.py) mostly hit short documents
near their top, phrased in the statute's own words - easy for every
retrieval strategy. These probe where strategies should differ:

- deep: the answer sits well past the first ~200 words of a long file.
  This matters for rag_current because all-MiniLM-L6-v2 truncates input to
  256 word-pieces, so a file's embedding never "sees" its later text.
- section_number: the question names an exact section.
- paraphrase: the question avoids the statute's own wording.
- cross_reference: the answer needs two sections, or a pointer followed.
- flag: a _FLAGS.md caveat (or an in-file note) changes the right answer.

NEEDS HUMAN REVIEW: every question below was drafted by Claude from the
knowledge-base text quoted in its `sources` (verbatim - see
tests/test_eval_questions_hard.py, which fails if a quote is not found in
its file). The quoted files are themselves a point-in-time conversion; the
expected answers have NOT been checked against the current Code of Alabama
or current Secretary of State / Ethics Commission material. Verify each
before trusting results built on it.
"""

from dataclasses import dataclass, field

from eval.eval_questions import EvalQuestion


@dataclass
class Source:
    path: str  # relative to knowledge_base/
    line: int  # 1-indexed line where the quote starts
    quote: str  # verbatim text from the file


@dataclass
class HardEvalQuestion(EvalQuestion):
    question_types: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    needs_human_review: bool = True


QUESTIONS_HARD: list[HardEvalQuestion] = [
    HardEvalQuestion(
        id="hard-17-5-13-identification-crossref",
        eval_category="compliance",
        question=(
            "Under § 17-5-13, what identification has to appear on campaign "
            "flyers and other printed election material?"
        ),
        notes=(
            "The statute points to § 17-5-2(a)(5), which is now ELECTION; the "
            "identification definition moved to (a)(8). Following the pointer "
            "literally gives the wrong definition (flagged in _FLAGS.md)."
        ),
        question_types=["section_number", "cross_reference", "flag"],
        expect_answer_category="compliance",
        expect_citation_contains=["fcpa_statute/17-5-13"],
        expect_text_contains_all=["full name", "address"],
        sources=[
            Source(
                "fcpa_statute/17-5-13_printed_material_must_bear_identification.md",
                11,
                "which does not contain the identification required by Section "
                "17-5-2(a)(5) of the person, candidate, principal campaign "
                "committee, or political action committee responsible",
            ),
            Source(
                "fcpa_statute/17-5-13_printed_material_must_bear_identification.md",
                15,
                'The definition of IDENTIFICATION ("the full name and complete '
                'address") currently appears at § 17-5-2(a)(8).',
            ),
            Source(
                "fcpa_statute/17-5-2_definitions.md",
                89,
                "(8) IDENTIFICATION. The full name and complete address.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-late-report-second-offense",
        eval_category="compliance",
        question=(
            "If a campaign committee turns in a required finance report late "
            "for the second time in the same election cycle, what's the most "
            "the state can fine it?"
        ),
        notes="Paraphrased: avoids 'civil penalty', 'schedule', 'offense'.",
        question_types=["paraphrase"],
        expect_answer_category="compliance",
        expect_citation_contains=["fcpa_statute/17-5-19.1"],
        expect_text_contains_all=["600", "15"],
        sources=[
            Source(
                "fcpa_statute/17-5-19.1_civil_penalties.md",
                17,
                "(2) The lesser of six hundred dollars ($600) or 15 percent of "
                "the amount of contributions or expenditures not properly "
                "reported for a second offense in an election cycle.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-late-report-48-hour-grace",
        eval_category="compliance",
        question=(
            "Our committee filed its first late report of this election cycle "
            "about 30 hours after it was due. Does Alabama treat that as a "
            "penalized offense?"
        ),
        notes=(
            "Needs subsection (h)'s first-failure / 48-hour grace, not just "
            "the (b) penalty schedule."
        ),
        question_types=["cross_reference", "paraphrase"],
        expect_answer_category="compliance",
        expect_citation_contains=["fcpa_statute/17-5-19.1"],
        expect_text_contains_all=["48"],
        sources=[
            Source(
                "fcpa_statute/17-5-19.1_civil_penalties.md",
                31,
                "(h) Failure to file a timely report shall not be considered an "
                "offense or subjected to a civil penalty pursuant to subsection "
                "(a) so long as it is the first failure by that candidate or "
                "political action committee for the election cycle and the "
                "report is filed within 48 hours of the time it was due.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-fake-audio-disclaimer",
        eval_category="compliance",
        question=(
            "Under Alabama law, if a political ad uses a computer-generated "
            "audio clip that fakes a candidate's voice, what disclosure does "
            "it need and where in the clip does it go?"
        ),
        notes=(
            "Paraphrased: avoids 'materially deceptive media' and 'artificial "
            "intelligence'. Answer is in (c)(3), past the definitions."
        ),
        question_types=["paraphrase", "deep"],
        expect_answer_category="compliance",
        expect_citation_contains=["fcpa_statute/17-5-16.1"],
        expect_text_contains_any=["beginning and end", "beginning and the end", "start and end"],
        sources=[
            Source(
                "fcpa_statute/17-5-16.1_materially_deceptive_media_ai.md",
                57,
                "(3) If the media consists only of audio and contains no image "
                "or video, the disclaimer is read at the beginning and end of "
                "the media in a clearly spoken manner",
            ),
            Source(
                "fcpa_statute/17-5-16.1_materially_deceptive_media_ai.md",
                45,
                '"This media has been manipulated by technical means and depicts '
                'speech or conduct that did not occur."',
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-independent-candidate-sei-deadline",
        eval_category="compliance",
        question=(
            "I'm running as an independent candidate. When is my Statement of "
            "Economic Interests due?"
        ),
        notes=(
            "_FLAGS.md: the SOS ballot-access guide says 5 days after the "
            "petition; the controlling statute says 5 days after the first "
            "primary election. A correct answer gives the statute's rule."
        ),
        question_types=["flag", "cross_reference"],
        expect_answer_category="compliance",
        expect_citation_contains=["36-25-15"],
        expect_text_contains_all=["primary"],
        sources=[
            Source(
                "ethics_law/36-25-15_candidates_statement_of_economic_interests.md",
                11,
                "or in the case of an independent candidate, not more than five "
                "days after the date of the first primary election",
            ),
            Source(
                "sos_guidance/independent_candidate_ballot_access_2026.md",
                37,
                "Independent candidates must file a Statement of Economic "
                "Interests with the Alabama Ethics Commission not more than 5 "
                "days after he or she submits the ballot access petition.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-36-25-15c-no-sei-consequence",
        eval_category="compliance",
        question=(
            "Under § 36-25-15(c), what happens to a candidate who doesn't file "
            "a Statement of Economic Interests, and can they get extra time?"
        ),
        question_types=["section_number"],
        expect_answer_category="compliance",
        expect_citation_contains=["36-25-15"],
        expect_text_contains_all=["ballot"],
        expect_text_contains_any=["five days", "5 days", "five additional", "5 additional"],
        sources=[
            Source(
                "ethics_law/36-25-15_candidates_statement_of_economic_interests.md",
                15,
                "the name of the individual shall not appear on the ballot and "
                "the candidate shall be deemed not qualified as a candidate in "
                "that election. Notwithstanding the foregoing, the commission, "
                "for good cause shown, may allow the candidate an additional "
                "five days to file the statement of economic interests.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-portal-delete-filed-transaction",
        eval_category="compliance",
        question=(
            "In the Secretary of State's FCPA online filing system, can I "
            "delete a contribution I entered by mistake if it was already "
            "included in a report I filed?"
        ),
        notes=(
            "Deep: line ~1130 of the 1,713-line (~14k-token) Tyler portal "
            "manual, about two-thirds of the way in."
        ),
        question_types=["deep"],
        expect_citation_contains=["sos_guidance/fcpa_user_guide_tyler_technologies_v1.md"],
        expect_text_contains_all=["amend"],
        sources=[
            Source(
                "sos_guidance/fcpa_user_guide_tyler_technologies_v1.md",
                1130,
                "Deletion is only possible if the transaction has NOT been "
                "included in a filed report.",
            ),
            Source(
                "sos_guidance/fcpa_user_guide_tyler_technologies_v1.md",
                1139,
                "Note: If the transaction has already been filed in a report, "
                "you must instead amend the report.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-portal-password-rules",
        eval_category="compliance",
        question=(
            "What password rules does the Secretary of State's FCPA campaign "
            "finance filing system enforce?"
        ),
        notes="Deep: line ~771 of the 1,713-line portal manual.",
        question_types=["deep"],
        expect_citation_contains=["sos_guidance/fcpa_user_guide_tyler_technologies_v1.md"],
        expect_text_contains_all=["12", "90"],
        sources=[
            Source(
                "sos_guidance/fcpa_user_guide_tyler_technologies_v1.md",
                771,
                "You will be prompted to set a new password that meets all "
                "system requirements (minimum 12\ncharacters, including "
                "uppercase, lowercase, number, and special character). For "
                "additional\nsecurity, update your password every 90 days.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-lobbyist-meal-limit",
        eval_category="compliance",
        question=(
            "Under Alabama's ethics law, how much can a lobbyist spend buying "
            "an elected official a meal outside of any official event, and is "
            "there a yearly cap?"
        ),
        notes=(
            "Deep + paraphrase: item 16 of THING OF VALUE, line 171 of the "
            "185-line § 36-25-1 definitions file (~92% of the way in)."
        ),
        question_types=["deep", "paraphrase"],
        expect_answer_category="compliance",
        expect_citation_contains=["ethics_law/36-25-1_definitions"],
        expect_text_contains_all=["25", "150"],
        sources=[
            Source(
                "ethics_law/36-25-1_definitions.md",
                171,
                "not to exceed for a lobbyist twenty-five dollars ($25) per meal "
                "with a limit of one hundred fifty dollars ($150) per year",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-ethics-law-candidate-definition",
        eval_category="compliance",
        question=(
            "Who counts as a 'candidate' for purposes of Alabama's Ethics Law, "
            "and can someone become one just by fundraising before they "
            "qualify?"
        ),
        notes=(
            "Cross-reference: § 36-25-1(3) defines candidate only by pointing "
            "to § 17-5-2, where the $1,000 fundraising trigger lives."
        ),
        question_types=["cross_reference"],
        expect_answer_category="compliance",
        expect_citation_contains=[
            "ethics_law/36-25-1_definitions",
            "fcpa_statute/17-5-2_definitions",
        ],
        expect_text_contains_all=["1,000"],
        sources=[
            Source(
                "ethics_law/36-25-1_definitions.md",
                17,
                "(3) CANDIDATE. This term as used in this chapter shall have the "
                "same meaning ascribed to it in Section 17-5-2.",
            ),
            Source(
                "fcpa_statute/17-5-2_definitions.md",
                17,
                "b. Received contributions or made expenditures in excess of one "
                "thousand dollars ($1,000)",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-church-disclosure",
        eval_category="compliance",
        question=(
            "Does a church in Alabama have to disclose its members' donations "
            "under the state's campaign finance reporting rules?"
        ),
        notes="Deep: subsection (g) of § 17-5-8, past ~1,800 tokens of text.",
        question_types=["deep", "paraphrase"],
        expect_answer_category="compliance",
        expect_citation_contains=["fcpa_statute/17-5-8"],
        expect_text_contains_all=["exempt"],
        expect_text_contains_any=["influence"],
        sources=[
            Source(
                "fcpa_statute/17-5-8_reports_of_contributions_and_expenditures.md",
                49,
                "churches are exempt from the requirements of this section "
                "unless the church's expenditures are used to influence the "
                "outcome of an election. Nothing herein shall require a church "
                "to disclose the identities, donations, or contributions of "
                "members of the church.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-17-5-7.2-campaign-property",
        eval_category="compliance",
        question=(
            "What does § 17-5-7.2 require a campaign to do with property worth "
            "$500 or more after the election, and by when?"
        ),
        notes=(
            "Section number in the query: in a spot check, embedding search "
            "ranked a different section first for a '17-5-15.1' query, so this "
            "probes number-matching. (b)'s office-use exception is a bonus."
        ),
        question_types=["section_number", "cross_reference"],
        expect_answer_category="compliance",
        expect_citation_contains=["fcpa_statute/17-5-7.2"],
        expect_text_contains_all=["120"],
        expect_text_contains_any=["liquidat", "fair market"],
        sources=[
            Source(
                "fcpa_statute/17-5-7.2_disposal_of_campaign_property.md",
                11,
                "property purchased by or contributed to a principal campaign "
                "committee with a value of five hundred dollars ($500) or more "
                "shall be liquidated at fair market value or donated to a "
                "qualified entity pursuant to subsection (a) of Section 17-5-7 "
                "not more than 120 days following the election.",
            ),
        ],
    ),
    HardEvalQuestion(
        id="hard-17-5-18-repealed",
        eval_category="compliance",
        question="What penalty does § 17-5-18 impose for failing to file a required report?",
        notes=(
            "_FLAGS.md: repealed, kept only for citation resolution. A correct "
            "answer says it was repealed and points to § 17-5-19 / 17-5-19.1."
        ),
        question_types=["section_number", "flag"],
        expect_answer_category="compliance",
        expect_citation_contains=["fcpa_statute/17-5-18"],
        expect_text_contains_all=["repealed"],
        expect_text_contains_any=["17-5-19"],
        sources=[
            Source(
                "fcpa_statute/17-5-18_repealed.md",
                11,
                "Repealed by Act 2013-311, §3, effective August 1, 2013.",
            ),
            Source(
                "fcpa_statute/17-5-18_repealed.md",
                13,
                "Penalties for late or inaccurate filings are now handled under "
                "§ 17-5-19 (criminal violations) and § 17-5-19.1 (civil "
                "penalties).",
            ),
        ],
    ),
]
