# Per-Agent Hook Reference

全局安装 `trellis-runtime` 后各 agent 平台的 hook 配置。所有 command 通过 `uvx` 调用，无需 per-project `.trellis/scripts/`。

## entry points

| Command | 映射 upstream 文件 | 用途 |
|---|---|---|
| `trellis-hook-inject-workflow-state` | `shared-hooks/inject-workflow-state.py` | 每次 prompt 注入 workflow-state breadcrumb |
| `trellis-hook-session-start` | `shared-hooks/session-start.py` | session 开始注入完整上下文（spec/tasks/developer） |
| `trellis-hook-inject-subagent-context` | `shared-hooks/inject-subagent-context.py` | sub-agent dispatch 时注入任务上下文 |
| `trellis-hook-inject-shell-session-context` | `shared-hooks/inject-shell-session-context.py` | shell session 上下文注入 |
| `trellis-task` | `trellis/scripts/task.py` | task CLI（create/start/finish/archive/list） |
| `trellis-get-context` | `trellis/scripts/get_context.py` | git/工作区上下文 |
| `trellis-add-session` | `trellis/scripts/add_session.py` | 记录 session 到 journal |
| `trellis-get-developer` | `trellis/scripts/get_developer.py` | 读取 developer identity |
| `trellis-init-developer` | `trellis/scripts/init_developer.py` | 初始化 developer identity |

## Codex

2 个 active hook：`SessionStart` + `UserPromptSubmit`。

