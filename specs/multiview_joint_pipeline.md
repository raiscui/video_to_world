# Multi-View Joint Reconstruction Flow

## Goal

Provide one joint entry point for folders like:

```text
source/flashvsr_reference_xhc_bai/full_scale2x/
  0/rgb/xhc-bai_97e474c6.mp4
  1/rgb/xhc-bai_97e474c6.mp4
  ...
  5/rgb/xhc-bai_97e474c6.mp4
```

All selected views should be merged into one shared `scene_root`, then Stage 1/2/3 should run only once on that merged scene.

## Flowchart

```mermaid
flowchart TD
    Input["views_root (0..5)"]
    Discover["discover one rgb/*.mp4 per numeric view"]
    PerView["run preprocess_video.py per view"]
    MergeNpzd["merge per-view results.npz into one combined results.npz"]
    MergeFrames["merge per-view frames_subsampled into one combined frames folder"]
    SharedScene["shared scene_root"]
    Reconstruct["run run_reconstruction.py once with root_path"]

    Input --> Discover
    Discover --> PerView
    PerView --> MergeNpzd
    PerView --> MergeFrames
    MergeNpzd --> SharedScene
    MergeFrames --> SharedScene
    SharedScene --> Reconstruct
```

## Sequence

```mermaid
sequenceDiagram
    participant User
    participant Joint as run_multiview_reconstruction.py
    participant Pre as preprocess_multiview.py
    participant Single as preprocess_video.py
    participant Scene as shared scene_root
    participant Recon as run_reconstruction.py

    User->>Joint: pass views_root + stage args
    Joint->>Pre: launch joint Stage 0
    Pre->>Pre: discover 0..5 and validate one scene_stem
    loop for each selected view
        Pre->>Single: preprocess one view video
        Single-->>Pre: per-view results.npz + frames_subsampled
    end
    Pre->>Scene: merge per-view outputs into one shared scene_root
    Joint->>Recon: run reconstruction once with --config.root-path
    Recon->>Scene: Stage 1/2/3 shared outputs
```
