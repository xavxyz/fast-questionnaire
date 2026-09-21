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

## Create a Questionnaire issue

Prepare the body of a `to-questionnaire` file, create the issue in a private
repository, and print its URL. The issue's title is the document's top-level
heading. A public repository is refused before anything is created.

```sh
uv run new tests/fixtures/template.md EPF-MDE/complex-web-services
```

## Run the app

```sh
uv run fastapi dev
```
