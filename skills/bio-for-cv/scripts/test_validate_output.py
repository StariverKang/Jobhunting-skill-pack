#!/usr/bin/env python3
"""Regression tests for the self-summary output validator."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from validate_output import ValidationError, validate


SKILL_ROOT = Path(__file__).resolve().parents[1]
LEXICON = (SKILL_ROOT / "references" / "lexicon.md").read_text(encoding="utf-8")
SKILL_TEXT = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
PATTERNS = (SKILL_ROOT / "references" / "patterns.md").read_text(encoding="utf-8")
EXAMPLES = (SKILL_ROOT / "references" / "examples.md").read_text(encoding="utf-8")


VALID_SAMPLE = """\
1. 商业分析背景，熟悉A股、机器人、ESG与TMT领域的研究逻辑，兼具公司分析、行业研究和定量验证能力，能够从基本面、技术路径与经营数据建立系统判断
2. 公司与行业研究能力扎实，能够运用Desk Research、Benchmark和Top-down/Bottom-up搭建框架，完成资料检索、赛道拆解、个股筛选并形成深度报告与估值判断
3. 兼具定量分析与技术理解，能够使用Excel整理财务数据、编写SQL查询并用Python完成回测，理解FastAPI接口开发与React前端组件的基本逻辑，并通过Scenario/Sensitivity检验关键假设、解释科技公司的成长逻辑
4. 长文本研究、英文商业表达与结构化沟通能力突出，能够持续产出市场周报、投资计划书和讨论材料，并通过多源信息交叉验证提炼核心观点、风险因素与后续跟踪重点
"""


class ValidateOutputTests(unittest.TestCase):
    def assert_rejected(self, old: str, new: str, expected_message: str) -> None:
        with self.assertRaisesRegex(ValidationError, expected_message):
            validate(VALID_SAMPLE.replace(old, new))

    def test_accepts_natural_four_line_summary(self) -> None:
        self.assertEqual(len(validate(VALID_SAMPLE)), 4)

    def test_accepts_complete_copywriting_term(self) -> None:
        updated = VALID_SAMPLE.replace("英文商业表达", "英文Copywriting与商业表达")
        self.assertEqual(len(validate(updated)), 4)

    def test_rejects_redundant_university_name(self) -> None:
        self.assert_rejected(
            "商业分析背景",
            "上海财经大学商业分析背景",
            "repeats an education institution",
        )

    def test_accepts_major_background_without_university(self) -> None:
        updated = VALID_SAMPLE.replace("商业分析背景", "金融学背景")
        self.assertEqual(len(validate(updated)), 4)

    def test_allows_university_only_for_explicit_standalone_bio(self) -> None:
        standalone = VALID_SAMPLE.replace("商业分析背景", "上海财经大学商业分析背景")
        self.assertEqual(len(validate(standalone, allow_school=True)), 4)

    def test_rejects_chinese_colon(self) -> None:
        self.assert_rejected("能力扎实，能够", "能力扎实：能够", "Chinese colon")

    def test_rejects_ascii_colon(self) -> None:
        self.assert_rejected("能力扎实，能够", "能力扎实:能够", "ASCII colon")

    def test_rejects_em_dash_fragment(self) -> None:
        self.assert_rejected("公司与行业研究", "内容—KOL链路与英文物料产出", "em dash")

    def test_rejects_en_dash_fragment(self) -> None:
        self.assert_rejected("公司与行业研究", "内容–KOL链路与英文物料产出", "en dash")

    def test_rejects_truncated_copywriting(self) -> None:
        self.assert_rejected("英文商业表达", "英文Copy", "truncated 'Copy'")

    def test_rejects_specific_competition_ranking(self) -> None:
        self.assert_rejected(
            "商业分析背景，熟悉A股、机器人、ESG与TMT领域的研究逻辑，兼具公司分析、行业研究和定量验证能力，能够从基本面、技术路径与经营数据建立系统判断",
            "商业分析本科生，曾在近万人模拟投资赛中获赛区第3名（Top 1%）",
            "experience narration",
        )

    def test_rejects_specific_percentile_ranking(self) -> None:
        self.assert_rejected(
            "商业分析背景，熟悉A股、机器人、ESG与TMT领域的研究逻辑，兼具公司分析、行业研究和定量验证能力，能够从基本面、技术路径与经营数据建立系统判断",
            "商业分析背景，模拟投资赛成绩为Top 1%",
            "specific percentile ranking",
        )

    def test_rejects_job_target_positioning(self) -> None:
        self.assert_rejected(
            "熟悉A股、机器人、ESG与TMT领域的研究逻辑",
            "定位TMT行业研究实习，熟悉A股、机器人与ESG研究逻辑",
            "job-target positioning",
        )

    def test_rejects_employer_team_framing(self) -> None:
        self.assert_rejected(
            "长文本研究、英文商业表达与结构化沟通能力突出",
            "面向中小券商TMT组的覆盖研究，长文本研究与沟通能力突出",
            "employer or JD framing",
        )

    def test_rejects_future_transfer_statement(self) -> None:
        self.assert_rejected(
            "长文本研究、英文商业表达与结构化沟通能力突出",
            "可将投资研究经验用于公司覆盖工作，英文表达与沟通能力突出",
            "future transfer statement",
        )

    def test_rejects_mixed_terms_as_tools(self) -> None:
        self.assert_rejected(
            "能够使用Excel整理财务数据、编写SQL查询并用Python完成回测",
            "熟悉Prompt、RAG、SQL、Python等工具，能够处理用户数据并完成回测",
            "bare-enumerates",
        )

    def test_rejects_bare_mixed_category_enumeration(self) -> None:
        self.assert_rejected(
            "能够使用Excel整理财务数据、编写SQL查询并用Python完成回测",
            "掌握Prompt Engineering、RAG、SQL与Python，能够处理用户数据并完成回测",
            "bare-enumerates",
        )

    def test_rejects_programming_language_as_tool(self) -> None:
        self.assert_rejected(
            "能够使用Excel整理财务数据、编写SQL查询并用Python完成回测",
            "能够使用Excel整理财务数据，熟悉Python等工具并完成回测",
            "classifies Python.*as 工具",
        )

    def test_rejects_ai_technology_as_tool(self) -> None:
        self.assert_rejected(
            "理解FastAPI接口开发与React前端组件的基本逻辑",
            "熟悉RAG等工具的基本使用逻辑，能够完成知识检索与信息处理",
            "classifies RAG.*as 工具",
        )

    def test_rejects_method_and_metric_as_one_idea(self) -> None:
        self.assert_rejected(
            "完成资料检索、赛道拆解、个股筛选",
            "运用Funnel、CTR/CVR思路并完成资料检索、赛道拆解和个股筛选",
            "bare-enumerates Funnel.*CTR",
        )

    def test_rejects_ai_method_flattened_into_technology_list(self) -> None:
        self.assert_rejected(
            "理解FastAPI接口开发与React前端组件的基本逻辑",
            "了解NLP、LLM、RAG、CoT等AI技术原理与推理逻辑",
            "bare-enumerates RAG.*CoT",
        )

    def test_accepts_key_ai_terms_with_category_specific_explanations(self) -> None:
        updated = VALID_SAMPLE.replace(
            "兼具定量分析与技术理解，能够使用Excel整理财务数据、编写SQL查询并用Python完成回测，理解FastAPI接口开发与React前端组件的基本逻辑，并通过Scenario/Sensitivity检验关键假设、解释科技公司的成长逻辑",
            "兼具AI理解与场景判断，了解NLP、LLM与RAG等技术原理，熟悉CoT等推理方法，具备Agent/Workflow的基础设计能力，能够对应用场景、输入质量和能力边界形成清晰判断",
        )
        self.assertEqual(len(validate(updated)), 4)

    def test_rejects_framework_and_library_as_tools(self) -> None:
        self.assert_rejected(
            "理解FastAPI接口开发与React前端组件的基本逻辑",
            "熟悉FastAPI、React等工具的基本使用逻辑",
            "bare-enumerates|classifies FastAPI",
        )

    def test_accepts_category_accurate_ai_sentence(self) -> None:
        updated = VALID_SAMPLE.replace(
            "能够使用Excel整理财务数据、编写SQL查询并用Python完成回测，理解FastAPI接口开发与React前端组件的基本逻辑",
            "掌握Prompt Engineering，理解RAG的检索增强机制，能够编写SQL查询并用Python处理数据",
        )
        self.assertEqual(len(validate(updated)), 4)

    def test_accepts_same_category_software_tools(self) -> None:
        updated = VALID_SAMPLE.replace(
            "能够使用Excel整理财务数据、编写SQL查询并用Python完成回测，理解FastAPI接口开发与React前端组件的基本逻辑",
            "能够使用Excel、SPSS等工具整理并检验财务数据，编写SQL查询并用Python完成回测",
        )
        self.assertEqual(len(validate(updated)), 4)

    def test_accepts_same_category_metrics(self) -> None:
        updated = VALID_SAMPLE.replace(
            "完成资料检索、赛道拆解、个股筛选",
            "追踪CTR、CVR等指标并完成资料检索、赛道拆解和个股筛选",
        )
        self.assertEqual(len(validate(updated)), 4)

    def test_rejects_hollow_conversion_triad(self) -> None:
        self.assert_rejected(
            "完成资料检索、赛道拆解、个股筛选并形成深度报告与估值判断",
            "把问题转化为需求清单、体验优化建议和可执行运营动作，并完成资料检索",
            "hollow conversion phrasing",
        )

    def test_rejects_slippage_without_price_mechanism(self) -> None:
        self.assert_rejected(
            "完成资料检索、赛道拆解、个股筛选并形成深度报告与估值判断",
            "围绕TVL、交易量与流动性深度观察协议表现，结合滑点解释成交质量差异",
            "滑点/Slippage without a mechanism",
        )

    def test_accepts_plain_language_liquidity_mechanism(self) -> None:
        updated = VALID_SAMPLE.replace(
            "完成资料检索、赛道拆解、个股筛选并形成深度报告与估值判断",
            "围绕TVL、交易量与流动性深度判断盘口是否足够厚、大额买卖会否明显扰动价格",
        )
        self.assertEqual(len(validate(updated)), 4)

    def test_accepts_slippage_after_stated_mechanism(self) -> None:
        updated = VALID_SAMPLE.replace(
            "完成资料检索、赛道拆解、个股筛选并形成深度报告与估值判断",
            "判断盘口厚薄和大额买卖会否扰动价格，即滑点风险，并撰写竞品分析报告",
        )
        self.assertEqual(len(validate(updated)), 4)

    def test_accepts_object_preserving_conversion(self) -> None:
        updated = VALID_SAMPLE.replace(
            "完成资料检索、赛道拆解、个股筛选并形成深度报告与估值判断",
            "把文案歧义、入口错位和奖励路径中断还原到具体步骤，形成可验收的反馈清单",
        )
        self.assertEqual(len(validate(updated)), 4)

    def test_accepts_specific_content_conversion(self) -> None:
        updated = VALID_SAMPLE.replace(
            "完成资料检索、赛道拆解、个股筛选并形成深度报告与估值判断",
            "能够捕捉平台热点与用户情绪，将信号转化为选题、内容钩子和传播节奏",
        )
        self.assertEqual(len(validate(updated)), 4)

    def test_accepts_ave_dex_revised_summary(self) -> None:
        revised = """\
