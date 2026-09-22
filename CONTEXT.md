# fast-questionnaire

A respondent answers a Questionnaire, written as a GitHub issue, through a
secret link, without needing a GitHub account.

## Language

**Questionnaire**:
A `to-questionnaire` document held as the body of a GitHub issue in a private repository.
_Avoid_: Form, survey

**Author**:
The person who wrote the Questionnaire and is mentioned when answers arrive.
_Avoid_: Sender, owner

**Respondent**:
The person who opens the secret link and answers the Questionnaire.
_Avoid_: User, recipient

**Secret link**:
The one URL that opens a Questionnaire, its key derived from the issue it names.
_Avoid_: Share link, token

**Answer slot**:
The place in a Questionnaire where one answer is written, under its question.
_Avoid_: Field, input

**Draft**:
The respondent's unsent answers, kept only in their browser.
_Avoid_: Autosave

**Send**:
The respondent's one action: writing every answer on the page into the Questionnaire issue. A Send is either in flight, sent, or failed.
_Avoid_: Submit, save

**Sent**:
The state after a successful Send while no answer on the page has changed since, so that the page shows what the issue holds.
