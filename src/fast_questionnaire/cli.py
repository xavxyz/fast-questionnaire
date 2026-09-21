"""The command-line tool the author runs from their laptop."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .body import BodyTransformError, prepare
from .github import GitHubError, Repository, create_issue, refuse_public_repository
from .settings import MissingSetting, github_token

# The document's top-level heading, which becomes the issue's title. The first
# `#` line wins: a `to-questionnaire` document opens with it, so no fenced code
# block can come before it.
_TOP_LEVEL_HEADING = re.compile(r"^#\s+(?P<text>.+?)\s*#*\s*$")


class RefusedDocument(Exception):
    """A document the tool refuses to send as a Questionnaire."""


def new(argv: list[str] | None = None) -> int:
    """Create the Questionnaire issue in a private repository, print its URL."""
    parser = argparse.ArgumentParser(
        prog="new",
        description=(
            "Crée l'issue Questionnaire dans un dépôt privé à partir d'un "
            "fichier to-questionnaire, et affiche son adresse."
        ),
    )
    parser.add_argument(
        "file",
        type=Path,
        help="le fichier Markdown écrit avec la skill to-questionnaire",
    )
    parser.add_argument(
        "repository",
        help="le dépôt privé où l'issue est créée, sous la forme propriétaire/dépôt",
    )
    arguments = parser.parse_args(argv)

    try:
        document = arguments.file.read_text(encoding="utf-8")
    except OSError as unreadable:
        print(f"Fichier illisible : {unreadable}", file=sys.stderr)
        return 2

    try:
        # Everything the document alone can settle is settled first: a refusal
        # here costs no call to GitHub, and creates nothing.
        body = prepare(document)
        title = _title(document)
        repository = Repository.parse(arguments.repository)
        token = github_token()
        refuse_public_repository(repository, token)
        url = create_issue(repository, title, body, token)
    except (BodyTransformError, RefusedDocument, MissingSetting, GitHubError) as refusal:
        print(str(refusal), file=sys.stderr)
        return 1

    print(url)
    return 0


def _title(document: str) -> str:
    """The document's top-level heading."""
    for line in document.split("\n"):
        heading = _TOP_LEVEL_HEADING.match(line)
        if heading:
            return heading["text"]
    raise RefusedDocument(
        "Ce document n'a pas de titre de premier niveau : ajoute une ligne "
        "« # » au-dessus, elle donne son titre à l'issue."
    )
