"""Turn Alabama statute citations in an assistant answer into Justia links.

Display-time only: the app applies link_statutes() to the answer it
renders, while AssistantAnswer.text stays raw so the statute detector,
safety checks and eval harness keep seeing plain "§ 17-5-8".

The output is rendered with HTML enabled, so the answer's own `&` and
`<` are escaped first and model/user-supplied markup shows as text.
`>` is left alone so markdown blockquotes still work.
"""

import re

LINK_COLOR = "#1c83e1"
JUSTIA_FCPA_URL = "https://law.justia.com/codes/alabama/title-17/chapter-5/section-17-5-{section}/"

_SPACE = r"[  ]"
_PREFIX = rf"(?:\bAla\.{_SPACE}?Code{_SPACE}?§|§|\b[Ss]ection)"
_MULTI_PREFIX = rf"(?:\bAla\.{_SPACE}?Code{_SPACE}?§§|§§|\b[Ss]ections)"
# A complete Title-Chapter-Section number (e.g. 17-5-8, 17-22A-12,
# 17-5-19.1) with an optional subsection chain like "(a)(1)".
_NUMBER = r"\d+[A-Z]?-\d+[A-Z]?-\d+(?:\.\d+)?(?:\([A-Za-z0-9]+\))*"
_LIST_SEPARATOR = rf"(?:,?{_SPACE}+(?:and|or|through|to){_SPACE}+|,{_SPACE}+)"

# Only prefixed citations are recognised: a bare "17-5-7" is never matched,
# so phone numbers and dates in the knowledge base / campaign data stay
# untouched. A single citation ("§ 17-5-7", "Section 17-5-7",
# "Ala. Code § 17-5-7") is linked including its prefix. In a multi-section
# citation ("§§ 17-5-7 and 17-5-8") each complete number is its own
# citation; ranges are not expanded, and partial shorthand ("through -9")
# ends the list and stays plain.
_CITATION_RE = re.compile(
    rf"(?P<multi>{_MULTI_PREFIX}{_SPACE}?{_NUMBER}(?:{_LIST_SEPARATOR}{_NUMBER})*)"
    rf"|(?P<single>{_PREFIX}{_SPACE}?{_NUMBER})"
)
_NUMBER_RE = re.compile(
    r"(?P<title>\d+[A-Z]?)-(?P<chapter>\d+[A-Z]?)-(?P<section>\d+(?:\.\d+)?)"
    r"(?:\([A-Za-z0-9]+\))*"
)


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;")


def _render_citation(citation_text: str, number: re.Match) -> str:
    # Fair Campaign Practices Act only (Title 17, Chapter 5); every other
    # statute is left as plain text.
    if (number["title"], number["chapter"]) != ("17", "5"):
        return citation_text
    url = JUSTIA_FCPA_URL.format(section=number["section"].replace(".", "-"))
    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'style="color:{LINK_COLOR};text-decoration:underline">{citation_text}</a>'
    )


def _link_citation(match: re.Match) -> str:
    if match["multi"]:
        return _NUMBER_RE.sub(lambda n: _render_citation(n[0], n), match[0])
    return _render_citation(match[0], _NUMBER_RE.search(match[0]))


def link_statutes(text: str) -> str:
    return _CITATION_RE.sub(_link_citation, _escape_html(text))
