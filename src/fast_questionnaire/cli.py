"""The command-line tool the author runs from their laptop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .body import BodyTransformError, prepare


def new(argv: list[str] | None = None) -> int:
    """Print the Questionnaire body a `to-questionnaire` file would become."""
    parser = argparse.ArgumentParser(
        prog="new",
        description=(
            "Prépare le corps de l'issue à partir d'un fichier to-questionnaire "
            "et l'affiche. Rien n'est créé sur GitHub."
        ),
    )
    parser.add_argument(
        "file",
        type=Path,
        help="le fichier Markdown écrit avec la skill to-questionnaire",
    )
    arguments = parser.parse_args(argv)

    try:
        document = arguments.file.read_text(encoding="utf-8")
    except OSError as unreadable:
        print(f"Fichier illisible : {unreadable}", file=sys.stderr)
        return 2

    try:
        body = prepare(document)
    except BodyTransformError as refusal:
        print(str(refusal), file=sys.stderr)
        return 1

    sys.stdout.write(body if body.endswith("\n") else body + "\n")
    return 0
