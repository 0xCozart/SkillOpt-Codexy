# SkillOpt Train Promote

Own the whole SkillOpt loop: run training when requested, audit the generated candidate with a grill-based promotion gate, then promote, partially promote, keep experimental, or reject.

## Modes

Choose one mode from the user's wording:

- `train-audit-promote`: user asks to run/train SkillOpt and decide promotion.
- `audit-latest`: user asks to audit latest SkillOpt output.
- `audit-run`: user gives a specific `tmp/skillopt/<run>` path.
- `audit-all`: user asks for all/pending SkillOpt outputs.

Do not run training when the user only asks to audit. Do not audit unrelated global Codex skills unless explicitly asked; "all skills" here means all SkillOpt-generated candidate skills in the current repo.

## Preflight

Before training or promotion:

1. Confirm repo support:
   - Prefer `npm run skillopt:train` when present.
   - Otherwise look for `tooling/skillopt/run-skillopt.sh`.
   - If neither exists, stop and report that the repo is not wired for SkillOpt.
2. Check for an active run in this repo:
   - Inspect processes for `skillopt:train`, `run-skillopt.sh`, or `scripts/train.py` using this repo path.
   - If one is active, do not start another. Monitor it if the user asked to run, or audit it after completion if artifacts exist.
3. Capture current state:
   - `git status --short`
   - note unrelated dirty files and do not revert them.
4. Read repo authority that exists:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `docs/CODEBASE_MAP.md`
   - `CONTEXT.md`
   - ADRs
   - README / PRD / product authority docs relevant to the candidate
   - `tooling/skillopt/PROMOTION_AUDIT.md` if present

## Training

For `train-audit-promote`:

1. Run the repo command in the foreground:
   - `npm run skillopt:train`, or
   - `tooling/skillopt/run-skillopt.sh train ...`
2. Do not leave the command running when finalizing the turn.
3. If training fails:
   - inspect the run directory if one was created
   - write or update an audit artifact saying no promotion happened
   - do not promote
4. If training succeeds:
   - use the newest run directory printed by the command or newest `tmp/skillopt/*/summary.json`
   - prefer `RUN_REPORT.md` when present

## Required Run Artifacts

For each audited run, read:

- `tooling/skillopt/initial-skill.md`
- `<run>/best_skill.md`
- `<run>/RUN_REPORT.md`, if present
- `<run>/summary.json`
- `<run>/history.json`
- `<run>/slow_update/**/slow_result.json`, if present
- rollout/eval result files needed to prove improved or regressed item behavior

If `best_skill.md` or enough scoring evidence is missing, decision is `keep experiment only`.

## Grill Promotion Gate

Use `$grill-with-docs` when repo docs or authority files can validate terminology, product truths, ownership rules, or existing decisions. Use `$grill-me` when there are no useful docs and the promotion decision depends on product/workflow judgment.

Use the repo's `PROMOTION_AUDIT.md` questions when available. Otherwise apply this gate. Answer from artifacts first; ask the user only for product judgment that cannot be resolved from repo docs or run artifacts.

For each run, make both cases:

1. What exact behavior improved?
   - cite item ids, baseline result, candidate result, and artifact paths.
2. What exact behavior got worse?
   - cite regressions, failed examples, or say no regression evidence was found.
3. Did the candidate add broader or vaguer instructions?
   - quote or summarize risky text.
4. Did the candidate preserve repo product truths and authority docs?
   - check existing `AGENTS.md`, `CLAUDE.md`, CODEBASE_MAP, README, PRDs, and runbooks.
5. Did the candidate conflict with existing instructions?
   - cite exact conflict or say none found.
6. Is the dataset large enough for the claim?
   - small train/test splits mean directional evidence only.
7. What is the narrowest safe promotion?
   - prefer `tooling/skillopt/initial-skill.md`.
8. What must not be promoted?
   - list overfit, benchmark-only, redundant, broad, or unsafe instructions.

Important: treat `<run>/best_skill.md` as the final candidate. If the run report or slow-update artifacts show force-injected slow-update guidance, audit that final content, not only the score-gated `best_step` diff.

## Decisions

Choose exactly one per run:

- `promote unchanged`: all candidate guidance is narrow, evidence-backed, and consistent with repo authority.
- `promote partial edits only`: some guidance is useful but the candidate is mixed, broad, overfit, or based on a small dataset.
- `keep experiment only`: evidence is weak, incomplete, too benchmark-specific, or not worth durable guidance.
- `reject candidate`: guidance conflicts with repo truth, degrades behavior, or creates unsafe agent behavior.

Default to `promote partial edits only` for small datasets with large score jumps.

## Promotion Rules

Only promote after the grill gate is complete.

- Never blindly copy `best_skill.md` over `AGENTS.md` or `initial-skill.md`.
- Prefer minimal edits to `tooling/skillopt/initial-skill.md`.
- Edit `AGENTS.md` only when the audit proves a durable repo-wide instruction gap.
- Preserve unrelated dirty files.
- If target files already have unrelated user edits, patch only the audited lines or stop and report the conflict.
- If rejecting or keeping experimental, do not modify guidance files.

## Audit Artifact

Write an artifact for every audited run:

`tooling/skillopt/audits/<run-name>-promotion-audit.md`

Include:

- run path and input artifacts
- score summary
- candidate diff summary
- better case
- worse case
- grill route used: `$grill-with-docs` or `$grill-me`
- slow-update notes, if any
- decision
- promoted edits, if any
- rejected edits
- `AGENTS.md` changed: yes/no and why
- verification

For `audit-all`, write one artifact per run and a short aggregate summary in `tooling/skillopt/audits/INDEX.md`.

## Verification

After edits:

- Run `git diff --check` on touched files.
- Run repo syntax/parse checks when package or shell files changed.
- If only markdown guidance changed, at least verify files exist and links/paths referenced in the audit are valid.
- Report skipped checks explicitly.