**上游状态**：Trellis `codex.ts:60-62` 将 Codex 标记为 class-2 pull-based 平台，`hooks.json` 仅注册 `UserPromptSubmit`，`session-start.py` 以 "retained compatibility template and regression surface"（`codex.ts:73-75`）保留但不接线。但 class-2 分类针对的是 **sub-agent 上下文注入**——PreToolUse 只对 Bash 触发，CollabAgentSpawn hook 未实现（#15486）——与 SessionStart 独立。Codex 官方早已支持 SessionStart（matcher: `startup|resume|clear|compact`）。全局安装可自行注册 SessionStart，`session-start.py` 已输出正确的 `hookSpecificOutput.hookEventName: "SessionStart"` JSON 格式。session-start.py 在 uvx 下 `_detect_platform` 返回 `None` 不影响正确性：仅 kiro 分支输出纯文本，其余平台统一输出 JSON envelope。

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [{
          "type": "command",
          "command": "uvx --from trellis-runtime trellis-hook-session-start",
          "timeout": 30
        }]
      }
    ],
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "uvx --from trellis-runtime trellis-hook-inject-workflow-state",
        "timeout": 15
      }]
    }]
  }
}
```

放置位置：per-project `.codex/hooks.json`。

前置条件：用户级 `~/.codex/config.toml` 设置 `features.hooks = true`（Codex 0.129+）；Codex 0.129+ 还需一次性 `/hooks` TUI 审批。

## Claude Code

3 个 hook 文件，3 个 event 类型。

```json
{
  "hooks": {
    "SessionStart": [
      {"matcher": "startup", "hooks": [{"type": "command", "command": "uvx --from trellis-runtime trellis-hook-session-start", "timeout": 30}]},
      {"matcher": "clear",   "hooks": [{"type": "command", "command": "uvx --from trellis-runtime trellis-hook-session-start", "timeout": 30}]},
      {"matcher": "compact", "hooks": [{"type": "command", "command": "uvx --from trellis-runtime trellis-hook-session-start", "timeout": 30}]}
    ],
    "PreToolUse": [
      {"matcher": "Task",  "hooks": [{"type": "command", "command": "uvx --from trellis-runtime trellis-hook-inject-subagent-context", "timeout": 30}]},
      {"matcher": "Agent", "hooks": [{"type": "command", "command": "uvx --from trellis-runtime trellis-hook-inject-subagent-context", "timeout": 30}]}
    ],
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "uvx --from trellis-runtime trellis-hook-inject-workflow-state", "timeout": 15}]}
    ]
  }
}
```

放置位置：per-project `.claude/settings.json`。Claude 不支持 user-level hooks，必须 per-project。

## OpenCode

OpenCode 用 JS plugins（非 Python hooks），不走 `uvx` 方案。plugins 内部 `TrellisContext(directory)` 直接读 `.trellis/` 文件系统。

全局化路径：将 `packages/cli/src/templates/opencode/` 下的 JS plugins 拷贝到全局位置（`~/.config/opencode/plugin/`）。plugins 不依赖 Python，仅读 `.trellis/` 文件。

作为独立后续项，不在本任务范围内。

## uvx 运行时行为

1. `uvx --from trellis-runtime <command>` 首次运行创建隔离 venv + 安装包（2-5s），后续命中缓存（<0.5s）
2. hook 从 stdin 读取 platform JSON payload
3. hook 内部 `find_trellis_root(cwd)` 向上查找 `.trellis/`
4. `sys.path.insert(0, ".trellis/scripts")` — per-project `.trellis/scripts/` 存在时优先（向后兼容），不存在则回退到 site-packages 的全局 `common`
5. 向 stdout 输出注入 context，正常执行

## stdin/stdout 协议

### stdin（所有 hook 统一）

各 agent 通过 stdin 传 JSON payload。hook 读取的主要字段：

| 字段 | 用途 | fallback |
|---|---|---|
| `cwd` | 项目根目录定位 | `os.getcwd()` |
| `tool_name` / `toolName` | sub-agent 类型识别（仅 inject-subagent-context） | 无 |
| `agent_name` | Claude Task 工具名（仅 inject-subagent-context） | 无 |
| `tool_input.prompt` / `prompt` | sub-agent 原始 prompt（仅 inject-subagent-context） | 无 |

读取方式差异：
- `inject-workflow-state.py`：线程 + 0.2s timeout（防御 Kiro IDE 的 open-stdin 问题）
- `session-start.py` / `inject-subagent-context.py`：直接 `json.loads(sys.stdin.read())`

Codex / Claude 均在写入 payload 后关闭 stdin，三种方式都能正常工作。

### stdout（按平台分支）

**inject-workflow-state.py** — 三条输出路径：

| platform | stdout 格式 | Codex 全局安装命中？ |
|---|---|---|
| kiro | 纯文本 breadcrumb | 不适用 |
| gemini | `{"hookSpecificOutput": {"hookEventName": "BeforeAgent", "additionalContext": ...}}` | 不适用 |
| 其他（含 Codex/Claude） | `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ...}}` | ✅ |

**session-start.py** — 两条输出路径：

| platform | stdout 格式 |
|---|---|
| kiro | 纯文本 context |
| 其他 | `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ...}, "additional_context": ...}`（同时含 camelCase + snake_case 兼容 Cursor） |

**inject-subagent-context.py** — 统一输出（所有平台同一 JSON）：

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {...}
  },
  "permission": "allow",
  "updated_input": {...},
  "updatedInput": {...}
}
```

多格式并存（Claude 格式 + Cursor 格式 + Gemini 格式），各平台取自己认识的字段。

## 平台检测（_detect_platform）与 uvx 兼容性

三个 hook 都用 `_detect_platform(input_data)` 判断调用方平台，检测优先级：

1. `input_data["cursor_version"]` 存在 → cursor
2. 环境变量 `*_PROJECT_DIR`（`CLAUDE_PROJECT_DIR`, `CURSOR_PROJECT_DIR` 等 9 个）→ 对应平台
3. `sys.argv[0]` 路径包含 `.claude` / `.codex` / `.cursor` / `.gemini` → 对应平台
4. 以上都不命中 → `None`

### uvx 下的检测情况

| 平台 | 环境变量检测 | argv[0] 路径检测 | uvx 下结果 |
|---|---|---|---|
| Claude | ✅ `CLAUDE_PROJECT_DIR` 由 Claude Code 设置 | 不依赖 | ✅ 正常检测为 `claude` |
| Codex | ❌ 无 `CODEX_PROJECT_DIR` 环境变量 | ❌ argv[0] 为 uvx entry point，不含 `.codex` | ⚠️ 退化为 `None` |
| OpenCode | N/A（JS plugins，不走 Python hooks） | N/A | N/A |

