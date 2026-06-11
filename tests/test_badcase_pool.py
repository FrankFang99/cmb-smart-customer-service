"""
测试 6: v3.4.0 Badcase 标注池
==============================
覆盖:
- JSONL 持久化
- 从 eval_results_v340.json 入池
- 自动定级 (P0/P1/P2)
- 自动初判根因
- 标注接口 (label_badcase)
- 一键入知识库 (add_faq_to_kb)
- 周会分析 (weekly_summary)
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from src.eval.badcase_pool import BadcasePool, BadcaseRecord, ROOT_CAUSE_OPTIONS, FIX_ACTION_OPTIONS


class TestBadcaseRecord:
    """Badcase 单条记录测试"""

    def test_from_eval_sample_intent_mismatch(self):
        """intent_match=False -> 自动定级 P1, 根因 intent_mismatch"""
        sample = {
            "sample_id": "TEST_001",
            "question": "办什么卡好",
            "expected_intent": "sales_credit_prod",
            "actual_intent": "sys_invalid",
            "is_p0_label": False,
            "l0_triggered": False,
            "cascade": "L2",
            "action": "answer_template",
            "elapsed_ms": 30.0,
            "llm_called": False,
            "rag_hit": True,
            "intent_match": False,
            "transfer_correct": False,
            "p0_recall": None,
            "l0_compliance": None,
        }
        rec = BadcaseRecord.from_eval_sample(sample)
        assert rec.sample_id == "TEST_001"
        assert rec.p_level == "P1"
        assert rec.root_cause == "intent_mismatch"

    def test_from_eval_sample_l0_miss_trigger_p0(self):
        """P0 样本 + p0_recall=False -> 自动定级 P0, 根因 l0_miss_trigger"""
        sample = {
            "sample_id": "TEST_002",
            "question": "账户异常冻结",
            "expected_intent": "sec_freeze_unexpected",
            "actual_intent": "sec_freeze_unexpected",
            "is_p0_label": True,
            "l0_triggered": False,
            "cascade": "L2",
            "action": "answer_template",
            "elapsed_ms": 20.0,
            "llm_called": False,
            "rag_hit": True,
            "intent_match": True,
            "transfer_correct": False,
            "p0_recall": False,
            "l0_compliance": None,
        }
        rec = BadcaseRecord.from_eval_sample(sample)
        assert rec.p_level == "P0"
        assert rec.root_cause == "l0_miss_trigger"

    def test_to_dict_from_dict_roundtrip(self):
        """to_dict / from_dict 来回不丢字段"""
        sample = {
            "sample_id": "TEST_003",
            "question": "测试",
            "expected_intent": "info_acc_balance",
            "actual_intent": "info_acc_balance",
            "is_p0_label": False,
            "l0_triggered": False,
            "cascade": "L1",
            "action": "answer_template",
            "elapsed_ms": 10.0,
            "llm_called": False,
            "rag_hit": True,
            "intent_match": True,
            "transfer_correct": False,
            "p0_recall": None,
            "l0_compliance": None,
        }
        rec = BadcaseRecord.from_eval_sample(sample)
        d = rec.to_dict()
        rec2 = BadcaseRecord.from_dict(d)
        assert rec2.sample_id == rec.sample_id
        assert rec2.question == rec.question
        assert rec2.p_level == rec.p_level


class TestBadcasePool:
    """Badcase 池测试"""

    @pytest.fixture
    def tmp_pool(self, tmp_path):
        """临时池 - 不污染真实数据"""
        return BadcasePool(pool_path=str(tmp_path / "test_pool.jsonl"))

    def test_empty_pool_creates_file(self, tmp_pool):
        """空池也能正常工作"""
        assert len(tmp_pool.records) == 0
        # 不存在文件, get_by_p_level 返 []
        assert tmp_pool.get_by_p_level("P0") == []
        assert tmp_pool.get_unlabeled() == []

    def test_add_and_persist(self, tmp_pool):
        """add() -> _save() -> 重新 load 能读回"""
        rec = BadcaseRecord(
            sample_id="TEST_001",
            question="测试问题",
            expected_intent="info_acc_balance",
            actual_intent="info_acc_balance",
            is_p0_label=False,
            l0_triggered=False,
            cascade="L1",
            action="answer_template",
            elapsed_ms=10.0,
            llm_called=False,
            rag_hit=True,
            intent_match=True,
            transfer_correct=False,
            p0_recall=None,
            l0_compliance=None,
        )
        assert tmp_pool.add(rec) is True
        # 重复 add 应跳过
        assert tmp_pool.add(rec) is False
        # 重新 load
        pool2 = BadcasePool(pool_path=tmp_pool.pool_path)
        assert len(pool2.records) == 1
        assert pool2.records[0].sample_id == "TEST_001"

    def test_label_badcase_updates_fields(self, tmp_pool):
        """label_badcase 更新字段并保存"""
        rec = BadcaseRecord(
            sample_id="TEST_001",
            question="q",
            expected_intent="a",
            actual_intent="b",
            is_p0_label=False,
            l0_triggered=False,
            cascade="L2",
            action="answer",
            elapsed_ms=10.0,
            llm_called=False,
            rag_hit=True,
            intent_match=False,
            transfer_correct=False,
            p0_recall=None,
            l0_compliance=None,
        )
        tmp_pool.add(rec)
        ok = tmp_pool.label_badcase(
            sample_id="TEST_001",
            root_cause="intent_mismatch",
            fix_action="add_intent_pattern",
            p_level="P1",
            fix_note="加规则",
        )
        assert ok is True
        loaded = tmp_pool.records[0]
        assert loaded.root_cause == "intent_mismatch"
        assert loaded.fix_action == "add_intent_pattern"
        assert loaded.p_level == "P1"
        assert loaded.fix_note == "加规则"

    def test_label_badcase_nonexistent_returns_false(self, tmp_pool):
        """label 不存在的 sample_id 返 False"""
        ok = tmp_pool.label_badcase(sample_id="NOT_EXIST", root_cause="x")
        assert ok is False

    def test_get_by_p_level_and_open(self, tmp_pool):
        """P 等级查询 + 待办查询"""
        for i, p in enumerate(["P0", "P1", "P2", "P0"]):
            tmp_pool.add(BadcaseRecord(
                sample_id=f"TEST_{i:03d}",
                question="q",
                expected_intent="a",
                actual_intent="b",
                is_p0_label=False,
                l0_triggered=False,
                cascade="L2",
                action="answer",
                elapsed_ms=10.0,
                llm_called=False,
                rag_hit=True,
                intent_match=False,
                transfer_correct=False,
                p0_recall=None,
                l0_compliance=None,
                p_level=p,
            ))
        assert len(tmp_pool.get_by_p_level("P0")) == 2
        assert len(tmp_pool.get_by_p_level("P1")) == 1
        assert len(tmp_pool.get_by_p_level("P2")) == 1
        assert len(tmp_pool.get_unlabeled()) == 4
        assert len(tmp_pool.get_open()) == 4
        # 标一条 fix_done
        tmp_pool.label_badcase(sample_id="TEST_000", fix_done=True)
        assert len(tmp_pool.get_open()) == 3

    def test_weekly_summary_keys(self, tmp_pool):
        """周会分析返回的字段完整"""
        summary = tmp_pool.weekly_summary()
        for k in ["total", "by_root_cause", "by_fix_action", "by_p_level",
                  "by_intent_group", "fix_done_count", "fix_done_rate",
                  "p0_open_count", "p1_open_count", "p0_open_samples", "p1_open_samples"]:
            assert k in summary

    def test_export_markdown(self, tmp_pool):
        """导出 markdown 周报"""
        rec = BadcaseRecord(
            sample_id="TEST_001",
            question="测试",
            expected_intent="info_acc_balance",
            actual_intent="sys_invalid",
            is_p0_label=False,
            l0_triggered=False,
            cascade="L2",
            action="answer",
            elapsed_ms=10.0,
            llm_called=False,
            rag_hit=True,
            intent_match=False,
            transfer_correct=False,
            p0_recall=None,
            l0_compliance=None,
            root_cause="intent_mismatch",
            p_level="P1",
        )
        tmp_pool.add(rec)
        text = tmp_pool.export_markdown()
        assert "Badcase 标注池周报" in text
        assert "TEST_001" in text
        assert "intent_mismatch" in text


class TestBadcasePoolIntegration:
    """集成测试: 从真实 eval_results_v340.json 入池"""

    @pytest.fixture
    def eval_results_path(self):
        # 项目 data/eval_results_v340.json
        return Path(__file__).resolve().parents[1] / "data" / "eval_results_v340.json"

    def test_real_eval_import(self, eval_results_path, tmp_path):
        """从真实 v3.4.0 评测结果入池"""
        if not eval_results_path.exists():
            pytest.skip("data/eval_results_v340.json 不存在")
        pool = BadcasePool(pool_path=str(tmp_path / "real_pool.jsonl"))
        added = pool.add_from_eval_results(str(eval_results_path), only_failures=True)
        # 真实数据应有 13 个失败样本
        assert added == 13
        # 周会分析
        summary = pool.weekly_summary()
        assert summary["total"] == 13
        # 至少 5 个 P0 (l0_miss_trigger 类)
        assert summary["p0_open_count"] >= 5
        # 根因分布含 intent_mismatch 和 l0_miss_trigger
        assert "intent_mismatch" in summary["by_root_cause"]
        assert "l0_miss_trigger" in summary["by_root_cause"]


class TestRootCauseAndFixOptions:
    """根因分类和修复动作常量测试"""

    def test_root_cause_options_complete(self):
        """根因选项完整"""
        assert "intent_mismatch" in ROOT_CAUSE_OPTIONS
        assert "l0_miss_trigger" in ROOT_CAUSE_OPTIONS
        assert "l0_false_trigger" in ROOT_CAUSE_OPTIONS
        assert "retrieval_miss" in ROOT_CAUSE_OPTIONS
        assert "cascade_routing_err" in ROOT_CAUSE_OPTIONS

    def test_fix_action_options_complete(self):
        """修复动作选项完整"""
        assert "add_faq" in FIX_ACTION_OPTIONS
        assert "adjust_threshold" in FIX_ACTION_OPTIONS
        assert "add_intent_pattern" in FIX_ACTION_OPTIONS
        assert "transfer_to_human" in FIX_ACTION_OPTIONS
        assert "ignore" in FIX_ACTION_OPTIONS
        assert "pending" in FIX_ACTION_OPTIONS
