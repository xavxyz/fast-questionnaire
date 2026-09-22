"""Tests for the letterhead, exercised only through its public operation."""

from pathlib import Path

from fast_questionnaire.letterhead import extract

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_extract_reads_a_french_letterhead():
    letterhead = extract(fixture("questionnaire-fr.md"))

    assert letterhead.title == (
        "Réservation des salles de la médiathèque : ce que l'équipe doit savoir"
    )
    assert letterhead.sender == "l'équipe produit"
    assert letterhead.recipient == "la responsable de la médiathèque"
    assert letterhead.objective == (
        "fixer les contraintes réelles du service de réservation, pour décider "
        "ce que l'équipe peut construire avant la rentrée."
    )
    assert letterhead.usage == (
        "recopiées sur [exemple/reservations#1]"
        "(https://github.com/exemple/reservations/issues/1), puis dans le "
        "dossier de conception."
    )


def test_extract_takes_the_french_letterhead_out_of_the_body():
    document = fixture("questionnaire-fr.md")

    body = extract(document).body

    assert body.startswith("## Contexte\n")
    assert document.endswith(body)
    assert "\n# " not in body
    assert "**Objectif :**" not in body
    assert "**De :**" not in body


def test_extract_reads_an_english_letterhead_and_takes_it_out_of_the_body():
    document = fixture("template.md")

    letterhead = extract(document)

    assert letterhead.title == "Launch capacity for the booking service"
    assert letterhead.sender == "the product team"
    assert letterhead.recipient == "the operations lead"
    assert letterhead.objective == (
        "decide how much capacity to provision before launch."
    )
    assert letterhead.usage == "copied into the design document."
    assert letterhead.body.startswith("## Context\n")
    assert document.endswith(letterhead.body)


def test_extract_leaves_a_document_without_a_letterhead_as_it_is():
    document = "## Contexte\n\nRien d'autre.\n\n### La question\n\n>\n"

    letterhead = extract(document)

    assert letterhead.body == document
    assert (
        letterhead.title,
        letterhead.sender,
        letterhead.recipient,
        letterhead.objective,
        letterhead.usage,
    ) == ("", "", "", "", "")


def test_extract_keeps_a_bold_opening_paragraph_that_is_not_a_letterhead():
    document = "# Titre\n\n**En bref :** rien à signaler.\n\n## Contexte\n"

    letterhead = extract(document)

    assert letterhead.body == "**En bref :** rien à signaler.\n\n## Contexte\n"
    assert letterhead.objective == ""


def test_extract_reads_a_letterhead_that_copies_someone_in():
    document = (
        "# Titre\n\n"
        "**Objectif :** comprendre.\n\n"
        "**De :** Xavier Cazalot, **À :** Fanny Sterna, "
        "**Copie :** Antoine Gademer, **Usage des réponses :** recopiées.\n\n"
        "## Contexte\n"
    )

    letterhead = extract(document)

    assert letterhead.sender == "Xavier Cazalot"
    assert letterhead.recipient == "Fanny Sterna"
    assert letterhead.copy == "Antoine Gademer"
    assert letterhead.usage == "recopiées."
    assert letterhead.body == "## Contexte\n"
