"""The letterhead: who sends a Questionnaire, to whom, and why.

A `to-questionnaire` document opens with its title, then a paragraph giving its
objective and one naming its sender, its recipient and what the answers will be
used for — in French or in English. The page shows these in its header and its
sidebar, so they are taken out of the Markdown before it is rendered; the rest
of the document, answer slots included, comes back untouched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TITLE = re.compile(r"^#\s+\S")

# A bold label opening a field: `**Objectif :**`, `**From:**`, or with the colon
# left outside the bold, `**De** :`.
_LABEL = re.compile(r"\*\*\s*(?P<label>[^*:]+?)\s*(?::\s*\*\*|\*\*\s*:)")

_FIELDS = {
    "objectif": "objective",
    "purpose": "objective",
    "de": "sender",
    "from": "sender",
    "à": "recipient",
    "to": "recipient",
    "usage des réponses": "usage",
    "how your answers will be used": "usage",
}


@dataclass(frozen=True)
class Letterhead:
    """The letterhead of a document, and the document without it.

    A field the document does not give is empty.
    """

    sender: str
    recipient: str
    objective: str
    usage: str
    body: str


def extract(document: str) -> Letterhead:
    """Take the letterhead off the top of a Questionnaire's Markdown.

    The top-level heading, the objective paragraph and the sender/recipient
    paragraph go; everything from the first line that is none of these stays,
    as it was written.
    """
    lines = document.split("\n")
    fields: dict[str, str] = {}
    at = _past_blanks(lines, 0)

    if at < len(lines) and _TITLE.match(lines[at]):
        at = _past_blanks(lines, at + 1)

    while at < len(lines):
        end = at
        while end < len(lines) and lines[end].strip():
            end += 1
        given = _fields(" ".join(line.strip() for line in lines[at:end]))
        if given is None:
            break
        fields.update(given)
        at = _past_blanks(lines, end)

    return Letterhead(
        sender=fields.get("sender", ""),
        recipient=fields.get("recipient", ""),
        objective=fields.get("objective", ""),
        usage=fields.get("usage", ""),
        body="\n".join(lines[at:]),
    )


def _past_blanks(lines: list[str], at: int) -> int:
    """The first line from `at` on that is not blank."""
    while at < len(lines) and not lines[at].strip():
        at += 1
    return at


def _fields(paragraph: str) -> dict[str, str] | None:
    """The letterhead fields a paragraph gives, or None if it is not one.

    A paragraph is part of the letterhead only if it opens on a label and every
    label in it is one the letterhead knows: anything else is the document's.
    """
    labels = list(_LABEL.finditer(paragraph))
    if not labels or labels[0].start() != 0:
        return None
    fields: dict[str, str] = {}
    for label, following in zip(labels, [*labels[1:], None]):
        field = _FIELDS.get(label["label"].lower())
        if field is None:
            return None
        end = following.start() if following else len(paragraph)
        fields[field] = paragraph[label.end() : end].strip().rstrip(",").strip()
    return fields
