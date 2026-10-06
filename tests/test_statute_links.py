from assistant.statute_links import link_statutes

JUSTIA = "https://law.justia.com/codes/alabama/title-17/chapter-5/"


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


def test_non_fcpa_citations_are_not_linked():
    text = "See § 36-25-1 and the old § 17-22A-12."

    assert link_statutes(text) == text
