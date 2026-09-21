"""The web app the respondent opens.

One secret link answers two requests: a GET shows the Questionnaire, a POST
sends the answers into its issue. Both go through the very same checks — the
key first, then the repository's visibility — and every other path is the
not-found page. It is thin glue over the body transform and the GitHub API, and
holds no format knowledge of its own.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .body import BodyTransformError, Part, Slot, answer, read
from .github import (
    GitHubError,
    Issue,
    PublicRepository,
    Repository,
    comment_on_issue,
    fetch_issue,
    refuse_public_repository,
    write_issue_body,
)
from .link import KEY, opens
from .page import draft_key, parts
from .settings import MissingSetting, github_token, master_secret

# What GitHub lets an owner or a repository be called. A name outside this is
# not-found like any other unknown path: the key is computed from these two
# words, so nothing else can ever carry one.
_NAMEABLE = re.compile(r"^[A-Za-z0-9._-]+$")

# What the page reads to know a send has just succeeded, and so to show the
# confirmation the respondent is owed.
ENVOYE = "envoye"

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class _Closed(Exception):
    """A request the app answers with a page instead of a Questionnaire."""

    def __init__(self, response: Response) -> None:
        super().__init__()
        self.response = response


@app.get("/{owner}/{name}/{number}", include_in_schema=False)
def questionnaire(
    request: Request,
    owner: str,
    name: str,
    number: str,
    key: str = "",
    envoye: str = "",
) -> Response:
    """Show one Questionnaire issue to whoever holds its secret link."""
    try:
        repository, issue_number, token = _opened(request, owner, name, number, key)
        issue = fetch_issue(repository, issue_number, token)
    except _Closed as closed:
        return closed.response
    except GitHubError as failed:
        return _error(request, str(failed), status_code=502)

    return _page(
        request, repository, issue_number, issue, key, envoye=bool(envoye)
    )


@app.post("/{owner}/{name}/{number}", include_in_schema=False)
async def envoi(
    request: Request, owner: str, name: str, number: str, key: str = ""
) -> Response:
    """Send the answers into the Questionnaire issue, then confirm.

    The body is re-read here, immediately before it is rewritten: GitHub has no
    conditional update, so the narrowest possible window is the only protection
    the author's own edits get.
    """
    try:
        repository, issue_number, token = _opened(request, owner, name, number, key)
    except _Closed as closed:
        return closed.response

    submitted = await request.form()
    try:
        issue = fetch_issue(repository, issue_number, token)
        document = read(issue.body)
        written = answer(issue.body, _answers(document, submitted))
        write_issue_body(repository, issue_number, written, token)
        comment_on_issue(
            repository, issue_number, _comment(issue.author, document), token
        )
    except GitHubError as failed:
        return _error(request, str(failed), status_code=502)
    except BodyTransformError as refused:
        return _error(request, str(refused), status_code=500)

    # A redirect, so that the page the respondent then reads is the issue as it
    # now stands rather than the form they just posted.
    return RedirectResponse(
        f"{request.url.path}?{urlencode({KEY: key, ENVOYE: '1'})}", status_code=303
    )


@app.api_route("/{path:path}", methods=["GET", "POST"], include_in_schema=False)
def not_found(request: Request, path: str) -> Response:
    """Reveal nothing about which issues exist."""
    return _not_found(request)


def _opened(
    request: Request, owner: str, name: str, number: str, key: str
) -> tuple[Repository, int, str]:
    """Everything a secret link must satisfy before an issue is touched.

    Showing and sending come through here alike, so that the page and the send
    can never disagree about which links open a Questionnaire.
    """
    if not (_NAMEABLE.match(owner) and _NAMEABLE.match(name) and number.isdigit()):
        raise _Closed(_not_found(request))
    repository = Repository(owner=owner, name=name)
    issue_number = int(number)

    try:
        secret = master_secret()
    except MissingSetting as missing:
        raise _Closed(_error(request, str(missing), status_code=500)) from missing

    # The key first: a wrong or missing one is told nothing, not even that the
    # repository exists.
    if not opens(repository, issue_number, secret, key):
        raise _Closed(_not_found(request))

    try:
        token = github_token()
        refuse_public_repository(repository, token)
    except PublicRepository as public:
        raise _Closed(_refused(request, str(public))) from public
    except MissingSetting as missing:
        raise _Closed(_error(request, str(missing), status_code=500)) from missing
    except GitHubError as failed:
        raise _Closed(_error(request, str(failed), status_code=502)) from failed

    return repository, issue_number, token


def _answers(document: list[Part], submitted) -> dict[str, str]:
    """The text the respondent sent for each slot the issue still holds.

    A slot the form says nothing about is left out rather than emptied: only a
    text area the respondent actually saw can withdraw an answer.
    """
    written: dict[str, str] = {}
    for part in document:
        if isinstance(part, Slot):
            sent = submitted.get(part.name)
            if isinstance(sent, str):
                written[part.name] = sent
    return written


def _comment(author: str, document: list[Part]) -> str:
    """What the issue tells its author once answers have been sent.

    A different sentence the first time and every time after, so that the
    author knows whether to read the answers or to re-read them.
    """
    answered = any(
        isinstance(part, Slot) and part.answer for part in document
    )
    mention = f"@{author} " if author else ""
    sent = "Réponses mises à jour." if answered else "Réponses envoyées."
    return f"{mention}{sent} Elles sont dans le corps de l'issue, sous chaque question."


def _page(
    request: Request,
    repository: Repository,
    issue_number: int,
    issue: Issue,
    key: str,
    envoye: bool,
) -> Response:
    """The Questionnaire as the respondent reads and answers it.

    The page carries the name the respondent's draft is kept under, and whether
    a send has just succeeded: the draft itself never leaves their browser.
    """
    return TEMPLATES.TemplateResponse(
        request,
        "questionnaire.html",
        {
            "title": issue.title,
            "parts": parts(read(issue.body)),
            "key": key,
            "envoye": envoye,
            "draft": draft_key(repository, issue_number),
        },
    )


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
    """GitHub, or the environment, kept the page from being shown or sent."""
    return TEMPLATES.TemplateResponse(
        request, "erreur.html", {"erreur": erreur}, status_code=status_code
    )
