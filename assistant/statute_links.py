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

# Only prefixed citations: a bare "17-5-7" is never matched, so phone
# numbers and dates in the knowledge base / campaign data stay untouched.
# Fair Campaign Practices Act only (Title 17, Chapter 5); a trailing
# subsection chain like "(a)(1)" is part of the link text.
_FCPA_CITATION_RE = re.compile(
    r"§[  ]?17-5-(?P<section>\d+(?:\.\d+)?)(?:\([A-Za-z0-9]+\))*"
)


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;")


def _fcpa_link(match: re.Match) -> str:
    url = JUSTIA_FCPA_URL.format(section=match["section"].replace(".", "-"))
    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'style="color:{LINK_COLOR};text-decoration:underline">{match[0]}</a>'
    )


def link_statutes(text: str) -> str:
    return _FCPA_CITATION_RE.sub(_fcpa_link, _escape_html(text))
