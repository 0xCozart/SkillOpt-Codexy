import json
from pathlib import Path

from skillopt.run_report import write_run_report


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_run_report_recommends_audited_promotion_for_improved_best(tmp_path):
    repo_root = tmp_path / "repo"
    out_root = repo_root / "tmp" / "skillopt" / "run-1"
    out_root.mkdir(parents=True)
    (out_root / "best_skill.md").write_text("better skill\n", encoding="utf-8")
    _write_json(
        out_root / "summary.json",
        {
            "baseline_selection_hard": 0.25,
            "best_selection_hard": 0.5,
            "best_step": 2,
            "best_origin": "step_0002",
            "total_steps": 2,
            "total_accepts": 1,
            "total_rejects": 1,
            "total_skips": 0,
            "test_delta_hard": None,
            "total_wall_time_s": 12.3,
            "config": {"train_size": 4, "num_epochs": 2, "batch_size": 40},
            "token_summary": {"_total": {"total_tokens": 1234, "calls": 8}},
        },
    )
    _write_json(
        out_root / "history.json",
        [
            {
                "step": 1,
                "action": "reject",
                "selection_hard": 0.25,
                "best_score": 0.25,
                "n_edits_ranked": 2,
                "rejected_edits": [{"change_summary": ["too broad"]}],
            },
            {
                "step": 2,
                "action": "accept_new_best",
                "selection_hard": 0.5,
                "best_score": 0.5,
                "n_edits_ranked": 1,
                "rewrite_change_summary": ["Prefer raw/graded separation."],
            },
        ],
    )

    result = write_run_report(
        out_root=out_root,
        repo_root=repo_root,
        repo_log_path=repo_root / "tooling" / "skillopt" / "RUN_LOG.md",
    )

    report = result.report_path.read_text(encoding="utf-8")
    assert "Promote partial edits only after audit" in report
    assert "AGENTS.md was not updated automatically" in report
    assert "Agent Grill Summary" in report
    assert "AGENTS.md promotion decision" in report
    assert "Prefer raw/graded separation." in report
    assert "Dataset is small" in report

    run_log = (repo_root / "tooling" / "skillopt" / "RUN_LOG.md").read_text(
        encoding="utf-8",
    )
    assert "run-1" in run_log
    assert "Promote partial edits only after audit" in run_log


def test_run_report_distinguishes_score_best_from_slow_update_best_skill(tmp_path):
    repo_root = tmp_path / "repo"
    out_root = repo_root / "tmp" / "skillopt" / "run-slow"
    slow_dir = out_root / "slow_update" / "epoch_04"
    slow_dir.mkdir(parents=True)
    (out_root / "best_skill.md").write_text(
        "score-gated skill\n<!-- SLOW_UPDATE_START -->\nslow guidance\n<!-- SLOW_UPDATE_END -->\n",
        encoding="utf-8",
    )
    _write_json(
        out_root / "summary.json",
        {
            "baseline_selection_hard": 0.0,
            "best_selection_hard": 1.0,
            "best_step": 2,
            "current_origin": "slow_update_epoch_04",
            "best_origin": "step_0002",
            "total_steps": 4,
            "total_accepts": 2,
            "total_rejects": 0,
            "total_skips": 2,
            "config": {"train_size": 4},
        },
    )
    _write_json(
        out_root / "runtime_state.json",
        {
            "current_origin": "slow_update_epoch_04",
            "best_origin": "step_0002",
            "best_step": 2,
        },
    )
    _write_json(
        out_root / "history.json",
        [
            {"step": 1, "action": "accept_new_best", "selection_hard": 0.5},
            {"step": 2, "action": "accept_new_best", "selection_hard": 1.0},
            {"step": 3, "action": "skip_no_patches"},
            {"step": 4, "action": "skip_no_patches"},
        ],
    )
    _write_json(
        slow_dir / "slow_result.json",
        {
            "action": "force_accept",
            "epoch": 4,
            "prev_hard": 1.0,
            "curr_hard": 1.0,
            "slow_update_content": "Keep exact route spans.",
        },
    )

    result = write_run_report(out_root=out_root, repo_root=repo_root)

    report = result.report_path.read_text(encoding="utf-8")
    assert "Best score origin: step_0002" in report
    assert "Current skill origin: slow_update_epoch_04" in report
    assert "Slow-update guidance was force-injected after the score-gated best step." in report
    assert "slow_update/epoch_04/slow_result.json" in report
    assert "Keep exact route spans." in report


def test_run_report_marks_incomplete_run_as_experiment_only(tmp_path):
    repo_root = tmp_path / "repo"
    out_root = repo_root / "tmp" / "skillopt" / "run-2"
    out_root.mkdir(parents=True)
    _write_json(out_root / "runtime_state.json", {"last_completed_step": 0})
    _write_json(
        out_root / "config.json",
        {"train_size": 4, "num_epochs": 4, "batch_size": 40},
    )

    result = write_run_report(out_root=out_root, repo_root=repo_root)

    report = result.report_path.read_text(encoding="utf-8")
    assert "Incomplete - no optimization steps finished" in report
    assert "Keep candidate as experiment output only" in report
    assert "history.json was not present" in report


def test_run_report_upserts_repo_log_entry_for_same_run(tmp_path):
    repo_root = tmp_path / "repo"
    out_root = repo_root / "tmp" / "skillopt" / "run-3"
    out_root.mkdir(parents=True)
    _write_json(
        out_root / "summary.json",
        {
            "baseline_selection_hard": 0.0,
            "best_selection_hard": 0.0,
            "best_step": 0,
            "total_steps": 1,
            "total_accepts": 0,
            "total_rejects": 1,
            "total_skips": 0,
            "config": {"train_size": 4},
        },
    )
    _write_json(out_root / "history.json", [{"step": 1, "action": "reject"}])
    log_path = repo_root / "tooling" / "skillopt" / "RUN_LOG.md"

    write_run_report(out_root=out_root, repo_root=repo_root, repo_log_path=log_path)
    write_run_report(out_root=out_root, repo_root=repo_root, repo_log_path=log_path)

    log = log_path.read_text(encoding="utf-8")
    assert log.count("skillopt-run:start:") == 1
    assert log.count("## run-3") == 1
