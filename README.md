# SkillOpt-Codexy: Codex-Backed Skill Optimization

SkillOpt-Codexy is a Codex-oriented fork of Microsoft SkillOpt. It keeps the original reflective training loop, adds Codex CLI backends, and includes an installable Codex skill for configuring project repositories, running training, auditing candidates, and promoting or rejecting durable AGENTS.md instructions.

[![Upstream Project](https://img.shields.io/badge/Upstream-Microsoft%20SkillOpt-8dbb3c)](https://github.com/microsoft/SkillOpt) [![Paper](https://img.shields.io/badge/Paper-arXiv-b31b1b)](https://arxiv.org/abs/2605.23904) [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Codex Agent Skill

This fork ships a standalone skill at `skills/skillopt-codexy/` for Codex agents. The skill is the agent-facing entrypoint; the Python package is the training engine it drives.

### Installing For Agents

Clone this repository somewhere stable:

```bash
git clone https://github.com/0xCozart/SkillOpt-Codexy.git ~/.codex/SkillOpt-Codexy
cd ~/.codex/SkillOpt-Codexy
python3 -m pip install -e .
codex login
```

Then install or expose the skill folder using whichever convention the host Codex agent supports:

- Shared install: copy or symlink `~/.codex/SkillOpt-Codexy/skills/skillopt-codexy` into the agent's shared skills directory.
- Project-local install: copy or symlink `skills/skillopt-codexy` into `<project>/.agents/skills/skillopt-codexy`.
- If the agent has a skill installer, point it at this GitHub repo and the `skills/skillopt-codexy` folder.

After install, ask the agent to use `skillopt-codexy` when configuring, training, auditing, or promoting repo instructions.

### Configuring A Target Repo

The skill does not assume where this repository is cloned. In each target project repo, the installing agent should run:

```bash
export SKILLOPT_CODEXY_ROOT=/path/to/SkillOpt-Codexy
python3 "$SKILLOPT_CODEXY_ROOT/scripts/configure_target_repo.py" --repo /path/to/project
```

The configurator writes:

- `tooling/skillopt/initial-skill.md` - seed instructions to train from
- `tooling/skillopt/PROMOTION_AUDIT.md` - local promotion decision template
- `tooling/skillopt/RUN_LOG.md` - append/update log for generated reports
- `tooling/skillopt/run-skillopt.sh` - project-local launcher that finds this checkout via `SKILLOPT_CODEXY_ROOT`, `.agents/vendor/SkillOpt-Codexy`, `~/.codex/SkillOpt-Codexy`, or other common paths

If the target project has `package.json`, the configurator also adds:

```bash
npm run skillopt:train
npm run skillopt:eval
npm run skillopt:report
```

For repos without `package.json`, use the launcher directly:

```bash
tooling/skillopt/run-skillopt.sh train ...
tooling/skillopt/run-skillopt.sh report --out_root tmp/skillopt/<run>
```

### Agent Workflow

Installing agents should follow this flow:

1. Configure the target repo.
2. Replace the scaffold in `tooling/skillopt/initial-skill.md` with the repo's real operating rules.
3. Run a small representative training job first.
4. Generate `RUN_REPORT.md` for the run.
5. Audit with the bundled promotion gate in `skills/skillopt-codexy/references/skillopt-train-promote.md`.
6. Use `$grill-with-docs` when repo authority docs exist; use `$grill-me` when the decision is mainly product/workflow judgment without usable docs.
7. Promote unchanged, partially promote, keep experimental, or reject.

Training output is never promoted directly into AGENTS.md. Edit AGENTS.md only when the audit proves a durable repo-wide instruction gap. Otherwise prefer updating `tooling/skillopt/initial-skill.md` or keeping the run as experiment evidence.

## 🎬 SkillOpt Demo Video

https://github.com/user-attachments/assets/eb12d3bc-371c-467f-904d-91b61f339ed7

<p align="center">
  <a href="https://youtu.be/JUBMDTCiM0M"><b>▶ Watch the full demo on YouTube</b></a>
</p>

---

## Install

**Requirements:** Python 3.10+

```bash
git clone https://github.com/0xCozart/SkillOpt-Codexy.git
cd SkillOpt-Codexy
pip install -e .

# For ALFWorld benchmark (optional):
pip install -e ".[alfworld]"
alfworld-download
```

### Configure API Credentials

```bash
cp .env.example .env
# Edit .env with your API credentials, then:
source .env
```

**Azure OpenAI** (recommended):
```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
# Option 1: API key auth
export AZURE_OPENAI_API_KEY="your-key"
# Option 2: Azure CLI auth (no API key needed)
export AZURE_OPENAI_AUTH_MODE="azure_cli"
```

> **Note:** `AZURE_OPENAI_ENDPOINT` is always required. Without it, all LLM calls will fail.

**OpenAI** directly:
```bash
export OPENAI_API_KEY="sk-..."
```

**Codex CLI** (uses your local Codex subscription login, no API key):
```bash
codex login

python scripts/train.py \
    --config configs/searchqa/default.yaml \
    --split_dir /path/to/your/searchqa_split \
    --backend codex \
    --optimizer_model gpt-5.5 \
    --target_model gpt-5.5
```

`--backend codex` runs optimizer calls through the Codex CLI chat backend
(`codex_chat`) and target rollouts through the Codex exec harness
(`codex_exec`). For chat-only target rollouts, use
`--backend codex_chat` instead.

**Anthropic Claude**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Qwen (local vLLM)**:
```bash
export QWEN_CHAT_BASE_URL="http://localhost:8000/v1"
export QWEN_CHAT_MODEL="Qwen/Qwen3.5-4B"
```

---

## Data Preparation

SkillOpt expects data in a **split directory** with `train/`, `val/`, `test/` subdirectories, each containing a JSON file (e.g., `items.json`).

```
data/my_split/
├── train/items.json
├── val/items.json
└── test/items.json
```

Each JSON file is an array of task items. The required fields depend on the benchmark. For example, SearchQA items look like:

```json
[
  {
    "id": "unique_item_id",
    "question": "Who wrote the novel ...",
    "context": "[DOC] relevant passage text ...",
    "answers": ["expected answer"]
  }
]
```

See `skillopt/envs/<benchmark>/dataloader.py` for the exact format each benchmark expects.

> **Note:** Benchmark datasets are not included in this repository. Prepare your own data following the format above.

### Supported Benchmarks

| Benchmark | Type | Config |
|---|---|---|
| SearchQA | QA | `configs/searchqa/default.yaml` |
| ALFWorld | Embodied agent | `configs/alfworld/default.yaml` |
| DocVQA | Document QA | `configs/docvqa/default.yaml` |
| LiveMathematicianBench | Math | `configs/livemathematicianbench/default.yaml` |
| SpreadsheetBench | Code generation | `configs/spreadsheetbench/default.yaml` |
| OfficeQA | Tool-augmented QA | `configs/officeqa/default.yaml` |

---

## Quick Start

### Training

```bash
# Minimal example — train on SearchQA:
python scripts/train.py \
    --config configs/searchqa/default.yaml \
    --split_dir /path/to/your/searchqa_split \
    --azure_openai_endpoint https://your-resource.openai.azure.com/ \
    --optimizer_model gpt-5.5 \
    --target_model gpt-5.5

# Train on LiveMathematicianBench:
python scripts/train.py \
    --config configs/livemathematicianbench/default.yaml \
    --split_dir /path/to/your/livemath_split \
    --azure_openai_endpoint https://your-resource.openai.azure.com/ \
    --optimizer_model gpt-5.5 \
    --target_model gpt-5.5

# Train on ALFWorld:
python scripts/train.py \
    --config configs/alfworld/default.yaml \
    --split_dir /path/to/your/alfworld_split \
    --azure_openai_endpoint https://your-resource.openai.azure.com/ \
    --optimizer_model gpt-5.5 \
    --target_model gpt-5.5
```

Key CLI arguments:

| Argument | Description | Example |
|---|---|---|
| `--config` | Benchmark config YAML | `configs/searchqa/default.yaml` |
| `--split_dir` | Path to data split directory | `/path/to/split` |
| `--azure_openai_endpoint` | Azure OpenAI endpoint URL | `https://your-resource.openai.azure.com/` |
| `--optimizer_model` | Optimizer model deployment name | `gpt-5.5` |
| `--target_model` | Target model deployment name | `gpt-5.5` |
| `--num_epochs` | Number of training epochs | `4` |
| `--batch_size` | Batch size per step | `40` |
| `--workers` | Parallel rollout workers | `8` |
| `--out_root` | Output directory | `outputs/my_run` |

### Eval Only

Evaluate a trained skill on specific data splits without training:

```bash
# Evaluate on test set only:
python scripts/eval_only.py \
  --config configs/searchqa/default.yaml \
  --skill outputs/my_run/best_skill.md \
  --split valid_unseen \
  --split_dir /path/to/searchqa_split \
  --azure_openai_endpoint https://your-resource.openai.azure.com/

# Evaluate on all splits (train + val + test):
python scripts/eval_only.py \
  --config configs/searchqa/default.yaml \
  --skill outputs/my_run/best_skill.md \
  --split all \
  --split_dir /path/to/searchqa_split \
  --azure_openai_endpoint https://your-resource.openai.azure.com/
```

| Split | Description |
|---|---|
| `valid_unseen` | Test set |
| `valid_seen` | Validation set |
| `train` | Training set |
| `all` | All splits combined (default) |

### Output Structure

Each run writes to a structured output directory:

```
outputs/<run_name>/
├── config.json              # Flattened runtime config
├── history.json             # Per-step training history
├── runtime_state.json       # Resume checkpoint
├── best_skill.md            # Best validated skill document
├── skills/skill_vXXXX.md   # Skill snapshot per step
├── steps/step_XXXX/        # Per-step artifacts (patches, evals)
├── slow_update/epoch_XX/   # Slow update logs
└── meta_skill/epoch_XX/    # Meta skill logs
```

Re-running the same command auto-resumes from the last completed step.

---

## WebUI

Launch the monitoring dashboard (optional):

```bash
pip install -e ".[webui]"
python -m skillopt_webui.app
```

| Flag | Default | Description |
|---|---|---|
| `--port` | 7860 | Server port |
| `--host` | `0.0.0.0` | Bind address |
| `--share` | off | Create a public Gradio share link |

```bash
# With public share link (useful for remote servers)
python -m skillopt_webui.app --share
```

---

## Citation

```bibtex
@misc{yang2026skilloptexecutivestrategyselfevolving,
      title={SkillOpt: Executive Strategy for Self-Evolving Agent Skills}, 
      author={Yifan Yang and Ziyang Gong and Weiquan Huang and Qihao Yang and Ziwei Zhou and Zisu Huang and Yan Li and Xuemei Gao and Qi Dai and Bei Liu and Kai Qiu and Yuqing Yang and Dongdong Chen and Xue Yang and Chong Luo},
      year={2026},
      eprint={2605.23904},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2605.23904}
}
```
