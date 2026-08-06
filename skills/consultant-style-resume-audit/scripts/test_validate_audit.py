#!/usr/bin/env python3
"""Regression tests across candidate tiers and material shapes."""

from validate_audit import DISCLAIMER, REQUIRED, validate


def valid_sample(tier: str, total: str, density: str) -> str:
    sections = list(REQUIRED)
    sections.extend(
        [
            f"- **候选人档次：** {tier}",
            f"- **履历总量：** {total}",
            f"- **单条密度：** {density}",
            "- **分档得分：** 80/100",
            "问题｜工具链与动作｜结果与影响｜可追问 Hook",
            "| 原写法 | 建议写法 |",
            "- **是否建议继续：** 是",
            "- **首批处理范围：** 示例经历",
            "- **首批模式：** final",
            "| 可用事实 | 待确认/禁止补写 |",
            "请使用 cv-experience-refinement 继续处理。",
            "- [ ] 检查",
            DISCLAIMER,
        ]
    )
    return "\n\n".join(sections)


def main() -> int:
    cases = (
        ("起步型", "过少", "单薄"),
        ("起步型", "过少", "丰富"),
        ("成长型", "适中", "混合"),
        ("成长型", "过多", "单薄"),
        ("冲刺型", "过多", "丰富"),
        ("冲刺型", "适中", "丰富"),
    )
    for case in cases:
        assert validate(valid_sample(*case)) == [], case

    assert any("候选人档次" in item for item in validate(valid_sample("未知", "适中", "适中")))
    assert any("最后一行" in item for item in validate(valid_sample(*cases[0]) + "\n尾巴"))
    assert any("缺少章节" in item for item in validate(valid_sample(*cases[0]).replace(REQUIRED[4], "")))
    assert any("首批模式" in item for item in validate(valid_sample(*cases[0]).replace("**首批模式：** final", "**首批模式：** unknown")))
    assert any("可用事实" in item for item in validate(valid_sample(*cases[0]).replace("可用事实", "来源信息")))
    print("OK: six routing cases, refinement handoff, and negative checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
