#!/usr/bin/env python3
"""Validate the stable structure and routing fields of a resume audit."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED = (
    "# 简历审查报告",
    "## 一句话结论",
    "## 候选人档次与材料形态",
    "## 叙事主线",
    "## P0：先修这些",
    "## P1：决定专业性与匹配度",
    "## 履历容量与编排",
    "## 逐段结构审查",
    "## 行业术语与岗位语言",
    "## 呈现与包装建议",
    "## 接轨 cv-experience-refinement",
    "## 分档专项建议",
    "## P2：下一阶段补强",
    "## 30 秒提交前检查",
)
TIERS = ("起步型", "成长型", "冲刺型")
TOTALS = ("过少", "适中", "过多")
DENSITIES = ("单薄", "适中", "丰富", "混合")
REFINEMENT_MODES = ("final", "enhanced-draft", "incomplete")
DISCLAIMER = "> 结果仅供参考，需要手动修正"


def has_labeled_choice(text: str, label: str, choices: tuple[str, ...]) -> bool:
    return any(f"**{label}：** {choice}" in text for choice in choices)


def validate(text: str) -> list[str]:
    errors: list[str] = []
    for heading in REQUIRED:
        if heading not in text:
            errors.append(f"缺少章节：{heading}")

    positions = [text.find(heading) for heading in REQUIRED]
    found = [position for position in positions if position >= 0]
    if found != sorted(found):
        errors.append("章节顺序不符合模板")

    if not has_labeled_choice(text, "候选人档次", TIERS):
        errors.append("候选人档次必须明确选择起步型、成长型或冲刺型")
    if not has_labeled_choice(text, "履历总量", TOTALS):
        errors.append("履历总量必须明确选择过少、适中或过多")
    if not has_labeled_choice(text, "单条密度", DENSITIES):
        errors.append("单条密度必须明确选择单薄、适中、丰富或混合")
    if "**分档得分：**" not in text:
        errors.append("缺少对应档次量表得分")

    if "问题" not in text or "工具链" not in text or "结果" not in text:
        errors.append("逐段审查必须包含问题、工具链和结果")
    if "可追问 Hook" not in text:
        errors.append("缺少可追问 Hook")
    if "原写法" not in text or "建议写法" not in text:
        errors.append("包装建议必须保留原写法与建议写法")
    if "**是否建议继续：**" not in text:
        errors.append("精修交接包必须说明是否建议继续")
    if "**首批处理范围：**" not in text:
        errors.append("精修交接包必须明确首批处理范围")
    if not has_labeled_choice(text, "首批模式", REFINEMENT_MODES):
        errors.append("首批模式必须明确选择 final、enhanced-draft 或 incomplete")
    if "可用事实" not in text or "待确认/禁止补写" not in text:
        errors.append("精修交接包必须分开可用事实与待确认/禁止补写内容")
    if "请使用 cv-experience-refinement" not in text:
        errors.append("精修交接包必须提供可复制的 cv-experience-refinement 调用语句")
    if "[ ]" not in text and "[x]" not in text.lower():
        errors.append("缺少 30 秒检查项")
    if not text.rstrip().endswith(DISCLAIMER):
        errors.append(f"最后一行必须为：{DISCLAIMER}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    args = parser.parse_args()
    errors = validate(args.audit.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: audit structure and routing are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
