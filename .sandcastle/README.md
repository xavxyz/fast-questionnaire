# Sandcastle harness

Drives the implementation of this repository's GitHub issues with Claude Code
agents running in Vercel Sandbox microVMs.

This directory is the orchestrator, not the application. The application is
Python; the harness is TypeScript because [Sandcastle](https://github.com/mattpocock/sandcastle)
is, so it keeps its own `package.json`, `node_modules`, `tsconfig.json` and test
run here rather than adding a Node project to the repository root. Agents are
told not to edit it, and editing it mid-run has no effect on a run already in
flight. All commands below run from the repository root:

```bash
npm --prefix .sandcastle run check   # typecheck the orchestrator
npm --prefix .sandcastle test        # its scheduling rules
```

## How a run works

1. The host reads the issue with `gh` and interpolates it into `prompt.md`.
2. A fresh Vercel Sandbox starts. Claude Code and `uv` are installed into it,
   and the repository is given to it as a git clone.
3. The agent implements the issue and must get `uv sync --locked` and
   `uv run pytest` green **inside the sandbox**, then commits.
4. The agent emits a `<verdict>` listing every acceptance criterion and whether
   it met it.
5. Sandcastle syncs the commits back to this checkout. The host then re-runs
   both gates itself against the synced branch — the agent's verdict is an
   input to the decision, never the decision — and rejects any run that modified
   `.sandcastle/`.
6. The host pushes the branch, opens a pull request, and — for issues not
   reserved for human review — merges it.

The sandbox never receives a GitHub token, a Vercel token, or the app's master
secret. Everything that writes to GitHub runs on your machine under your own
`gh` login.

The host-side gates run code the agent wrote, on your machine. They run with
the Vercel credentials and the Claude token removed from their environment, but
otherwise as you. Review what an agent wrote before you trust it with more.

## Setup

You need `gh` (logged in), `uv` and Node 24 on the host.

```bash
cp .sandcastle/.env.example .sandcastle/.env
claude setup-token          # paste the result as CLAUDE_CODE_OAUTH_TOKEN
cp .env.example .env        # then fill in VERCEL_TOKEN, VERCEL_TEAM_ID, VERCEL_PROJECT_ID
```

Sandboxes are billed to a Vercel project. Any project on your team works — this
app itself deploys to FastAPI Cloud, not Vercel, so the project exists only to
own the sandboxes. `npx vercel link` in this directory creates or picks one and
writes both IDs to `.vercel/project.json`.

Two env files, and which one a credential goes in is a security decision.
Sandcastle builds the sandbox's environment from the *keys* of
`.sandcastle/.env`, so everything there is readable by the autonomous agent —
and a key that is not there is never forwarded, even when the host process has
it. `.env` at the repository root is therefore host-only: the `sandcastle`
script loads it into the orchestrator, and nothing copies it into the microVM.
The Vercel token lives there because the agent has no business holding a
credential that can spend on your account. `main.mts` refuses to start if it
finds `VERCEL_TOKEN` in `.sandcastle/.env`, and refuses to start with no token at
all rather than failing later with an opaque SDK error. Then:

```bash
npm --prefix .sandcastle install
npm --prefix .sandcastle run sandcastle -- --dry-run    # prints the plan, runs nothing
npm --prefix .sandcastle run sandcastle -- --only 3     # one issue
npm --prefix .sandcastle run sandcastle                 # the whole pipeline
```

Run it from a clean working tree on `main`. The script refuses to start
otherwise, because agents' commits are applied onto this checkout.

`SANDCASTLE_MODEL` overrides the model if you want to trade quality for compute
on a wave you are less worried about.

## Adding issues

`WAVES` in `main.mts` is the execution order and `REVIEW_BY_HUMAN` the issues
that stop at a draft pull request. Add an issue there once it is labelled
`ready-for-agent`, and record what it depends on as a GitHub native issue
dependency — that graph, not the waves, decides what a failure skips.

## When an agent fails

One agent dying does not end the run. Its siblings in the same wave are left to
finish, whatever they produce is landed as usual, and the failure is recorded
against that issue.

What happens next depends on what actually needed that issue. The waves are an
execution order, not a dependency graph; the real one lives in GitHub's native
issue dependencies, which `main.mts` reads at startup. Only the issues that
transitively depend on a failure are skipped. If those dependencies cannot be
read at all, the run stops at the first failure rather than guess.

The run ends with a summary of what landed, what failed and what was skipped,
and exits non-zero if anything failed. An agent that got as far as its own
branch leaves it behind, along with its transcript under `.sandcastle/logs/`;
both are named in the summary so you can read them.

Neither needs cleaning up before you retry. Sandcastle ignores `baseBranch`
when a branch already exists, so a leftover branch cannot be reused — the next
run therefore reclaims it itself: it removes the worktree still holding it, if
Sandcastle kept one because the agent left uncommitted changes, parks the
branch's commits on a ref under `refs/sandcastle/attempts/issue-N/`, and cuts a
fresh branch from `main`. The ref is printed as it goes, so a failed attempt
worth salvaging survives (`git log <ref>`, `git checkout -b … <ref>`);
uncommitted changes in a removed worktree do not. A branch held by a worktree
Sandcastle did not create is left strictly alone and fails that issue instead.

## It runs unattended

`REVIEW_BY_HUMAN` is empty, so every ticket merges as soon as the host's gates
pass and its agent reports every acceptance criterion met, and the next wave
branches from that merge. Add an issue to `REVIEW_BY_HUMAN` to make the run open
a draft for it and stop there instead; merge the draft and run the same command
again — closed issues are skipped, so it picks up where it left off.

## Things that will bite

**Tickets lean on their spec.** Tickets sliced by `/to-tickets` name their
spec under a `## Parent` heading and defer to it for testing decisions and
scope. The sandbox cannot read GitHub, so the host fetches that parent and
interpolates it into `prompt.md` as `{{PARENT_SPEC}}`.

**Criteria the sandbox cannot meet stop the chain.** An agent that honestly
reports a criterion unmet makes its ticket unlandable, and everything
downstream is skipped. A criterion that needs GitHub, a real credential or a
browser belongs in a human ticket, not in one listed in `WAVES`.

**The install hooks.** The Vercel provider ignores `.sandcastle/Dockerfile`, so
`claude` and `uv` are installed by `onSandboxReady` hooks in `main.mts` and
symlinked onto `PATH`. If a run dies immediately with a command-not-found, those
hooks are what to fix. The sandbox runs the `node24` image, the one this harness
was first proven on; `uv` downloads whatever Python `pyproject.toml` asks for.

**The compute budget, not the clock.** Vercel Hobby gives 5 Active-CPU-hours per
month; when they are gone, sandbox creation is paused until the billing cycle
resets. Installing dependencies and running tests are what actually consume
it — the agent waiting on model responses is nearly free. `main.mts` sets the
session timeout explicitly because the provider's own default is 5 minutes.

**A dropped agent stream is not a failed agent.** `@vercel/sandbox` runs a
command by holding one HTTP stream open from launch to exit and reading two
chunks from it. For an agent that socket is silent for an hour, so an idle
timeout anywhere on the path closes it and the run dies with `exec failed:
terminated` or `Stream ended before command finished` — while the sandbox is
still working. `detached-exec.mts` takes the agent off that socket: the command
runs detached inside the sandbox and the host polls for its exit code, so every
request is sub-second and a failed poll is simply retried. `@vercel/sandbox` is
pinned to the 1.10 line this workaround was written against.

**Sync-out rewrites commit SHAs.** Commits come back through
`git format-patch` / `git am --3way`. A long, divergent run can fail to apply
cleanly. That looks like lost work but is not: the patches are on disk under
`.sandcastle/patches/`.
