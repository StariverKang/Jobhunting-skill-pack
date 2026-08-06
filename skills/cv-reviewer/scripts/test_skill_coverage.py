#!/usr/bin/env python3
"""Check tier coverage, density routing, lexicon breadth, and source anonymization."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def require(text: str, phrases: tuple[str, ...], label: str) -> None:
    missing = [phrase for phrase in phrases if phrase not in text]
    assert not missing, f"{label} missing: {missing}"


def main() -> int:
    skill = read("SKILL.md")
    routing = read("references/candidate-routing.md")
    method = read("references/methodology.md")
    output = read("references/output-template.md")
    lexicons = "\n".join(
        [
            read("references/lexicon-business.md"),
            read("references/lexicon-product-tech.md"),
            read("references/lexicon-sector.md"),
        ]
    )
    package_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix in {".md", ".py"}
    )

    require(skill + routing, ("起步型", "成长型", "冲刺型"), "candidate tiers")
    require(skill + routing, ("过少 + 单薄", "过少 + 丰富", "过多 + 单薄", "过多 + 丰富", "混合"), "material routing")
    require(method + skill, ("问题", "工具链", "结果", "两层“总—分”", "个性锚点", "可追问 Hook"), "methodology")
    require(
        skill + output,
        (
            "cv-experience-refinement",
            "支柱 / 证明",
            "补充",
            "删除",
            "final",
            "enhanced-draft",
            "incomplete",
            "可用事实",
            "待确认/禁止补写",
            "可复制调用语句",
        ),
        "experience refinement handoff",
    )
    require(
        lexicons,
        (
            "市场、品牌、增长与内容",
            "销售、商务拓展与客户成功",
            "战略、咨询、商业分析与财务",
            "产品管理与产品运营",
            "数据分析、数据科学与实验",
            "AI、机器学习与智能应用",
            "供应链、制造与质量",
            "教育、培训与学习产品",
            "医疗、医药与生命科学",
            "法律、合规、风控与审计",
            "公共部门、公益与国际发展",
        ),
        "industry lexicons",
    )

    forbidden = (
        "Ka" + "ze",
        "ME" + "XC",
        "Ku" + "Coin",
        "LX" + "DAO",
        "TEAM" + "AKING",
        "Jay" + "den",
        "康" + "泓正",
        "wojiao" + "nzj",
    )
    leaked = [marker for marker in forbidden if marker.lower() in package_text.lower()]
    assert not leaked, f"candidate-specific traces found: {leaked}"

    print("OK: tier, density, lexicon, refinement handoff, methodology, and anonymization coverage passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
