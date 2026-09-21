"""The command-line tool the author runs from their laptop."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .body import BodyTransformError, prepare
from .github import GitHubError, Repository, create_issue, refuse_public_repository
from .link import secret_link
from .settings import MissingSetting, github_token, master_secret

# The document's top-level heading, which becomes the issue's title. The first
# `#` line wins: a `to-questionnaire` document opens with it, so no fenced code
# block can come before it.
_TOP_LEVEL_HEADING = re.compile(r"^#\s+(?P<text>.+?)\s*#*\s*$")

# An issue as GitHub addresses it, with whatever query or anchor the author
# copied along with it from their browser.
_ISSUE_URL = re.compile(
    r"^https?://(?:www\.)?github\.com"
    r"/(?P<owner>[^/\s]+)/(?P<name>[^/\s]+)/issues/(?P<number>\d+)/?"
    r"(?:[?#]\S*)?$"
)


class RefusedDocument(Exception):
    """A document the tool refuses to send as a Questionnaire."""


class RefusedIssueURL(Exception):
    """An issue address the tool cannot read."""


def new(argv: list[str] | None = None) -> int:
    """Create the Questionnaire issue in a private repository, print its link."""
    parser = argparse.ArgumentParser(
        prog="new",
        description=(
            "Crée l'issue Questionnaire dans un dépôt privé à partir d'un "
            "fichier to-questionnaire, et affiche son lien secret."
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
        # Everything the document and the environment alone can settle is
        # settled first: a refusal here costs no call to GitHub, and creates
        # nothing. A Questionnaire issue nobody can be given a link to would be
        # worse than no issue at all.
        body = prepare(document)
        title = _title(document)
        repository = Repository.parse(arguments.repository)
        token = github_token()
        secret = master_secret()
        refuse_public_repository(repository, token)
        number = create_issue(repository, title, body, token)
    except _Refusal as refusal:
        print(str(refusal), file=sys.stderr)
        return 1

    print(secret_link(repository, number, secret))
    return 0


def link(argv: list[str] | None = None) -> int:
    """Print the secret link of a Questionnaire issue that already exists."""
    parser = argparse.ArgumentParser(
        prog="link",
        description=(
            "Affiche le lien secret d'une issue Questionnaire existante, "
            "pour renvoyer un lien égaré."
        ),
    )
    parser.add_argument(
        "issue_url",
        metavar="issue-url",
        help="l'adresse de l'issue, par exemple "
        "https://github.com/EPF-MDE/complex-web-services/issues/12",
    )
    arguments = parser.parse_args(argv)

    try:
        repository, number = _issue(arguments.issue_url)
        secret = master_secret()
    except _Refusal as refusal:
        print(str(refusal), file=sys.stderr)
        return 1

    print(secret_link(repository, number, secret))
    return 0


# Everything the tool refuses or fails at, told to the author as a sentence
# rather than as a traceback.
_Refusal = (
    BodyTransformError,
    RefusedDocument,
    RefusedIssueURL,
    MissingSetting,
    GitHubError,
)


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


def _issue(issue_url: str) -> tuple[Repository, int]:
    """The repository and the number an issue address carries."""
    addressed = _ISSUE_URL.match(issue_url.strip())
    if not addressed:
        raise RefusedIssueURL(
            f"Adresse d'issue « {issue_url} » illisible : copie-la depuis le "
            "navigateur, par exemple "
            "https://github.com/EPF-MDE/complex-web-services/issues/12."
        )
    repository = Repository(owner=addressed["owner"], name=addressed["name"])
    return repository, int(addressed["number"])
