#!/usr/bin/env python3
"""Validate the Markdown contract for cv-experience-refinement output.

This script checks structure and length only.  It cannot verify that a claim,
number, method, tool, or result is factually correct.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


DEFAULT_MIN_OVERVIEW = 80
DEFAULT_MIN_THEME = 80
QUALITY_NOTE = "数据、方法论、工具等细节需要自行根据事实修正，不保证绝对正确。"
QUALITY_NOTE_LINE = f"> 注：{QUALITY_NOTE}"

EXPERIENCE_HEADER = re.compile(r"^##\s+\S")
THEME_LINE = re.compile(
    r"^(?P<indent>[ ]{0,3})[-*]\s+\*\*(?P<label>[^*\n:：]+)[：:]\*\*\s*(?P<body>.*)$"
)
OVERVIEW_PREFIX = re.compile(r"^(?:\*\*)?工作概述(?:\*\*)?[：:]\s*")
MISSING_ACTIONS_HEADER = re.compile(r"^###\s+缺失的动作/方面\s*$")
OLD_CONFIRMATION_HEADER = re.compile(r"^###\s+待核验与修改\s*$")
UNRESOLVED_MARKER = re.compile(r"【(?:需核验|待补|待确认)[^】\n]*】")
LIST_ITEM = re.compile(r"^\s*[-*]\s+\S")


class ValidationError(ValueError):
    """Raised when output does not meet the skill contract."""


@dataclass(frozen=True)
class ExperienceBlock:
    heading: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class Theme:
    label: str
    first_sentence: str
    body: str


def _nonempty(lines: Sequence[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip()]


def visible_length(text: str) -> int:
    """Count visible characters while ignoring whitespace and Markdown markers."""
    visible = text.replace("**", "").replace("`", "").replace(">", "")
    return len(re.sub(r"\s+", "", visible))


def split_blocks(text: str) -> list[ExperienceBlock]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    starts = [index for index, line in enumerate(lines) if EXPERIENCE_HEADER.match(line)]
    if not starts:
        raise ValidationError("expected at least one '## [经历标题]' heading")

    prefix = _nonempty(lines[: starts[0]])
    if prefix:
        raise ValidationError("text before the first experience heading is not allowed")

    blocks: list[ExperienceBlock] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        blocks.append(ExperienceBlock(lines[start].strip(), tuple(lines[start + 1 : end])))
    return blocks


def _theme_starts(lines: Sequence[str]) -> list[tuple[int, re.Match[str]]]:
    return [
        (index, match)
        for index, line in enumerate(lines)
        if (match := THEME_LINE.match(line)) is not None
    ]


def _overview(lines: Sequence[str]) -> str:
    starts = _theme_starts(lines)
    end = starts[0][0] if starts else len(lines)
    collected: list[str] = []
    for line in lines[:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or LIST_ITEM.match(line):
            continue
        if stripped == QUALITY_NOTE_LINE:
            continue
        collected.append(OVERVIEW_PREFIX.sub("", stripped))
    return " ".join(collected).strip()


def _themes(lines: Sequence[str]) -> list[Theme]:
    starts = _theme_starts(lines)
    themes: list[Theme] = []
    for position, (start, match) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        continuation: list[str] = []
        for line in lines[start + 1 : end]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or stripped == QUALITY_NOTE_LINE:
                break
            continuation.append(stripped)
        first_sentence = match.group("body").strip()
        body_parts = [first_sentence, *continuation]
        themes.append(
            Theme(
                label=match.group("label").strip(),
                first_sentence=first_sentence,
                body=" ".join(part for part in body_parts if part).strip(),
            )
        )
    return themes


def _missing_action_items(lines: Sequence[str]) -> list[str]:
    for index, line in enumerate(lines):
        if MISSING_ACTIONS_HEADER.match(line.strip()):
            items: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate.strip().startswith("#"):
                    break
                if LIST_ITEM.match(candidate):
                    items.append(candidate.strip())
            return items
    return []


def _has_missing_actions_header(lines: Sequence[str]) -> bool:
    return any(MISSING_ACTIONS_HEADER.match(line.strip()) for line in lines)


def _has_old_confirmation_header(lines: Sequence[str]) -> bool:
    return any(OLD_CONFIRMATION_HEADER.match(line.strip()) for line in lines)


def _validate_complete_block(
    block: ExperienceBlock,
    *,
    source_overview_length: int | None,
) -> None:
    overview = _overview(block.lines)
    if not overview:
        raise ValidationError(f"{block.heading}: missing a prose 工作概述 before themes")
    if "我" in overview or "本人" in overview:
        raise ValidationError(f"{block.heading}: 工作概述 must not use first-person wording")

    required_overview_length = max(
        DEFAULT_MIN_OVERVIEW, source_overview_length or 0
    )
    actual_overview_length = visible_length(overview)
    if actual_overview_length < required_overview_length:
        raise ValidationError(
            f"{block.heading}: 工作概述 has {actual_overview_length} visible characters; "
            f"requires at least {required_overview_length}"
        )

    themes = _themes(block.lines)
    if not 2 <= len(themes) <= 4:
        raise ValidationError(
            f"{block.heading}: expected 2–4 primary themes, found {len(themes)}"
        )

    labels = [theme.label for theme in themes]
    if len({label.casefold() for label in labels}) != len(labels):
        raise ValidationError(f"{block.heading}: primary theme labels must be unique")

    for theme in themes:
        if not theme.first_sentence:
            raise ValidationError(
                f"{block.heading}: theme '{theme.label}' needs a core sentence after its label"
            )
        body_length = visible_length(theme.body)
        if body_length < DEFAULT_MIN_THEME:
            raise ValidationError(
                f"{block.heading}: theme '{theme.label}' has {body_length} visible characters "
                f"after its label; requires at least {DEFAULT_MIN_THEME}"
            )


def validate(
    text: str,
    *,
    mode: str,
    source_overview_lengths: Sequence[int] | None = None,
) -> list[str]:
    """Validate Markdown and return the validated experience headings.

    Modes: ``final`` for fact-checked text, ``enhanced-draft`` for text with
    a single mandatory global quality note, and ``incomplete`` when the source
    lacks enough actions/aspects to write a complete experience.  ``draft`` is
    retained as a compatibility alias for ``enhanced-draft``.
    """
    mode = {"draft": "enhanced-draft"}.get(mode, mode)
    if mode not in {"final", "enhanced-draft", "incomplete"}:
        raise ValueError(f"unknown mode: {mode}")

    blocks = split_blocks(text)
    headings = [block.heading for block in blocks]
    if source_overview_lengths is not None:
        if len(source_overview_lengths) != len(blocks):
            raise ValidationError(
                "--source-overview-lengths must provide one integer for each experience block"
            )
        if any(length < 0 for length in source_overview_lengths):
            raise ValidationError("source overview lengths cannot be negative")

    if mode == "incomplete":
        for block in blocks:
            if not _has_missing_actions_header(block.lines) or not _missing_action_items(block.lines):
                raise ValidationError(
                    f"{block.heading}: incomplete mode requires a ### 缺失的动作/方面 section with list items"
                )
        return headings

    nonempty_lines = _nonempty(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    if mode == "enhanced-draft":
        if not nonempty_lines or nonempty_lines[-1] != QUALITY_NOTE_LINE:
            raise ValidationError(
                "enhanced-draft must end with the exact global data/method/tool revision note"
            )
        if sum(line == QUALITY_NOTE_LINE for line in nonempty_lines) != 1:
            raise ValidationError("enhanced-draft must contain the global revision note exactly once")
    elif QUALITY_NOTE in text:
        raise ValidationError("final output cannot contain the enhanced-draft revision note")

    for index, block in enumerate(blocks):
        if _has_missing_actions_header(block.lines):
            raise ValidationError(f"{block.heading}: complete output cannot include 缺失的动作/方面")
        if _has_old_confirmation_header(block.lines):
            raise ValidationError(f"{block.heading}: use the global revision note instead of 待核验与修改")
        if UNRESOLVED_MARKER.search("\n".join(block.lines)):
            raise ValidationError(f"{block.heading}: complete output cannot contain unresolved placeholders")
        source_length = (
            source_overview_lengths[index] if source_overview_lengths is not None else None
        )
        _validate_complete_block(block, source_overview_length=source_length)

    return headings


def _parse_source_overview_lengths(raw: str | None) -> list[int] | None:
    if raw is None:
        return None
    try:
        values = [int(part.strip()) for part in raw.split(",") if part.strip()]
    except ValueError as error:
        raise ValidationError("source overview lengths must be comma-separated integers") from error
    if not values:
        raise ValidationError("source overview lengths cannot be empty")
    return values


def read_input(path: str | None) -> str:
    if path in (None, "-"):
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate cv-experience-refinement Markdown: experience title, no-first-person "
            "工作概述, 2–4 themes, minimum lengths, and correct output mode."
        )
    )
    parser.add_argument("input", nargs="?", help="UTF-8 Markdown file, or '-' for stdin")
    parser.add_argument(
        "--mode",
        choices=("final", "enhanced-draft", "incomplete", "draft"),
        required=True,
    )
    parser.add_argument(
        "--source-overview-lengths",
        help="comma-separated visible-character counts for source overviews, in experience order",
    )
    args = parser.parse_args()

    try:
        headings = validate(
            read_input(args.input),
            mode=args.mode,
            source_overview_lengths=_parse_source_overview_lengths(args.source_overview_lengths),
        )
    except (OSError, UnicodeError, ValidationError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1

    print(f"VALID: {args.mode} output with {len(headings)} experience block(s)")
    for heading in headings:
        print(heading)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
