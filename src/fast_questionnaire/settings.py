"""The settings the command-line tool and the app read from the environment.

The spec allows exactly two, and this version needs the first of them: the
GitHub token every write is made with. Locally it comes from a gitignored
`.env` at the root of the repository; on FastAPI Cloud, from a secret
environment variable. Nothing is ever read from a file that is committed.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

GITHUB_TOKEN = "GITHUB_TOKEN"


class MissingSetting(Exception):
    """A setting the tool and the app cannot run without."""


def github_token() -> str:
    """The GitHub token, from the environment or from a local `.env`.

    A variable already set in the environment wins over the `.env`, so a
    deployment never picks up a laptop's leftovers.
    """
    load_dotenv()
    token = os.environ.get(GITHUB_TOKEN, "").strip()
    if not token:
        raise MissingSetting(
            f"Jeton GitHub introuvable : définis {GITHUB_TOKEN} dans "
            "l'environnement, ou dans un fichier .env à la racine du dépôt "
            "(il n'est jamais commité)."
        )
    return token
