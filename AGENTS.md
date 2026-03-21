# Repository Guidelines

遇到 huggingface 模型要下载 先查找下https://modelscope.cn/  是否有 如果不会找, 就告诉我 我来找

## Project Structure & Module Organization
This repository is a Python 3.10 research codebase for video-to-3D reconstruction. Top-level scripts are the main entry points: `run_reconstruction.py`, `run_multiview_reconstruction.py`, `preprocess_video.py`, `preprocess_multiview.py`, `frame_to_model_icp.py`, `global_optimization.py`, `train_inverse_deformation.py`, `train_gs.py`, and `eval_gs.py`. Core logic lives in `algos/`, `models/`, `losses/`, `data/`, and `utils/`. Configuration dataclasses are kept in `configs/`. Tests live in `tests/`, workflow notes live in `specs/`, visual assets live in `assets/`, and third-party compatibility patches are stored in `patches/`.

## Build, Test, and Development Commands
Use `pixi` for environment management and command execution.

```bash
pixi install
pixi run setup
pixi run test
pixi run python preprocess_video.py --input_video /path/to/video.mp4
pixi run python run_reconstruction.py --config.input-video /path/to/video.mp4
pixi run python run_multiview_reconstruction.py --views-root source/example/full_scale2x --config.mode fast
pixi run python -m frame_to_model_icp --config.root-path /path/to/scene
pixi run python -m train_gs --config.root-path /path/to/scene --config.run frame_to_model_icp_50_2_offset0
pixi run python -m eval_gs --config.root-path /path/to/scene --config.run frame_to_model_icp_50_2_offset0
pixi run ruff check .
pixi run ruff format .
```

Use `pixi shell` for a shell, or `--help` on any script to inspect `tyro`-generated CLI options before changing configs.

## Coding Style & Naming Conventions
Use 4-space indentation, Python 3.10 syntax, and keep lines within Ruff’s 120-character limit. Follow existing naming: modules, functions, and variables use `snake_case`; classes and dataclasses use `PascalCase`; configuration fields remain explicit and descriptive. Prefer small, stage-focused helpers over large utility grab-bags, and keep new CLI/config options aligned with the existing dataclass + `tyro` pattern in `configs/`.

## Testing Guidelines
Use `pixi run test` for unit tests and `pixi run ruff check .` for linting. Keep new tests lightweight and independent from GPU-only dependencies when possible; orchestration logic should be covered with temp directories and dry-run assertions. For behavior changes in the heavy reconstruction stages, include the exact manual validation command in the PR description.

## Commit & Pull Request Guidelines
Recent history uses short, imperative, lowercase subjects such as `fix project root in auto eval` and `improve env setup instructions`. Keep commit messages in that style and scoped to one logical change. PRs should explain the affected pipeline stage, list validation commands, note any new dependencies or patch changes under `patches/`, and include output screenshots only when the change affects visual results or viewer behavior.

## Security & Configuration Tips
Avoid committing datasets, checkpoints, or scene folders. Keep local experiment paths and large outputs outside Git, and document required third-party repo pins or patch updates in `README.md` when they change.
If `pixi run install-gsplat` fails around `gsplat/cuda/csrc/third_party/glm`, do not trust `git submodule status` alone. Verify that `third_party/gsplat/gsplat/cuda/csrc/third_party/glm/glm/gtc/type_ptr.hpp` actually exists. The repository install script now auto-recovers broken GLM submodule state and can reuse a local GLM tree through `GSPLAT_GLM_LOCAL_DIR` in `.envrc`.
