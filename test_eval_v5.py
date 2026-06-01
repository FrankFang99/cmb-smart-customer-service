"""测试评测引擎 v5.0"""
import json
from src.eval.eval_runner_v5 import EvaluationEngine, EvalConfig, EvalReportGenerator

# 加载数据集
with open('data/evaluation_dataset_v5.0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples'][:20]  # 取20个样本测试

print(f"数据集: {data['dataset_version']}")
print(f"总样本: {data['total_samples']}, 多意图样本: {data.get('multi_intent_count', 0)}")
print(f"测试样本数: {len(samples)}")
print()

# 创建模拟Agent
class MockAgent:
    def process(self, question, context):
        return {
            "intent": "info_bill_amount",
            "answer": "您可以登录招商银行App查询账单金额",
            "confidence": 0.9,
            "latency_ms": 50
        }

# 运行评测
config = EvalConfig(max_samples=20)
engine = EvaluationEngine(config, MockAgent(), samples)
results = engine.run()

# 打印摘要
EvalReportGenerator.print_summary(results)

print()
print("测试完成!")