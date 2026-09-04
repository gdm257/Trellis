# trellis-runtime Package Conventions

## Scope

`trellis-runtime/` 是 fork 本地 Python 包：把上游模板中的 `.trellis` scripts / hooks 打包为可 `uvx` 全局安装的 runtime（README、pyproject、`src/`）。本文记录它的同步流程、版本与发布约定、入口契约和验证方式。

约束：`src/` 下的 vendored 文件永不手改，唯一合法变更路径是 `scripts/sync_upstream.sh`。

## Source Of Truth & Sync

上游模板位于 fork checkout 内 `packages/cli/src/templates/`，是唯一源。`sync_upstream.sh` 的映射：

| 上游路径 | 目标 | 转换 |
|---|---|---|
| `trellis/scripts/common/*.py` | `src/common/` | 原样拷贝 |
| `shared-hooks/*.py` | `src/trellis_runtime/upstream/hooks/` | hyphen→underscore 文件名 |
| `trellis/scripts/*.py`（跳过 `__init__.py`） | `src/trellis_runtime/upstream/entry/` | 原样拷贝 |
| `<platform>/hooks/*.py` | `src/trellis_runtime/platform_hooks/<platform>/` | hyphen→underscore |

规则：

- merge 上游后必须重跑 sync，再提交；`--check` 退出 1 表示 drift，作为 CI/提交前闸门。
- 新平台若带 `hooks/*.py`，sync 自动收录（例：0.6.15 新增 `snow/hooks/write-trellis-context.py` → `platform_hooks/snow/`）。该 hook 若需要 uvx 调用入口，须在 pyproject `[project.scripts]` 手工加一行——sync 不会改 pyproject。
- 上游删除脚本或 hook 时，sync 只覆盖同名文件：目标侧遗留文件需手工删除并在 commit message 说明。

## Versioning & Release

- 版本跟随上游 Trellis 版本：sync 上游 `X.Y.Z` 后，pyproject `version = "X.Y.Z"`。
- `postN` 仅用于 runtime 自身的非 sync 改进（如 dispatcher、wrapper、pyproject 调整）。
- release commit：`chore(release): bump trellis-runtime to <version>`，diff 只有 pyproject 一行。
- annotated tag：`runtime-v<version>`，必须带 `runtime-` 前缀（无前缀的 `v0.6.5.post2` 是一次性旧例）。

### Wrong vs Correct

sync 上游 0.6.15 之后的版本演进：

```text
# Wrong — 沿用 postN 递增
version = "0.6.5.post4"        # tag: runtime-v0.6.5.post4

# Correct — 取上游版本号
version = "0.6.15"             # tag: runtime-v0.6.15
```

历史佐证：`runtime-v0.6.5`（sync 0.6.5）→ `runtime-v0.6.5.post1/2/3`（均为 runtime 本地改进，post3 = dispatcher commit）。

## Entry Contract

分发层只有一个契约：每个 entry / hook 模块暴露模块级可调用的 `main()`（返回 `int` 或 `None`）。

- `src/trellis_runtime/cli.py`：`COMMANDS = {"task": task, ...}`，分发即 `module.main()`。
- pyproject `[project.scripts]`：12 个 entry point 全部指向 `<module>:main`，与 COMMANDS 一一对应（dispatcher `trellis-runtime` + 5 个 `trellis-*` CLI + 6 个 `trellis-hook-*`）。

### Validation & Error Matrix

| 条件 | 行为 |
|---|---|
| `trellis-runtime <unknown>` | stderr 提示 + exit 2 |
| 无参数 / `-h` / `--help` | 打印 usage，exit 0 |
| entry 模块缺失 `main` | dispatch 时 `AttributeError`（sync 后跑 smoke 测试即可暴露） |

### Gotcha

> 上游可能把 `main()` 改为 re-export（0.6.15 的 `get_context.py`：`from common.git_context import main`）。模块属性仍然满足契约，**不要**为此手改 vendored 文件；`cli.py` 与 `[project.scripts]` 都无需变动。

## Verification

```bash
cd trellis-runtime                # 必须在包目录内；repo 根没有该 uv 项目
./scripts/sync_upstream.sh --check   # drift 闸门，期望 "OK: all files in sync."
uv sync                              # 重建 editable venv
uv run trellis-runtime task list     # smoke：exit 0
uv run trellis-runtime get-context --help   # smoke：exit 0
```

### Common Mistake: 在 repo 根运行 `uv run trellis-runtime`

**Symptom**: `error: Failed to spawn: 'trellis-runtime' — program not found`。

**Cause**: `uv run` 按 cwd 解析 uv 项目；repo 根不是 `trellis-runtime/` 的项目，找不到 venv 入口。

**Fix**: `cd trellis-runtime` 后运行，或 `uv run --project trellis-runtime trellis-runtime <cmd>`。
