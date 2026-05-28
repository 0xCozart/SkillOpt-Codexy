from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunReportResult:
    report_path: Path
    repo_log_path: Path | None
    decision: str
    status: str


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _fmt_score(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _short_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is None:
        return str(path)
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _history_action_counts(history: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accept": sum(1 for h in history if "accept" in str(h.get("action", ""))),
        "reject": sum(1 for h in history if h.get("action") == "reject"),
        "skip": sum(1 for h in history if str(h.get("action", "")).startswith("skip")),
    }


def _summarize_step(step: dict[str, Any]) -> str:
    parts = [
        f"step {step.get('step', '?')}",
        f"action={step.get('action', 'unknown')}",
    ]
    if "selection_hard" in step:
        parts.append(f"selection={_fmt_score(step.get('selection_hard'))}")
    if "best_score" in step:
        parts.append(f"best={_fmt_score(step.get('best_score'))}")
    if "n_edits_ranked" in step:
        parts.append(f"edits={step.get('n_edits_ranked')}")
    return ", ".join(parts)


def _change_summary(step: dict[str, Any]) -> list[str]:
    changes = step.get("rewrite_change_summary")
    if isinstance(changes, list) and changes:
        return [str(x) for x in changes[:3]]

    rejected = step.get("rejected_edits")
    if isinstance(rejected, list):
        summaries: list[str] = []
        for item in rejected[:3]:
            if not isinstance(item, dict):
                continue
            change = item.get("change_summary")
            if isinstance(change, list):
                summaries.extend(str(x) for x in change[:2])
            elif change:
                summaries.append(str(change))
        return summaries[:3]

    return []


def _load_slow_updates(out_root: Path, repo_root: Path | None) -> list[dict[str, Any]]:
    slow_root = out_root / "slow_update"
    if not slow_root.exists():
        return []

    rows: list[dict[str, Any]] = []
    for path in sorted(slow_root.glob("epoch_*/slow_result.json")):
        data = _load_json(path, {})
        if not isinstance(data, dict):
            continue
        content = str(data.get("slow_update_content") or "").strip()
        rows.append(
            {
                "path": _short_path(path, repo_root),
                "epoch": path.parent.name.removeprefix("epoch_"),
                "action": data.get("action", "unknown"),
                "prev_hard": data.get("prev_hard"),
                "curr_hard": data.get("curr_hard"),
                "content": content,
            },
        )
    return rows


def _decide(
    *,
    history: list[dict[str, Any]],
    baseline: Any,
    best: Any,
    best_step: int,
) -> tuple[str, str, str]:
    if not history:
        return (
            "Incomplete - no optimization steps finished",
            "Keep candidate as experiment output only",
            "history.json was not present or contained no completed steps.",
        )

    try:
        baseline_f = float(baseline)
        best_f = float(best)
    except (TypeError, ValueError):
        baseline_f = None
        best_f = None

    if best_step <= 0:
        return (
            "Complete - no accepted better skill",
            "Keep candidate as experiment output only",
            "No candidate beat the initial skill on the selection set.",
        )

    if baseline_f is not None and best_f is not None and best_f > baseline_f:
        return (
            "Complete - candidate improved selection score",
            "Promote partial edits only after audit",
            "The best candidate improved the selection hard score, but AGENTS.md promotion still needs the objective promotion audit.",
        )

    return (
        "Complete - candidate accepted without proven baseline lift",
        "Promote partial edits only after audit",
        "A candidate became current/best during training, but the available summary does not prove a baseline hard-score lift.",
    )


def _build_markdown(out_root: Path, repo_root: Path | None) -> tuple[str, str, str]:
    summary = _load_json(out_root / "summary.json", {})
    history_raw = _load_json(out_root / "history.json", [])
    history: list[dict[str, Any]] = history_raw if isinstance(history_raw, list) else []
    runtime_state = _load_json(out_root / "runtime_state.json", {})
    config = summary.get("config") if isinstance(summary.get("config"), dict) else {}
    if not config:
        config = _load_json(out_root / "config.json", {})

    baseline = summary.get("baseline_selection_hard")
    best = summary.get("best_selection_hard", runtime_state.get("best_score"))
    best_step = int(summary.get("best_step", runtime_state.get("best_step", 0)) or 0)
    status, decision, reason = _decide(
        history=history,
        baseline=baseline,
        best=best,
        best_step=best_step,
    )
    counts = _history_action_counts(history)
    train_size = config.get("train_size")
    total_tokens = summary.get("token_summary", {}).get("_total", {})
    current_origin = summary.get(
        "current_origin",
        runtime_state.get("current_origin", "unknown"),
    )
    best_origin = summary.get(
        "best_origin",
        runtime_state.get("best_origin", "unknown"),
    )
    slow_updates = _load_slow_updates(out_root, repo_root)
    force_slow_updates = [
        row for row in slow_updates if row.get("action") == "force_accept"
    ]

    accepted = [h for h in history if "accept" in str(h.get("action", ""))]
    rejected = [h for h in history if h.get("action") == "reject"]
    best_skill = out_root / "best_skill.md"
    report_path = out_root / "RUN_REPORT.md"

    lines = [
        "# SkillOpt Run Report",
        "",
        "## Decision",
        "",
        f"- Status: {status}",
        f"- Recommendation: {decision}",
        f"- Why: {reason}",
        "- AGENTS.md: AGENTS.md was not updated automatically by SkillOpt. Promote there only after the audit supports a durable repo-instruction change.",
    ]

    if isinstance(train_size, int | float) and train_size < 20:
        lines.append(
            f"- Dataset caution: Dataset is small (train_size={int(train_size)}), so treat results as directional rather than statistically strong.",
        )

    lines.extend(
        [
            "",
            "## Scores",
            "",
            f"- Baseline selection hard: {_fmt_score(baseline)}",
            f"- Best selection hard: {_fmt_score(best)}",
            f"- Best step: {best_step}",
            f"- Best score origin: {best_origin}",
            f"- Current skill origin: {current_origin}",
            f"- Test hard: {_fmt_score(summary.get('test_hard'))}",
            f"- Test delta hard: {_fmt_score(summary.get('test_delta_hard'))}",
            "",
            "## Agent Grill Summary",
            "",
            f"- Better-case claim: best selection hard changed from {_fmt_score(baseline)} to {_fmt_score(best)}.",
            f"- Worse-case claim: train_size={train_size if train_size is not None else 'n/a'} and the run may be overfit to this seed split.",
            f"- AGENTS.md promotion decision: {decision}. SkillOpt did not edit AGENTS.md; use the promotion audit before any manual repo-instruction change.",
            "",
            "## Steps",
            "",
            f"- Completed steps: {len(history)}",
            f"- Accepted: {counts['accept']}",
            f"- Rejected: {counts['reject']}",
            f"- Skipped: {counts['skip']}",
        ],
    )

    if accepted:
        lines.extend(["", "### Better Case", ""])
        for step in accepted[-5:]:
            lines.append(f"- {_summarize_step(step)}")
            for change in _change_summary(step):
                lines.append(f"  - Evidence: {change}")
    else:
        lines.extend(["", "### Better Case", "", "- No accepted candidate is recorded in history.json."])

    if rejected:
        lines.extend(["", "### Worse Case", ""])
        for step in rejected[-5:]:
            lines.append(f"- {_summarize_step(step)}")
            for change in _change_summary(step):
                lines.append(f"  - Rejected edit evidence: {change}")
    else:
        lines.extend(["", "### Worse Case", "", "- No rejected candidate is recorded in history.json."])

    if force_slow_updates:
        lines.extend(["", "## Slow Update Notes", ""])
        lines.append(
            "- Slow-update guidance was force-injected after the score-gated best step. Audit best_skill.md as the final candidate, not only the accepted step diff.",
        )
        for row in force_slow_updates[-5:]:
            content = str(row.get("content") or "").replace("\n", " ")
            if len(content) > 240:
                content = content[:237].rstrip() + "..."
            lines.append(
                "- "
                f"epoch={row.get('epoch')} action={row.get('action')} "
                f"prev={_fmt_score(row.get('prev_hard'))} "
                f"curr={_fmt_score(row.get('curr_hard'))} "
                f"artifact={row.get('path')}",
            )
            if content:
                lines.append(f"  - Guidance: {content}")

    lines.extend(
        [
            "",
            "## Promotion Checklist",
            "",
            "- Compare the initial skill with best_skill.md before changing repo instructions.",
            "- Fill tooling/skillopt/PROMOTION_AUDIT.md with the strongest better-case and worse-case from artifacts.",
            "- Prefer promoting to tooling/skillopt/initial-skill.md first unless the candidate fixes a durable AGENTS.md gap.",
            "- Do not promote benchmark-specific wording, broad/vague instructions, or guidance that conflicts with repo authority docs.",
            "",
            "## Artifacts",
            "",
            f"- Run directory: {_short_path(out_root, repo_root)}",
            f"- This report: {_short_path(report_path, repo_root)}",
            f"- Best skill: {_short_path(best_skill, repo_root) if best_skill.exists() else 'not written'}",
            f"- History: {_short_path(out_root / 'history.json', repo_root) if (out_root / 'history.json').exists() else 'missing'}",
            f"- Summary: {_short_path(out_root / 'summary.json', repo_root) if (out_root / 'summary.json').exists() else 'missing'}",
        ],
    )

    if total_tokens:
        lines.extend(
            [
                "",
                "## Runtime",
                "",
                f"- Wall time seconds: {summary.get('total_wall_time_s', 'n/a')}",
                f"- Token calls: {total_tokens.get('calls', 'n/a')}",
                f"- Total tokens: {total_tokens.get('total_tokens', 'n/a')}",
            ],
        )

    return "\n".join(lines).rstrip() + "\n", decision, status


def _build_log_entry(
    *,
    out_root: Path,
    repo_root: Path | None,
    decision: str,
    status: str,
    report_path: Path,
) -> tuple[str, str]:
    marker_id = hashlib.sha1(str(out_root.resolve()).encode("utf-8")).hexdigest()[:12]
    run_name = out_root.name
    entry = "\n".join(
        [
            f"<!-- skillopt-run:start:{marker_id} -->",
            f"## {run_name}",
            "",
            f"- Status: {status}",
            f"- Recommendation: {decision}",
            f"- Run directory: {_short_path(out_root, repo_root)}",
            f"- Report: {_short_path(report_path, repo_root)}",
            f"<!-- skillopt-run:end:{marker_id} -->",
            "",
        ],
    )
    return marker_id, entry


def _upsert_log(log_path: Path, marker_id: str, entry: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    start = f"<!-- skillopt-run:start:{marker_id} -->"
    end = f"<!-- skillopt-run:end:{marker_id} -->"
    if log_path.exists():
        content = log_path.read_text(encoding="utf-8")
    else:
        content = "# SkillOpt Run Log\n\n"

    start_idx = content.find(start)
    end_idx = content.find(end)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        end_idx += len(end)
        content = content[:start_idx] + entry.rstrip() + content[end_idx:]
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + entry

    log_path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_run_report(
    *,
    out_root: str | Path,
    repo_root: str | Path | None = None,
    repo_log_path: str | Path | None = None,
) -> RunReportResult:
    out_path = Path(out_root)
    repo_path = Path(repo_root) if repo_root is not None else None
    markdown, decision, status = _build_markdown(out_path, repo_path)
    report_path = out_path / "RUN_REPORT.md"
    report_path.write_text(markdown, encoding="utf-8")

    log_path = Path(repo_log_path) if repo_log_path is not None else None
    if log_path is not None:
        marker_id, entry = _build_log_entry(
            out_root=out_path,
            repo_root=repo_path,
            decision=decision,
            status=status,
            report_path=report_path,
        )
        _upsert_log(log_path, marker_id, entry)

    return RunReportResult(
        report_path=report_path,
        repo_log_path=log_path,
        decision=decision,
        status=status,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a SkillOpt run report.")
    parser.add_argument("--out_root", required=True)
    parser.add_argument("--repo_root")
    parser.add_argument("--repo_log")
    args = parser.parse_args(argv)

    result = write_run_report(
        out_root=args.out_root,
        repo_root=args.repo_root,
        repo_log_path=args.repo_log,
    )
    print(f"[skillopt report] status: {result.status}")
    print(f"[skillopt report] recommendation: {result.decision}")
    print(f"[skillopt report] report: {result.report_path}")
    if result.repo_log_path is not None:
        print(f"[skillopt report] repo log: {result.repo_log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
