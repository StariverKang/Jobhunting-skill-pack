#!/usr/bin/env python3
"""Validate the strict four-line output contract for this skill."""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path


MAX_VISIBLE_CHARACTERS = 120
MIN_VISIBLE_CHARACTERS = 55
MIN_TOTAL_VISIBLE_CHARACTERS = 280
NUMBERED_LINE = re.compile(
    r"^\s*(?:(?P<plain>[1-4])[.、．)]|[（(](?P<wrapped>[1-4])[）)])\s*(?P<body>.*?)\s*$"
)
FORBIDDEN_PUNCTUATION = {
    ":": "ASCII colon",
    "：": "Chinese colon",
    "—": "em dash",
    "–": "en dash",
}
TRUNCATED_COPYWRITING = re.compile(r"(?i)(?<![A-Za-z])copy(?![A-Za-z])")
REDUNDANT_EDUCATION_INSTITUTION = re.compile(
    r"[\u4e00-\u9fff]{2,24}(?:\u5927\u5b66|\u5b66\u9662)"
    r"(?=[\u4e00-\u9fffA-Za-z0-9]{0,12}(?:\u4e13\u4e1a|\u80cc\u666f|\u672c\u79d1|\u7855\u58eb|\u535a\u58eb))"
)
EXPERIENCE_NARRATION = (
    (re.compile(r"曾(?:在|于|获|任|负责|参与|完成)"), "experience narration"),
    (re.compile(r"(?:荣获|斩获|获得).{0,24}(?:奖|第?[一二三四五六七八九十百\d]+名|Top\s*\d)"), "award narration"),
    (re.compile(r"第[一二三四五六七八九十百\d]+名"), "specific ranking"),
    (re.compile(r"(?i)Top\s*\d+(?:\.\d+)?\s*%"), "specific percentile ranking"),
)
TARGET_LEAKAGE = (
    (re.compile(r"(?:职业)?定位.{0,24}(?:实习|岗位|职位)"), "job-target positioning"),
    (re.compile(r"面向.{0,36}(?:券商|公司|团队|岗位|职位|研究组|业务组|实习)"), "employer or JD framing"),
    (re.compile(r"(?:适配|匹配|契合).{0,20}(?:公司|团队|岗位|职位|JD|需求)"), "explicit fit explanation"),
    (re.compile(r"(?:目标|该)(?:公司|团队|岗位|职位|JD)"), "target-employer reference"),
    (re.compile(r"可将.{0,48}(?:用于|迁移至)"), "future transfer statement"),
    (re.compile(r"(?:快速|尽快)进入.{0,24}(?:场景|岗位|团队|工作)"), "expected-role statement"),
)

