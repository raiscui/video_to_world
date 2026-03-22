## Why

GS training currently stops as a one-shot run. The saved checkpoints are enough for evaluation, viewing, and PLY export, but they are not sufficient for resuming optimization from the last completed iteration. This makes long runs fragile: if a 10k or 15k iteration job is interrupted, the project must restart training from scratch instead of continuing from a saved state.

This is worth fixing now because the repository has already moved from short smoke runs to real long-running 3DGS training. We now have concrete evidence that long jobs are stable enough to start, but the lack of a formal resume path still leaves unnecessary recovery risk and wastes GPU time.

## What Changes

- Add a formal GS training resume workflow for both 2DGS and 3DGS runs.
- Extend GS checkpoints to store all state required for seamless continuation, not just model weights.
- Add CLI/config support to resume from the latest checkpoint automatically or from an explicit checkpoint path.
- Ensure resumed runs preserve iteration numbering, save/eval schedules, learning-rate scheduling, and final export behavior.
- Improve operator visibility so logs and config files clearly show whether a run started fresh or resumed from a prior checkpoint.

## Capabilities

### New Capabilities
- `gs-training-resume`: Resume GS training from a saved checkpoint with restored model, optimizer, scheduler, and iteration state so interrupted long runs can continue without restarting from iteration 0.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `train_gs.py`
  - `configs/stage3_gs.py`
  - GS checkpoint save/load helpers and related utilities
  - tests covering GS training lifecycle and checkpoint behavior
- Affected runtime behavior:
  - GS checkpoint format/content
  - CLI/config surface for GS training
  - logging around checkpoint save and resume state
- Likely follow-on docs updates:
  - README / runbook guidance for long-running GS jobs
