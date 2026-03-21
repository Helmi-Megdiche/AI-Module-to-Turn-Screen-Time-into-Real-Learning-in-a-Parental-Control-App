#!/usr/bin/env sh
# POSIX-friendly wrapper (Git Bash / macOS / Linux)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
node scripts/run-all-tests.js "$@"
