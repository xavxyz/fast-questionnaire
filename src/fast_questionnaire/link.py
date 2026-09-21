"""The secret link: the one place the key is computed and checked.

The command-line tool and the app both come here, so the links the tool prints
are the links the app accepts. A link's path carries owner, repository and
issue number, and its query carries a key: an HMAC-SHA256 of `owner/repo#number`
under the master secret. Nothing is stored per link, one issue's key cannot be
derived from another's, and rotating the master secret revokes every link at
once.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import quote

from .github import Repository

# Where the app answers, and so where a secret link points. The base lives here
# rather than in the environment because the settings are exactly two, the
# GitHub token and the master secret: deploying under another domain is a
# one-line change, in one place.
APP = "https://fast-questionnaire.fastapicloud.dev"

# The query parameter the key travels in.
KEY = "key"


def secret_link(repository: Repository, number: int, secret: str) -> str:
    """The secret link that opens one Questionnaire issue's page."""
    path = f"/{quote(repository.owner)}/{quote(repository.name)}/{number:d}"
    return f"{APP}{path}?{KEY}={key(repository, number, secret)}"


def key(repository: Repository, number: int, secret: str) -> str:
    """The key of one Questionnaire issue, and of no other.

    An HMAC-SHA256 of `owner/repo#number` under the master secret, in
    URL-safe base64 without padding so that it travels in a query as it is.
    """
    signed = hmac.new(
        secret.encode("utf-8"),
        _signed_name(repository, number).encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(signed).decode("ascii").rstrip("=")


def opens(repository: Repository, number: int, secret: str, offered: str) -> bool:
    """Whether the key offered opens that issue.

    The comparison is constant time: a wrong key tells its bearer nothing about
    how wrong it is.
    """
    return hmac.compare_digest(key(repository, number, secret), offered)


def _signed_name(repository: Repository, number: int) -> str:
    """What the key signs: the issue, named as GitHub names it."""
    return f"{repository}#{number:d}"
