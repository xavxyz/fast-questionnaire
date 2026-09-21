# fast-questionnaire

Answer a `to-questionnaire` issue through a secret link: a FastAPI app and a
command-line tool sharing one body transform.

## Develop

```sh
uv sync
uv run pytest
```

## Prepare a Questionnaire body

Print the issue body a `to-questionnaire` file would become. Nothing is created
on GitHub.

```sh
uv run new tests/fixtures/template.md
```

## Run the app

```sh
uv run fastapi dev
```
