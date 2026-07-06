# trellis-runtime

Trellis Python runtime scripts and hooks, packaged for global install via `uvx`.

Install once, use across every project — no per-project `.trellis/scripts/` needed.

## Quick start

```bash
# From this directory
uv build
uv run trellis-task --help
uv run trellis-hook-inject-workflow-state --help
```

After publishing to PyPI:

```bash
uvx --from trellis-runtime trellis-task --help
```

## Package layout

```
trellis-runtime/
├── pyproject.toml
├── scripts/
│   └── sync_upstream.sh          # sync from ../packages/cli/src/templates/
├── src/
│   ├── common/                     # 21 runtime modules (byte-identical to upstream)
│   │   ├── paths.py
│   │   ├── active_task.py
│   │   ├── config.py
│   │   └── ...
│   └── trellis_runtime/
│       └── upstream/
│           ├── hooks/              # 4 hook scripts (hyphen→underscore rename)
│           │   ├── inject_workflow_state.py
│           │   ├── session_start.py
│           │   ├── inject_subagent_context.py
│           │   └── inject_shell_session_context.py
│           └── entry/              # 5 CLI entry scripts
│               ├── task.py
│               ├── get_context.py
│               ├── add_session.py
│               ├── get_developer.py
│               └── init_developer.py
```

## Sync from upstream

```bash
# In this fork repo — syncs from ../packages/cli/src/templates/
./scripts/sync_upstream.sh

# Verify in CI — exits 1 if src/ drifted from upstream
./scripts/sync_upstream.sh --check
```

## Hook entry points

| Command | Upstream file |
|---|---|
| `trellis-hook-inject-workflow-state` | `inject-workflow-state.py` |
| `trellis-hook-session-start` | `session-start.py` |
| `trellis-hook-inject-subagent-context` | `inject-subagent-context.py` |
| `trellis-hook-inject-shell-session-context` | `inject-shell-session-context.py` |

CLI entry points: `trellis-task`, `trellis-get-context`, `trellis-add-session`, `trellis-get-developer`, `trellis-init-developer`.

## Per-agent hook config

See [hook-reference.md](.trellis/tasks/07-06-pypi-global-runtime/hook-reference.md) for complete Codex / Claude / OpenCode hook JSON configurations.

## Custom package name

Edit `name` in `pyproject.toml`. The sync script never overwrites it.
