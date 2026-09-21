"""The web app the respondent opens.

Every path is not-found: the secret link route comes with the page.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.api_route("/{path:path}", methods=["GET", "POST"], include_in_schema=False)
async def not_found(path: str) -> None:
    """Reveal nothing about which issues exist."""
    raise HTTPException(status_code=404, detail="Page introuvable")
