"""The settings the command-line tool and the app read from the environment.

There are exactly two: the GitHub token every write is made with, and the
master secret every secret link is computed from. Locally they come from a
gitignored `.env` at the root of the repository; on FastAPI Cloud, from secret
environment variables. Nothing is ever read from a file that is committed.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

GITHUB_TOKEN = "GITHUB_TOKEN"
MASTER_SECRET = "MASTER_SECRET"


class MissingSetting(Exception):
    """A setting the tool and the app cannot run without."""


def github_token() -> str:
    """The GitHub token, from the environment or from a local `.env`."""
    return _setting(
        GITHUB_TOKEN,
        f"Jeton GitHub introuvable : définis {GITHUB_TOKEN} dans "
        "l'environnement, ou dans un fichier .env à la racine du dépôt "
        "(il n'est jamais commité).",
    )


def master_secret() -> str:
    """The master secret every secret link is computed from.

    Changing it invalidates every link ever printed, which is the kill switch:
    it is never written down anywhere but the environment.
    """
    return _setting(
        MASTER_SECRET,
        f"Secret maître introuvable : définis {MASTER_SECRET} dans "
        "l'environnement, ou dans un fichier .env à la racine du dépôt "
        "(il n'est jamais commité). Sans lui, aucun lien secret ne peut être "
        "calculé.",
    )


def _setting(name: str, missing: str) -> str:
    """One setting, from the environment or from a local `.env`.

    A variable already set in the environment wins over the `.env`, so a
    deployment never picks up a laptop's leftovers.
    """
    load_dotenv()
    value = os.environ.get(name, "").strip()
    if not value:
        raise MissingSetting(missing)
    return value