### Codex 检测退化影响

当 `_detect_platform` 返回 `None`（uvx 调用时），`inject-workflow-state.py` 行为变化：

| 功能 | platform == "codex" 时 | platform == None 时（uvx） |
|---|---|---|
| `codex.dispatch_mode` banner | ✅ 注入 `<codex-mode>` 提示 inline/sub-agent 模式 | ❌ 不注入 |
| no-task bootstrap notice | ✅ 注入 `<trellis-bootstrap>` 引导 trellis-start skill | ❌ 不注入 |
| breadcrumb source 信息 | ❌ 抑制（codex 专属） | ✅ 显示（非 codex 行为） |
| 核心 breadcrumb（active task + workflow state） | ✅ | ✅ 不受影响 |
| stdout JSON 格式 | `hookSpecificOutput.UserPromptSubmit` | ✅ 相同 |

**结论**：核心功能不受影响，丢失的是两个 Codex 专属质量增强。hook 仍产出有效 JSON，Codex 正常解析。

### 可选修复：显式平台标记

如果需要恢复 Codex 专属行为，在 hook command 中设置环境变量绕过检测：

```json
{
  "command": "set TRELLIS_FORCE_PLATFORM=codex && uvx --from trellis-runtime trellis-hook-inject-workflow-state",
  "timeout": 15
}
```

但当前 hook 不读取 `TRELLIS_FORCE_PLATFORM`（上游未实现）。该字段需要上游在 `_detect_platform` 中增加：

```python
forced = os.environ.get("TRELLIS_FORCE_PLATFORM")
if forced:
    return forced
```

在 fork 不可改的前提下，此修复需要等上游采纳。当前版本接受退化行为作为全局安装的 trade-off。

## Prompt 覆盖（命令路径重定向）

hook 注入的上下文（workflow.md、session-start breadcrumb、skill/command 文件）里写死了 `python3 ./.trellis/scripts/<name>.py`。全局安装后这些文件不存在，需要一段 prompt 覆盖，告诉 LLM 改用 uvx。

**覆盖 prompt（中文版）**：

```
本项目未安装 .trellis/scripts/。所有 `python3 ./.trellis/scripts/<name>.py` 命令一律替换为 `uvx --from trellis-runtime trellis-<name>`：

- task.py → trellis-task
- get_context.py → trellis-get-context
- add_session.py → trellis-add-session
- get_developer.py → trellis-get-developer
- init_developer.py → trellis-init-developer

参数完全相同。
```

**英文版**：

```
Do NOT use `python3 ./.trellis/scripts/<name>.py` — this project has no .trellis/scripts/. Replace every occurrence with `uvx --from trellis-runtime trellis-<name>` (same flags):

- task.py → trellis-task
- get_context.py → trellis-get-context
- add_session.py → trellis-add-session
- get_developer.py → trellis-get-developer
- init_developer.py → trellis-init-developer
```

**放置位置**：

- Codex：`AGENTS.md`（TRELLIS managed block 之外，不会被 `trellis update` 覆盖）
- Claude：`CLAUDE.md` 或 `AGENTS.md`（Claude Code 读取 AGENTS.md）
- 任意平台：用户自定义 instruction / system prompt

LLM 看到映射规则后能自动泛化——遇到 `python3 ./.trellis/scripts/task.py list --mine` 会执行 `uvx --from trellis-runtime trellis-task list --mine`，无需逐条枚举。

## 向后兼容

项目内同时存在 `.trellis/scripts/`（via `trellis init`）时，hook 的 `sys.path.insert` 使 per-project 版本优先。这意味着：

- `trellis init` 过的项目：per-project scripts 运行（与现状完全一致）
- 仅全局安装的项目：site-packages 中的 `common` 运行
- 两者皆有：per-project 优先（sys.path 顺序）

两种路径对最终用户透明，无需感知。
