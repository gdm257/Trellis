# `.trellis` Dependency Audit

## Scope

本规范只记录当前安装面和 shipped template 中对 `.trellis/` 具体路径的硬编码依赖。consumer 使用精确名称：skill name、command name、agent name、script name、CLI command name。同名 agent 在不同平台重名时用 `Claude` / `Codex` 限定；仅存在于 shipped template 的 consumer 明确标注 `(shipped template)`。

依赖模式：

- `exec`: 直接执行、读取、写入或扫描该路径。
- `emit`: 只输出命令或指令，不保证自己执行。
- `doc`: 文档或示例引用，不是运行依赖。

## Spec Files

| `.trellis` path | Hardcoded consumers | 作用 | 必要性 | 不存在的影响 |
|---|---|---|---|---|
| `spec/guides/index.md` | `exec: trellis-start; trellis-before-dev`<br>`emit: session-start.py; packages_context.py; workflow.md`<br>`doc: trellis-meta` | 共享跨包思考指南入口 | `exec` consumer 必需；普通任务操作不需要 | `session-start.py` 不列出该指南；`trellis-start` / `trellis-before-dev` 的读取命令失败；`packages_context.py` 只检查 `guides/` 目录，可能继续广播缺失的 index 路径 |
| `spec/frontend/**` | `exec: onboard (shipped template)`<br>`emit: integrate-skill (shipped template); break-loop (shipped template)`<br>`doc: trellis-meta` | 前端规范写入与占位符检查目标 | 当前安装的 task/session runtime 不需要；仅上述 shipped template 行为需要 | 当前 runtime 不失败。`onboard` 的 guarded `grep` 返回 0，可能把缺失目录误判为已定制；`integrate-skill` / `break-loop` 需要先创建目标才能完成写入 |
| `spec/backend/**` | `exec: onboard (shipped template)`<br>`emit: integrate-skill (shipped template); break-loop (shipped template)`<br>`doc: trellis-meta` | 后端规范写入与占位符检查目标 | 当前安装的 task/session runtime 不需要；仅上述 shipped template 行为需要 | 当前 runtime 不失败。`onboard` 的 guarded `grep` 返回 0，可能把缺失目录误判为已定制；`integrate-skill` / `break-loop` 需要先创建目标才能完成写入 |

`trellis-spec-bootstrap` 没有硬编码 `guides`、`frontend`、`backend` 三个路径；它动态扫描当前 `.trellis/spec/` 树。

## Scripts And Workflow

| `.trellis` path | Hardcoded consumers | 作用 | 必要性 | 不存在的影响 |
|---|---|---|---|---|
| `scripts/get_context.py` | `exec: trellis-start; trellis-continue; trellis-before-dev; trellis-check; trellis-finish-work; /trellis:continue; /trellis:improve-ut; /trellis:finish-work; Codex trellis-implement; Codex trellis-check`<br>`emit: session-start.py; workflow.md; task.py; task_store.py`<br>`doc: trellis-meta` | 输出 session、package、phase、record context | 所有 `exec` consumer 必需 | `exec` consumer 在命令启动处失败；`emit` consumer 继续输出不可用命令；未走这些入口的普通操作不受影响 |
| `scripts/task.py` | `exec: trellis-brainstorm; first-principles-thinking; trellis-finish-work; /trellis:finish-work; Claude trellis-research; Codex trellis-research; Codex trellis-implement; Codex trellis-check`<br>`emit: session-start.py; workflow.md`<br>`doc: trellis-meta` | 任务创建、状态、归档和 curated context 管理 | 所有 `exec` consumer 必需 | 任务命令和依赖它的 agent 步骤失败；`session-start.py` / `workflow.md` 输出不可用命令；普通文件编辑不受影响 |
| `scripts/add_session.py` | `exec: trellis-finish-work; /trellis:finish-work`<br>`emit: workflow.md`<br>`doc: trellis-meta` | 追加 journal 并更新 developer index | session 记录链路必需 | finish-work 的记录步骤失败；`workflow.md` 输出不可用命令；任务读写和 context 查询不受影响 |
| `scripts/init_developer.py` | `exec: trellis init`<br>`emit: workflow.md`<br>`doc: trellis-meta` | 创建 `.developer`、developer workspace、journal 和 index | 首次身份初始化必需；已初始化项目不需要 | 直接执行失败；`trellis init` 捕获失败并提示手动执行同样不可用的命令，`.developer` 保持缺失；既有身份流程不受影响 |
| `scripts/get_developer.py` | `doc: trellis-meta; workspace-index.md` | 输出当前 developer identity | 当前安装面没有 `exec` consumer；手动工具 | 没有 active runtime consumer 失败；手动执行失败；其他 task/session 操作不受影响 |
| `workflow.md` | `exec: workflow_phase.py; session-start.py; inject-workflow-state.py; trellis-start; trellis-continue; /trellis:continue; Claude trellis-research; Claude trellis-implement`<br>`exec writer: trellis init; trellis workflow; trellis update`<br>`emit: task.py; task_context.py`<br>`doc: trellis-meta` | phase/step 指引、skill routing、workflow-state breadcrumb 源 | workflow/context/breadcrumb 链路必需；generic task CRUD 不需要 | `workflow_phase.py` 抛 `FileNotFoundError`；`session-start.py` 显示 no workflow；`inject-workflow-state.py` 使用 generic fallback；依赖读取的 skill/command/agent 指引缺失；`task.py list/create/start/finish` 等通用操作继续 |

