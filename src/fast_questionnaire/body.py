"""The body transform: the one module that knows the Questionnaire body format.

It knows nothing of GitHub, HTTP or the page. Prepare turns a document written
with the `to-questionnaire` skill into an issue body whose answer stubs have
become named answer slots; Read gives that body back as the document in order,
Markdown segments interleaved with answer slots; Answer writes the respondent's
answers back into those slots and changes nothing else.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

SLOT_OPEN = "<!-- q:{name} -->"
SLOT_CLOSE = "<!-- /q -->"

# A Markdown ATX heading, at any level: the slot takes its name from the
# nearest one above it, whether the question is a `###` or a `##` section that
# is itself the question.
_HEADING = re.compile(r"^#{1,6}\s+(?P<text>.+?)\s*#*\s*$")
_FENCE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
_UNNAMEABLE = re.compile(r"[^a-z0-9]+")

# The markers as Read finds them again in a body GitHub may have been edited
# through: a name is whatever Prepare wrote, never recomputed from the heading,
# so rewording a question leaves its answer where it is.
_SLOT_OPEN = re.compile(r"^<!-- q:(?P<name>\S+) -->$")
_SLOT_CLOSE = re.compile(r"^<!-- /q -->$")


@dataclass(frozen=True)
class Segment:
    """A run of the document GitHub renders as it was written."""

    markdown: str


@dataclass(frozen=True)
class Slot:
    """An answer slot, with the answer the body holds for it right now."""

    name: str
    heading: str
    answer: str


type Part = Segment | Slot


class BodyTransformError(Exception):
    """A document or body the transform refuses to work with."""


class PrepareError(BodyTransformError):
    """A document Prepare refuses to turn into a Questionnaire body."""


class AnswerError(BodyTransformError):
    """Answers Answer refuses to write into a Questionnaire body."""


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


def read(body: str) -> list[Part]:
    """Give back a Questionnaire issue body as the document, in order.

    Markdown segments interleaved with answer slots, each slot carrying its
    name, the heading above it as the body words it today, and its current
    answer with the blockquote prefix removed — empty when unanswered.
    """
    document: list[Part] = []
    segment: list[str] = []
    answer: list[str] | None = None
    name = ""
    asked = ""
    heading = ""
    fence: str | None = None

    for line in body.split("\n"):
        if answer is not None:
            if _SLOT_CLOSE.match(line.strip()):
                document.append(Slot(name=name, heading=asked, answer=_answer(answer)))
                answer = None
            else:
                answer.append(line)
            continue

        opening = None if fence is not None else _SLOT_OPEN.match(line.strip())
        if opening:
            _end(document, segment)
            segment = []
            answer = []
            name = opening["name"]
            asked = heading
            continue

        if fence is not None:
            if _closes(fence, line):
                fence = None
        else:
            opened = _FENCE.match(line)
            heading_here = None if opened else _HEADING.match(line)
            if opened:
                fence = opened["fence"]
            elif heading_here:
                heading = heading_here["text"]
        segment.append(line)

    if answer is not None:
        # A slot nobody closed: the rest of the body is its answer, rather than
        # a page that loses everything below a marker an edit broke.
        document.append(Slot(name=name, heading=asked, answer=_answer(answer)))
    else:
        _end(document, segment)
    return document


def _end(document: list[Part], segment: list[str]) -> None:
    """Close the Markdown segment running up to a slot, or to the end."""
    markdown = "\n".join(segment)
    if markdown.strip():
        document.append(Segment(markdown=markdown))


def _answer(quoted: list[str]) -> str:
    """The answer a slot holds, with the blockquote prefix removed.

    An unanswered slot holds a bare `>` stub, and so gives back nothing.
    """
    written = []
    for line in quoted:
        if line.startswith("> "):
            written.append(line[2:])
        elif line.rstrip() == ">":
            written.append("")
        else:
            # A line the author wrote into the slot by hand, without the
            # blockquote prefix: give it back as it stands rather than lose it.
            written.append(line)
    answer = "\n".join(written).strip("\n")
    return answer if answer.strip() else ""


def answer(body: str, answers: Mapping[str, str]) -> str:
    """Write answers into a Questionnaire issue body, and change nothing else.

    Only the contents of the answer slots named in `answers` change: every
    other byte of the body — the questions, the context, the markers, and the
    slots the mapping says nothing about — comes back as it went in, so that
    whatever the author edited elsewhere since the page was opened is kept.

    Each answer line is written as a blockquote line, an empty answer restores
    the bare `>` stub, and a name matching no slot is refused rather than
    written nowhere and forgotten.
    """
    written: list[str] = []
    named: list[str] = []
    inside = False
    keeping = False
    fence: str | None = None

    for line in body.split("\n"):
        if inside:
            if _SLOT_CLOSE.match(line.strip()):
                inside = False
                written.append(line)
            elif keeping:
                # A slot the mapping says nothing about: its answer is not
                # this send's to change.
                written.append(line)
            continue

        opening = None if fence is not None else _SLOT_OPEN.match(line.strip())
        if opening:
            name = opening["name"]
            named.append(name)
            written.append(line)
            inside = True
            keeping = name not in answers
            if not keeping:
                written.extend(_quoted(answers[name]))
            continue

        if fence is not None:
            if _closes(fence, line):
                fence = None
        else:
            opened = _FENCE.match(line)
            if opened:
                fence = opened["fence"]
        written.append(line)

    unknown = [name for name in answers if name not in named]
    if unknown:
        raise AnswerError(
            "Ces réponses ne correspondent à aucun emplacement du Questionnaire : "
            f"« {' », « '.join(unknown)} ». L'issue a peut-être changé depuis "
            "que la page a été ouverte."
        )

    return "\n".join(written)


def _quoted(answer: str) -> list[str]:
    """One answer as the blockquote lines that go inside its slot.

    An answer with nothing in it gives back the bare `>` stub the slot was
    prepared with, so that withdrawing an answer leaves the issue reading as
    the document with that blank unfilled.
    """
    lines = _neutralised(answer).split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return [">"]
    return [f"> {line}" if line.strip() else ">" for line in lines]


def _neutralised(answer: str) -> str:
    """An answer that can only ever be read as the answer it is.

    Line endings come from a browser, so they are normalised to the one the
    body uses. HTML comment openers and closers are turned into the character
    references GitHub renders as the very same characters, so that an answer
    reads on the issue exactly as it was written but can neither close a slot
    marker nor open a comment that swallows the questions below it. The escape
    is idempotent: an answer sent twice comes back the same.
    """
    normalised = answer.replace("\r\n", "\n").replace("\r", "\n")
    return normalised.replace("<!--", "&lt;!--").replace("-->", "--&gt;")
