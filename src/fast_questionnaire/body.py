"""The body transform: the one module that knows the Questionnaire body format.

It knows nothing of GitHub, HTTP or the page. Prepare turns a document written
with the `to-questionnaire` skill into an issue body whose answer stubs have
become named answer slots.
"""

from __future__ import annotations

import re
import unicodedata

SLOT_OPEN = "<!-- q:{name} -->"
SLOT_CLOSE = "<!-- /q -->"

# A Markdown ATX heading, at any level: the slot takes its name from the
# nearest one above it, whether the question is a `###` or a `##` section that
# is itself the question.
_HEADING = re.compile(r"^#{1,6}\s+(?P<text>.+?)\s*#*\s*$")
_FENCE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
_UNNAMEABLE = re.compile(r"[^a-z0-9]+")


class BodyTransformError(Exception):
    """A document or body the transform refuses to work with."""


class PrepareError(BodyTransformError):
    """A document Prepare refuses to turn into a Questionnaire body."""


def prepare(document: str) -> str:
    """Turn a `to-questionnaire` document into a Questionnaire issue body.

    Every line consisting only of `>` becomes an answer slot, named after the
    nearest heading above it and wrapped in markers GitHub renders as nothing.
    Everything else is left exactly as it was written.
    """
    prepared: list[str] = []
    headings_by_name: dict[str, str] = {}
    heading: str | None = None
    fence: str | None = None

    for line in document.split("\n"):
        if fence is not None:
            prepared.append(line)
            if _closes(fence, line):
                fence = None
            continue

        opening = _FENCE.match(line)
        if opening:
            prepared.append(line)
            fence = opening["fence"]
            continue

        heading_here = _HEADING.match(line)
        if heading_here:
            prepared.append(line)
            heading = heading_here["text"]
            continue

        if line.rstrip() != ">":
            prepared.append(line)
            continue

        if heading is None:
            raise PrepareError(
                "Un emplacement de réponse n'a aucun titre au-dessus de lui : "
                "chaque ligne « > » doit suivre la question à laquelle elle répond."
            )
        name = _slot_name(heading)
        if name in headings_by_name:
            raise PrepareError(
                f"Deux emplacements de réponse porteraient le même nom « {name} » : "
                f"les titres « {headings_by_name[name]} » et « {heading} » ne se "
                "distinguent pas. Reformule l'un des deux."
            )
        headings_by_name[name] = heading
        prepared.append(SLOT_OPEN.format(name=name))
        prepared.append(line)
        prepared.append(SLOT_CLOSE)

    if not headings_by_name:
        raise PrepareError(
            "Ce document ne contient aucun emplacement de réponse : ajoute une "
            "ligne « > » seule sous chaque question."
        )

    return "\n".join(prepared)


def _slot_name(heading: str) -> str:
    """The name a slot takes from the heading above it."""
    decomposed = unicodedata.normalize("NFKD", heading.lower())
    unaccented = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return _UNNAMEABLE.sub("-", unaccented).strip("-")


def _closes(fence: str, line: str) -> bool:
    """Whether the line closes a fenced code block opened with `fence`."""
    closing = line.strip()
    return len(closing) >= len(fence) and set(closing) == {fence[0]}
