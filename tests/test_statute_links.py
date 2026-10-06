import re

from assistant.statute_links import link_statutes

JUSTIA = "https://law.justia.com/codes/alabama/title-17/chapter-5/"
PSEUDO_OPEN = (
    '<span title="Link coming soon" '
    'style="color:#1c83e1;text-decoration:underline;cursor:default">'
)


def test_fcpa_citation_becomes_justia_link():
    out = link_statutes("See § 17-5-12 for ad rules.")

    assert out == (
        f'See <a href="{JUSTIA}section-17-5-12/" target="_blank" '
        'rel="noopener noreferrer" style="color:#1c83e1;text-decoration:underline">'
        "§ 17-5-12</a> for ad rules."
    )


def test_citation_without_space_after_section_sign_is_linked():
    out = link_statutes("See §17-5-12.")

    assert f'href="{JUSTIA}section-17-5-12/"' in out
    assert ">§17-5-12</a>" in out


def test_decimal_section_dot_becomes_hyphen_in_url():
    out = link_statutes("Under § 17-5-19.1, penalties apply.")

    assert f'href="{JUSTIA}section-17-5-19-1/"' in out
    assert ">§ 17-5-19.1</a>" in out


def test_sentence_ending_period_is_not_part_of_section():
    out = link_statutes("Required by § 17-5-8.")

    assert f'href="{JUSTIA}section-17-5-8/"' in out
    assert ">§ 17-5-8</a>." in out


def test_subsection_chain_is_link_text_but_url_is_section_page():
    out = link_statutes("Per § 17-5-8(a)(1), report it.")

    assert f'href="{JUSTIA}section-17-5-8/"' in out
    assert ">§ 17-5-8(a)(1)</a>, report it." in out


def test_bare_number_without_prefix_is_not_linked():
    assert link_statutes("Section number 17-5-7 alone") == "Section number 17-5-7 alone"


def test_phone_numbers_and_dates_are_unchanged():
    text = "Call 1-800-274-8683 by 26-09-18."

    assert link_statutes(text) == text


def test_answer_html_is_escaped():
    out = link_statutes("<script>alert(1)</script> Q&A")

    assert out == "&lt;script>alert(1)&lt;/script> Q&amp;A"


def test_blockquote_marker_is_preserved():
    assert link_statutes("> quoted statute text") == "> quoted statute text"


def test_text_without_citations_is_unchanged():
    text = "Contributions over \\$100 must be itemized."

    assert link_statutes(text) == text


def test_ethics_law_citation_becomes_pseudo_link():
    out = link_statutes("See § 36-25-1 for definitions.")

    assert out == f"See {PSEUDO_OPEN}§ 36-25-1</span> for definitions."
    assert "href" not in out


def test_old_fcpa_numbering_is_pseudo_link_not_mapped_to_17_5():
    out = link_statutes("the old § 17-22A-12.")

    assert out == f"the old {PSEUDO_OPEN}§ 17-22A-12</span>."
    assert "justia" not in out


def test_other_title_citation_becomes_pseudo_link():
    out = link_statutes("Per § 11-45-1(b), cities may act.")

    assert out == f"Per {PSEUDO_OPEN}§ 11-45-1(b)</span>, cities may act."


def test_fcpa_and_non_fcpa_citations_in_same_answer():
    out = link_statutes("Compare § 17-5-12 with § 36-25-1.")

    assert f'<a href="{JUSTIA}section-17-5-12/"' in out
    assert f"{PSEUDO_OPEN}§ 36-25-1</span>." in out


def test_section_prefix_citation_is_linked():
    out = link_statutes("Under Section 17-5-7, solicit after session.")

    assert f'href="{JUSTIA}section-17-5-7/"' in out
    assert ">Section 17-5-7</a>, solicit" in out


def test_lowercase_section_prefix_mid_sentence_is_linked():
    out = link_statutes("as required by section 17-5-8.")

    assert ">section 17-5-8</a>." in out


def test_ala_code_prefix_is_part_of_link_text():
    out = link_statutes("See Ala. Code § 17-5-7 for details.")

    assert f'See <a href="{JUSTIA}section-17-5-7/"' in out
    assert ">Ala. Code § 17-5-7</a> for details." in out


def test_section_prefix_with_subsections():
    out = link_statutes("Section 17-5-8(a)(1) applies.")

    assert f'href="{JUSTIA}section-17-5-8/"' in out
    assert ">Section 17-5-8(a)(1)</a> applies." in out


def test_ala_code_prefix_with_decimal_section():
    out = link_statutes("Ala. Code § 17-5-19.1 sets penalties.")

    assert f'href="{JUSTIA}section-17-5-19-1/"' in out
    assert ">Ala. Code § 17-5-19.1</a> sets penalties." in out


def test_non_fcpa_citations_with_other_prefixes_become_pseudo_links():
    out = link_statutes("Section 36-25-1 and Ala. Code § 36-25-14 cover ethics.")

    assert out == (
        f"{PSEUDO_OPEN}Section 36-25-1</span> and "
        f"{PSEUDO_OPEN}Ala. Code § 36-25-14</span> cover ethics."
    )


def test_prose_section_without_statute_number_is_unchanged():
    text = "This section explains reporting; see the next section, Section 3."

    assert link_statutes(text) == text


def _linked_sections(out):
    return re.findall(r'href="[^"]*section-(17-5-[\d-]+)/"', out)


def test_multi_section_citation_links_each_number():
    out = link_statutes("See §§ 17-5-7 and 17-5-8.")

    assert _linked_sections(out) == ["17-5-7", "17-5-8"]
    assert out.startswith("See §§ <a ")
    assert ">17-5-7</a> and <a " in out
    assert ">17-5-8</a>." in out


def test_mixed_list_classifies_each_number_independently():
    out = link_statutes("Under §§ 17-5-7, 17-5-8, and 36-25-1, ...")

    assert _linked_sections(out) == ["17-5-7", "17-5-8"]
    assert f">17-5-8</a>, and {PSEUDO_OPEN}36-25-1</span>, ..." in out


def test_list_members_keep_their_subsections():
    out = link_statutes("§§ 17-5-8(a) and 17-5-9 apply.")

    assert _linked_sections(out) == ["17-5-8", "17-5-9"]
    assert ">17-5-8(a)</a> and " in out


def test_range_links_only_the_written_endpoints():
    out = link_statutes("§§ 17-5-7 through 17-5-9")

    assert _linked_sections(out) == ["17-5-7", "17-5-9"]
    assert ">17-5-7</a> through <a " in out


def test_partial_shorthand_in_range_stays_plain():
    out = link_statutes("§§ 17-5-7 through -9 cover this.")

    assert _linked_sections(out) == ["17-5-7"]
    assert ">17-5-7</a> through -9 cover this." in out


def test_plural_sections_prefix_links_each_number():
    out = link_statutes("Sections 17-5-7 and 17-5-8 apply.")

    assert _linked_sections(out) == ["17-5-7", "17-5-8"]
    assert out.startswith("Sections <a ")


def test_ala_code_multi_section_prefix_links_each_number():
    out = link_statutes("Ala. Code §§ 17-5-7 and 17-5-8")

    assert _linked_sections(out) == ["17-5-7", "17-5-8"]
    assert out.startswith("Ala. Code §§ <a ")


def test_list_does_not_swallow_unprefixed_number_after_prose():
    out = link_statutes("§§ 17-5-7 and 17-5-8 apply; call 1-800-274-8683.")

    assert _linked_sections(out) == ["17-5-7", "17-5-8"]
    assert "call 1-800-274-8683." in out
