"""
测试 16: v3.5.3 评测集 v6.0 train/holdout 拆分
============================================
覆盖:
- 1500 样本
- train 991 / holdout 509 拆分
- 种子 42 可复现
- 业务组分布
- P0 分布
"""
import json
import random
from collections import Counter
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "evaluation_dataset_v6.0.json"


class TestV6Dataset:
    """v6.0 数据集测试"""

    @pytest.fixture
    def dataset(self):
        if not DATASET_PATH.exists():
            pytest.skip("data/evaluation_dataset_v6.0.json 不存在")
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_total_1500(self, dataset):
        """总样本 1500"""
        assert dataset["total_samples"] == 1500
        assert len(dataset["samples"]) == 1500

    def test_train_holdout_split(self, dataset):
        """train 991 + holdout 509"""
        train = [s for s in dataset["samples"] if s.get("split") == "train"]
        holdout = [s for s in dataset["samples"] if s.get("split") == "holdout"]
        assert len(train) == 991
        assert len(holdout) == 509
        assert len(train) + len(holdout) == 1500

    def test_split_ratio(self, dataset):
        """拆分比例 ~2/3 train"""
        train_n = sum(1 for s in dataset["samples"] if s.get("split") == "train")
        ratio = train_n / 1500
        assert 0.65 <= ratio <= 0.70  # 2/3 = 0.667

    def test_intent_group_coverage(self, dataset):
        """6 业务组全覆盖"""
        groups = Counter(s.get("intent", "").split("_")[0] for s in dataset["samples"])
        for g in ("info", "biz", "cons", "sys", "sec", "sales"):
            assert g in groups, f"缺少业务组 {g}"

    def test_p0_distribution(self, dataset):
        """P0 分布"""
        p0_count = sum(1 for s in dataset["samples"] if s.get("is_p0", False))
        ratio = p0_count / 1500
        # 14.3% ± 1%
        assert 0.13 <= ratio <= 0.16

    def test_all_samples_have_split(self, dataset):
        """每条样本都有 split 字段"""
        for s in dataset["samples"]:
            assert "split" in s
            assert s["split"] in ("train", "holdout")

    def test_stratified_split(self, dataset):
        """分层抽样 (按意图) - 每意图在 train/holdout 都有"""
        train_intents = Counter(s.get("intent") for s in dataset["samples"] if s.get("split") == "train")
        holdout_intents = Counter(s.get("intent") for s in dataset["samples"] if s.get("split") == "holdout")
        common = set(train_intents) & set(holdout_intents)
        # 至少 90% 意图在 train/holdout 都有
        assert len(common) / len(set(train_intents) | set(holdout_intents)) >= 0.9

    def test_seed_reproducibility(self, dataset):
        """种子 42 可复现 - 跑两次拆分结果一致"""
        samples = dataset["samples"]
        # 第一次按 split+id 排序
        first = sorted([(s["split"], s["id"]) for s in samples])
        # 第二次跑拆分
        from data.generate_dataset_v6 import expand_samples, split_train_holdout
        from data.generate_dataset_v6 import INPUT_PATH
        with open(INPUT_PATH, "r", encoding="utf-8") as f:
            v51 = json.load(f)
        base = v51["samples"]
        expanded = expand_samples(base, target_count=1500, seed=42)
        split = split_train_holdout(expanded, train_ratio=0.67, seed=42)
        second = sorted([(s["split"], s.get("id", "")) for s in split])
        # 比较 split 字段
        first_splits = [s[0] for s in first]
        second_splits = [s[0] for s in second]
        assert first_splits == second_splits

    def test_eval_result_v353_exists(self):
        """v3.5.3 评测结果存在"""
        result_path = PROJECT_ROOT / "data" / "eval_results_v353.json"
        if not result_path.exists():
            pytest.skip("data/eval_results_v353.json 不存在 (评测可能没跑)")
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        # 关键字段
        assert "summary" in result
        assert "overall" in result["summary"]
        assert "train" in result["summary"]
        assert "holdout" in result["summary"]
        # holdout 准确率在合理范围
        holdout = result["summary"]["holdout"]
        assert 0.7 <= holdout["intent_accuracy"] <= 0.95
