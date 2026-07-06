# Publish trellis runtime to PyPI for global hook usage

## Goal

将 Trellis 的 Python runtime（`.trellis/scripts/common/` + hooks + entry scripts）打包为独立 Python 包，使各 agent 平台通过 `uvx` 调用全局安装的 hook/CLI，消除每个项目必须保留 `.trellis/scripts/` 目录的依赖。CI 就绪即可，不要求实际发布到 PyPI。

## Background

通过源码分析确认（Trellis v0.6.2，`packages/cli/src/templates/`）：

- `.trellis/scripts/common/` 的 21 个 Python 模块**零 `__file__` 锚定**。所有路径解析走 `Path.cwd()` → `get_repo_root()`（`common/paths.py:73`），向上查找 `.trellis/` 目录。
- hooks（`shared-hooks/*.py`）**同样零 `__file__`**。它们用 `find_trellis_root(cwd)` 定位项目根，然后 `sys.path.insert(0, root / ".trellis" / "scripts")` 加载 `common/`。该 `sys.path.insert` 是 deferred import（在函数内部），如果 `.trellis/scripts/` 不存在则静默跳过，Python 回退到 site-packages 中已安装的 `common` 包。
- 所有 hooks 和 entry scripts 都有 `def main()` + `if __name__ == "__main__":`，可直接作为 `console_scripts` entry point（`get_context.py` 例外，它 re-export `from common.git_context import main`）。
- `.trellis/config.yaml` / `.trellis/spec/` / `.trellis/tasks/` / `.trellis/workspace/` 是项目状态，保留 per-project。

结论：`common/` 的代码是 static（不随项目变化），全局安装后 `from common.xxx import` 照常解析到 site-packages，无需修改任何上游文件。

### Codex SessionStart 上游未注册

