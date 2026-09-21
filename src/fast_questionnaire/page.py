"""What the page needs to show a Questionnaire: Markdown turned into HTML.

The body transform gives the document back as Markdown segments interleaved
with answer slots; this turns each segment into the HTML the respondent reads,
server-side. Mermaid blocks are the one exception: they come out as the element
Mermaid looks for, and the browser draws them.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from markdown_it.renderer import RendererHTML

from .body import Part, Segment, Slot
from .github import Repository

# Where the respondent's draft lives in their browser. The app stores nothing
# of a draft itself; it only tells the page which name to keep it under.
DRAFT = "fast-questionnaire"

# The class Mermaid, loaded from a CDN, draws on its own once the page is
# loaded. The code stays escaped: the browser reads the diagram's source from
# the element's text, so `<br/>` and `-->` reach Mermaid as they were written.
MERMAID = "mermaid"


def _fence(
    renderer: RendererHTML, tokens: list, index: int, options: dict, env: dict
) -> str:
    """A fenced code block: a diagram for Mermaid, or code as it was written."""
    token = tokens[index]
    language = token.info.strip().split(maxsplit=1)[0] if token.info.strip() else ""
    if language == MERMAID:
        return f'<pre class="mermaid">{escapeHtml(token.content)}</pre>\n'
    return RendererHTML.fence(renderer, tokens, index, options, env)


# Headings, emphasis, links, lists and tables, and no raw HTML: a Questionnaire
# is a document, not a page, and the slot markers are the only HTML it carries.
_MARKDOWN = MarkdownIt("commonmark", {"html": False}).enable(
    ["table", "strikethrough"]
)
_MARKDOWN.add_render_rule("fence", _fence)


def to_html(markdown: str) -> str:
    """One Markdown segment, as the respondent reads it."""
    return _MARKDOWN.render(markdown)


def parts(document: list[Part]) -> list[dict]:
    """The document as the template walks it: Markdown, then a slot, then…"""
    walked: list[dict] = []
    for part in document:
        if isinstance(part, Segment):
            walked.append({"kind": "markdown", "html": to_html(part.markdown)})
        elif isinstance(part, Slot):
            walked.append(
                {
                    "kind": "slot",
                    "name": part.name,
                    "heading": part.heading,
                    "answer": part.answer,
                }
            )
    return walked


def draft_key(repository: Repository, number: int) -> str:
    """The name the respondent's draft is kept under in their browser.

    Owner, repository and issue number, as GitHub names the issue, so that two
    Questionnaires opened in the same browser never share a draft.
    """
    return f"{DRAFT}:{repository}#{number:d}"
