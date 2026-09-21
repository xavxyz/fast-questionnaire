## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for `xavxyz/fast-questionnaire` via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

- Package boundaries are machine-checked: read `src/fast_questionnaire/README.md` before adding a package, or importing across one.