`codex.ts:60-62` 将 Codex 标记为 class-2 pull-based 平台（PreToolUse 只对 Bash 触发，CollabAgentSpawn hook 未实现 [#15486]）。`hooks.json`（`codex/hooks.json`）仅注册 `UserPromptSubmit`，`session-start.py` 以 "retained compatibility template and regression surface"（`codex.ts:73-75`）保留但不接线。

但 class-2 分类针对的是 **sub-agent 上下文注入**，与 SessionStart 独立。Codex 官方早已支持 SessionStart（matcher: `startup|resume|clear|compact`）。全局 hooks 可自行注册 SessionStart——`session-start.py` 已输出正确的 `hookSpecificOutput.hookEventName: "SessionStart"` JSON 格式，且 uvx 下 `_detect_platform` 返回 `None` 仅影响 kiro 分支（纯文本输出），其余平台统一走 JSON envelope 路径，不影响 Codex。详见 [hook-reference.md](./hook-reference.md#codex)。

## Constraints

1. **不修改上游 Python scripts** — fork repo，无 push 权限。`common/`、hooks、entry scripts 必须按 upstream 原样同步（byte-identical content）。
2. **不修改 Trellis CLI JS** — `packages/cli/` 下所有 TypeScript 不可改。
3. **使用 `uvx` 调用** — 各 agent 的 hook command 用 `uvx --from trellis-runtime <entry-point>` 形式。
4. **per-project 兼容** — 项目内如果存在 `.trellis/scripts/`（via `trellis init`），hook 的 `sys.path.insert` 优先使用 per-project 版本（sys.path 顺序优先）。全局包作为 fallback。

## Package Design

### Package name

可配置，默认 `trellis-runtime`。在 fork repo 的 `trellis-runtime/pyproject.toml` 直接改 `name` 字段即可，同步脚本不覆盖该文件。

### 实际目录结构

包直接放在 fork repo 的 `trellis-runtime/` 子目录下，而非独立 repo。上游 templates 就在同 repo 的 `packages/cli/src/templates/`，sync 脚本用相对路径直接引用，无需 clone 上游。

- `trellis-runtime/pyproject.toml` — hatchling 后端，9 个 console_scripts
- `trellis-runtime/scripts/sync_upstream.sh` — 从 `../packages/cli/src/templates/` 同步，`--check` 支持 CI drift 校验
- `trellis-runtime/src/common/` — 21 模块，byte-identical（已 MD5 校验）
- `trellis-runtime/src/trellis_runtime/upstream/hooks/` — 4 hooks，hyphen→underscore 重命名，内容不变
- `trellis-runtime/src/trellis_runtime/upstream/entry/` — 5 entry scripts

CI workflows 放在 repo 根的 `.github/workflows/`，与 Trellis 自有的 `ci.yml`/`publish.yml` 共存，用 `runtime-` 前缀避免冲突。

### 同步规则

同步脚本 `scripts/sync_upstream.sh` 从同 repo 的 templates 拷贝：

- `packages/cli/src/templates/trellis/scripts/common/` → `src/common/`（无 rename）
- `packages/cli/src/templates/shared-hooks/*.py` → `src/trellis_runtime/upstream/hooks/`（hyphen→underscore，content 不变）
- `packages/cli/src/templates/trellis/scripts/*.py` → `src/trellis_runtime/upstream/entry/`（skip `__init__.py`）

文件名 rename（hyphen → underscore）不修改文件内容，仅因为 Python module name 不允许 hyphen。upstream 文件保持 byte-identical。

### console_scripts

- `trellis-hook-inject-workflow-state` = `trellis_runtime.upstream.hooks.inject_workflow_state:main`
- `trellis-hook-session-start` = `trellis_runtime.upstream.hooks.session_start:main`
- `trellis-hook-inject-subagent-context` = `trellis_runtime.upstream.hooks.inject_subagent_context:main`
- `trellis-hook-inject-shell-session-context` = `trellis_runtime.upstream.hooks.inject_shell_session_context:main`
- `trellis-task` = `trellis_runtime.upstream.entry.task:main`
- `trellis-get-context` = `trellis_runtime.upstream.entry.get_context:main`
- `trellis-add-session` = `trellis_runtime.upstream.entry.add_session:main`
- `trellis-get-developer` = `trellis_runtime.upstream.entry.get_developer:main`
- `trellis-init-developer` = `trellis_runtime.upstream.entry.init_developer:main`

### 运行时 import 链验证

全局安装后 hook 的执行路径：

1. `uvx --from trellis-runtime trellis-hook-inject-workflow-state` 启动
2. console_script 调用 `trellis_runtime.upstream.hooks.inject_workflow_state:main()`
3. `main()` 读 stdin JSON，用 `find_trellis_root(cwd)` 定位 `.trellis/`
4. `sys.path.insert(0, root / ".trellis" / "scripts")` — 如果 `.trellis/scripts/` 存在（per-project init 过）则优先用 per-project；不存在则静默跳过
5. `from common.active_task import resolve_active_task` — sys.path 中 `.trellis/scripts/` 不存在 → 回退到 site-packages → 找到全局安装的 `common`
6. 正常执行 hook 逻辑

entry scripts 的执行路径类似，但 `from common.xxx import` 是 module-level（不在函数内）。由于 `common` 在 site-packages 中，console_script 启动时 Python 已经能解析。

**已验证**（`uv build` + smoke test 全部通过）：`uv run trellis-task --help`、`uv run trellis-hook-inject-workflow-state`、`uv run trellis-hook-session-start`、`uv run trellis-get-context --help` 均正确执行。

## Per-Agent Hook Commands

各 agent 平台的完整 hook command 配置（Codex / Claude / OpenCode）见 [hook-reference.md](./hook-reference.md)。本文档不重复细节。

本任务的 `uvx` 方案覆盖 Codex 和 Claude（Python hooks）。OpenCode 走 JS plugins，作为独立后续项。

## CI Design

两个 workflow，放在 repo 根 `.github/workflows/`：

### `runtime-build-test.yml`

触发：push/PR 且 paths 命中 `trellis-runtime/**` 或上游 templates 变动。校验同步内容 byte-identical（`sync_upstream.sh --check`）+ `uv build` + smoke test（`trellis-task --help`、`trellis-hook-* --help`、`trellis-get-context --help`）。

### `runtime-publish.yml`

触发：push tag `runtime-v*`（前缀避开 Trellis 自身的 `v*` tag）+ manual dispatch。`uv build` 始终运行（验证可构建）；`uv publish` 仅在配置了 `PYPI_TOKEN` secret 时执行——未配置时 workflow 退化为 build-only gate。

版本号追踪 upstream Trellis 版本（upstream `0.6.2` → 包 `0.6.2`）。tag 格式 `runtime-v0.6.2`。

### sync

没有独立的 sync workflow。包就在 fork repo 内，templates 在同 repo，直接 `./scripts/sync_upstream.sh` 手动同步后 commit 即可。`--check` 已接入 `runtime-build-test.yml` 防止 drift。

## Acceptance Criteria

- [x] `uv build` 成功产出 wheel/sdist，`uv run trellis-task --help` 可调用（`runtime-build-test.yml` 验证）
- [x] Codex hook command 通过 `uvx` 调用 `trellis-hook-inject-workflow-state`，在没有 `.trellis/scripts/` 的项目中正常工作（读取 `.trellis/config.yaml` + `tasks/`）
- [x] Claude Code hook commands 同上（3 个 hook 全部通过 `uvx` 运行）
- [x] per-project `.trellis/scripts/` 存在时，hook 的 `sys.path.insert` 优先使用 per-project 版本（向后兼容）
- [x] CI `runtime-publish.yml` 就绪：`uv build` 始终运行，`uv publish` 仅在配置 `PYPI_TOKEN` 时执行
- [x] CI `runtime-build-test.yml` 就绪：push/PR 触发，校验同步内容 + 构建产物 + smoke test
- [x] `src/common/` 和 `src/trellis_runtime/upstream/` 内容与 upstream byte-identical（`sync_upstream.sh --check` 校验）
- [x] 包名可配置：修改 `pyproject.toml` 的 `name` 字段即可，同步脚本不覆盖

## Open Questions

1. **`uvx` 首次启动延迟** — `uvx` 第一次运行会创建 venv + 下载包，可能有 2-5s 延迟。hook timeout 需要考虑（Codex 15s、Claude 30s 应该够）。
2. **`common` 顶层包命名冲突风险** — top-level `common` 可能与其他 pip 包冲突。`uvx` 隔离环境降低风险，但 `pip install` 场景需评估。备选：改用 namespace package 或 `trellis_common`（但需要 monkey-patch import path）。
3. **Codex 平台检测退化** — `_detect_platform` 在 uvx 调用下对 Codex 返回 `None`（无 `CODEX_PROJECT_DIR` 环境变量，argv[0] 不含 `.codex`）。核心 breadcrumb 不受影响，但丢失 `codex.dispatch_mode` banner 和 no-task bootstrap notice 两个 Codex 专属质量增强。详细分析见 [hook-reference.md](./hook-reference.md#平台检测_detect_platform与-uvx-兼容性)。上游需要增加 `TRELLIS_FORCE_PLATFORM` 支持才能修复。