# Longest and more specific terms must appear first so that, for example,
# ``Prompt`` is not extracted from ``Prompt Engineering``.
SEMANTIC_TERMS = (
    ("Chain-of-Thought Prompting", "method"),
    ("Top-down/Bottom-up", "method"),
    ("Human-in-the-loop", "quality_mechanism"),
    ("Prompt Engineering", "method"),
    ("Agentic Workflow", "ai_system_pattern"),
    ("Sales Qualified Lead", "business_stage"),
    ("PostgreSQL", "database"),
    ("JavaScript", "programming_language"),
    ("TypeScript", "programming_language"),
    ("A/B Testing", "method"),
    ("检索增强生成", "ai_technology"),
    ("提示词工程", "method"),
    ("Power BI", "software_tool"),
    ("Benchmark", "method"),
    ("FastAPI", "framework"),
    ("Tableau", "software_tool"),
    ("Instagram", "platform"),
    ("Google Ads", "platform"),
    ("Meta Ads", "platform"),
    ("MySQL", "database"),
    ("Python", "programming_language"),
    ("React", "library"),
    ("Prompt", "prompt_artifact"),
    ("提示词", "prompt_artifact"),
    ("Funnel", "method"),
    ("RAG", "ai_technology"),
    ("LLM", "ai_technology"),
    ("NLP", "ai_technology"),
    ("Embedding", "ai_technology"),
    ("Workflow", "ai_system_pattern"),
    ("Agent", "ai_system_pattern"),
    ("CoT", "method"),
    ("AI Skill", "capability_package"),
    ("SQL", "query_language"),
    ("Excel", "software_tool"),
    ("SPSS", "software_tool"),
    ("HITL", "quality_mechanism"),
    ("Evals", "evaluation_method"),
    ("API", "interface"),
    ("TikTok", "platform"),
    ("CTR", "metric"),
    ("CVR", "metric"),
    ("ROAS", "metric"),
    ("ROI", "metric"),
    ("CAC", "metric"),
    ("LTV", "metric"),
)
SEMANTIC_TERM_PATTERN = re.compile(
    "|".join(
        f"(?P<t{index}>{re.escape(term)})"
        for index, (term, _) in enumerate(SEMANTIC_TERMS)
    ),
    re.IGNORECASE,
)
SEMANTIC_CATEGORY_LABELS = {
    "method": "方法",
    "prompt_artifact": "提示词文本",
    "ai_technology": "AI技术",
    "programming_language": "编程语言",
    "query_language": "查询语言",
    "software_tool": "软件工具",
    "framework": "框架",
    "library": "开发库",
    "database": "数据库",
    "quality_mechanism": "质量机制",
    "evaluation_method": "评估方法",
    "interface": "接口",
    "platform": "平台",
    "metric": "指标",
    "business_stage": "业务阶段",
    "ai_system_pattern": "AI系统形态",
    "capability_package": "能力封装",
}
ENUMERATION_CONNECTOR = re.compile(r"\s*(?:、|,|，|/|及|与|和)\s*")
CATCH_ALL_PATTERN = re.compile(
    r"(?P<items>[^。；;，,]{1,120}?)等(?P<label>工具|技术|方法|语言|指标|框架|库|平台|机制|接口|数据库)"
)
CATCH_ALL_CATEGORIES = {
    "工具": {"software_tool"},
    "技术": {"ai_technology"},
    "方法": {"method", "evaluation_method"},
    "语言": {"programming_language", "query_language"},
    "指标": {"metric"},
    "框架": {"framework"},
    "库": {"library"},
    "平台": {"platform"},
    "机制": {"quality_mechanism"},
    "接口": {"interface"},
    "数据库": {"database"},
}


class ValidationError(ValueError):
    """Raised when output violates the skill contract."""


def visible_length(text: str) -> int:
    """Count non-whitespace Unicode code points after NFC normalization."""
    normalized = unicodedata.normalize("NFC", text)
    return sum(not character.isspace() for character in normalized)


def semantic_terms(text: str) -> list[tuple[str, str, int, int]]:
    """Return recognized terms with semantic categories and spans."""
    matches: list[tuple[str, str, int, int]] = []
    for match in SEMANTIC_TERM_PATTERN.finditer(text):
        term_index = int(match.lastgroup[1:])
        _, category = SEMANTIC_TERMS[term_index]
        matches.append((match.group(), category, match.start(), match.end()))
    return matches


def validate_semantic_enumerations(body: str, line_number: int) -> None:
    """Reject lists that flatten methods, technologies, languages, and tools."""
    terms = semantic_terms(body)
    for left, right in zip(terms, terms[1:]):
        connector = body[left[3] : right[2]]
        if ENUMERATION_CONNECTOR.fullmatch(connector) and left[1] != right[1]:
            left_label = SEMANTIC_CATEGORY_LABELS[left[1]]
            right_label = SEMANTIC_CATEGORY_LABELS[right[1]]
            raise ValidationError(
                f"line {line_number} bare-enumerates {left[0]} ({left_label}) and "
                f"{right[0]} ({right_label}); split the categories and give each "
                "an accurate predicate"
            )

    for catch_all in CATCH_ALL_PATTERN.finditer(body):
        label = catch_all.group("label")
        allowed_categories = CATCH_ALL_CATEGORIES[label]
        listed_terms = semantic_terms(catch_all.group("items"))
        for term, category, _, _ in listed_terms:
            if category not in allowed_categories:
                category_label = SEMANTIC_CATEGORY_LABELS[category]
                raise ValidationError(
                    f"line {line_number} classifies {term} ({category_label}) as "
                    f"{label}; use its real semantic category and an accurate action"
                )


