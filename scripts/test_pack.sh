#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf -- "$test_root"' EXIT

"$repo_root/install.sh" --source "$repo_root" --target "$test_root/skills"

skills=(
  "consultant-style-resume-audit"
  "cv-experience-refinement"
  "bio-for-cv"
)

for skill in "${skills[@]}"; do
  test -f "$test_root/skills/$skill/SKILL.md"
  diff -qr "$repo_root/skills/$skill" "$test_root/skills/$skill"
done

python3 "$repo_root/skills/consultant-style-resume-audit/scripts/test_validate_audit.py"
python3 "$repo_root/skills/consultant-style-resume-audit/scripts/test_skill_coverage.py"
python3 "$repo_root/skills/cv-experience-refinement/scripts/test_validate_output.py"
python3 "$repo_root/skills/bio-for-cv/scripts/test_validate_output.py"

echo "All pack checks passed."
