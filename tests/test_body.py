"""Tests for the body transform, exercised only through its public operations."""

import re
from pathlib import Path

import pytest

from fast_questionnaire.body import PrepareError, prepare

FIXTURES = Path(__file__).parent / "fixtures"

# The slot markers are part of the format Prepare publishes: GitHub renders them
# as nothing, so the tests read the body the way GitHub does, through them.
SLOT_MARKER = re.compile(r"^<!-- (?:q:(?P<name>\S+)|/q) -->$")


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def slot_names(body: str) -> list[str]:
    """The names of the answer slots in a body, in order."""
    matches = (SLOT_MARKER.match(line) for line in body.split("\n"))
    return [match["name"] for match in matches if match and match["name"]]


def without_slot_markers(body: str) -> str:
    """The body as it stands once the invisible slot markers are dropped."""
    return "\n".join(
        line for line in body.split("\n") if not SLOT_MARKER.match(line)
    )


def test_prepare_names_each_slot_after_the_heading_above_it():
    body = prepare(fixture("template.md"))

    assert slot_names(body) == [
        "what-load-is-the-system-expected-to-handle-at-launch",
        "anything-else",
    ]


def test_prepare_names_a_slot_after_a_section_that_is_itself_the_question():
    body = prepare(fixture("template.md"))

    # "## Anything else?" has no `###` question of its own.
    assert "anything-else" in slot_names(body)


def test_prepare_wraps_the_bare_stub_in_the_slot():
    body = prepare(fixture("template.md"))

    assert "<!-- q:anything-else -->\n>\n<!-- /q -->" in body


def test_prepare_names_the_slots_of_a_real_questionnaire():
    body = prepare(fixture("questionnaire-fr.md"))

    assert slot_names(body) == [
        "combien-de-creneaux-un-etudiant-peut-il-reserver-d-avance",
        "que-se-passe-t-il-quand-un-etudiant-ne-se-presente-pas",
        "le-service-peut-il-envoyer-un-rappel-par-mail-exemple-fr-15-minutes-avant-le-creneau",
        "combien-de-temps-l-historique-des-reservations-doit-il-etre-conserve",
        "autre-chose",
    ]


@pytest.mark.parametrize("name", ["template.md", "questionnaire-fr.md"])
def test_prepare_leaves_everything_outside_the_slots_unchanged(name):
    document = fixture(name)

    assert without_slot_markers(prepare(document)) == document


def test_prepare_ignores_a_bare_stub_inside_a_fenced_code_block():
    document = (
        "# Titre\n"
        "\n"
        "## Contexte\n"
        "\n"
        "```\n"
        "> ceci est un exemple\n"
        ">\n"
        "# pas un titre\n"
        "```\n"
        "\n"
        "### La seule question\n"
        "\n"
        ">\n"
    )

    body = prepare(document)

    assert slot_names(body) == ["la-seule-question"]


def test_prepare_refuses_a_document_without_an_answer_stub():
    document = "# Titre\n\n## Contexte\n\nRien à répondre ici.\n"

    with pytest.raises(PrepareError) as refusal:
        prepare(document)

    assert "aucun emplacement de réponse" in str(refusal.value)


def test_prepare_refuses_two_slots_that_would_share_a_name():
    document = (
        "# Titre\n"
        "\n"
        "## Réservations\n"
        "\n"
        "### Combien de temps ?\n"
        "\n"
        ">\n"
        "\n"
        "## Données\n"
        "\n"
        "### Combien de temps ?\n"
        "\n"
        ">\n"
    )

    with pytest.raises(PrepareError) as refusal:
        prepare(document)

    assert "combien-de-temps" in str(refusal.value)


def test_prepare_refuses_a_stub_with_no_heading_above_it():
    document = "Une question sans titre.\n\n>\n"

    with pytest.raises(PrepareError) as refusal:
        prepare(document)

    assert "titre" in str(refusal.value)
