import argparse

from scripts import train
from skillopt import model


def test_train_backend_codex_uses_codex_for_optimizer_and_target_exec(tmp_path):
    cfg = train.load_config(
        argparse.Namespace(
            config="configs/searchqa/default.yaml",
            cfg_options=[
                f"env.out_root={tmp_path / 'out'}",
                "model.backend=codex",
                "env.split_dir=/tmp/split",
            ],
        )
    )

    assert cfg["model_backend"] == "codex"
    assert cfg["optimizer_backend"] == "codex_chat"
    assert cfg["target_backend"] == "codex_exec"


def test_set_backend_codex_routes_optimizer_to_codex_chat():
    previous_optimizer = model.get_optimizer_backend()
    previous_target = model.get_target_backend()
    try:
        model.set_backend("codex")
        assert model.get_optimizer_backend() == "codex_chat"
        assert model.get_target_backend() == "codex_exec"
        assert model.get_backend_name() == "codex"
    finally:
        model.set_optimizer_backend(previous_optimizer)
        model.set_target_backend(previous_target)
