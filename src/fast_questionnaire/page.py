"""What the page needs to show a Questionnaire: Markdown turned into HTML.

The body transform gives the document back as Markdown segments interleaved
with answer slots; this turns each segment into the HTML the respondent reads,
server-side. Mermaid blocks are the one exception: they come out as the element
Mermaid looks for, and the browser draws them. Its `##` and `###` headings are
also the page's outline, each one an anchor the sidebar links to.
"""

from __future__ import annotations

import re
import unicodedata

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


# The headings the outline lists: the sections, and the questions inside them.
_OUTLINE = ("h2", "h3")

_UNANCHORABLE = re.compile(r"[^a-z0-9]+")


def to_html(markdown: str) -> str:
    """One Markdown segment, as the respondent reads it."""
    return _MARKDOWN.render(markdown)


def inline_html(markdown: str) -> str:
    """A line of Markdown, links and emphasis included, without a paragraph."""
    return _MARKDOWN.renderInline(markdown)


def parts(document: list[Part]) -> list[dict]:
    """The document as the template walks it: Markdown, then a slot, then…

    Each slot carries its number, counting from one, and each outline heading
    its anchor.
    """
    return _walk(document)[0]


def outline(document: list[Part]) -> list[dict]:
    """The document's `##` and `###` headings, in order, as the sidebar lists them.

    Each carries its level, its text, the anchor `parts` gave it, and the name
    of the slot answering it, if any: the answer slot the body transform named
    after that heading, which is the first slot below it.
    """
    return _walk(document)[1]


def _walk(document: list[Part]) -> tuple[list[dict], list[dict]]:
    """The parts and the outline, in the one pass that keeps their anchors equal."""
    walked: list[dict] = []
    headings: list[dict] = []
    anchors: set[str] = set()
    answered_by_next_slot: dict | None = None
    number = 0
    for part in document:
        if isinstance(part, Segment):
            tokens = _MARKDOWN.parse(part.markdown)
            for index, token in enumerate(tokens):
                if token.type != "heading_open":
                    continue
                # Any heading, even one the outline leaves out, is the one the
                # slot below it answers.
                answered_by_next_slot = None
                if token.tag not in _OUTLINE:
                    continue
                text = _text(tokens[index + 1])
                anchor = _anchor(text, anchors)
                token.attrSet("id", anchor)
                answered_by_next_slot = {
                    "level": int(token.tag[1]),
                    "text": text,
                    "anchor": anchor,
                    "slot": None,
                }
                headings.append(answered_by_next_slot)
            walked.append(
                {
                    "kind": "markdown",
                    "html": _MARKDOWN.renderer.render(
                        tokens, _MARKDOWN.options, {}
                    ),
                }
            )
        elif isinstance(part, Slot):
            number += 1
            if answered_by_next_slot is not None:
                answered_by_next_slot["slot"] = part.name
                answered_by_next_slot = None
            walked.append(
                {
                    "kind": "slot",
                    "number": number,
                    "name": part.name,
                    "heading": part.heading,
                    "answer": part.answer,
                }
            )
    return walked, headings


def _text(inline) -> str:
    """A heading's words, without its Markdown."""
    return "".join(
        child.content
        for child in inline.children or []
        if child.type in ("text", "code_inline")
    )


def _anchor(text: str, taken: set[str]) -> str:
    """An anchor for a heading, unique on the page."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    unaccented = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    anchor = "section-" + (_UNANCHORABLE.sub("-", unaccented).strip("-") or "sans-titre")
    unique, count = anchor, 1
    while unique in taken:
        count += 1
        unique = f"{anchor}-{count}"
    taken.add(unique)
    return unique


def initials(name: str) -> str:
    """The one or two letters the recipient's circle shows in place of a photo.

    From the capitalised words when there are some, `MD` for `Marie Dupont`,
    otherwise from the longer words of a role, `RM` for `la responsable de la
    médiathèque`.
    """
    words = [re.sub(r"^\w['’]", "", word) for word in name.split()]
    words = [word for word in words if word and word[0].isalpha()]
    chosen = (
        [word for word in words if word[0].isupper()]
        or [word for word in words if len(word) > 3]
        or words
    )
    return "".join(word[0] for word in chosen[:2]).upper()


def draft_key(repository: Repository, number: int) -> str:
    """The name the respondent's draft is kept under in their browser.

    Owner, repository and issue number, as GitHub names the issue, so that two
    Questionnaires opened in the same browser never share a draft.
    """
    return f"{DRAFT}:{repository}#{number:d}"