def validate(text: str, *, allow_school: bool = False) -> list[tuple[str, int]]:
    """Return normalized bodies and counts, or raise ValidationError."""
    normalized = unicodedata.normalize("NFC", text)
    lines = [line for line in normalized.splitlines() if line.strip()]

    if len(lines) != 4:
        raise ValidationError(f"expected exactly 4 non-empty lines, found {len(lines)}")

    validated: list[tuple[str, int]] = []
    for expected_number, line in enumerate(lines, start=1):
        match = NUMBERED_LINE.fullmatch(line)
        if not match:
            raise ValidationError(
                f"line {expected_number} must start with a supported number marker"
            )

        actual_number = int(match.group("plain") or match.group("wrapped"))
        if actual_number != expected_number:
            raise ValidationError(
                f"line {expected_number} uses number {actual_number}; expected {expected_number}"
            )

        body = match.group("body").strip()
        if not body:
            raise ValidationError(f"line {expected_number} has an empty body")

        for punctuation, label in FORBIDDEN_PUNCTUATION.items():
            if punctuation in body:
                raise ValidationError(
                    f"line {expected_number} contains {label}; "
                    "write the hierarchy as a natural sentence"
                )

        if TRUNCATED_COPYWRITING.search(body):
            raise ValidationError(
                f"line {expected_number} uses truncated 'Copy'; "
                "write '英文文案撰写' or the complete term 'Copywriting'"
            )

        if not allow_school and REDUNDANT_EDUCATION_INSTITUTION.search(body):
            raise ValidationError(
                f"line {expected_number} repeats an education institution; "
                "resume-top summaries should keep only the relevant major or "
                "discipline background"
            )

        for pattern, label in EXPERIENCE_NARRATION:
            if pattern.search(body):
                raise ValidationError(
                    f"line {expected_number} contains {label}; "
                    "summarize the supported ability instead of the specific experience"
                )

        for pattern, label in TARGET_LEAKAGE:
            if pattern.search(body):
                raise ValidationError(
                    f"line {expected_number} contains {label}; "
                    "write the candidate's existing ability and value instead"
                )

        validate_semantic_enumerations(body, expected_number)

        count = visible_length(body)
        if count < MIN_VISIBLE_CHARACTERS:
            raise ValidationError(
                f"line {expected_number} has {count} visible characters; "
                f"minimum is {MIN_VISIBLE_CHARACTERS}"
            )
        if count > MAX_VISIBLE_CHARACTERS:
            raise ValidationError(
                f"line {expected_number} has {count} visible characters; "
                f"maximum is {MAX_VISIBLE_CHARACTERS}"
            )
        validated.append((body, count))

    total_count = sum(count for _, count in validated)
    if total_count < MIN_TOTAL_VISIBLE_CHARACTERS:
        raise ValidationError(
            f"four lines have {total_count} visible characters in total; "
            f"minimum is {MIN_TOTAL_VISIBLE_CHARACTERS}"
        )

    return validated


def read_text(input_path: str | None) -> str:
    if input_path in (None, "-"):
        return sys.stdin.read()
    return Path(input_path).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate four rich, candidate-centered self-summary lines of 55-120 "
            "characters each and at least 280 characters in total, "
            "without colons, dash-based fragments, truncated Copywriting, "
            "specific experience narration, employer/JD framing, or mixed-category "
            "keyword enumeration; education institutions are omitted by default."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="UTF-8 text file to validate; omit or use '-' to read stdin.",
    )
    parser.add_argument(
        "--allow-school",
        action="store_true",
        help=(
            "Allow an education institution for a standalone bio; resume-top "
            "summaries should use the default and omit it."
        ),
    )
    args = parser.parse_args()

    try:
        validated = validate(read_text(args.input), allow_school=args.allow_school)
    except (OSError, UnicodeError, ValidationError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1

    print("VALID")
    for index, (_, count) in enumerate(validated, start=1):
        print(f"{index}: {count}/{MAX_VISIBLE_CHARACTERS}")
    print(f"total: {sum(count for _, count in validated)}/{MIN_TOTAL_VISIBLE_CHARACTERS} minimum")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
