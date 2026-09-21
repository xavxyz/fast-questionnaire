"""The GitHub calls the command-line tool and the app make.

It knows nothing of the Questionnaire body format: it takes a title and a body
already prepared, gives a body back as GitHub holds it, writes a body back as
the transform rewrote it, comments on an issue, and it answers one question
about a repository — is it private? Every failure comes back as a `GitHubError`
carrying a message meant for a human, never as a traceback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

API = "https://api.github.com"
API_VERSION = "2022-11-28"
TIMEOUT = 10.0

_REPOSITORY = re.compile(r"^(?P<owner>[^/\s]+)/(?P<name>[^/\s]+)$")


class GitHubError(Exception):
    """GitHub refused, failed, or could not be reached."""


class PublicRepository(GitHubError):
    """A repository a Questionnaire must never be created in."""


@dataclass(frozen=True)
class Repository:
    """A repository, as the author names it on the command line."""

    owner: str
    name: str

    @classmethod
    def parse(cls, argument: str) -> Repository:
        """The repository named `owner/repo`."""
        named = _REPOSITORY.match(argument.strip())
        if not named:
            raise GitHubError(
                f"Dépôt « {argument} » illisible : écris-le sous la forme "
                "propriétaire/dépôt, par exemple EPF-MDE/complex-web-services."
            )
        return cls(owner=named["owner"], name=named["name"])

    def __str__(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class Issue:
    """A Questionnaire issue, as GitHub holds it right now."""

    number: int
    title: str
    body: str
    # Who opened it: the author a comment mentions when answers are sent, so
    # that they are notified without watching the issue.
    author: str


def refuse_public_repository(repository: Repository, token: str) -> None:
    """Refuse a public repository, before anything is created or shown.

    A Questionnaire carries constraints the Instructor reveals only when asked,
    so it can only ever live where Students cannot read it.
    """
    described = _request("GET", f"/repos/{repository}", token)
    if not described.get("private", False):
        raise PublicRepository(
            f"Le dépôt {repository} est public : un Questionnaire y publierait "
            "des contraintes qui doivent rester hors de la vue des Étudiants. "
            "Choisis un dépôt privé."
        )


def create_issue(
    repository: Repository, title: str, body: str, token: str
) -> int:
    """Create the Questionnaire issue and give back its number.

    The number, with the repository, is all a secret link is made of.
    """
    created = _request(
        "POST",
        f"/repos/{repository}/issues",
        token,
        payload={"title": title, "body": body},
    )
    number = created.get("number")
    if not isinstance(number, int):
        raise GitHubError(
            f"GitHub a créé l'issue dans {repository} sans en donner le numéro : "
            "va la chercher sur le dépôt, puis demande son lien avec « link »."
        )
    return number


def fetch_issue(repository: Repository, number: int, token: str) -> Issue:
    """Read a Questionnaire issue, body included.

    The body is re-read every time the page is shown or written, so that what
    the respondent sees is what the issue holds, edits by the author included.
    """
    fetched = _request("GET", f"/repos/{repository}/issues/{number:d}", token)
    body = fetched.get("body")
    title = fetched.get("title")
    if not isinstance(title, str):
        raise GitHubError(
            f"GitHub a répondu pour {repository}#{number} sans donner d'issue."
        )
    return Issue(
        number=number,
        title=title,
        body=body if isinstance(body, str) else "",
        author=_author(fetched),
    )


def _author(fetched: dict) -> str:
    """The login of whoever opened the issue, when GitHub gives one."""
    opened_by = fetched.get("user")
    login = opened_by.get("login") if isinstance(opened_by, dict) else None
    return login if isinstance(login, str) else ""


def write_issue_body(
    repository: Repository, number: int, body: str, token: str
) -> None:
    """Write a Questionnaire issue's body back, answers included.

    The body written is the one the transform rewrote from the body read a
    moment earlier: GitHub offers no conditional update, so re-reading just
    before writing is all that stands between a send and the author's own
    edits.
    """
    _request(
        "PATCH",
        f"/repos/{repository}/issues/{number:d}",
        token,
        payload={"body": body},
    )


def comment_on_issue(
    repository: Repository, number: int, comment: str, token: str
) -> None:
    """Tell the author, on the issue itself, that answers have been sent."""
    _request(
        "POST",
        f"/repos/{repository}/issues/{number:d}/comments",
        token,
        payload={"body": comment},
    )


def _request(
    method: str, path: str, token: str, payload: dict | None = None
) -> dict:
    """One GitHub API call, with every failure turned into a `GitHubError`."""
    try:
        response = httpx.request(
            method,
            f"{API}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": API_VERSION,
            },
            json=payload,
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as unreachable:
        raise GitHubError(f"GitHub est injoignable : {unreachable}") from unreachable

    if response.is_error:
        raise GitHubError(_refusal(response))

    try:
        return response.json()
    except ValueError as unreadable:
        raise GitHubError(
            f"Réponse de GitHub illisible : {unreadable}"
        ) from unreadable


def _refusal(response: httpx.Response) -> str:
    """What to tell the author about a GitHub answer that is an error."""
    if response.status_code == 401:
        return (
            "GitHub refuse le jeton (401) : il est invalide ou expiré. "
            "Crée-en un nouveau et remets-le dans l'environnement."
        )
    if response.status_code == 404:
        return (
            "Dépôt introuvable (404) : soit il n'existe pas, soit le jeton "
            "ne l'a pas dans ses dépôts sélectionnés."
        )
    return f"GitHub a répondu {response.status_code} : {_detail(response)}"


def _detail(response: httpx.Response) -> str:
    """GitHub's own explanation, when it gives one."""
    try:
        explained = response.json()
    except ValueError:
        explained = None
    if isinstance(explained, dict) and explained.get("message"):
        return str(explained["message"])
    return response.text.strip() or "aucune explication."
