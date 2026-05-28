---
name: skillopt-codexy
description: Use when a Codex agent needs to train, audit, and promote or reject repository-specific AGENTS.md instructions with SkillOpt-Codexy. Applies to configuring a project repo for SkillOpt training, creating repeatable run scripts, running Codex-backed optimization, writing run reports, and deciding whether candidate instructions should be promoted.
---

# SkillOpt-Codexy

Use this skill to run SkillOpt-Codexy against a project repository and turn training output into an audited repo-instruction change. Do not edit AGENTS.md directly from training results; promote only after the audit supports a durable repo rule.

For audit and promotion decisions, read [references/skillopt-train-promote.md](references/skillopt-train-promote.md). It is the canonical gate for train, audit, promote, partial-promote, keep-experimental, and reject decisions.

## Locate SkillOpt-Codexy

Find the SkillOpt-Codexy code before configuring the target repo:

1. If `SKILLOPT_CODEXY_ROOT` is set, use that.
2. Else check common installs:
   - `<target-repo>/.agents/vendor/SkillOpt-Codexy`
   - `<target-repo>/.agents/SkillOpt-Codexy`
   - `~/.codex/SkillOpt-Codexy`
   - `~/code/SkillOpt-Codexy`
   - `~/code/skillz`
3. Confirm it contains `scripts/train.py`, `scripts/eval_only.py`, and `skillopt/run_report.py`.
4. If missing, clone `https://github.com/0xCozart/SkillOpt-Codexy.git` to either `~/.codex/SkillOpt-Codexy` for shared use or `.agents/vendor/SkillOpt-Codexy` for project-local use.

## Configure A Project

From the target repository root, run:

```bash
python3 "$SKILLOPT_CODEXY_ROOT/scripts/configure_target_repo.py" --repo .
```

If `SKILLOPT_CODEXY_ROOT` is not set, run the script by absolute path from the located SkillOpt-Codexy checkout. The script creates:

- `tooling/skillopt/initial-skill.md`
- `tooling/skillopt/PROMOTION_AUDIT.md`
- `tooling/skillopt/run-skillopt.sh`
- `tooling/skillopt/RUN_LOG.md`
- package manager scripts when a root `package.json` exists

After configuration, inspect `tooling/skillopt/initial-skill.md`. Replace scaffold text with the actual current repo instructions, workflow rules, and failure patterns that SkillOpt should optimize.

## Train

Prefer the project-local launcher:

```bash
npm run skillopt:train -- \
  --config configs/searchqa/default.yaml \
  --split_dir /absolute/path/to/split-data \
  --backend codex \
  --optimizer_model gpt-5.5 \
  --target_model gpt-5.5
```

If there is no `package.json`, run:

```bash
tooling/skillopt/run-skillopt.sh train \
  --config configs/searchqa/default.yaml \
  --split_dir /absolute/path/to/split-data \
  --backend codex
```

Use small, representative split data first. A training run is evidence, not authority.

## Report And Audit

After training, generate a report for the run directory:

```bash
npm run skillopt:report -- --out_root tmp/skillopt/latest
```

or:

```bash
tooling/skillopt/run-skillopt.sh report --out_root tmp/skillopt/latest
```

Then run the promotion gate from [references/skillopt-train-promote.md](references/skillopt-train-promote.md) and write the audit artifact it requires.
Use that reference's `Final Response` section for the user-facing closeout after any promote, partial-promote, keep-experimental, or reject decision.

Audit style:

- Use `$grill-with-docs` when the repo has authority docs such as `AGENTS.md`, `CLAUDE.md`, `docs/CODEBASE_MAP.md`, `CONTEXT.md`, ADRs, product docs, or runbooks that can validate the candidate.
- Use `$grill-me` when there are no useful repo docs and the decision is mainly product/workflow judgment.
- Answer from artifacts and codebase evidence first. Ask the user only for product judgment that cannot be resolved locally.

Also fill `tooling/skillopt/PROMOTION_AUDIT.md` when present:

- Better case: exact candidate instruction, artifact paths, score movement, and concrete repo failure it prevents.
- Worse case: overfit risks, benchmark-specific wording, conflict with existing repo authority, and second-order effects.
- Decision: `promote`, `partial-promote`, or `reject`.

## Promote Or Reject

Promote only durable, repo-general rules after the canonical gate is complete. Prefer placing candidate text in `tooling/skillopt/initial-skill.md` first. Edit AGENTS.md only when all are true:

- The candidate fixes a repeated real workflow failure.
- The wording is not benchmark-specific.
- It does not conflict with project docs, ownership rules, security rules, or existing AGENTS.md instructions.
- The audit includes a clear reject case and still supports promotion.

When rejecting, keep the run report and audit. Do not delete failed runs; they explain why a rule was not adopted.

## Verification

Before claiming completion:

- Run the target repo's relevant tests or lint after any AGENTS.md/package script changes.
- Confirm `tooling/skillopt/run-skillopt.sh report --out_root <run>` writes `RUN_REPORT.md`.
- Confirm `tooling/skillopt/RUN_LOG.md` contains one entry for the run, not duplicates.
