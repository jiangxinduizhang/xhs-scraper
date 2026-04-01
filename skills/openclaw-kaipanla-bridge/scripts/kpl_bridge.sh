#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

is_repo_root() {
  local candidate="$1"
  [[ -f "$candidate/KPL_HANDOFF.md" && -f "$candidate/scripts/kpl_tool.py" ]]
}

resolve_repo_root() {
  local candidate=""

  if [[ -f "$SKILL_DIR/repo-root.txt" ]]; then
    candidate="$(tr -d '[:space:]' < "$SKILL_DIR/repo-root.txt")"
    if [[ -n "$candidate" ]] && is_repo_root "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  fi

  if [[ -n "${OPENCLAW_KPL_REPO_ROOT:-}" ]] && is_repo_root "${OPENCLAW_KPL_REPO_ROOT}"; then
    printf '%s\n' "$OPENCLAW_KPL_REPO_ROOT"
    return 0
  fi

  if [[ -n "${KPL_REPO_ROOT:-}" ]] && is_repo_root "${KPL_REPO_ROOT}"; then
    printf '%s\n' "$KPL_REPO_ROOT"
    return 0
  fi

  candidate="$PWD"
  while true; do
    if is_repo_root "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
    [[ "$candidate" == "/" ]] && break
    candidate="$(dirname "$candidate")"
  done

  return 1
}

resolve_python() {
  local candidates=(
    "$repo_root/.venv/bin/python"
    "$repo_root/venv/bin/python"
    "/opt/homebrew/bin/python3.11"
    "python3.11"
    "python3"
  )
  local py=""

  for py in "${candidates[@]}"; do
    if [[ -x "$py" ]]; then
      printf '%s\n' "$py"
      return 0
    fi
    if command -v "$py" >/dev/null 2>&1; then
      command -v "$py"
      return 0
    fi
  done

  return 1
}

if [[ ${1:-} == "--repo-root" ]]; then
  if [[ $# -lt 2 ]]; then
    echo "usage: $0 [--repo-root PATH] <kpl_tool args...>" >&2
    exit 2
  fi
  export OPENCLAW_KPL_REPO_ROOT="$2"
  shift 2
fi

if [[ $# -eq 0 ]]; then
  echo "usage: $0 [--repo-root PATH] <kpl_tool args...>" >&2
  exit 2
fi

repo_root="$(resolve_repo_root)" || {
  cat >&2 <<'ERR'
无法定位 xhs-scraper 仓库根目录。
请先向人类确认仓库路径，然后将该绝对路径写入当前 skill 目录下的 repo-root.txt（仅一行）。
也可临时设置 OPENCLAW_KPL_REPO_ROOT / KPL_REPO_ROOT，或从仓库目录内重试。
ERR
  exit 1
}

python_bin="$(resolve_python)" || {
  cat >&2 <<'ERR'
无法找到可用的 Python 解释器。
请优先提供 Python 3.11+，或在仓库内创建 .venv / venv。
ERR
  exit 1
}

cd "$repo_root"
exec "$python_bin" "$repo_root/scripts/kpl_tool.py" "$@"
