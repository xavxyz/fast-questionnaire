"""The web app the respondent opens.

One route answers a secret link; every other path is the not-found page. The
route checks the key before anything else, refuses a public repository even
with a valid key, then reads the issue and shows the Questionnaire. It is thin
glue over the body transform and the GitHub API, and holds no format knowledge
of its own.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.templating import Jinja2Templates

from .body import read
from .github import (
    GitHubError,
    PublicRepository,
    Repository,
    fetch_issue,
    refuse_public_repository,
)
from .link import opens
from .page import parts
from .settings import MissingSetting, github_token, master_secret

# What GitHub lets an owner or a repository be called. A name outside this is
# not-found like any other unknown path: the key is computed from these two
# words, so nothing else can ever carry one.
_NAMEABLE = re.compile(r"^[A-Za-z0-9._-]+$")

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/{owner}/{name}/{number}", include_in_schema=False)
def questionnaire(
    request: Request, owner: str, name: str, number: str, key: str = ""
) -> Response:
    """Show one Questionnaire issue to whoever holds its secret link."""
    if not (_NAMEABLE.match(owner) and _NAMEABLE.match(name) and number.isdigit()):
        return _not_found(request)
    repository = Repository(owner=owner, name=name)
    issue_number = int(number)

    try:
        secret = master_secret()
    except MissingSetting as missing:
        return _error(request, str(missing), status_code=500)

    # The key first: a wrong or missing one is told nothing, not even that the
    # repository exists.
    if not opens(repository, issue_number, secret, key):
        return _not_found(request)

    try:
        token = github_token()
        refuse_public_repository(repository, token)
        issue = fetch_issue(repository, issue_number, token)
    except PublicRepository as public:
        return _refused(request, str(public))
    except MissingSetting as missing:
        return _error(request, str(missing), status_code=500)
    except GitHubError as failed:
        return _error(request, str(failed), status_code=502)

    return TEMPLATES.TemplateResponse(
        request,
        "questionnaire.html",
        {"title": issue.title, "parts": parts(read(issue.body))},
    )


@app.api_route("/{path:path}", methods=["GET", "POST"], include_in_schema=False)
def not_found(request: Request, path: str) -> Response:
    """Reveal nothing about which issues exist."""
    return _not_found(request)


def _not_found(request: Request) -> Response:
    """The one plain page a link that opens nothing ever shows."""
    return TEMPLATES.TemplateResponse(
        request, "introuvable.html", status_code=404
    )


def _refused(request: Request, refus: str) -> Response:
    """A Questionnaire the app refuses to show, valid key or not."""
    return TEMPLATES.TemplateResponse(
        request, "refus.html", {"refus": refus}, status_code=403
    )


def _error(request: Request, erreur: str, status_code: int) -> Response:
    """GitHub, or the environment, kept the page from being shown."""
    return TEMPLATES.TemplateResponse(
        request, "erreur.html", {"erreur": erreur}, status_code=status_code
    )