## Channel Agents

| `.trellis` path | Hardcoded consumers | 作用 | 必要性 | 不存在的影响 |
|---|---|---|---|---|
| `agents/<name>.md` 或 `agents/<name>/AGENT.md` | `exec: agent-loader.ts; trellis channel spawn --agent <name>`<br>`exec scanner: agent-refs.ts; trellis init --workflow; trellis workflow`<br>`exec writer: trellis update`<br>`doc: trellis-channel; trellis-meta` | channel worker 的 frontmatter 和 system prompt 定义 | 仅显式 `--agent <name>` 或引用该 agent 的 workflow 需要 | 普通单-agent workflow 继续；显式选中的 agent spawn 失败；workflow 安装/切换只输出 non-blocking warning；`trellis update` 可回填 managed agent |

## Developer And Workspace

| `.trellis` path | Hardcoded consumers | 作用 | 必要性 | 不存在的影响 |
|---|---|---|---|---|
| `.developer` | `exec: paths.py; developer.py; init_developer.py; get_developer.py; session_context.py; trellis init; trellis update`<br>`exec identity caller: get_context.py; add_session.py; task.py; safe_commit.py; task_queue.py; task_store.py` | 当前 checkout 的 developer identity，决定 workspace、journal 和 `--mine` / implicit assignee | identity-specific 操作必需；generic task 操作不需要 | `get_developer.py`、`add_session.py`、`task.py list --mine`、无 `--assignee` 的 `task.py create` 退出 1；`get_context.py` 文本模式输出初始化错误并截断 context，JSON mode 输出 `developer: ""`；`task.py list/start/finish` 等非 identity 操作和显式 `--assignee` 创建继续 |
| `workspace/<developer>/index.md` | `exec: add_session.py; safe_commit.py`<br>`exec writer: developer.py`<br>`doc: trellis-meta` | session 计数、journal 状态和 history index | 可靠 journal 记录和 scoped staging 必需；非 journal workflow 不需要 | session 编号从 1 重新开始；`add_session.py` 可先追加或创建 journal，再因 index 缺失失败，留下 partial journal state；`.developer` 已存在时 `init_developer.py` 不会修复该 index；非 journal workflow 继续 |
| `workspace/index.md` | `doc: trellis-meta` | 全局 workspace 文档入口 | runtime 不需要 | 没有 task/session runtime 影响；仅文档链接失效 |

## Management State

| `.trellis` path | Hardcoded consumers | 作用 | 必要性 | 不存在的影响 |
|---|---|---|---|---|
| `config.yaml` | `exec: config.py; trellis_config.py; session-start.py; inject-workflow-state.py; workflow_phase.py; task_store.py; add_session.py; trellis init; trellis update; trellis channel`<br>`emit: safe_commit.py` | monorepo package、task hooks、journal、scope、channel guard、Codex dispatch 设置 | 文件可选； configured semantics 必需 | reader 得到空 config 或 defaults，基础 task/session 操作继续，但 monorepo、hook、scope、journal、channel guard、dispatch 语义降级 |
| `.version` | `exec: session_context.py; trellis update`<br>`exec writer: trellis init`<br>`doc: trellis-meta` | 记录已安装 template version，供 update/migration 比较 | update 语义需要；普通 task/session runtime 不需要 | `session_context.py` 返回 `None` 并省略版本比较；`trellis update` 把项目版本视为 `unknown`，跳过 regular migration，但 template 更新和 hash-verified cleanup 继续；`trellis init` 重写该文件 |
| `.template-hashes.json` | `exec: template-hash.ts; manifest-prune.ts; trellis init; trellis update; trellis uninstall; trellis workflow`<br>`doc: create-manifest; trellis-meta` | template provenance 和 user-modified/pristine 分类 | task/session runtime 不需要；安全 update/uninstall/workflow 切换需要 | hashes 加载为 `{}`；`trellis update` 可重建 tracking 但失去可靠 modified/pristine 分类；`trellis uninstall` 因无法证明 ownership 退出 1；`trellis workflow` 把已有不同 `workflow.md` 视为 modified，要求 force/create-new/skip 类处理 |

`safe_commit.py` 含 `.template-hashes.json` 字面量，但只把它排除出 staging，不解析内容，也不因该文件缺失而失败。
