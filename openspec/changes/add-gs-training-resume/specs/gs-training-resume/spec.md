## ADDED Requirements

### Requirement: GS training can resume from the latest saved checkpoint
The system SHALL allow GS training to resume from the most recent resume-capable checkpoint in the configured output directory so that interrupted long-running jobs can continue without restarting from iteration 0.

#### Scenario: Resume from latest checkpoint in output directory
- **WHEN** a user starts GS training with resume enabled and the output directory contains one or more resume-capable checkpoints
- **THEN** the system SHALL select the checkpoint with the greatest completed iteration and continue training from the next iteration

#### Scenario: No checkpoint exists for requested resume
- **WHEN** a user starts GS training with resume enabled and no resume-capable checkpoint exists in the target output directory
- **THEN** the system SHALL fail before training begins with a clear error that explains no checkpoint was found to resume from

### Requirement: GS training can resume from an explicit checkpoint path
The system SHALL allow GS training to resume from a user-specified checkpoint path so operators can continue a run from a selected saved state instead of relying on automatic latest-checkpoint discovery.

#### Scenario: Resume from explicit checkpoint path
- **WHEN** a user provides an explicit GS resume checkpoint path
- **THEN** the system SHALL load that checkpoint and continue training from the next iteration after the checkpoint's recorded completed iteration

#### Scenario: Explicit checkpoint path is invalid
- **WHEN** a user provides a checkpoint path that does not exist or cannot be parsed as a resume-capable GS checkpoint
- **THEN** the system SHALL fail before training begins with a clear validation error that identifies the invalid path or unsupported checkpoint format

### Requirement: Resume checkpoints preserve optimization progress
The system SHALL persist and restore all state required for seamless continuation of optimization, including model parameters, optimizer state, scheduler state, and completed iteration metadata.

#### Scenario: Resume preserves optimizer and scheduler progress
- **WHEN** a GS run resumes from a saved checkpoint
- **THEN** the restored run SHALL continue with the saved optimizer state, scheduler state, and iteration count instead of reinitializing them from scratch

#### Scenario: Resume preserves save and evaluation cadence
- **WHEN** a resumed GS run continues training
- **THEN** checkpoint saving, intermediate evaluation, and final export SHALL occur according to the original global iteration numbering rather than restarting the schedule from zero

### Requirement: Resume validates checkpoint compatibility before training
The system MUST validate that a requested resume checkpoint is compatible with the requested training run before optimization begins.

#### Scenario: Renderer mismatch is rejected
- **WHEN** the checkpoint renderer type does not match the requested renderer for the new run
- **THEN** the system MUST fail before training starts with an error that explains the renderer mismatch

#### Scenario: Incompatible structural state is rejected
- **WHEN** the checkpoint metadata is incompatible with the requested training run, including unsupported checkpoint version or incompatible model layout
- **THEN** the system MUST fail before training starts with a clear compatibility error instead of silently starting a fresh run or partially loading state

### Requirement: Downstream checkpoint consumers remain usable after resume support is added
The system SHALL keep checkpoint-consuming evaluation and export tools functional after resume-capable checkpoints are introduced.

#### Scenario: Evaluation loads new resume-capable checkpoint format
- **WHEN** `eval_gs` or another checkpoint consumer loads a checkpoint produced by the new resume-capable training flow
- **THEN** it SHALL extract and use the model weights without requiring the caller to manually rewrite the checkpoint file

#### Scenario: Legacy weights-only checkpoint remains supported for evaluation
- **WHEN** a downstream tool loads an older weights-only GS checkpoint created before resume support was added
- **THEN** it SHALL continue to load successfully for evaluation or export workflows
