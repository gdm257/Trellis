#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dispatch wrapper for session-start hooks.

The shared-hooks ``session_start.py`` emits a top-level ``additional_context``
key for Cursor compatibility. Codex and Copilot use ``deny_unknown_fields``
on their output schemas, so that key causes deserialization failure. Their
per-agent forks (``codex/hooks/session-start.py``, ``copilot/hooks/session-start.py``)
emit only Codex/Copilot-safe keys.

This wrapper reads stdin once, detects the calling platform, then delegates
to the matching per-agent fork or falls back to the shared version. Upstream
and TS templates are never modified.
"""
from __future__ import annotations

import io
import json
import os
import sys


def _detect_target(hook_input: dict) -> str:
    """Return the platform whose session-start fork should run.

    Detection signals (ordered by specificity):
    - Codex: ``permission_mode`` field in SessionStart input JSON.
      Codex's ``SessionStartCommandInput`` always sends it; Claude Code / Qoder /
      Droid / Gemini / Trae do not.
    - Copilot: ``COPILOT_PROJECT_DIR`` env var, set by the Copilot hook runner.
    - Fallback: ``"shared"`` (shared-hooks version for all other platforms).
    """
    if isinstance(hook_input.get("permission_mode"), str):
        return "codex"
    if os.environ.get("COPILOT_PROJECT_DIR"):
        return "copilot"
    return "shared"


def main() -> None:
    raw_stdin = sys.stdin.read()

    try:
        hook_input = json.loads(raw_stdin) if raw_stdin.strip() else {}
        if not isinstance(hook_input, dict):
            hook_input = {}
    except (json.JSONDecodeError, ValueError):
        hook_input = {}

    target = _detect_target(hook_input)

    # Restore stdin for the target's main(), but use a wrapper that survives
    # common.__init__ stream reconfiguration (StringIO lacks reconfigure and
    # its detach() raises, breaking the _configure_stream fallback path).
    sys.stdin = _BufferedStdin(raw_stdin)

    if target == "codex":
        from trellis_runtime.platform_hooks.codex.session_start import main as run
    elif target == "copilot":
        from trellis_runtime.platform_hooks.copilot.session_start import main as run
    else:
        from trellis_runtime.upstream.hooks.session_start import main as run

    run()


class _BufferedStdin:
    """Stdin replacement carrying pre-read content through a module boundary.

    Delegates read()/readline() to an internal StringIO, but also provides a
    no-op reconfigure() so that common.__init__._configure_stream picks the
    safe first branch instead of trying detach() on a StringIO (which raises
    io.UnsupportedOperation).
    """

    encoding = "utf-8"
    errors = "replace"

    def __init__(self, content: str) -> None:
        self._buf = io.StringIO(content)

    def read(self, *args, **kwargs):
        return self._buf.read(*args, **kwargs)

    def readline(self, *args, **kwargs):
        return self._buf.readline(*args, **kwargs)

    def reconfigure(self, **kwargs) -> None:
        pass


if __name__ == "__main__":
    main()
