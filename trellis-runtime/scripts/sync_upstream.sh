#!/usr/bin/env bash
# sync_upstream.sh — copy upstream Trellis scripts/hooks into this package.
#
# In this fork repo the upstream templates live at:
#   ../../packages/cli/src/templates/  (relative to this file)
#
# Sources (read-only, never modified):
#   trellis/scripts/common/    → src/common/
#   shared-hooks/*.py           → src/trellis_runtime/upstream/hooks/  (hyphen→underscore)
#   trellis/scripts/*.py        → src/trellis_runtime/upstream/entry/  (skip __init__.py)
#   <agent>/hooks/*.py          → src/trellis_runtime/platform_hooks/<agent>/  (hyphen→underscore)
#
# Usage:
#   ./scripts/sync_upstream.sh              # sync
#   ./scripts/sync_upstream.sh --check      # dry-run: verify in sync, exit 1 if drift
#   UPSTREAM_REPO=/path/to/fork ./scripts/sync_upstream.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_ROOT="${PKG_ROOT}/src"

# Default: assume upstream templates are in the same repo (fork checkout)
UPSTREAM_REPO="${UPSTREAM_REPO:-$(cd "$PKG_ROOT/.." && pwd)}"
UPSTREAM_TEMPLATES="$UPSTREAM_REPO/packages/cli/src/templates"

DRY_RUN=false
if [[ "${1:-}" == "--check" ]]; then
  DRY_RUN=true
  shift
fi

if [[ ! -d "$UPSTREAM_TEMPLATES" ]]; then
  echo "ERROR: upstream templates not found at $UPSTREAM_TEMPLATES" >&2
  echo "Set UPSTREAM_REPO to point at your Trellis fork checkout." >&2
  exit 1
fi

to_module_name() { echo "${1//-/_}"; }

DRIFT=0

# 1. common/
COMMON_SRC="$UPSTREAM_TEMPLATES/trellis/scripts/common"
COMMON_DST="$SRC_ROOT/common"
mkdir -p "$COMMON_DST"
for f in "$COMMON_SRC"/*.py; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  if $DRY_RUN; then
    diff -q "$f" "$COMMON_DST/$base" >/dev/null 2>&1 || { echo "DRIFT: $base"; DRIFT=1; }
  else
    cp "$f" "$COMMON_DST/$base"
  fi
done

# 2. shared-hooks (rename hyphen→underscore)
HOOKS_SRC="$UPSTREAM_TEMPLATES/shared-hooks"
HOOKS_DST="$SRC_ROOT/trellis_runtime/upstream/hooks"
mkdir -p "$HOOKS_DST"
for f in "$HOOKS_SRC"/*.py; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  mod="$(to_module_name "$base")"
  if $DRY_RUN; then
    diff -q "$f" "$HOOKS_DST/$mod" >/dev/null 2>&1 || { echo "DRIFT: $mod"; DRIFT=1; }
  else
    cp "$f" "$HOOKS_DST/$mod"
  fi
done

# 3. entry scripts (skip __init__.py)
ENTRY_SRC="$UPSTREAM_TEMPLATES/trellis/scripts"
ENTRY_DST="$SRC_ROOT/trellis_runtime/upstream/entry"
mkdir -p "$ENTRY_DST"
for f in "$ENTRY_SRC"/*.py; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  [[ "$base" == "__init__.py" ]] && continue
  if $DRY_RUN; then
    diff -q "$f" "$ENTRY_DST/$base" >/dev/null 2>&1 || { echo "DRIFT: $base"; DRIFT=1; }
  else
    cp "$f" "$ENTRY_DST/$base"
  fi
done

# 4. per-agent hooks (codex, copilot, … — any platform with hooks/*.py)
PLATFORM_HOOKS_DST="$SRC_ROOT/trellis_runtime/platform_hooks"
for platform_dir in "$UPSTREAM_TEMPLATES"/*/hooks; do
  [[ -d "$platform_dir" ]] || continue
  platform="$(basename "$(dirname "$platform_dir")")"
  # Skip non-agent template dirs
  [[ "$platform" == "shared-hooks" || "$platform" == "trellis" ]] && continue
  platform_dst="$PLATFORM_HOOKS_DST/$platform"
  mkdir -p "$platform_dst"
  for f in "$platform_dir"/*.py; do
    [[ -f "$f" ]] || continue
    base="$(basename "$f")"
    mod="$(to_module_name "$base")"
    if $DRY_RUN; then
      diff -q "$f" "$platform_dst/$mod" >/dev/null 2>&1 || { echo "DRIFT: $platform/$mod"; DRIFT=1; }
    else
      cp "$f" "$platform_dst/$mod"
    fi
  done
done

if $DRY_RUN; then
  if [[ $DRIFT -eq 1 ]]; then
    echo "FAIL: files drifted from upstream. Run ./scripts/sync_upstream.sh to fix."
    exit 1
  fi
  echo "OK: all files in sync."
else
  echo "Sync complete."
fi