1. 传播学背景，熟悉Web3钱包与CEX场景中的内容运营、社区触达与链上活动增长，兼具竞品研究和用户洞察，网感好，能够捕捉市场热点、上币叙事和社群情绪，并理解链上用户的参与动机。
2. 行业研究能力扎实，能够运用Desk Research与Benchmark对比竞品的交易路径、增长动作和转化表现，并可围绕TVL、交易量与流动性深度判断盘口是否足够厚、大额买卖会否明显扰动价格，撰写竞品分析报告。
3. 用户sense较好，善于从VOC、User Journey、社群反馈和路径阻塞定位真实卡点，能够推进KOL筛选并开展Telegram与X宣发，把文案歧义、入口错位和奖励路径中断还原到具体步骤，形成可验收的反馈清单。
4. 闭环意识强，能够串联活动规则配置、渠道宣发、合作推进与反馈归纳，围绕Listing、Airdrop与Quest组织触达和转化，追踪CTR、CVR与链上活跃，沉淀SOP与复盘结论。
"""
        self.assertEqual(len(validate(revised)), 4)
        self.assert_rejected(
            "商业分析背景，熟悉A股、机器人、ESG与TMT领域的研究逻辑，兼具公司分析、行业研究和定量验证能力，能够从基本面、技术路径与经营数据建立系统判断",
            "商业分析背景，具备行业研究能力",
            "minimum is 70",
        )

    def test_accepts_lines_at_the_seventy_character_floor(self) -> None:
        floor = """\
