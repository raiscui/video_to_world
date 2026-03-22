## 1. Resume configuration and checkpoint schema

- [ ] 1.1 Add formal resume configuration fields to `GSConfig`, including resume enablement and explicit checkpoint-path support.
- [ ] 1.2 Introduce shared GS checkpoint save/load helpers that write a structured checkpoint envelope with version, renderer, completed iteration, model state, optimizer state, scheduler state, and resume metadata.
- [ ] 1.3 Update checkpoint writing to reject or skip incomplete payloads and preserve the existing checkpoint naming convention.

## 2. Resume-aware training flow

- [ ] 2.1 Update `train_gs.py` to detect resume intent, resolve the latest or explicit checkpoint source, and validate compatibility before entering the training loop.
- [ ] 2.2 Restore model, optimizer, scheduler, and iteration progress from resume-capable checkpoints, then continue training from the next global iteration.
- [ ] 2.3 Preserve save/eval cadence, final save behavior, and operator-visible logging/config output for resumed runs.

## 3. Downstream checkpoint compatibility

- [ ] 3.1 Update checkpoint consumers such as `eval_gs`, `utils/export_checkpoint_to_ply.py`, and `utils/view_checkpoint.py` to load the new structured checkpoint format.
- [ ] 3.2 Keep legacy weights-only checkpoints compatible for evaluation, export, and viewer workflows.
- [ ] 3.3 Add clear error handling for unsupported or incompatible checkpoint payloads in both training and downstream tools.

## 4. Verification and documentation

- [ ] 4.1 Add automated tests for fresh start, resume-from-latest, resume-from-explicit-path, compatibility validation failures, and downstream loading of legacy/new checkpoints.
- [ ] 4.2 Run targeted verification for GS training resume behavior and confirm resumed iteration numbering, save cadence, and eval cadence remain correct.
- [ ] 4.3 Update operator-facing documentation to explain how to start a fresh run, resume from latest, and resume from an explicit checkpoint.
