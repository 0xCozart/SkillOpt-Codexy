from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


RUNNER = """#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-}"
if [[ -z "$COMMAND" ]]; then
  echo "usage: tooling/skillopt/run-skillopt.sh <train|eval|report> [args...]" >&2
  exit 2
fi
shift

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ -n "${SKILLOPT_CODEXY_ROOT:-}" ]]; then
  CODEXY_ROOT="$SKILLOPT_CODEXY_ROOT"
elif [[ -d "$REPO_ROOT/.agents/vendor/SkillOpt-Codexy" ]]; then
  CODEXY_ROOT="$REPO_ROOT/.agents/vendor/SkillOpt-Codexy"
elif [[ -d "$REPO_ROOT/.agents/SkillOpt-Codexy" ]]; then
  CODEXY_ROOT="$REPO_ROOT/.agents/SkillOpt-Codexy"
elif [[ -d "$HOME/.codex/SkillOpt-Codexy" ]]; then
  CODEXY_ROOT="$HOME/.codex/SkillOpt-Codexy"
elif [[ -d "$HOME/code/SkillOpt-Codexy" ]]; then
  CODEXY_ROOT="$HOME/code/SkillOpt-Codexy"
elif [[ -d "$HOME/code/skillz" ]]; then
  CODEXY_ROOT="$HOME/code/skillz"
else
  echo "SkillOpt-Codexy checkout not found. Set SKILLOPT_CODEXY_ROOT=/path/to/SkillOpt-Codexy." >&2
  exit 1
fi

cd "$REPO_ROOT"
mkdir -p tmp/skillopt

case "$COMMAND" in
  train)
    python3 "$CODEXY_ROOT/scripts/train.py" "$@"
    ;;
  eval)
    python3 "$CODEXY_ROOT/scripts/eval_only.py" "$@"
    ;;
  report)
    python3 "$CODEXY_ROOT/skillopt/run_report.py" \\
      --repo_root "$REPO_ROOT" \\
      --repo_log "$REPO_ROOT/tooling/skillopt/RUN_LOG.md" \\
      "$@"
    ;;
  *)
    echo "unknown SkillOpt-Codexy command: $COMMAND" >&2
    exit 2
    ;;
esac
"""


INITIAL_SKILL = """# Initial Repo Skill

Replace this scaffold with the current repository operating rules before training.

Include only instructions that are useful for an agent working in this repo:

- Required docs or maps to read before broad search.
- Commands used for tests, lint, type checks, and local verification.
- Common failure modes that should be avoided.
- Promotion criteria for changes to AGENTS.md.

Do not include secrets, private credentials, or machine-only paths unless they are intentionally part of the repo workflow.
"""


PROMOTION_AUDIT = """# SkillOpt-Codexy Promotion Audit

## Run

- Run directory:
- Report:
- Candidate skill:
- Baseline skill:

## Better Case

- Score movement:
- Concrete repo failure this prevents:
- Candidate wording to promote:
- Evidence artifacts:

## Worse Case

- Overfit or benchmark-specific wording:
- Conflicts with repo docs or AGENTS.md:
- Second-order effects:
- Missing verification:

## Decision

Decision: undecided

Allowed values: promote, partial-promote, reject.

Rationale:
"""


RUN_LOG = """# SkillOpt-Codexy Run Log
"""


def _write_if_missing(path: Path, content: str, *, executable: bool = False) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | 0o111)
    return True


def _load_package_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _update_package_json(path: Path) -> bool:
    data = _load_package_json(path)
    if data is None:
        return False
    scripts = data.setdefault("scripts", {})
    if not isinstance(scripts, dict):
        raise ValueError(f"{path}: scripts must be an object")

    wanted = {
        "skillopt:train": "tooling/skillopt/run-skillopt.sh train",
        "skillopt:eval": "tooling/skillopt/run-skillopt.sh eval",
        "skillopt:report": "tooling/skillopt/run-skillopt.sh report",
    }
    changed = False
    for key, value in wanted.items():
        if scripts.get(key) != value:
            scripts[key] = value
            changed = True

    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changed


def configure(repo: Path) -> list[str]:
    repo = repo.resolve()
    if not repo.exists():
        raise FileNotFoundError(repo)

    changed: list[str] = []
    if _write_if_missing(repo / "tooling/skillopt/initial-skill.md", INITIAL_SKILL):
        changed.append("created tooling/skillopt/initial-skill.md")
    if _write_if_missing(repo / "tooling/skillopt/PROMOTION_AUDIT.md", PROMOTION_AUDIT):
        changed.append("created tooling/skillopt/PROMOTION_AUDIT.md")
    if _write_if_missing(repo / "tooling/skillopt/RUN_LOG.md", RUN_LOG):
        changed.append("created tooling/skillopt/RUN_LOG.md")
    if _write_if_missing(repo / "tooling/skillopt/run-skillopt.sh", RUNNER, executable=True):
        changed.append("created tooling/skillopt/run-skillopt.sh")
    if _update_package_json(repo / "package.json"):
        changed.append("updated package.json scripts")
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Configure a project repo for SkillOpt-Codexy training.")
    parser.add_argument("--repo", default=".", help="Target project repository root")
    args = parser.parse_args(argv)

    changed = configure(Path(args.repo))
    if changed:
        for item in changed:
            print(f"[skillopt-codexy] {item}")
    else:
        print("[skillopt-codexy] already configured")
    print("[skillopt-codexy] set SKILLOPT_CODEXY_ROOT if the launcher cannot locate this checkout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
