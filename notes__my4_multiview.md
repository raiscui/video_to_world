## [2026-03-23 23:47:10] [Session ID: codex-20260323-234020] 笔记: `source/my4` 多视角目录兼容性调查

## 来源

### 来源1: 本地目录扫描

- 路径: `source/my4`
- 要点:
  - 存在 `0..11` 共 12 个数字目录,符合联合入口按视角编号扫描的基本前提。
  - 每个数字目录都包含 `generated_videos/generated_video_0.mp4`。
  - 根目录还有 `manifest.json` 和 `shared/`。
  - 每个视角目录还包含 `custom_camera_trajectory.npz`、`custom_3D_gaussian_trajectory.json`、`rendering_4D_maps/`。

### 来源2: 代码静态阅读

- 文件: `preprocess_multiview.py`
- 要点:
  - `PreprocessMultiViewConfig.video_glob` 默认值是 `rgb/*.mp4`。
  - `iter_view_dirs()` 已支持按数字顺序遍历视角目录,并不限制必须只有 6 个视角。
  - `find_single_video()` 只按单个 glob 查找,没有做常见布局自动回退。
  - `scene_stem` 当前主要用于一致性检查、日志和 summary,不是联合流程的核心输入。

### 来源3: 动态验证

- 命令:
  - `timeout 30s pixi run python run_multiview_reconstruction.py --views-root source/my4 --dry-run --config.mode fast`
  - `timeout 30s pixi run python run_multiview_reconstruction.py --views-root source/my4 --video-glob 'generated_videos/*.mp4' --dry-run --config.mode fast`
- 关键输出:
  - 默认命令失败: `No video matched 'rgb/*.mp4' under '.../source/my4/0'`
  - 显式指定 `generated_videos/*.mp4` 后成功输出:
    - `preprocess_multiview.py --views-root .../source/my4 --scene-root .../source/my4_preprocessed --video-glob 'generated_videos/*.mp4' ...`
    - `run_reconstruction.py --config.root-path .../source/my4_preprocessed --config.mode fast --config.dry-run`

## 综合发现

### 现象

- 当前失败是旧默认输入布局与新素材目录不匹配。
- 12 个视角数量本身没有暴露出限制。

### 假设

- 主假设:
  - 只要把视频发现层改成支持常见布局自动识别, 主流程无需大改。
- 备选解释:
  - VerseCrafter 风格目录未来可能还会依赖根级 `manifest.json` 提供更稳定的 `scene_stem` 或路径提示。

### 当前结论

- 已验证结论:
  - `source/my4` 现在就能用联合入口跑,但需要显式传 `--video-glob 'generated_videos/*.mp4'`。
  - 更合理的修复点在 `preprocess_multiview.py` 的输入发现逻辑,而不是 Stage 1/2/3。

## [2026-03-23 23:55:55] [Session ID: codex-20260323-234020] 笔记: 修复后的二次验证

## 来源

### 来源1: 修改后 dry-run

- 命令:
  - `timeout 30s pixi run python run_multiview_reconstruction.py --views-root source/my4 --dry-run --config.mode fast`
- 关键输出:
  - `preprocess_multiview.py --views-root .../source/my4 --scene-root .../source/my4_preprocessed --video-glob auto ... --dry-run`
  - `run_reconstruction.py --config.root-path .../source/my4_preprocessed --config.mode fast --config.dry-run`

### 来源2: 单元测试与 lint

- 命令:
  - `timeout 120s pixi run python -m unittest tests/test_run_multiview_reconstruction.py`
  - `timeout 120s pixi run ruff check preprocess_multiview.py run_multiview_reconstruction.py tests/test_run_multiview_reconstruction.py`
- 关键输出:
  - `Ran 5 tests ... OK`
  - `All checks passed!`

## 综合发现

### 结论

- 上一轮“需要手动传 `--video-glob`”的临时结论已过期。
- 新代码已经把该兼容能力前移到了默认输入发现阶段。
- 对 `source/my4` 来说,现在可以直接使用:
  - `pixi run python run_multiview_reconstruction.py --views-root source/my4 --scene-root <目标目录> --config.mode extensive`
