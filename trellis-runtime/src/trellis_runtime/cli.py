#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Default CLI dispatcher: `uvx trellis-runtime <name> ...`.

Saves the `--from` flag: `uvx trellis-runtime task ...` instead of
`uvx --from trellis-runtime trellis-task ...`. The per-command `trellis-*`
entry points remain installed and preferred where available.
"""
from __future__ import annotations

import sys

from trellis_runtime.upstream.entry import add_session, get_context, get_developer, init_developer, task

COMMANDS = {
    "task": task,
    "get-context": get_context,
    "add-session": add_session,
    "get-developer": get_developer,
    "init-developer": init_developer,
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
