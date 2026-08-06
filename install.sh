#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/StariverKang/Jobhunting-skill-pack.git"
SKILLS=(
  "consultant-style-resume-audit"
  "cv-experience-refinement"
  "bio-for-cv"
)

target_dir="${AGENT_SKILLS_DIR:-${HOME}/.agents/skills}"
source_dir=""
temp_dir=""

usage() {
  cat <<'EOF'
Usage: ./install.sh [--target DIR | --agents | --codex | --claude] [--source DIR]

Options:
  --target DIR  Install into a custom skills directory.
  --agents      Install into ~/.agents/skills (default).
  --codex       Install into ~/.codex/skills.
  --claude      Install into ~/.claude/skills.
  --source DIR  Use a local repository checkout (mainly for testing).
  -h, --help    Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || { echo "Error: --target requires a directory." >&2; exit 2; }
      target_dir="$2"
      shift 2
      ;;
    --agents)
      target_dir="${HOME}/.agents/skills"
      shift
      ;;
    --codex)
      target_dir="${HOME}/.codex/skills"
      shift
      ;;
    --claude)
      target_dir="${HOME}/.claude/skills"
      shift
      ;;
    --source)
      [[ $# -ge 2 ]] || { echo "Error: --source requires a directory." >&2; exit 2; }
      source_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cleanup() {
  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    rm -rf -- "$temp_dir"
  fi
}
trap cleanup EXIT

if [[ -z "$source_dir" ]]; then
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-/dev/null}")" 2>/dev/null && pwd || true)"
  if [[ -n "$script_dir" && -d "$script_dir/skills" ]]; then
    source_dir="$script_dir"
  else
    command -v git >/dev/null 2>&1 || {
      echo "Error: git is required for remote installation." >&2
      exit 1
    }
    temp_dir="$(mktemp -d)"
    git clone --depth 1 "$REPO_URL" "$temp_dir/repo"
    source_dir="$temp_dir/repo"
  fi
fi

[[ -d "$source_dir/skills" ]] || {
  echo "Error: skills directory not found under $source_dir" >&2
  exit 1
}

for skill in "${SKILLS[@]}"; do
  [[ -f "$source_dir/skills/$skill/SKILL.md" ]] || {
    echo "Error: missing skills/$skill/SKILL.md" >&2
    exit 1
  }
done

mkdir -p "$target_dir"
timestamp="$(date '+%Y%m%d-%H%M%S')"
backup_dir="$target_dir/.jobhunting-skill-pack-backups/$timestamp"
backed_up=false

for skill in "${SKILLS[@]}"; do
  destination="$target_dir/$skill"
  if [[ -e "$destination" ]]; then
    mkdir -p "$backup_dir"
    mv -- "$destination" "$backup_dir/$skill"
    backed_up=true
  fi
  cp -R "$source_dir/skills/$skill" "$destination"
  echo "Installed $skill -> $destination"
done

if [[ "$backed_up" == true ]]; then
  echo "Previous versions backed up to $backup_dir"
fi

echo "Jobhunting Skill Pack installed successfully."
