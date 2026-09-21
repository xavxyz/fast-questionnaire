You are implementing one GitHub issue in the `fast-questionnaire` repository,
autonomously, with no human available to answer questions.

## Your issue

Issue number: {{ISSUE_NUMBER}}

Title: {{ISSUE_TITLE}}

{{ISSUE_BODY}}

## The spec it was sliced from

Your issue is one ticket cut from a larger spec. The spec is here for context:
its "Testing Decisions", "Out of Scope" and implementation decisions bind you,
but its user stories are shared between tickets — build only what your issue
asks for.

{{PARENT_SPEC}}

## Rules

**Vocabulary.** If `CONTEXT.md` exists at the repository root, read it first and
use its terms exactly — in identifiers, test names, comments and commit
messages. Read any ADR under `docs/adr/` that touches the area you work in, and
do not contradict one silently. Otherwise, the issue's own terms (Questionnaire,
answer slot, Prepare, Read, Answer, secret link…) are the vocabulary: do not
invent synonyms for them.

**Scope.** Implement your issue and nothing else. Do not start work described by
another issue or listed under the issue's "Out of Scope", even if it looks
trivial and adjacent. Do not refactor code outside your issue's scope. Do not
edit `.sandcastle/` — that is the harness running you, and changing it has no
effect on this run.

**Tooling.** The application is Python, managed with `uv`, and tested with
`pytest`. Add dependencies with `uv add` (and `uv add --dev` for test-only
ones) so that `pyproject.toml` and `uv.lock` stay in step, and commit both.
Never commit `.env`, `.venv/` or caches; keep `.gitignore` covering them.

**Testing.** Follow the issue's "Testing Decisions" exactly. Where it names a
seam, test only through that seam's public operations — never its internals,
helpers or regular expressions — and do not add tests for what it says is not
tested. Build the seam test-first.

**Secrets.** This sandbox holds no GitHub token and no app secrets, and must
not: never hard-code one, and never make a test depend on the network or on a
real credential. Settings are read from the environment.

**The gate.** Before you finish, both of these must pass from a clean checkout.
Run them yourself and fix what they report:

```
uv sync --locked
uv run pytest
```

If you cannot get both green, say so honestly in your verdict rather than
weakening a test, skipping a test, or loosening an assertion to make them pass.
Deleting, `skip`-ing or `xfail`-ing a failing test to reach green counts as a
failed gate.

**Committing.** Commit your work with a clear message referencing
`#{{ISSUE_NUMBER}}`. Leave no uncommitted changes in the working tree. Do not
push, do not open a pull request, and do not touch the issue on GitHub — the
harness on the host does all of that after this run ends.

**Language.** All user-facing interface text is French. Code identifiers,
comments, commit messages and your verdict are English.

## When you are done

Work through your issue's acceptance criteria one at a time and verify each one
against the code you actually wrote — not against what you intended to write.
If the issue has no explicit acceptance-criteria list, use its user stories and
implementation decisions as the criteria.

Then emit your verdict as the last thing you output, in exactly this form:

<verdict>
{
  "gates": { "sync": true, "tests": true },
  "criteria": [
    { "text": "<the acceptance criterion, verbatim from the issue>", "met": true, "note": "" }
  ],
  "summary": "<two or three sentences: what you built and anything the reviewer should look at>"
}
</verdict>

Every criterion must appear in `criteria`, in the order the issue lists them.
Set `met` to `false` for anything you did not fully implement and explain why in
`note`. An honest `false` is useful; a `true` you cannot justify breaks the
pipeline that trusts this verdict to merge your work.

Then output <promise>COMPLETE</promise>
