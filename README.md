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
answer slot is, pre-filled with the answer the issue holds. Sending the
answers back is not there yet.

A wrong or missing key shows a plain not-found page, the same one every
unknown path shows, and an issue in a public repository is refused even with a
valid key.

```sh
uv run fastapi dev
```
