#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf -- "$test_root"' EXIT

mkdir -p "$test_root/skills/consultant-style-resume-audit"
touch "$test_root/skills/consultant-style-resume-audit/legacy-marker"
"$repo_root/install.sh" --source "$repo_root" --target "$test_root/skills"

skills=(
  "cv-reviewer"
  "cv-experience-refinement"
  "bio-for-cv"
)

for skill in "${skills[@]}"; do
  test -f "$test_root/skills/$skill/SKILL.md"
  diff -qr "$repo_root/skills/$skill" "$test_root/skills/$skill"
done

test ! -e "$test_root/skills/consultant-style-resume-audit"
compgen -G "$test_root/skills/.jobhunting-skill-pack-backups/*/consultant-style-resume-audit/legacy-marker" >/dev/null

python3 "$repo_root/skills/cv-reviewer/scripts/test_validate_audit.py"
python3 "$repo_root/skills/cv-reviewer/scripts/test_skill_coverage.py"
python3 "$repo_root/skills/cv-experience-refinement/scripts/test_validate_output.py"
python3 "$repo_root/skills/bio-for-cv/scripts/test_validate_output.py"

echo "All pack checks passed."
