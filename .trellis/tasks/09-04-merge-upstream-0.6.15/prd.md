# Merge upstream 0.6.15

## Background

上游 mindfold-ai/Trellis 已发布 v0.6.15（merge-base `bd0bc80c`，共 188 个提交）。fork 在 `trellis-runtime/`（vendored runtime 包）、`.trellis/spec/cli/backend/trellis-dependencies.md`、docs 上有独立提交，与上游改动路径重叠小。

前期调查结论：

- 脚本与 `.trellis` 文件集合不变：5 个 entry 脚本、workflow.md、config.yaml、`.version`、`.template-hashes.json` 均保留。
- 新增路径 `.trellis/.runtime/sessions/`（active-task 指针，per-session，commit 7677aa22 / 592e93ef）。
- config.yaml 新增 `trusted_context_dirs`、`auto_trust_trellis_symlinks`；Codex dispatch 默认 `inline` → `auto`。
- shared-hooks 4 个文件集合不变，内部大改（+899 行）。
- snow 平台新增 `hooks/write-trellis-context.py`（sync 会自动拷入 platform_hooks/snow/）。
- runtime 分发契约保持：`get_context.py` 改为 `from common.git_context import main` 重导出，`module.main` 属性仍存在，cli.py 与 pyproject 12 个 entry points 无需改动。

## Requirements

1. 将 upstream `v0.6.15` merge 进 `main`，解决冲突时保留 fork 的 `trellis-runtime/` 与 fork docs/spec 提交。
2. merge 后运行 `trellis-runtime/scripts/sync_upstream.sh`，vendored 代码与 0.6.15 模板一致（`--check` 通过）。
3. 更新 `.trellis/spec/cli/backend/trellis-dependencies.md`：新增 `.trellis/.runtime/sessions/` 行；补充 config.yaml 行的 `trusted_context_dirs` / `auto_trust_trellis_symlinks` / dispatch 默认值变化。
4. trellis-runtime 重建后冒烟验证：`uvx trellis-runtime task list` 与 `get-context` 正常退出。

## Acceptance Criteria

- [ ] `git merge v0.6.15` 完成且工作树干净
- [ ] `sync_upstream.sh --check` 输出 OK
- [ ] `uvx trellis-runtime task list` 退出码 0
- [ ] `uvx trellis-runtime get-context` 退出码 0
- [ ] trellis-dependencies.md 含 `.runtime/sessions` 行且 config.yaml 行已更新
- [ ] 变更已提交到 main

## Constraints

- 不 push；merge 结果留在本地 main，推送由用户决定。
- 不修改 `trellis-runtime/src/` 下 vendored 文件（只经 sync 脚本更新）。
