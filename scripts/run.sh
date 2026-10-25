#!/usr/bin/env bash
set -euo pipefail
skill_root="$(cd "$(dirname "$0")/.." && pwd)"
runtime="${TEACHING_VIDEO_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/teaching-video-skill}"
export TEACHING_VIDEO_HOME="$runtime"
prefix="${TEACHING_VIDEO_ENV:-$runtime/envs/teaching-video}"
script="${1:-doctor}"
if [ "$#" -gt 0 ]; then shift; fi
case "$script" in doctor|pipeline|images|media_audit|draft_ops|verify_codec|project|test_pipeline|test_portable) ;; *) echo "Unknown script" >&2; exit 2;; esac
[ -x "$prefix/bin/python" ] || { echo "Run bash scripts/bootstrap.sh first." >&2; exit 2; }
export PATH="$prefix/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
exec "$prefix/bin/python" -X utf8 "$skill_root/scripts/$script.py" "$@"
