## Context

`train_gs.py` currently treats GS training as a one-shot job. The training loop always starts from iteration 0, and saved checkpoints are plain `model.state_dict()` payloads. This is enough for `eval_gs`, `view_checkpoint`, and `export_checkpoint_to_ply`, but not enough to resume optimization after interruption.

The project has already moved beyond tiny smoke runs. Real 3DGS jobs now run for thousands of iterations, use LPIPS, write intermediate checkpoints, and may trigger automatic evaluation afterward. That makes interruption recovery operationally important. The current gap is not only in `train_gs.py`; it also affects every utility that reads GS checkpoints, because those tools currently expect weights-only checkpoint files.

Constraints:
- Existing weights-only checkpoints must remain usable for evaluation and export.
- Resume must work for both `2dgs` and `3dgs` training.
- Resume must preserve global iteration numbering so save/eval cadence remains predictable.
- Resume must fail loudly on incompatible checkpoint state instead of silently starting fresh.

## Goals / Non-Goals

**Goals:**
- Add a formal resume path to GS training.
- Save all state required to continue optimization seamlessly.
- Allow resume from either the latest checkpoint in the output directory or an explicit checkpoint path.
- Keep downstream tools compatible with both legacy and new checkpoint formats.
- Make resume state visible in logs and saved config so operators can audit how a run started.

**Non-Goals:**
- Reconstruct progress if no resume-capable checkpoint has been saved.
- Resume Stage 1 or Stage 2 pipelines; this change is only for Stage 3 GS training.
- Change the training objective, renderer math, or evaluation metrics.
- Guarantee bitwise-identical results across interrupted and uninterrupted runs beyond the restored optimization state.

## Decisions

### Decision: Introduce a structured GS checkpoint envelope
Resume requires more than model weights. The checkpoint format should move from raw `model.state_dict()` to a structured payload that includes:
- checkpoint format version
- renderer type
- completed iteration
- serialized training config subset needed for validation
- model state
- optimizer state
- scheduler state
- optional RNG state snapshots

Why this approach:
- It creates a single source of truth for resume metadata.
- It supports compatibility validation before mutating training state.
- It avoids inventing sidecar files that can drift out of sync.

Alternative considered:
- Keep weights-only checkpoint files and write optimizer/scheduler state to sidecar files.
  - Rejected because it increases operator error risk and makes checkpoint movement/copying fragile.

### Decision: Add explicit resume config knobs instead of implicit magic
`GSConfig` should gain formal resume controls, likely an enable flag plus an optional explicit checkpoint path.

Why this approach:
- It keeps fresh starts and resumed runs distinguishable.
- It lets operators choose between “resume latest in this output dir” and “resume exactly this checkpoint”.
- It avoids accidental resume from stale files when a user intended a fresh run.

Alternative considered:
- Always auto-resume if any checkpoint exists in the output directory.
  - Rejected because it makes run intent ambiguous and can surprise operators.

### Decision: Resume continues from the next global iteration and reuses original cadence
If a checkpoint records completed iteration `N`, resumed training should continue at `N + 1`. Save/eval logic should continue using the global iteration number rather than re-basing the resumed segment to zero.

Why this approach:
- Operators can reason about checkpoints and eval folders using one iteration timeline.
- Existing conventions like `checkpoint_005000.pt` keep their meaning.
- It prevents resumed runs from duplicating save/eval milestones under different local counters.

Alternative considered:
- Restart loop counters from zero inside the resumed session.
  - Rejected because it makes checkpoint naming, eval directories, and schedule semantics confusing.

### Decision: Downstream consumers must load both legacy and new checkpoint formats
Once resume support changes the checkpoint payload shape, every checkpoint reader must unwrap the new envelope and still accept older weights-only checkpoints.

Affected consumers include at least:
- `eval_gs`
- `utils/export_checkpoint_to_ply.py`
- `utils/view_checkpoint.py`

Why this approach:
- It avoids breaking existing artifacts and older experiment directories.
- It allows gradual migration instead of forcing all historical checkpoints to be rewritten.

Alternative considered:
- Migrate all existing checkpoints or only support the new format.
  - Rejected because this repository already has many historical GS outputs and tooling assumptions.

### Decision: Resume validation should fail before heavy initialization continues
Before entering the training loop, resume logic should validate checkpoint compatibility with the requested renderer and expected model structure.

Why this approach:
- It gives operators an early, clear error.
- It avoids burning GPU time on a run that will later fail or silently diverge.
- It prevents partial state restores that are difficult to reason about.

Alternative considered:
- Best-effort partial loading with warnings.
  - Rejected because “formal resume” should be strict and reliable, not a warm-start approximation.

## Risks / Trade-offs

- [Checkpoint format change affects multiple tools] → Add a shared checkpoint loader helper and regression tests for both legacy and new formats.
- [Resume state may still miss some stochastic context] → Persist RNG state where practical and document any remaining nondeterministic limits.
- [Users may confuse fresh start and resume behaviors] → Record resume source in logs and saved config; require explicit resume opt-in.
- [Partially written checkpoints could be selected as latest] → Write checkpoints atomically or validate payload completeness before accepting them as resume candidates.
- [2DGS and 3DGS may diverge in future state requirements] → Keep checkpoint metadata versioned and validate renderer-specific expectations separately.

## Migration Plan

1. Add structured GS checkpoint save/load helpers.
2. Update `train_gs.py` to save resume-capable checkpoints and restore state when resume is requested.
3. Update checkpoint consumers to unwrap the new format while remaining backward compatible with weights-only checkpoints.
4. Add tests for fresh start, resume-from-latest, resume-from-explicit-path, legacy checkpoint compatibility, and incompatible resume failure.
5. Update operator-facing docs after implementation is verified.

Rollback strategy:
- If resume support causes issues, disable the new resume CLI path and keep downstream loaders accepting both formats so historical outputs remain usable.

## Open Questions

- Should resume save RNG state for Python, NumPy, and Torch CPU/CUDA, or is model/optimizer/scheduler restoration sufficient for this codebase's expectations?
- Should the default checkpoint naming remain `checkpoint_<iter>.pt`, or should resume-capable checkpoints be distinguished by metadata only?
- Should resumed runs append to the same output directory by default, or should the operator be encouraged to choose a new directory with explicit checkpoint source tracking?
