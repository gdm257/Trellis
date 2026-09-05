#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Default CLI dispatcher: `uvx trellis-runtime <name> ...`.

Saves the `--from` flag: `uvx trellis-runtime task ...` instead of
`uvx --from trellis-runtime trellis-task ...`. The per-command `trellis-*`
entry points remain installed and preferred where available. Hooks dispatch
the same way: `uvx trellis-runtime inject-workflow-state` ≡
`uvx --from trellis-runtime trellis-hook-inject-workflow-state`.
"""
from __future__ import annotations

import sys

from trellis_runtime.platform_hooks.claude import statusline
from trellis_runtime.platform_hooks.codex import session_start as codex_session_start
from trellis_runtime.platform_hooks.copilot import session_start as copilot_session_start
from trellis_runtime.platform_hooks.snow import write_trellis_context
from trellis_runtime.upstream.entry import add_session, get_context, get_developer, init_developer, task
from trellis_runtime.upstream.hooks import (
    inject_shell_session_context,
    inject_subagent_context,
    inject_workflow_state,
)
from trellis_runtime.wrappers import session_start

COMMANDS = {
    "task": task,
    "get-context": get_context,
    "add-session": add_session,
    "get-developer": get_developer,
    "init-developer": init_developer,
    "inject-workflow-state": inject_workflow_state,
    "session-start": session_start,
    "inject-subagent-context": inject_subagent_context,
    "inject-shell-session-context": inject_shell_session_context,
    "codex-session-start": codex_session_start,
    "copilot-session-start": copilot_session_start,
    "statusline": statusline,
    "write-trellis-context": write_trellis_context,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: trellis-runtime <command> [args...]")
        print(f"Commands: {', '.join(sorted(COMMANDS))}")
        return 0 if len(sys.argv) < 2 else 0

    name = sys.argv[1]
    module = COMMANDS.get(name)
    if module is None:
        print(f"Error: unknown command '{name}'", file=sys.stderr)
        print(f"Commands: {', '.join(sorted(COMMANDS))}", file=sys.stderr)
        return 2

    sys.argv = [sys.argv[0], *sys.argv[2:]]
    result = module.main()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
