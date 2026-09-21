"""Tests for the body transform, exercised only through its public operations."""

import re
from pathlib import Path

import pytest

from fast_questionnaire.body import PrepareError, Segment, Slot, prepare, read

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


# --- Read -------------------------------------------------------------------

# A body as GitHub holds it once an answer has been sent: the answer sits in
# its slot as a blockquote, which is what the issue shows the author.
ANSWERED_BODY = (
    "# Réservation des salles\n"
    "\n"
    "## Réservations\n"
    "\n"
    "### Combien de créneaux d'avance ?\n"
    "\n"
    "<!-- q:combien-de-creneaux-d-avance -->\n"
    "> Deux par jour.\n"
    ">\n"
    "> Sept jours glissants.\n"
    "<!-- /q -->\n"
    "\n"
    "## Autre chose ?\n"
    "\n"
    "<!-- q:autre-chose -->\n"
    ">\n"
    "<!-- /q -->\n"
)


def slots(document: list) -> list[Slot]:
    """The answer slots of a document Read gave back, in order."""
    return [part for part in document if isinstance(part, Slot)]


def segments(document: list) -> list[Segment]:
    """The Markdown segments of a document Read gave back, in order."""
    return [part for part in document if isinstance(part, Segment)]


@pytest.mark.parametrize("name", ["template.md", "questionnaire-fr.md"])
def test_read_gives_back_a_freshly_prepared_body_with_every_slot_empty(name):
    document = read(prepare(fixture(name)))

    assert slots(document)
    assert [slot.answer for slot in slots(document)] == [""] * len(slots(document))


def test_read_gives_back_the_slots_in_the_order_prepare_named_them():
    body = prepare(fixture("questionnaire-fr.md"))

    assert [slot.name for slot in slots(read(body))] == slot_names(body)


def test_read_carries_each_slot_s_name_and_heading():
    document = read(prepare(fixture("template.md")))

    assert [(slot.name, slot.heading) for slot in slots(document)] == [
        (
            "what-load-is-the-system-expected-to-handle-at-launch",
            "What load is the system expected to handle at launch?",
        ),
        ("anything-else", "Anything else?"),
    ]


def test_read_strips_the_blockquote_prefix_from_an_answered_slot():
    answered, catch_all = slots(read(ANSWERED_BODY))

    assert answered.answer == "Deux par jour.\n\nSept jours glissants."
    assert catch_all.answer == ""


def test_read_gives_back_markdown_segments_interleaved_with_the_slots():
    document = read(prepare(fixture("template.md")))

    assert [type(part) for part in document] == [Segment, Slot, Segment, Slot]
    assert "## Context" in document[0].markdown
    assert "## Anything else?" in document[2].markdown


def test_read_drops_the_invisible_slot_markers_from_the_markdown():
    document = read(prepare(fixture("questionnaire-fr.md")))

    assert all("<!--" not in segment.markdown for segment in segments(document))


def test_read_keeps_a_mermaid_block_inside_its_markdown_segment():
    document = read(prepare(fixture("questionnaire-fr.md")))

    assert "```mermaid" in document[0].markdown
    assert "flowchart LR" in document[0].markdown


def test_read_gives_back_a_body_without_a_slot_as_one_markdown_segment():
    body = "# Titre\n\nRien à répondre ici."

    assert read(body) == [Segment(markdown=body)]


def test_read_does_not_take_a_slot_s_heading_from_inside_a_code_block():
    body = prepare(
        "# Titre\n"
        "\n"
        "### La seule question\n"
        "\n"
        "```\n"
        "### pas un titre\n"
        "```\n"
        "\n"
        ">\n"
    )

    [slot] = slots(read(body))

    assert slot.heading == "La seule question"


def test_read_keeps_name_and_answer_when_the_question_s_wording_changed():
    """The author fixes a typo on GitHub; the respondent's answer stays put."""
    reworded = ANSWERED_BODY.replace(
        "### Combien de créneaux d'avance ?",
        "### Combien de créneaux un étudiant peut-il réserver d'avance ?",
    )

    answered, _ = slots(read(reworded))

    assert answered.name == "combien-de-creneaux-d-avance"
    assert (
        answered.heading
        == "Combien de créneaux un étudiant peut-il réserver d'avance ?"
    )
    assert answered.answer == "Deux par jour.\n\nSept jours glissants."


def test_read_keeps_an_answer_that_quotes_something_itself():
    body = (
        "### La question\n"
        "\n"
        "<!-- q:la-question -->\n"
        "> Elle m'a dit :\n"
        ">\n"
        "> > deux par jour\n"
        "<!-- /q -->\n"
    )

    [slot] = slots(read(body))

    assert slot.answer == "Elle m'a dit :\n\n> deux par jour"
