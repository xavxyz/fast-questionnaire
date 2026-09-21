# fast-questionnaire

Answer a `to-questionnaire` issue through a secret link: a FastAPI app and a
command-line tool sharing one body transform.

## Develop

```sh
uv sync
uv run pytest
```

## Settings

Read from the environment, and locally from a `.env` at the root of the
repository — gitignored, never committed. See `.env.example`.

- `GITHUB_TOKEN` — a fine-grained personal access token with Issues read and
  write on the repositories a Questionnaire lives in.
- `MASTER_SECRET` — the secret every secret link's key is computed from.
  Changing it invalidates every link at once.

## Create a Questionnaire issue

Prepare the body of a `to-questionnaire` file, create the issue in a private
repository, and print its secret link. The issue's title is the document's
top-level heading. A public repository is refused before anything is created.

```sh
uv run new tests/fixtures/template.md EPF-MDE/complex-web-services
```

## Resend a secret link

Print the secret link of a Questionnaire issue that already exists — the same
link `new` printed when it created it.

```sh
uv run link https://github.com/EPF-MDE/complex-web-services/issues/12
```

The link's path carries owner, repository and issue number, and its query
carries a key: an HMAC-SHA256 of `owner/repo#number` under the master secret.
Nothing is stored per link, and one issue's link cannot be derived from
another's.

## Open the secret link

The link shows the whole Questionnaire as a French page: headings, emphasis,
links, lists and tables are rendered server-side, Mermaid blocks are drawn in
the browser by Mermaid loaded from a CDN, and a text area sits where each
answer slot is, pre-filled with the answer the issue holds.

A wrong or missing key shows a plain not-found page, the same one every
unknown path shows, and an issue in a public repository is refused even with a
valid key.

```sh
uv run fastapi dev
```

## Keep the draft in the browser

The answers are saved in the respondent's browser as they type, so closing the
tab or losing the connection loses nothing. The draft is kept in
`localStorage` under `fast-questionnaire:owner/repo#number`, so two
Questionnaires never share one, and it is restored over the pre-filled answers
when the page loads. Nothing of a draft ever reaches the app.

A send that fails leaves the draft where it is, for a retry. A send that
succeeds clears it, so the page then shows what the issue actually holds.

## Send the answers

Pressing send posts the same secret link. The send checks the key and the
repository's visibility exactly as the page does, re-reads the issue body
immediately before writing it, and runs Answer: each answer is written as a
blockquote under its question, an emptied answer restores its bare `>` stub,
and every byte outside the answer slots is left as it was, so the author's own
edits elsewhere in the body are kept. HTML comment openers and closers in an
answer are escaped: they read the same on GitHub, but can neither close a slot
marker nor open a comment.

The issue then gets a comment mentioning its author — « Réponses envoyées »
the first time, « Réponses mises à jour » every time after — and the page
reloads with a confirmation. The respondent can send as often as they like. A
GitHub failure, an expired token included, shows a French error page and
writes nothing further.

## Deploy

Every pull request against `main` runs the checks: the tests, `tach check` and
the cycle check. They show on the pull request as the `CI / checks` status
check. See `.github/workflows/ci.yml`. Pull requests never deploy and never see
the deploy secrets.

Every push to `main` runs the same checks, then deploys to FastAPI Cloud once
they all pass. A failing check means no deploy, and pushes to other branches
never deploy. See `.github/workflows/deploy.yml`.

The deploy job reads two repository secrets, `FASTAPI_CLOUD_TOKEN` and
`FASTAPI_CLOUD_APP_ID`, and nothing else. They are created once, by the
maintainer, while logged in to FastAPI Cloud:

```sh
uv run fastapi cloud setup-ci --secrets-only
```

The deploy token expires after a year; re-run the same command to regenerate it.

The app's own settings, `GITHUB_TOKEN` and `MASTER_SECRET`, are set as
environment variables in FastAPI Cloud, never in GitHub: the repository is
public, and so are its workflow logs.

`fastapi deploy` from a laptop linked to the app still works as a manual
fallback:

```sh
uv run fastapi deploy
```
