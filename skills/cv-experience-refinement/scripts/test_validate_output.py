#!/usr/bin/env python3
"""Regression tests for the cv-experience-refinement output validator."""

from __future__ import annotations

import unittest

from validate_output import QUALITY_NOTE_LINE, ValidationError, validate


GOOD_FINAL = """## 匿名产品项目｜产品运营实习｜2025.01–2025.03

**工作概述：** 参与面向校园成员的协作服务建设，负责从用户反馈整理、需求优先级判断到功能上线沟通的连续工作，围绕降低信息分散和匹配效率不足的问题梳理产品规则、协调试用安排并沉淀后续版本的判断依据，使团队能够在有限资源下持续验证核心场景与用户价值。

- **需求分析与方案设计：** 围绕用户在项目匹配、能力展示和沟通确认中的具体阻碍收集反馈，将零散描述按使用场景、影响范围和实现成本拆分为需求清单，再与设计和开发成员对齐可验收的规则、页面信息与优先级。对存在理解歧义的环节补充说明和试用问题记录，形成可供后续评审、实现和版本取舍复用的材料。
- **上线协同与反馈迭代：** 负责跟进功能从需求确认到试用上线的沟通节奏，提前整理依赖项、异常场景和待确认信息，减少不同成员对范围和交付标准的理解偏差。上线后归集操作路径、用户反馈和问题类型，区分产品机制问题与实现问题并回写待办清单，通过周度复盘支持团队决定下一轮优化顺序与验证重点。
"""


GOOD_ENHANCED_DRAFT = f"""## 匿名内容项目｜内容运营实习｜2025.04–2025.06

**工作概述：** 参与面向目标用户的内容运营与周度排期工作，负责汇总发布表现、整理用户反馈并支持复盘沟通，围绕内容触达、互动变化和后续选题调整建立持续的信息整理节奏，使项目负责人能够基于统一观察口径判断内容方向、资源优先级和下一周期的执行安排，同时减少临时改稿和跨触点口径不一致造成的执行损耗。

- **数据整理与运营复盘：** 负责归集内容发布、互动反馈和阶段性运营信息，先统一内容类型、发布时间和用户反馈等基础维度，再按周识别表现波动与可能影响因素。围绕可复用的指标口径建立整理表、复盘框架和异常记录，向负责人同步需要继续验证的假设与调整建议，并将有效观察沉淀为后续排期、选题和资源分配时可调用的周度材料。
- **内容排期与上线协同：** 根据复盘结论协助调整下周期的选题优先级、素材准备和发布节奏，协调文案、设计或渠道侧的信息确认，避免同一内容在不同触点出现口径不一致或上线遗漏。对临时热点、素材延期和反馈变化保留可追溯的修改记录，使团队能在不打乱整体计划的情况下完成内容替换、风险检查和后续复盘。

{QUALITY_NOTE_LINE}
"""


class ValidateOutputTests(unittest.TestCase):
    def test_accepts_valid_final(self) -> None:
        self.assertEqual(len(validate(GOOD_FINAL, mode="final")), 1)

    def test_accepts_valid_enhanced_draft(self) -> None:
        self.assertEqual(len(validate(GOOD_ENHANCED_DRAFT, mode="enhanced-draft")), 1)

    def test_rejects_missing_summary(self) -> None:
        invalid = """## 匿名项目｜实习生
- **主题一：** 负责整理与沟通，围绕需求确认和信息同步形成基础材料，并在每次讨论后记录问题以支持后续工作安排和团队协作节奏持续优化。
- **主题二：** 负责上线跟进与反馈汇总，将不同来源的问题按场景分类，形成待办事项和复盘说明，帮助相关成员理解优先级与后续处理路径。
"""
        with self.assertRaisesRegex(ValidationError, "missing a prose 工作概述"):
            validate(invalid, mode="final")

    def test_rejects_first_person_and_short_overview(self) -> None:
        invalid = GOOD_FINAL.replace(
            "参与面向校园成员的协作服务建设，负责从用户反馈整理、需求优先级判断到功能上线沟通的连续工作，围绕降低信息分散和匹配效率不足的问题梳理产品规则、协调试用安排并沉淀后续版本的判断依据，使团队能够在有限资源下持续验证核心场景与用户价值。",
            "我负责产品运营。",
        )
        with self.assertRaisesRegex(ValidationError, "must not use first-person"):
            validate(invalid, mode="final")

    def test_rejects_theme_shorter_than_eighty_without_counting_label(self) -> None:
        invalid = GOOD_FINAL.replace(
            "围绕用户在项目匹配、能力展示和沟通确认中的具体阻碍收集反馈，将零散描述按使用场景、影响范围和实现成本拆分为需求清单，再与设计和开发成员对齐可验收的规则、页面信息与优先级。对存在理解歧义的环节补充说明和试用问题记录，形成可供后续评审、实现和版本取舍复用的材料。",
            "整理用户反馈并形成需求清单，支持相关成员确认后续工作安排。",
        )
        with self.assertRaisesRegex(ValidationError, "requires at least 80"):
            validate(invalid, mode="final")

    def test_rejects_theme_count_out_of_range(self) -> None:
        extra_theme = "\n- **额外主题：** 负责补充项目材料与会议记录，围绕参与人员的反馈整理行动项和责任分工，并在后续沟通中持续确认交付节奏、风险事项与待处理问题，形成可供团队复盘的过程资料和协作依据。\n"
        with self.assertRaisesRegex(ValidationError, "expected 2–4 primary themes"):
            validate(GOOD_FINAL + extra_theme * 3, mode="final")

    def test_enforces_longer_source_overview(self) -> None:
        with self.assertRaisesRegex(ValidationError, "requires at least 180"):
            validate(GOOD_FINAL, mode="final", source_overview_lengths=[180])

    def test_rejects_enhanced_draft_without_terminal_note(self) -> None:
        invalid = GOOD_ENHANCED_DRAFT.replace(f"\n{QUALITY_NOTE_LINE}\n", "\n")
        with self.assertRaisesRegex(ValidationError, "must end with the exact global"):
            validate(invalid, mode="enhanced-draft")

    def test_rejects_enhanced_note_in_final(self) -> None:
        with self.assertRaisesRegex(ValidationError, "final output cannot contain"):
            validate(GOOD_ENHANCED_DRAFT, mode="final")

    def test_accepts_incomplete_action_request(self) -> None:
        incomplete = """## 匿名公司｜实习生｜2025.01–2025.03

### 缺失的动作/方面

- 缺少该项目服务的业务、产品、用户或内部团队。
- 缺少持续负责的具体动作、对象、协作边界和交付物。
"""
        self.assertEqual(len(validate(incomplete, mode="incomplete")), 1)

    def test_rejects_incomplete_without_missing_list(self) -> None:
        invalid = """## 匿名公司｜实习生

### 缺失的动作/方面
"""
        with self.assertRaisesRegex(ValidationError, "requires a ### 缺失的动作/方面"):
            validate(invalid, mode="incomplete")


if __name__ == "__main__":
    unittest.main(verbosity=2)