1. 商业分析背景，熟悉科技行业与资本市场研究逻辑，兼具公司分析、行业研究、财务理解和数据验证能力，并能从业务、数据与竞争格局形成可复核的研究判断
2. 研究能力扎实，能够完成资料检索、行业拆解、公司分析、数据整理、观点提炼和结构化报告撰写，并输出明确的后续跟踪重点、风险提示、分歧来源与下一步动作
3. 兼具技术理解与定量分析能力，能够编写SQL查询并用Python处理业务数据，检验关键假设、解释模型结果和技术产品的成长逻辑，并说明假设变化如何影响结论
4. 英文表达和沟通能力较强，能够撰写研究材料、整理会议信息、协同相关方并持续跟踪关键问题、结论变化、风险事项及沟通重点，沉淀会议纪要、待办事项与沟通口径
"""
        validated = validate(floor)
        self.assertEqual(len(validated), 4)
        self.assertTrue(all(count >= 70 for _, count in validated))

    def test_lexicon_keeps_broad_role_and_industry_coverage(self) -> None:
        required_sections = (
            "项目管理、PMO 与战略推进黑话库",
            "产品经理、产品运营与用户研究黑话库",
            "互联网、泛互联网与增长黑话库",
            "市场、品牌、整合营销与公关黑话库",
            "快消、零售、渠道与品类管理黑话库",
            "销售、商务拓展、大客户与客户成功黑话库",
            "供应链、采购、计划与履约黑话库",
            "战略咨询、商业分析与经营管理黑话库",
            "经金商科、投研与财会黑话库",
            "HR、人才获取、猎头与组织发展黑话库",
            "创业者、新业务与公司经营黑话库",
            "数据分析、商业智能与分析工程黑话库",
            "AI、数据与技术黑话库",
            "Web3 与数字资产黑话库",
        )
        for section in required_sections:
            self.assertIn(f"## {section}", LEXICON)

    def test_lexicon_keeps_representative_term_variety(self) -> None:
        representative_terms = (
            "Critical Path",
            "Opportunity Solution Tree",
            "Incrementality",
            "Brand Lift",
            "Numeric/Weighted Distribution",
            "MEDDICC",
            "OTIF",
            "Issue Tree",
            "Quality of Earnings",
            "Time-to-Hire",
            "Founder-Market Fit",
            "Data Lineage",
            "Groundedness",
            "Account Abstraction",
        )
        for term in representative_terms:
            self.assertIn(term, LEXICON)

    def test_lexicon_keeps_rotation_and_disambiguation_rules(self) -> None:
        self.assertIn("不固定复用列表最前面的词", LEXICON)
        self.assertIn("不要三类岗位都回到 Funnel、CTR 和 Benchmark", LEXICON)
        self.assertIn("编写 SQL 查询", LEXICON)
        self.assertIn("推进销售合格线索", LEXICON)

    def test_skill_keeps_human_recruiter_language_alongside_jargon(self) -> None:
        for phrase in (
            "网感好",
            "产品sense",
            "用户sense",
            "兼具业务视角、用户视角与产品视角",
            "商业化意识",
            "闭环意识",
        ):
            self.assertIn(phrase, LEXICON)
        self.assertIn("5–9 个专业锚点", SKILL_TEXT)
        self.assertIn("关键行业术语的列举和说明是必须项", SKILL_TEXT)
        self.assertIn("不得为凑这项再引入未承接的新术语", SKILL_TEXT)
        self.assertIn("任务链", SKILL_TEXT)
        self.assertIn("至少一条用 2–4 个同类关键词", PATTERNS)
        self.assertIn("自然能力语言", PATTERNS)
        self.assertIn("可观察问题类型", PATTERNS)

    def test_calibration_examples_pass_validator(self) -> None:
        blocks = re.findall(r"```text\n(.*?)\n```", EXAMPLES, re.DOTALL)
        self.assertGreaterEqual(len(blocks), 7)
        for block in blocks:
            self.assertEqual(len(validate(block)), 4)


if __name__ == "__main__":
    unittest.main()
